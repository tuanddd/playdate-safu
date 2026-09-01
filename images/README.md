# Safu — generated art

Everything here is **pure 1-bit black & white** (no greys, no colour), drawn in the
WAGMI web-comic line-art style and sized for the Playdate's 400x240 display.

**Currently in FLAT mode: no dithering.** Every fill is white (or solid black for the
mask / CUT bar / silhouettes) so the shapes can be iterated until the scenes and the
character are nailed. The dither pattern ids (`p12/p25/p50/p75`, `d12..d75`) still
exist in both `DEFS` blocks but are defined as plain white — restore their old pattern
rects when it's time to bring tone back.

## Art direction

Modelled directly on three WAGMI pages in `../art-references/`:
`wagmi-interest-rate-01.png`, `wagmi-pay-raise-01.jpeg`, `wagmi-6jars-01.jpg`.

**Character** — Neko as he is drawn in the comics (not the sticker pack):

| | |
|---|---|
| Head | **squircle** — wider than tall (74x60 in the 100-unit cell), all four corners rounded hard, built by `squircle()` — the proportion in `wagmi-neko-1/2/4` |
| Ears | **small rounded triangles perched on top**, tilted slightly outward, every corner arced by `roundPoly()`; dithered inner ear |
| Eyes | small-to-mid solid black rounded ovals, set wide at x 35 / 65 — never huge kawaii eyes |
| Muzzle | tiny nose with a `w` mouth, sitting low on the face |
| Whiskers | 3 per side, long and thin, attached at the cheek |
| Body | **nendoroid** — the head is most of the cat. A small soft bean torso (~42 units wide vs the 74-unit head), stub arms ending in mitten paws, feet as bare ovals peeking out with a short split line, thin curving tail. No suit — the heist look is just the black mask. |

**Page grammar** — WAGMI is light, not heavy. White characters with a thin even outline,
tone supplied by dither washes behind them, generous white space, hand-lettered caption
boxes and floating text with a vertical rule, radial ray backdrops for impact beats.
Solid black is reserved for line art, the heist mask, silhouettes, the manga ray
wedges (`rayTicks`), and the CUT bar.

**Playdate scale** (per [donaldhays.com/2019/12/30/playdate-art-scale](https://donaldhays.com/2019/12/30/playdate-art-scale/)) —
the panel is Retina-class, so art reads about half as large as it does on a desktop:

- no line thinner than ~2px on the device; face line weights are silhouette `3.2`,
  features `2.6`, whiskers `2.2` in the 100-unit cell
- **body text is 11-13px, never 8px** — 8px is called out in the article as unreadable
- dither cells are 2px or 4px and pages are authored at 400x240 1:1, so every pattern
  lands on exact device pixels

## Sprite sheet — facial expressions

`neko-expressions-sheet-1bit.png` — 384x256, 6 columns x 4 rows, **64x64 per cell**.
`neko-faces-table-64-64.png` — identical file, named for the Playdate `imagetable` loader:

```lua
local faces <const> = gfx.imagetable.new("images/neko-faces-table-64-64")
faces:drawImage(NEKO.focused, x, y)
```

Frame order (1-indexed, row-major):

| # | id | # | id | # | id |
|---|---|---|---|---|---|
| 1 | neutral | 9 | surprise | 17 | excited |
| 2 | smiling | 10 | shocked | 18 | wink |
| 3 | happy | 11 | talking | 19 | dizzy |
| 4 | laugh | 12 | thinking | 20 | sleepy |
| 5 | sad | 13 | focused | 21 | mask-neutral |
| 6 | crying | 14 | smug | 22 | mask-focused |
| 7 | upset | 15 | shifty | 23 | mask-smug |
| 8 | raged | 16 | nervous | 24 | mask-panic |

The four `mask-*` frames are Neko in the heist mask (solid black band, white eye holes, pupils scaled to 58% so they stay readable at 64px) — the look he wears in the comic and,
by extension, in the safe-cracking scenes.

Single frames are also in `faces/neko-<id>.png` (64x64, 1-bit).
`neko-expressions-labelled.png` is the human-readable contact sheet.

## Comic pages

Each page is one 400x240 screen, so it can be shown full-frame on the device.

| File | Layout | Beat |
|---|---|---|
| `comic-01-midnight` | 1x1, full bleed | Midnight. Haloed moon, shooting star, sleeping city — and Neko already perched in silhouette on a foreground roof. |
| `comic-02-heist` | 2 skewed panels on top, 1 wide skewed panel below | Neko crouched on a rooftop ledge under the moon; ray-burst close-up on the mask; inside, moonlight through the window, Neko holding a **blank note** ("A NOTE... NOTHING ON IT."). |
| `comic-03-reveal` | 2 stacked wide panels + a black CUT bar | POV on the blank note — the safe sits in plain view at the right, unnoticed; the note drops and the safe gets the full ray-burst. Cut. |

`comic-neko-full-story.png` stacks all three.

**The blank note in page 2's last panel and page 3's first panel is deliberately empty** —
that is the seam where the safe-cracking mechanic gets inserted between the two scenes.

## Files

- `*-1bit.png` — game-ready, pure black & white, drop straight into `source/`
- `*.png` (no suffix) — anti-aliased greyscale master, re-threshold it if you want a different cut
- `*@4x.png` / `*@2x.png` — nearest-neighbour previews for looking at on a desktop
- `svg/` — the vector source and generators

## Regenerating

```sh
cd images/svg
node build-sheet.js      # expression SVGs
node build-comic.js      # comic page SVGs
./_run.sh '[{"svg":"...","png":"...","w":400,"h":240}]'   # SVG -> PNG via Chrome
```

Then threshold to 1-bit:

```sh
magick in.png -colorspace Gray -threshold 62% -type bilevel PNG8:out-1bit.png
```

Edit expressions in `svg/neko.js` (`EXPRESSIONS` table + the `EYE` / `M` vocabularies).
Edit scenes in `svg/comic.js` (scene primitives) and `svg/build-comic.js` (page layouts).
Scene primitives include `nekoFull` / `nekoCrouch` / `povNote` (bodies), `nekoSilhouette`
(far-shot black cat), `windowFrame`, `excl` / `quest` (haloed marks), plus `rayTicks`
(black manga impact wedges), `speedLines`, `moon`, `skyline`, `safe`.
