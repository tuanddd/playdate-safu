#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"

PORT="${PORT:-8787}"
BASE="${SAFU_URL:-http://127.0.0.1:$PORT}"
WORK="$(mktemp -d)"
SERVER_PID=""
PASS=0
FAIL=0
STATUS=""
BODY=""

A=aaaaaaaaaaaaaaa1
B=bbbbbbbbbbbbbbb2
C=0000000000000ccc
D=dddddddddddddddd
Z=fffffffffffffff0
Q=9999999999999999

cleanup() {
  if [ -n "$SERVER_PID" ]; then
    kill -- "-$SERVER_PID" 2>/dev/null || kill "$SERVER_PID" 2>/dev/null
    wait "$SERVER_PID" 2>/dev/null
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT

start_server() {
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then
    echo "port $PORT is already in use; stop that server or run with PORT=<free port>" >&2
    exit 1
  fi
  set -m
  WRANGLER_SEND_METRICS=false ./node_modules/.bin/wrangler dev --local --ip 127.0.0.1 --port "$PORT" \
    --persist-to "$WORK/state" >"$WORK/wrangler.log" 2>&1 </dev/null &
  SERVER_PID=$!
  set +m
  for _ in $(seq 1 120); do
    if curl -s -o /dev/null "$BASE/scores"; then
      echo "wrangler dev ready on $BASE (pid $SERVER_PID, fresh state in $WORK/state)"
      return 0
    fi
    sleep 0.5
  done
  echo "wrangler dev did not start:" >&2
  cat "$WORK/wrangler.log" >&2
  exit 1
}

request() {
  local method="$1" path="$2" body="${3:-}" client="${4-X-Safu-Client: 1}" player="${5:-}"
  local args=(-s -X "$method" -D "$WORK/headers" -o "$WORK/body" -w '%{http_code}')
  [ -n "$client" ] && args+=(-H "$client")
  [ -n "$player" ] && args+=(-H "X-Safu-Player: $player")
  [ -n "$body" ] && args+=(-H 'Content-Type: application/json' --data-binary "$body")
  STATUS="$(curl "${args[@]}" "$BASE$path")"
  BODY="$(cat "$WORK/body")"
}

post() {
  request POST /scores "$1" "X-Safu-Client: 1" "${2:-}"
}

get_as() {
  request GET /scores "" "X-Safu-Client: 1" "${1:-}"
}

json_true() {
  printf '%s' "$BODY" | node -e '
    let s = "";
    process.stdin.on("data", (d) => (s += d)).on("end", () => {
      let b;
      try { b = JSON.parse(s); } catch { process.exit(1); }
      const rows = (l) => l.map((r) => r.name + ":" + r.score).join(",");
      const sorted = (l) => l.every((r, i) => i === 0 || l[i - 1].score >= r.score);
      const mine = (l) => l.flatMap((r, i) => (r.me ? [i] : [])).join(",");
      const clean = (b) =>
        [...b.streak, ...b.lifetime].every((r) => {
          const keys = Object.keys(r).sort().join();
          return keys === "name,score" || (keys === "me,name,score" && r.me === true);
        });
      const ok = new Function("b", "rows", "sorted", "mine", "clean", "return (" + process.argv[1] + ");")(
        b, rows, sorted, mine, clean,
      );
      process.exit(ok ? 0 : 1);
    });
  ' "$1"
}

headers_ok() {
  local ctype clen size
  ctype="$(grep -i '^content-type:' "$WORK/headers" | tr -d '\r' | cut -d' ' -f2-)"
  clen="$(grep -i '^content-length:' "$WORK/headers" | tr -d '\r' | awk '{print $2}')"
  size="$(wc -c <"$WORK/body" | tr -d ' ')"
  [ "$ctype" = "application/json" ] && [ "$clen" = "$size" ] && [ "$size" -lt 4096 ]
}

expect() {
  local desc="$1" want="$2" expr="${3:-true}"
  if [ "$STATUS" = "$want" ] && json_true "$expr"; then
    PASS=$((PASS + 1))
    echo "PASS  $desc"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL  $desc"
    echo "      expected $want and: $expr"
    echo "      got $STATUS $BODY"
  fi
}

expect_headers() {
  if headers_ok; then
    PASS=$((PASS + 1))
    echo "PASS  $1"
  else
    FAIL=$((FAIL + 1))
    echo "FAIL  $1"
    cat "$WORK/headers"
  fi
}

expect_400() {
  post "$2"
  expect "400 $1" 400 'typeof b.error === "string" && Object.keys(b).length === 1'
}

if [ -z "${SAFU_URL:-}" ]; then
  start_server
else
  echo "using existing server at $BASE (board must be empty)"
fi

echo
echo "== header gate and routing"
request GET /scores "" ""
expect "GET /scores without X-Safu-Client -> 403" 403 'b.error === "forbidden"'
expect_headers "403 is application/json with exact Content-Length"
post_body='{"id":"'$A'","name":"NEKO","best":1,"lifetime":1}'
request POST /scores "$post_body" ""
expect "POST /scores without X-Safu-Client -> 403" 403 'b.error === "forbidden"'
request GET /scores "" "X-Safu-Client: 2"
expect "wrong X-Safu-Client value -> 403" 403 'b.error === "forbidden"'
request GET /nope
expect "GET unknown path -> 404" 404 'b.error === "not found"'
request POST /nope '{}'
expect "POST unknown path -> 404" 404 'b.error === "not found"'
request DELETE /scores
expect "DELETE /scores -> 404" 404 'b.error === "not found"'
request GET /
expect "GET / -> 404" 404 'b.error === "not found"'

echo
echo "== empty board"
request GET /scores
expect "GET empty board" 200 'b.streak.length === 0 && b.lifetime.length === 0 && b.updated === 0'
expect "board has exactly keys streak, lifetime, updated" 200 'Object.keys(b).sort().join() === "lifetime,streak,updated"'
expect_headers "GET is application/json with exact Content-Length"
get_as $A
expect "GET empty board with X-Safu-Player has no you block" 200 'b.streak.length === 0 && !("you" in b)'

echo
echo "== first and second player"
post '{"id":"'$A'","name":"  neko ","best":12,"lifetime":40}' $A
expect "POST valid player -> 200 with fresh board" 200 'rows(b.streak) === "NEKO:12" && rows(b.lifetime) === "NEKO:40"'
expect "name trimmed and uppercased" 200 'b.streak[0].name === "NEKO" && b.lifetime[0].name === "NEKO"'
expect "own rows flagged me:true" 200 'mine(b.streak) === "0" && mine(b.lifetime) === "0"'
expect "rows have only name, score (+ me), no id" 200 'clean(b) && !("id" in b.streak[0])'
expect "no you block when inside the top 10" 200 '!("you" in b)'
expect "updated is a unix timestamp in seconds" 200 'Number.isInteger(b.updated) && Math.abs(b.updated - Date.now() / 1000) < 120'
expect_headers "POST is application/json with exact Content-Length"

post '{"id":"'$B'","name":"Bob-2","best":20,"lifetime":30}'
expect "POST second player -> both lists sorted desc" 200 'rows(b.streak) === "BOB-2:20,NEKO:12" && rows(b.lifetime) === "NEKO:40,BOB-2:30"'
expect "POST without X-Safu-Player flags rows of the body id" 200 'mine(b.streak) === "0" && mine(b.lifetime) === "1" && clean(b)'

post '{"id":"'$C'","name":"cat_3.","best":12,"lifetime":12}' $C
expect "tie on streak: earlier timestamp ranks first" 200 'rows(b.streak) === "BOB-2:20,NEKO:12,CAT_3.:12" && mine(b.streak) === "2"'

request GET /scores
expect "GET returns sorted streak list" 200 'rows(b.streak) === "BOB-2:20,NEKO:12,CAT_3.:12"'
expect "GET returns sorted lifetime list" 200 'rows(b.lifetime) === "NEKO:40,BOB-2:30,CAT_3.:12"'
expect "GET without X-Safu-Player: no me flags, no ids, no you" 200 'mine(b.streak) === "" && mine(b.lifetime) === "" && clean(b) && !("you" in b)'
get_as $A
expect "GET as player A flags only A rows" 200 'mine(b.streak) === "1" && mine(b.lifetime) === "0" && clean(b)'
get_as $D
expect "GET as unknown player: no me, no you" 200 'mine(b.streak) === "" && mine(b.lifetime) === "" && !("you" in b)'

echo
echo "== player header"
post '{"id":"'$D'","name":"X","best":1,"lifetime":1}' $A
expect "POST with X-Safu-Player different from body id -> 400" 400 'b.error === "X-Safu-Player does not match id"'
get_as ABCDEF0123456789
expect "GET with malformed X-Safu-Player -> 400" 400 'typeof b.error === "string"'
post '{"id":"'$D'","name":"X","best":1,"lifetime":1}' short
expect "POST with malformed X-Safu-Player -> 400" 400 'typeof b.error === "string"'

echo
echo "== rate limit"
post '{"id":"'$C'","name":"CHEAT","best":999,"lifetime":999}'
expect "second POST for same id within 5s -> 429" 429 'typeof b.error === "string"'
expect_headers "429 is application/json with exact Content-Length"
request GET /scores
expect "rejected 429 write did not change the board" 200 'rows(b.streak) === "BOB-2:20,NEKO:12,CAT_3.:12"'

echo
echo "== validation"
expect_400 "id uppercase hex" '{"id":"AAAAAAAAAAAAAAA1","name":"X","best":1,"lifetime":1}'
expect_400 "id too short" '{"id":"aaaaaaaaaaaaaaa","name":"X","best":1,"lifetime":1}'
expect_400 "id too long" '{"id":"aaaaaaaaaaaaaaaa1","name":"X","best":1,"lifetime":1}'
expect_400 "id non-hex" '{"id":"zzzzzzzzzzzzzzzz","name":"X","best":1,"lifetime":1}'
expect_400 "id missing" '{"name":"X","best":1,"lifetime":1}'
expect_400 "id not a string" '{"id":1234567890123456,"name":"X","best":1,"lifetime":1}'
expect_400 "name empty" '{"id":"'$D'","name":"","best":1,"lifetime":1}'
expect_400 "name only spaces" '{"id":"'$D'","name":"   ","best":1,"lifetime":1}'
expect_400 "name 11 chars" '{"id":"'$D'","name":"ABCDEFGHIJK","best":1,"lifetime":1}'
expect_400 "name with !" '{"id":"'$D'","name":"NEKO!","best":1,"lifetime":1}'
expect_400 "name with non-ascii" '{"id":"'$D'","name":"NÉKO","best":1,"lifetime":1}'
expect_400 "name missing" '{"id":"'$D'","best":1,"lifetime":1}'
expect_400 "best > lifetime" '{"id":"'$D'","name":"X","best":10,"lifetime":5}'
expect_400 "best negative" '{"id":"'$D'","name":"X","best":-1,"lifetime":5}'
expect_400 "lifetime above 99999" '{"id":"'$D'","name":"X","best":1,"lifetime":100000}'
expect_400 "best not an integer" '{"id":"'$D'","name":"X","best":1.5,"lifetime":5}'
expect_400 "best as string" '{"id":"'$D'","name":"X","best":"1","lifetime":5}'
expect_400 "lifetime missing" '{"id":"'$D'","name":"X","best":1}'
expect_400 "invalid json" '{nope'
expect_400 "json array body" '[1,2]'
expect_400 "body too large" '{"id":"'$D'","name":"X","best":1,"lifetime":1,"pad":"'"$(printf 'x%.0s' $(seq 1 1100))"'"}'
request GET /scores
expect "rejected 400 writes did not change the board" 200 'b.streak.length === 3 && b.lifetime.length === 3'

echo
echo "== merge keeps max (waiting 5.5s for the rate limit window)"
sleep 5.5
post '{"id":"'$A'","name":"neko2","best":3,"lifetime":41}' $A
expect "lower best keeps stored best, higher lifetime wins, name updated" 200 'rows(b.streak) === "BOB-2:20,NEKO2:12,CAT_3.:12" && rows(b.lifetime) === "NEKO2:41,BOB-2:30,CAT_3.:12"'
expect "unchanged score keeps its original tie position" 200 'mine(b.streak) === "1" && b.streak[2].name === "CAT_3."'
post '{"id":"'$B'","name":"bob","best":25,"lifetime":26}' $B
expect "higher best wins, lower lifetime keeps stored lifetime" 200 'rows(b.streak) === "BOB:25,NEKO2:12,CAT_3.:12" && rows(b.lifetime) === "NEKO2:41,BOB:30,CAT_3.:12"'
request GET /scores
expect "GET reflects merged records" 200 'rows(b.streak) === "BOB:25,NEKO2:12,CAT_3.:12" && rows(b.lifetime) === "NEKO2:41,BOB:30,CAT_3.:12"'

echo
echo "== top 10 trimming and you block"
for i in 0 1 2 3 4 5 6 7 8 9; do
  post '{"id":"eeeeeeeeeeeeeee'$i'","name":"P'$i'","best":'$((i + 1))',"lifetime":'$((100 + i))'}' "eeeeeeeeeeeeeee$i"
done
post '{"id":"'$Z'","name":"ZERO","best":0,"lifetime":0}' $Z
expect "player with zero scores is accepted" 200 'true'
expect "zero-score player is not listed and gets no you block" 200 'mine(b.streak) === "" && mine(b.lifetime) === "" && !("you" in b)'
request GET /scores
expect "streak list trimmed to 10 and sorted" 200 'b.streak.length === 10 && sorted(b.streak) && rows(b.streak) === "BOB:25,NEKO2:12,CAT_3.:12,P9:10,P8:9,P7:8,P6:7,P5:6,P4:5,P3:4"'
expect "lifetime list trimmed to 10 and sorted" 200 'b.lifetime.length === 10 && sorted(b.lifetime) && b.lifetime[0].score === 109 && b.lifetime[9].score === 100'
expect "no row in the full board has an id field" 200 '![...b.streak, ...b.lifetime].some((r) => "id" in r) && clean(b)'
expect_headers "full board stays under 4 KB with exact Content-Length"
echo "      full board size: $(wc -c <"$WORK/body" | tr -d ' ') bytes"
get_as $A
expect "A: me on streak row 2, you.lifetime rank 11 only" 200 'mine(b.streak) === "1" && mine(b.lifetime) === "" && JSON.stringify(b.you) === "{\"lifetime\":{\"rank\":11,\"score\":41}}"'
get_as eeeeeeeeeeeeeee0
expect "P0: me on lifetime row 10, you.streak rank 13 only" 200 'mine(b.lifetime) === "9" && mine(b.streak) === "" && JSON.stringify(b.you) === "{\"streak\":{\"rank\":13,\"score\":1}}"'
get_as $C
expect "C: me on streak row 3, you.lifetime rank 13" 200 'mine(b.streak) === "2" && JSON.stringify(b.you) === "{\"lifetime\":{\"rank\":13,\"score\":12}}"'
expect "board with you has exactly keys streak, lifetime, updated, you" 200 'Object.keys(b).sort().join() === "lifetime,streak,updated,you"'
get_as $Z
expect "Z (not ranked): no me, no you" 200 'mine(b.streak) === "" && mine(b.lifetime) === "" && !("you" in b)'
post '{"id":"'$Q'","name":"QUINN","best":2,"lifetime":50}' $Q
expect "POST response carries you for both lists outside the top 10" 200 'mine(b.streak) === "" && mine(b.lifetime) === "" && JSON.stringify(b.you) === "{\"streak\":{\"rank\":13,\"score\":2},\"lifetime\":{\"rank\":11,\"score\":50}}"'
expect_headers "board with you block stays under 4 KB with exact Content-Length"

echo
echo "passed: $PASS  failed: $FAIL"
[ "$FAIL" -eq 0 ]
