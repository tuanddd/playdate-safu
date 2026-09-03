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
- `screens/` — captures of the running game, not generated art (see below)

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

---

## Screen captures (`screens/`)

Every distinct screen in the shipping game, from the simulator at native 400x240. Unlike
everything else in this folder these are **not** generated art — they are the real screens, so
they go stale the moment the UI changes. Recapture rather than touch them up.

| | |
|---|---|
| `01-title` | title, with the live dial |
| `02-play-blackout` | mid-run — a BLACKOUT run, so the flashlight cone is visible |
| `03-pause-menu` | the Ⓑ pause menu |
| `04-mods-catalogue` | Modifiers — the read-only catalogue |
| `05-debug-menu` | the Debug branch |
| `06-screens-menu` | Debug → Screens |
| `07-mods-picker` | Debug → Modifiers, the forced-set picker |
| `08-safe-open` `09-times-up` `10-caught` `11-boom` | the four end panels |

Captured by dropping a temporary `source/devshots.lua` into the build that stubs
`playdate.buttonJustPressed` against a frame schedule, overrides `Mods.roll` to force a known set,
and calls `playdate.simulator.writeToFile` on chosen frames. It is deleted again afterwards — it
must never ship.

The four end panels are reached through **Debug → Screens** in the pause menu, which sets the real
state and calls the same panel builders the game uses, so what is captured is the shipping screen
and not a mock of it.

## HUD layout experiments (`hud-*.png`)

Six candidate play-screen layouts, each with **three modifier slots** (§12 of `game.md`) plus the
dial, the run timer and the Ⓐ prompt. Built by `svg/build-hud.js` → `svg/hud.js`, rendered by
`svg/_run-hud.sh` (SVG → canvas → **hard threshold to pure 1-bit** → `@2x` nearest-neighbour
preview). No greys survive the threshold, so what you see is what the device shows.

Icons are the real [Pictogrammers Memory](https://github.com/Pictogrammers/Memory) set on its
native 22x22 pixel grid; the paths used here are vendored into `svg/memory-icons.json`, and the
set also ships `playdate/memory-table-22-22.png` + `icon.lua` if we adopt it in-engine.

| File | Layout | Dial radius | Modifiers shown as |
|---|---|---|---|
| `hud-01-vault-door` | Whole screen is the door: riveted plate, engraved timer, recessed dial well | 61 | Three bolted name plates, right column (name + effect) |
| `hud-02-left-rail` | Black 112px rail on the left, dial takes the rest | **82** | Cards in the rail (icon + name) |
| `hud-03-bottom-deck` | Dial floats high, console deck across the bottom | 74 | Three chips in the deck (name + effect) |
| `hud-04-bolt-ring` | Modifiers *are* the door's locking bolts, on bolt-work spokes | 65 | Icon-only discs, no text |
| `hud-05-lcd-console` | `iso-vault.webp` read: inverted LCD readout + alarm list | 74 | Rows under the readout (icon block + name + effect) |
| `hud-06-minimal` | Closest to the current build, maximum dial | **98** | Small icon stack in the right margin |

`hud-contact-sheet.png` shows all six at 1:1 for comparison.

Trade-off in one line: 2 and 6 protect the dial, 1 and 5 sell the fantasy, 3 is the most legible
mid-run, 4 is the only one that costs nothing in screen furniture.

Rebuild: `node svg/build-hud.js && svg/_run-hud.sh "$(node -e '…jobs…')"` — see the jobs array
in the git history of `svg/_run-hud.sh`.

## Modifier icons (`source/images/modifiers/`)

Twelve 14x14 1-bit icons, one per modifier in `game.md` §12. **Authored at 14x14, the size they
display at**, so every pixel is a device pixel — no resampling. Eight are hand-drawn; four are
[Pictogrammers Memory](https://github.com/Pictogrammers/Memory) art scaled from its native 22px
grid (those four are the softer ones).

### Where everything lives

| What | Path |
|---|---|
| Drawn source (ASCII grids) | `svg/icons-pixel.js` |
| Memory paths, vendored | `svg/memory-icons.json` |
| One SVG per icon | `svg/icons/<icon-id>.svg` |
| One PNG per icon, transparent | `../source/images/modifiers/<icon-id>.png` |
| Imagetable, 12 frames | `../source/images/mod-icons-table-14-14.png` (loads as `images/mod-icons`) |
| **id → path map** | `icons-manifest.json` |
| Lua catalogue + loaders | `../source/modifiers.lua` |
| Contact sheet | `hud-modifier-icons.png` |

### id → icon → frame

| # | Modifier | Icon id | Source |
|---|---|---|---|
| 1 | BLACKOUT | `eye-off` | Memory `eye` + slash |
| 2 | TOO LOUD | `music-note` | Memory |
| 3 | HAIR TRIGGER | `crosshair` | drawn |
| 4 | GREASED | `oil-slip` | drawn |
| 5 | STICKY | `goo-drip` | drawn |
| 6 | SCRAMBLED | `both-ways` | drawn |
| 7 | FOUR TUMBLERS | `four-pins` | drawn |
| 8 | WANDERING | `drift-target` | drawn |
| 9 | DECOY | `twin-marks` | drawn |
| 10 | ONE SHOT | `skull` | Memory |
| 11 | GUARD | `peaked-cap` | drawn |
| 12 | NITRO | `flask` | Memory |

### Using them

```lua
import "modifiers"

local run, mode = Mods.roll(3)          -- a playable triple + "hard"/"normal"
for i, m in ipairs(run) do
    Mods.drawIcon(m.id, 10, 10 + i * 20)
    gfx.drawText(m.name, 30, 10 + i * 20)
end
```

`Mods.iconImage(iconId)` pulls from the imagetable (cheap, prefer it);
`Mods.iconFile(iconId)` loads the standalone PNG.

### Editing an icon

Drawn icons are ASCII in `svg/icons-pixel.js` — `'#'` is black, every row must be 14 characters
(the renderer throws otherwise). After editing:

```sh
cd images/svg
node build-icon-files.js                       # SVGs + strip + manifest
./_run-hud.sh "$(node build-icon-files.js --jobs)"   # PNGs into source/
node build-modifier-icons.js && ./_run-hud.sh '[{"svg":"images/svg/hud-modifier-icons.svg","png":"images/hud-modifier-icons.png","w":452,"h":410,"zoom":2}]'
```

**Frame order in `Mods.iconFrames` must match `icons-manifest.json`.** Both are generated from the
`ICONS` array in `svg/build-icon-files.js` — change the order there, not by hand.

### Non-modifier glyphs on the same grid

`icons-pixel.js` also carries the HUD's own 14x14 art, exported by the same `--jobs` run:

| id | Ships as | Used by |
|---|---|---|
| `clock-14` | `source/images/clock-14.png` | the timer plate |
| `btn-a` | `source/images/btn-a-14.png` | every Ⓐ prompt |
| `btn-b` | `source/images/btn-b-14.png` | every Ⓑ prompt |

These replaced the 22px `clock.png` / `btn-a.png` / `btn-b.png`, which were larger than the 13px
label font they sat next to.
