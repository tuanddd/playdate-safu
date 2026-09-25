# safu-scores

Online scoreboard for Safu. A single Cloudflare Worker (`src/worker.js`) backed by one KV namespace. No framework, no runtime dependencies. `wrangler` is the only dev dependency.

## API

Request headers:

| header          | rule                                                                                                   |
|-----------------|--------------------------------------------------------------------------------------------------------|
| `X-Safu-Client` | must be `1` on every request, otherwise `403`. This is not security, it only filters out random scanners. |
| `X-Safu-Player` | the caller's own device id (16 lowercase hex). Optional. If present it must be well-formed, otherwise `400`. On POST it must equal the body `id`, otherwise `400`. |

All responses are `Content-Type: application/json` with an exact `Content-Length` and `Cache-Control: no-store, no-transform` (`no-transform` tells Cloudflare not to re-compress the body, which would replace `Content-Length` with chunked encoding).

Player ids are never returned in responses.

### `GET /scores`

```json
{
  "streak": [
    { "name": "BOB", "score": 25 },
    { "name": "NEKO", "score": 12, "me": true }
  ],
  "lifetime": [
    { "name": "P9", "score": 109 },
    { "name": "P8", "score": 108 }
  ],
  "updated": 1790316817,
  "you": { "lifetime": { "rank": 11, "score": 41 } }
}
```

- `streak`: top 10 by best streak. `lifetime`: top 10 by total safes cracked.
- Both lists are sorted by score, highest first. On a tie, whoever reached that score first ranks higher.
- Rows have only `name` and `score`. `"me": true` is added to the rows that belong to the caller, and is absent on every other row.
- `you` appears only when the caller is ranked 11th to 50th in a list. It then holds `streak` and/or `lifetime`, each `{"rank": N, "score": S}`, for just the lists where that is true. It is omitted entirely when the caller is in the top 10 of both lists, not ranked, below 50th, or unknown.
- The caller is the `X-Safu-Player` id on GET (no header means no `me` and no `you`), and the body `id` on POST.
- `updated` is the unix time in seconds of the last change to the board. It is `0` while the board is empty.
- Players with a score of `0` are not listed in that list.
- A full board is about 600 bytes.

### `POST /scores`

Request body:

```json
{ "id": "aaaaaaaaaaaaaaa1", "name": "neko", "best": 12, "lifetime": 40 }
```

| field      | rule                                                                                 |
|------------|--------------------------------------------------------------------------------------|
| `id`       | exactly 16 lowercase hex characters (`[0-9a-f]{16}`)                                 |
| `name`     | trimmed, then 1 to 10 chars of `A-Z a-z 0-9 space . - _`, then stored uppercased     |
| `best`     | JSON integer, 0 to 99999                                                             |
| `lifetime` | JSON integer, 0 to 99999, and `best` must not be greater than `lifetime`             |

The server merges with what it already has for that id: stored best = max(old, new), stored lifetime = max(old, new), and the name is replaced by the new one. It responds `200` with the same body as `GET /scores`, already including the change, so the game needs only one request.

Errors all have the shape `{"error":"<message>"}`:

| status | when                                                             |
|--------|------------------------------------------------------------------|
| 400    | invalid JSON, body over 1 KB, any field rule above broken, malformed `X-Safu-Player`, or `X-Safu-Player` different from the body `id` |
| 403    | missing or wrong `X-Safu-Client` header                          |
| 404    | any other path or method                                         |
| 429    | more than one POST for the same id within 5 seconds              |
| 500    | storage failure (for example the daily KV write quota ran out)   |

### Storage layout

- `p:<id>` holds `{"name","best","lifetime","ts"}` for each player. `ts` is the last accepted write, in milliseconds, used for the rate limit.
- `board` holds `{"updated","streak":[...],"lifetime":[...]}`. Each list keeps up to 50 entries `{id,name,score,ts}` internally and the API shows the top 10. On each POST the player's entry is replaced, the list is sorted and trimmed. The board is only written when it actually changes.

## Deploying for the first time

You need Node.js 22 or newer (`node --version`) and a free Cloudflare account. Nothing needs a credit card.

1. **Create a Cloudflare account** at https://dash.cloudflare.com/sign-up and verify your email address.

2. **Install the tools.** From the repo root:

   ```sh
   cd server
   npm install
   ```

3. **Log in.** This opens your browser. Click "Allow" on the Cloudflare page and return to the terminal.

   ```sh
   npx wrangler login
   ```

   `npx wrangler whoami` shows which account you are logged into.

4. **Create the KV namespace** that stores the scores:

   ```sh
   npx wrangler kv namespace create SCORES
   ```

   The output ends with a snippet like:

   ```
   [[kv_namespaces]]
   binding = "SCORES"
   id = "3f1c0e9a7b2d4c6e8f0a1b2c3d4e5f60"
   ```

   Copy that `id` value into `wrangler.toml`, replacing `REPLACE_WITH_YOUR_KV_NAMESPACE_ID`. Do not add a second `[[kv_namespaces]]` block, just change the id line.

5. **Deploy:**

   ```sh
   npx wrangler deploy
   ```

   On the very first deploy Wrangler may ask you to pick a `workers.dev` subdomain for your account. Choose any free name, for example `vincent`. When it finishes it prints the live URL:

   ```
   https://safu-scores.<your-subdomain>.workers.dev
   ```

   You can find it again later in the Cloudflare dashboard: **Workers & Pages** in the left menu, then click **safu-scores**. The URL is listed under **Domains & Routes** on its **Settings** tab. Your account's subdomain is also shown on the **Workers & Pages** overview page.

6. **Check it works:**

   ```sh
   curl -H 'X-Safu-Client: 1' https://safu-scores.<your-subdomain>.workers.dev/scores
   ```

   A fresh install answers `{"streak":[],"lifetime":[],"updated":0}`.

To ship a change to `src/worker.js` later, run `npx wrangler deploy` again. The URL stays the same.

## Calling it from the game

Host `safu-scores.<your-subdomain>.workers.dev`, port `443`, HTTPS. Send the headers `X-Safu-Client: 1`, `X-Safu-Player: <own id>` and, on POST, `Content-Type: application/json`. Read the whole body and pass it to `json.decode`. Highlight rows with `me == true`, and use `you.streak` / `you.lifetime` (when present) to show "#14 · 3" under a list.

## Managing the board

Wrangler's `kv` commands work on local test data unless you add `--remote`. Always pass `--remote` for the live board. Run these from `server/`.

Look at the stored board:

```sh
npx wrangler kv key get board --binding SCORES --remote
```

**Reset the board.** This clears the lists. Player records remain, so each player reappears with their stored best and lifetime the next time their game posts:

```sh
npx wrangler kv key delete board --binding SCORES --remote
```

**Full wipe.** This also deletes every player record, so everyone starts from whatever their device sends next:

```sh
npx wrangler kv key list --binding SCORES --remote --prefix p: > players.json
npx wrangler kv bulk delete players.json --binding SCORES --remote --force
npx wrangler kv key delete board --binding SCORES --remote
rm players.json
```

**Remove one cheater.** Delete their record, then take their entries out of the board by hand:

```sh
npx wrangler kv key delete p:<id> --binding SCORES --remote
npx wrangler kv key get board --binding SCORES --remote > board.json
npx wrangler kv key put board --path board.json --binding SCORES --remote
rm board.json
```

Between the `get` and the `put`, edit `board.json` and remove that id's objects from both `streak` and `lifetime`. Their device still holds its local scores and will post them again. If that is a problem, change the id check in `src/worker.js` to block that id.

## Local development

```sh
npm run dev
npm test
```

`npm run dev` serves the worker at `http://127.0.0.1:8787` using a local simulated KV stored in `.wrangler/state`. No Cloudflare login is needed.

`npm test` (which runs `test.sh`) starts its own `wrangler dev --local` on port 8787 with a fresh, empty temporary KV. It runs the curl checks and then stops the server. Port 8787 must be free. Use `PORT=8899 npm test` to pick another port.

## Honest limits

- **No anti-cheat.** The server only validates the shape and range of what it receives. The header value and the request format are visible to anyone who inspects the game or its traffic. A determined player can post any score up to 99999. Ids are self-assigned and are never returned by the API. A random 16-hex id cannot be guessed, but anyone who learns someone's id (for example by reading their device data) can post under it. Scores can only go up, but the name can be changed that way. Treat the board as for fun only. Moderation is manual (see "Remove one cheater"). There is no profanity filter on names.
- **KV free tier.** Workers KV allows 100,000 reads, 1,000 writes, 1,000 deletes and 1,000 lists per day, plus 1 GB of storage. The Workers free plan allows 100,000 requests per day. These were the numbers at the time of writing, so check Cloudflare's pricing page. Each accepted POST costs 1 write (the player record), or 2 when the board changes. The live board therefore handles roughly 500 to 1,000 score submissions per day. After that, POSTs return `500` until the quota resets at 00:00 UTC. GETs keep working. The $5/month Workers Paid plan raises the limits to millions.
- **Eventual consistency.** KV can take up to about 60 seconds to show a change at other Cloudflare locations. Two players posting at almost the same moment can overwrite each other's board update, because the last write wins. The player record still holds the correct max, and the entry comes back on that player's next POST. The 5-second rate limit is also best-effort for the same reason.
- **One write per second per key.** KV rejects rapid writes to the same key. During a burst of simultaneous POSTs, some may fail with `500` on the `board` key. The game should treat any non-200 as "try again later".
