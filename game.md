# Safu — Design Spec

This document describes the game **as it currently exists in `source/`**. It supersedes the
original MVP plan; where the build intentionally diverged from that plan, see §11.

> **Keep this file in sync with the code.** Any change to mechanics, tuning, screens, or feedback
> gets written here in the same pass as the code change.

---

## 1. The game

Safu is a game about cracking safes. The player turns the crank to turn the knob on the safe.
After 3 hits on the sweet spots, the safe can be cracked open and the run is finished.

The gameplay loop is intentionally short and simple, with challenges/modifiers layered on top to
make the cracking experience more fun — that's where the replayability comes from, not from
content volume.

The crank should feel indispensable, not like a substitute joystick. The core fantasy:

**Turn crank → feel for mechanical feedback → find sweet spot → reverse direction → repeat → pull the handle.**

---

## 2. Core rules

- Turn the dial to search for the sweet spot. On a hit there is a **visual cue** (the dial shakes
  briefly) and an **audio cue** (a k-chk, something latching into place).
- **Turn too fast and progress resets. Too slow and the timer runs out.**
- There are **3 sweet spots** to hit consecutively, in alternating directions.
- The player must **press Ⓐ to pull the handle**. Pulling it before all 3 are found resets the
  whole progress.

---

## 3. Current build at a glance

| | |
|---|---|
| Dial | 0–99, front-facing, recessed in the vault door at (122,128) r=52 |
| HUD | The screen **is** the safe door: timer plate, dial well, 3 modifier plates |
| Sweet spots | 3, randomly generated per run |
| Directions | CW → CCW → CW |
| Timer | **60 seconds** (counts down, `mm:ss.cc`) |
| Open the safe | Press Ⓐ after all 3 are found |
| Refresh rate | 50 fps |
| Screens | Title → Play → Win / Lose → (Ⓑ) → Title |
| Modifiers | 3 rolled per run — **effects and custom UI both live** |

### Tuning constants (`source/main.lua`)

| Constant | Value | Meaning |
|---|---|---|
| `GAME_MS` | `60000` | Run length, 1 minute |
| `DEG_PER_UNIT` | `3.6` | Crank degrees per dial unit → **1 crank revolution = 1 dial revolution** |
| `TOL` | `2.2` | Sweet spot half-width in dial units (zone is 4.4 units ≈ 7.9° wide) |
| `cfg.maxEngage` | `25` | Max speed to latch — 25 units/**sec** ≈ **90°/sec**. Per-run, so it lives in `Mods.buildCfg`, not `main.lua`; HAIR TRIGGER drops it to 7.5 |
| `RESET_SPEED` | `80` | Speed above which progress resets — 80 units/sec ≈ **288°/sec** |
| `DEAD_SPEED` | `1.5` | Below this the dial counts as stationary |
| `TICK_STEP` | `4` | A tick every 4 dial units → 25 ticks per revolution |
| `DIRS` | `{1, -1, 1}` | Required direction per tumbler |
| `EXIT_MS` | `420` | Length of the slide-up back to the title screen |

---

## 4. Screens & flow

### Title
Rotating dial (r=62) + big `SAFU` logotype + `Ⓐ CRACK IT`.
The crank already ticks here, so the mechanism is alive before the run starts.

### Play

The whole screen is the safe door — black surround, white plate, engraved inner frame, rivets.
Layout ported from `images/hud-01-vault-door.png`.

    ┌──────────────────────────────────────┐
    │ · · · · · · · · · · · · · · · · · ·  │
    │ ▓ 🕐 00:47.31 ▓        ╔═ BLACKOUT ═╗ │  ← timer plate, then the 3
    │                        ║ DIAL HIDDEN║ │    modifier plates, each on
    │      ╭─────────╮       ╚════════════╝ │    a checkered offset shadow
    │      │ ( DIAL ) │      ╔═ TOO LOUD ══╗ │
    │      ╰─────────╯       ╚════════════╝ │  ← dial sits in a dithered
    │        K-CHIK!         ╔═ GUARD ═════╗ │    recess, left of centre
    │        Ⓐ OPEN?         ╚════════════╝ │
    │ · · · · · · · · · · · · · · · · · ·  │
    └──────────────────────────────────────┘

| Element | Where |
|---|---|
| Timer plate | (24,20), sized from the fixed string `00:00.00` so it cannot twitch |
| Dial well | (122,120) r=64, 25% dither, 2px rim |
| Dial | (122,120) r=52 — centred in the door's inner area (y 8–232) |
| Modifier plates | x=232, y=20 + i·68, 140x58, corners **scooped inward** (r=6) |
| Ⓐ OPEN? | centred under the dial at y=186 |
| Ⓑ MENU | directly below it at y=204 |

Card fill, shadow and outline are all the **same polygon** (`notchedPoly` in `dial.lua`), so the
checkered shadow follows the scooped corners instead of squaring them off.

Each plate is two rows: a 14x14 icon centred against the title, then the subtitle wrapped to **at
most 2 lines**. Title and subtitle are the same family at two sizes and weights —
**Nontendo-Bold 13** over **Nontendo-Light 13** — same size, one weight apart. `FOUR TUMBLERS` is the widest title that fits; there is
no smaller weight to fall back to, so names must stay at or under 13 characters.

`Run.mods` is rolled in `startGame()` via `Mods.roll(3)`, and `Mods.buildCfg` turns the set into
`Run.cfg` — the tunables the run plays by. Effects and their visuals are both implemented (§12b).

**There is no progress indicator during play.** The player tracks their own progress from the
audio/visual cues. `Ⓐ Open?` is therefore a genuine gamble.

### Win
1. Screen shake + `K-CHUNK!` + sweet sound; BGM stops.
2. After 800 ms the live scene is captured, and a black panel **slides down over it** (460 ms,
   cubic ease-out) — the panel *is* the door opening.
3. Panel: `SAFE OPEN!` / `TIME LEFT` / frozen `mm:ss.cc` / `Ⓐ AGAIN` / `Ⓑ TITLE`.

### Lose
Same shape as the win, so both endings read as the door moving:

1. Timer hits `00:00.00` → `TIME'S UP` SFX over the live scene, BGM stops.
2. After 700 ms the scene is captured and a black panel **slides down over it** (460 ms, the same
   cubic ease-out the win panel uses).
3. Panel: `TIME'S UP` / `TUMBLERS FOUND` / the 3 progress dots / `Ⓐ TRY AGAIN` / `Ⓑ TITLE`.

Ⓑ then slides it **up** and off to reveal the title — the mirror of the way it arrived.

### Back to title (Ⓑ)
Pressing Ⓑ on **either** end screen slides that screen **up and off**, revealing the title
underneath — the mirror of the win panel sliding down.

    ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
    │  SAFE OPEN!  │        │  Ⓐ AGAIN     │        │     SAFU     │
    │  TIME LEFT   │   →    ├──────────────┤   →    │   ( dial )   │
    │  Ⓐ AGAIN     │        │     SAFU     │        │  Ⓐ CRACK IT  │
    │  Ⓑ TITLE     │        │   ( dial )   │        │              │
    └──────────────┘        └──────────────┘        └──────────────┘
         t = 0                  t = 0.5                  t = 1

`startToTitle()` calls `Sfx.titleAudio()` first — quitting mid-run from the pause menu would
otherwise carry the play BGM into the title screen. It then captures the live screen with
`gfx.getDisplayImage()`; `drawToTitle()` then draws
the title first and the captured image on top at `y = -240 * e`, where `e` is the same cubic
ease-out (`1-(1-t)³`) the win panel uses. Runs 420 ms in `STATE_TOTITLE`, then hands off to
`STATE_TITLE` and frees the image.

The crank stays live for the whole slide — the title dial is already turning and ticking as it is
revealed, so the mechanism never feels switched off. Lingering SFX are cleared on the way out.

### Crank docked
Gameplay pauses (**the timer does not advance**) and `UNDOCK THE CRANK` is shown.

---

## 5. Dial & crank mapping

- `delta = crankChange / 3.6` dial units per frame. Direct, 1:1, no smoothing or acceleration.
- `dialPos = (rawPos + posOffset) % 100`.
- **No index pointer is drawn.** Position is read from whichever numeral sits at 12 o'clock —
  there is no fixed mark to read against. A real safe dial has one; adding it is open work.
- Rendering (`Art.drawDial`): black rim, white face, white rim notches every 2 units, black
  tick marks every unit with 3 weights (major every 10, medium every 5, minor otherwise),
  rotated `00`–`90` numerals baked once at load, and a 4-spoke hub that turns with the dial.

---

## 6. Sweet spot detection

The dial **starts at a random position each run** (`rawPos = math.random(0, 99)`), and the three
targets are then generated relative to it: 3 random values `0–99`, each **≥18 units from the
starting position and from each other**.

Keeping targets clear of the start stops a tumbler spawning under the player for a free hit. It is
measured from the *random* start rather than from `0` on purpose — anchoring it to `0` left a fixed
126° band of the dial (83→17) that could never hold a sweet spot in any run, which was learnable
and skippable. With the start randomised, the excluded band moves every run and every position on
the dial is live across runs.

Per frame, in order:

0. `tumbler > 3` → **stop**. Once all three are latched the tumbler logic is skipped entirely,
   so cranking is consequence-free while you decide whether to pull the handle.
1. `speed > RESET_SPEED` → reset progress to tumbler 1, `RESET!`. *(§7)*
2. Not inside `±TOL` of the current target → **re-arm** and stop.
3. Not armed → stop. *(prevents re-triggering while sitting inside the zone)*
4. `speed < 0.03` → stop. *(dead zone; can't latch a stationary dial)*
5. Wrong direction → stop.
6. `speed > MAX_ENGAGE_SPEED` → **graze**. *(§7)*
7. **Hit.**

On a hit:
- The dial **snaps exactly onto the target** (via `posOffset`), so it lands on a clean number.
- 220 ms decaying screen shake (`sin`/`cos`, amplitude 4.5 → 0).
- `sweet.wav` + a `K-CHIK!` manga SFX placed randomly around the dial.
- Advance to the next tumbler; if it happens to be within `TOL` of where you are, start
  disarmed so the player must leave and re-enter the zone.

---

## 7. Speed gates

Two separate speed rules, and they behave differently:

**All speeds are dial units per second, never per frame.** `unitsPerSec()` divides the frame's
crank delta by the frame's own duration. This matters: per-frame thresholds silently tighten
whenever the frame rate dips — at 22 fps the same hand speed yields 2.3x the per-frame delta, so a
normal crank starts reading as `TOO FAST`. That is a bug the player experiences as "the game got
harder", with no way to tell it apart from a tuning change.

**Graze — `speed > MAX_ENGAGE_SPEED` *inside* the zone.**
You crossed the sweet spot too fast to catch it. Plays a low, quiet, half-rate tick + `TOO FAST`,
disarms until you leave the zone, and **resets progress if you were past tumbler 1**.
This is the "you can feel it but you blew past it" moment — the reason to slow down.

**Reset — `speed > RESET_SPEED` anywhere.**
Cranking wildly resets progress to tumbler 1 with `RESET!`. Punishes spinning the crank to brute
force the dial.

At tumbler 1 neither gate can cost progress (there is none), so early searching stays free.

---

## 8. The handle (Ⓐ)

Ⓐ pulls the handle at any time during play, **except while the crank is docked**:

- **All 3 found** → the safe opens.
- **Otherwise** → `LOCKED!` + a two-note thud, and **progress resets to tumbler 1**.

This intentionally reverses the original crank-only design. It converts a pure execution task
into a decision: *"was that third K-CHIK real, or did I miscount?"*

Ⓑ during play opens the **pause menu** (§8b). It used to toggle the FPS counter; that debug
binding is gone.

---

## 8b. Pause menu (Ⓑ)

Ⓑ freezes the run and opens a menu. The screen is captured on open and blitted underneath, and
`update()` runs none of the play logic while it is up — **the clock does not advance**. The crank
is still drained every frame (`pd.getCrankChange()`), or its accumulated rotation would arrive as
one huge delta on resume and trip `RESET_SPEED`.

    ┌────────────────────────────┐
    │▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│  ← 50% dither over the frozen scene
    │▒▒▒▒▒▒▒▒▒▒ SAFU ▒▒▒▒▒▒▒▒▒▒▒▒│  ← logo straddles the top border
    │▒▒▒▒┌──────────────┐▒▒▒▒▒▒▒▒│
    │▒▒▒▒│   ☞ Resume   │▒▒▒▒▒▒▒▒│  ← square corners here, not scooped;
    │▒▒▒▒│    Modifiers │▒▒▒▒▒▒▒▒│    labels centred, cursor to the left
    │▒▒▒▒│      Quit    │▒▒▒▒▒▒▒▒│
    │▒▒▒▒└──────────────┘▒▒▒▒▒▒▒▒│
    └────────────────────────────┘

Sizing rules that keep it symmetric: the cursor gutter is **mirrored on the right** so centred
labels sit in the middle of the panel; the height counts the **last label's own ink** (`Quit` has a
descender — measuring a descender-free sample eats 5px of the bottom gap); and the logo's lower
half is reserved above the first row so it cannot crowd it.

- **Up/Down** move the cursor (wraps), **Ⓐ** selects, **Ⓑ** closes and resumes.
- The cursor is `images/hand-cursor.png`, **poking along X** on a sine (0–5px) — it points at the
  live row rather than spinning in place.
- **Resume** closes · **Quit** slides up to the title.
- **Modifiers** opens the catalogue of **all 12**, not just the run's three — a reference the
  player can browse. Two pages of six, laid out 2 columns x 3 rows, each cell carrying the same
  icon + title + subtitle as a door card. Left/Right (or Up/Down) flips pages, Ⓐ or Ⓑ goes back.
- The panel is sized to its content: `menuBox()` measures **every** string that has to fit, each in
  the font it will be drawn in — including the subtitles, which are wider than the names above them.

---

## 9. Feedback

### Audio (`source/sound.lua`)

| Sound | Source | Notes |
|---|---|---|
| `tick` | `tick.wav` | **6 round-robin voices** so fast cranking never cuts itself off. Rate `0.94 + speed*0.05` + random jitter, volume `0.26 + speed*0.06` — faster cranking is higher and louder |
| `sweet` | `sweet.wav` | Full volume, unpitched. The K-CHIK |
| `graze` | `tick.wav` @ rate 0.45, vol 0.5 | Deliberately a *dulled* tick — the near miss |
| `handle` | `sweet` then `cleared.wav` after 1 s | The opening sequence |
| `locked` / `fail` / `reset` / `start` | square-wave synths | Two- and three-note descending motifs |
| `bgm` | `bgm.wav` @ vol 0.12 | Loops during play, stops on win/lose |
| `titleAudio` | — | Every route back to the title calls it: it silences the run's music and is the single place a title track should start |
| `uiConfirm` | `ui-confirm.wav` | Going *in*: opening the menu, entering the catalogue, Quit |
| `uiBack` | `ui-cancel-back.wav` | Coming *out*: Resume, leaving the catalogue, Ⓑ to the title |
| `uiHover` | `ui-hover.wav` | The cursor moving between menu rows, and catalogue page flips |

UI sounds are keyed to **intent, not to the button**. Ⓐ on `Resume` plays the *back* sound because
it leaves the menu; Ⓑ opening the menu plays *confirm* because it goes in. `Ⓐ OPEN?` during play is
deliberately excluded — it is a game action, and it already has the handle sounds.

Source MP3s live in `sound-fxs/`; the Playdate needs WAV for `sample.new`, so they are converted:

    afconvert -f WAVE -d LEI16@44100 -c 1 sound-fxs/ui-confirm.mp3 source/sounds/ui-confirm.wav

Ticks fire on **detent crossings** (every 4 dial units), not on a timer — so the tick rate emerges
from crank speed. Slow: `tik … tik … tik`. Fast: `tktktktktk`.

### Manga SFX (`source/dial.lua`)

Built procedurally at load, no image assets. `outlinedText()` draws the Bouncy-30 font in white
with a 3px black ring, then `bake()` pre-renders the rotation frames.

- **Wiggle-in**: 6 baked frames at `13°, -10°, 7°, -4°, 2°, 0°`, 34 ms apart — snaps into place.
- **Fade-out**: 5 `fadedImage` steps (Bayer 4×4 dither) over the last 200 ms, drifting 10px up.
- **Placement**: random angle around the dial, clamped to stay on screen.

Current set: `K-CHIK!` `K-CHUNK!` `SAFE OPEN!` `TIME'S UP` `SAFU` `TOO FAST` `RESET!` `LOCKED!`
plus a tiny `tik`.

The tiny `tik` is heavily rate-limited on purpose: only when `speed < 1.6`, at most once per
900 ms, and then only 14% of the time. Never one per tick — that would be visual noise.

---

## 10. Visual direction

1-bit as an intentional aesthetic. Clean, mechanical, high contrast, minimal UI, slight manga
influence. **The dial is the visual star** — no safe body is drawn.

Dithering (`kDitherTypeBayer4x4`) is currently used only for SFX fade-out. Per the Ditherpunk
reference, there is room to use it for shading rather than flat black/white.

**Text alignment:** measured, not eyeballed — every icon+label pair sits within 0px of centre
(audited by dumping the framebuffer and comparing ink centres). Two traps to know about:
`gfx.getTextSize`'s second argument is a font *family table*, not a font, and `pushContext` does
**not** reset the image draw mode — measure ink before switching to `kDrawModeFillWhite` or the
probe draws white on white and reports nothing.

Bitmap glyphs do not fill their line box, so centring a label by line height
leaves it sitting high. `Art.inkBand(font, text)` renders the string once, scans for its first and
last inked row, and caches the result; the Ⓐ/Ⓑ prompts, the card icons and the timer all centre on
that ink.

**Icons:** every HUD glyph is 14x14 to match the 13px label font — the modifier icons, the timer's
clock, and the Ⓐ/Ⓑ buttons (`images/svg/icons-pixel.js`). The old 22px `clock`, `btn-a` and `btn-b`
are gone.

**Fonts:** Roobert for the chrome, **Nontendo** for the modifier cards, **Bouncy-30** for the
manga SFX.

| Cut | Line | Used for |
|---|---|---|
| `Roobert-11-Medium` | 22 | screen headings, the pause menu's own list |
| `Roobert-10-Bold` | 14 | dial numerals, HUD timer, Ⓐ/Ⓑ prompts |
| `Nontendo-Bold` | 13 | modifier card + catalogue titles |
| `Nontendo-Light` | 13 | modifier card + catalogue subtitles |
| `Roobert-20-Medium` | 32 | the win panel's frozen time |
| `Bouncy-30` | — | manga SFX |

**Why the cards are the one exception to Roobert.** They need two weights at a size small enough
that a title plus a two-line subtitle fits a 58px card. Roobert **has no Light at any size and no
Medium below 11px** — at 11-Medium a subtitle is a 22px line box, so only one line fits and the
descriptions have to be cut to ~14 characters. Nontendo has Bold and Light in the same 13px box:
title 85px, subtitle wrapping to 26px, 42px of the 58px card used. Measured on device, the only
other SDK families with two weights that small are pixieval (15px) and Bitmore Medieval (11px);
Asheville Sans, Newsleak and Sasser Slab all need 63px or more.

Roobert-11-Medium's numerals are also wide enough that `00`–`90` collide on the dial, which is why
the dial uses the 10px cut.

---

## 11. Changed from the original plan

| Original plan | Now | Why |
|---|---|---|
| 5:00 timer | **1:00** | 5 min was far too slack for a ~20 s loop |
| Crank-only, no buttons | **Ⓐ pulls the handle** | Adds a real decision + a way to fail by nerve, not just by clock |
| `○ ○ ○` progress shown during play | **Hidden** (shown only on the lose screen) | Forces the player to track their own count; makes Ⓐ a gamble |
| Tolerance ±1 (36–38) | **±2.2** | Tuned to how precise the crank actually feels |
| No speed rules | **Graze + reset gates** | The "turn too fast" rule — gives fast cranking a real cost |
| Tick per dial unit | **Every 4 units** | 100/rev was mush; 25/rev reads as distinct detents |
| Door swings open | **Panel slides down** over a frozen scene | Cheaper, and reads well at 1-bit |
| No title screen | **Title screen** with a live, tickable dial | Mechanism is alive before you press start |
| No music | **Looping BGM** at low volume | — |
| "No audio tool available" | **Real WAV assets** in `source/sounds/` | Obsolete note; assets exist |

---

## 12. Modifiers — designed, not built

Twelve modifiers. **Every run draws 3.** None are implemented; this section is the spec.

### The set

| # | Name | Axis | Tags | Icon | What it does |
|---|---|---|---|---|---|
| 1 | **BLACKOUT** | Perception | `channel` | `eye` + slash | The dial is not drawn. Crack it by ear |
| 2 | **TOO LOUD** | Perception | `channel` | `volume-high` | Ticks ducked to near-silent under loud club BGM |
| 3 | **HAIR TRIGGER** | Motor | — | `target` | `maxEngage` 0.5 → 0.15. You must crawl the last few units |
| 4 | **GREASED** | Motor | — | `water` | The dial carries momentum after you stop cranking |
| 5 | **STICKY** | Motor | — | `anvil` | Needs a minimum crank speed to move at all — no creeping |
| 6 | **SCRAMBLED** | Memory | — | `arrow-left-right` | `dirs` randomised per tumbler instead of `{1,-1,1}` |
| 7 | **FOUR TUMBLERS** | Memory | `time` | `lock` | 4 sweet spots instead of 3 |
| 8 | **WANDERING** | Memory | — | `compass` | Targets drift, but only while you are *not* cranking. **Drift ≤ `Mods.MAX_DRIFT` (5 units/sec)** |
| 9 | **DECOY** | Risk | — | `help` | A fake 4th spot with a duller, learnable K-CHIK |
| 10 | **ONE SHOT** | Risk | `fail` | `skull` | A wrong Ⓐ ends the run instead of resetting progress |
| 11 | **GUARD** | Event | `fail` | `bell` | Footsteps: stop cranking within 3 s or you're caught |
| 12 | **NITRO** | Body | `fail` | `flask` | Accelerometer: keep the device level or it goes off |

**Icons are chosen and exported.** 14x14, 1-bit, transparent: eight hand-drawn on the 14 grid,
four from [Pictogrammers Memory](https://github.com/Pictogrammers/Memory). Assets live at
`source/images/modifiers/<icon-id>.png` and as the imagetable
`source/images/mod-icons-table-14-14.png`; `images/icons-manifest.json` maps id → file, and
`images/README.md` documents the pipeline. Contact sheet: `images/hud-modifier-icons.png`.

`source/modifiers.lua` carries the catalogue (id, name, sub, icon, axis, tags), the icon loaders,
and the pair-scoring rules below as `Mods.pairClass` / `Mods.score` / `Mods.roll`. It is **data and
art only — no modifier mechanic is implemented.** Its rule tables reproduce the 38 banned / 38 hard
/ 144 normal split stated below; change the two together.

### Modes and combinations

Axes are **flavour, not rules** — they were only ever a proxy for "these conflict." Compatibility
is now judged directly, per pair, and drives two modes.

**Every pair of modifiers is classified once:**

| Class | Weight | Meaning |
|---|---|---|
| **banned** | — | The run is impossible. Never offered in any mode |
| **hard ×2** | 2 | On its own makes a run hard mode |
| **hard ×1** | 1 | Needs a second friction to qualify |
| normal | 0 | Everything else — 46 of the 66 pairs |

**A drawn triple is scored by its three pairs:** any banned pair → discard; total ≥ 2 → **HARD**;
otherwise → **NORMAL**.

**220 possible triples → 38 banned, 38 hard, 144 normal. 182 playable runs.**

#### Banned — genuinely impossible (4 pairs)

| Pair | Why |
|---|---|
| BLACKOUT + TOO LOUD | Both continuous channels gone; only discrete SFX text remains |
| HAIR TRIGGER + STICKY | A floor speed above a ceiling speed — the window closes to nothing |
| TOO LOUD + GUARD | GUARD's *only* warning before a hard game over is audio, and TOO LOUD exists to bury audio |
| BLACKOUT + NITRO | The water layer would have to render over a pitch-black screen with no readable contrast, while a hidden tilt limit kills the run |

#### Hard ×2 — stacked death (3 pairs)

ONE SHOT + GUARD · ONE SHOT + NITRO · GUARD + NITRO

Two ways to lose instantly in one run. Beatable, but the run becomes about not dying.
All three together scores 6 — the signature hard-mode draw.

#### Hard ×1 — friction (13 pairs)

| Pair | Why |
|---|---|
| BLACKOUT + DECOY | BLACKOUT eats DECOY's *visual* tell — no dial means no missing shake. Audio tell survives |
| TOO LOUD + DECOY | The mirror: TOO LOUD buries DECOY's *audio* tell. Visual tell survives |
| TOO LOUD + SCRAMBLED | SCRAMBLED's wrong-direction tell is audio-only, so it gets buried |
| TOO LOUD + HAIR TRIGGER | Losing the audio speed encoding exactly when fine speed control matters most |
| BLACKOUT + WANDERING | Targets moving with no visual reference |
| HAIR TRIGGER + GREASED | Momentum vs. a 0.15 ceiling — you must coast in and let it decay |
| STICKY + GREASED | Lunge to break stiction, then get carried past |
| NITRO + GREASED | Fighting momentum is exactly what tilts the device |
| NITRO + STICKY | Lunging to break stiction tilts it too |
| SCRAMBLED + WANDERING | Unknown direction *and* a moving target |
| FOUR TUMBLERS + WANDERING | Four drifting targets inside 60 s |
| FOUR TUMBLERS + GUARD | More work against a clock that freezes |
| DECOY + ONE SHOT | A poisoned count where a wrong press is fatal |

#### DECOY's two tells are load-bearing

DECOY is only fair because it has one tell per channel — the duller `sweet-fake.wav` tail, and the
missing screen shake. **BLACKOUT kills the visual one; TOO LOUD kills the audio one.** Either alone
leaves a tell and is merely hard. Both together would leave none, which is why that pair is banned
on its own account anyway.

#### BLACKOUT and other UI tells

Under BLACKOUT only the timer and the three cards are lit, so any tell drawn elsewhere goes dark.

- **ONE SHOT + BLACKOUT is allowed.** The trembling Ⓐ element is invisible and that tell is
  deliberately sacrificed — ONE SHOT's rule is stated on its card, and the tremble is flavour
  rather than information the player needs to survive.
- **DECOY + BLACKOUT leaves exactly one tell.** With no `K-CHIK!` text and no shake, a real latch
  and a fake one differ *only* in the sound tail — the clean ring versus the 92 Hz dud at 105 ms.
  That difference is real and learnable, so the pair stays hard rather than banned, but it is the
  purest test of the audio tell in the whole set.
- **NITRO + BLACKOUT is banned** (above), which is what removes the contrast problem entirely.
  The water layer never has to render against black.

### Run layout

Play moves from one centred dial to a two-column layout inside a **vault-door frame**:

    ┌══════════════════════════════════┐
    ║ 🕐 00:47.31        ┌───────────┐ ║
    ║                    │ ◆ NAME    │ ║
    ║      ( DIAL )      │   subtitle│ ║
    ║                    ├───────────┤ ║
    ║                    │ ◆ NAME    │ ║
    ║                    │   subtitle│ ║
    ║                    ├───────────┤ ║
    ║   Ⓐ Open?          │ ◆ NAME    │ ║
    ║                    │   subtitle│ ║
    └══════════════════════════════════┘

Dial left, a column of three modifier cards right (icon + title + subtitle), everything wrapped in
a bordered container resembling the vault door. `CX`, `CY` and `R` all change; BLACKOUT and NITRO
are specified against this layout, so it lands first.

### The audio bed — one track, ever

`bgm.wav` currently loops for every run at volume 0.12. TOO LOUD wants `nightclub.wav` loud and
GUARD wants `ambience.wav` looping, so all three would stack.

**They never can.** TOO LOUD + GUARD is a banned pair, so at most one of them is ever active.
That means there is exactly **one background slot**, chosen once at run start — no mixing, no
ducking between tracks, no priority logic:

| Active modifier | Track | Volume |
|---|---|---|
| TOO LOUD | `nightclub.wav` | ~0.50 — it is the point |
| GUARD | `ambience.wav` | ~0.45, under the footsteps |
| neither | `bgm.wav` | 0.12 (unchanged default) |

`Sfx.bgmStart()` takes a track and a volume, or the existing single `fileplayer` swaps its file
with `load()`. Either way the run picks one and never changes it.

**BLACKOUT needs no change here.** Its tell is the mechanism audio, and the default bed at 0.12
does not mask it — measured below.

### Measured audio headroom

Checked because under BLACKOUT + DECOY the sound tail is the *only* tell in the game.

| Signal | Level | Notes |
|---|---|---|
| DECOY dud, 80–110 Hz peak | **−26.7 dB** | the tell |
| Real latch, same band | −40.6 dB | **14 dB apart** — clearly distinguishable |
| `bgm.wav` in-band @ 0.12 | −34.6 dB | dud sits ~8 dB *above* it — no masking |
| `nightclub.wav` in-band @ 0.5 | −22.7 dB | buries the dud, which is why TOO LOUD + DECOY leans on the visual tell |
| `footstep.wav` peak | −4.1 dB | punchy, sits well clear of ambience |

`ambience.wav` as delivered peaked at −30.2 dB — nearly inaudible at any sane fileplayer volume —
so the asset was normalised +20 dB rather than fought with a volume multiplier.

Anyone retuning `sweet-fake.wav` should re-check the first two rows: 14 dB of separation in the
80–110 Hz band is what makes DECOY fair.

### 12b. Effects layer — implemented

`Mods.buildCfg(mods)` returns one `Run.cfg` table holding every tunable a modifier touches,
defaulted to the unmodified game. `main.lua` reads `Run.cfg.x` instead of a constant, so no effect
needs a special case at its call site.

| Field | Default | Set by |
|---|---|---|
| `drawDial` `showEffects` `shake` | `true` | BLACKOUT → all false *(renderer reads these; not yet consumed)* |
| `bgmTrack` `bgmVol` `mechVol` | `sounds/bgm` `0.12` `1.0` | TOO LOUD → nightclub/0.50/0.18 · GUARD → ambience/0.45 |
| `maxEngage` | `25` | HAIR TRIGGER → `7.5` |
| `friction` | `nil` | GREASED → `0.90` |
| `stiction` | `0` | STICKY → `14` |
| `tumblers` | `3` | FOUR TUMBLERS → `4` |
| `randomDirs` | `false` | SCRAMBLED |
| `drift` | `0` | WANDERING → `Mods.MAX_DRIFT` (5) |
| `decoy` `oneShot` `guard` `nitro` | `false` | their own modifiers |

**Where each effect lives**

- **GREASED / STICKY** — `readCrank`. Stiction banks sub-threshold input and releases it in one
  shove; greasing follows the crank exactly while it turns, then coasts. Both are gated on
  `state == STATE_PLAY`: `Run.cfg` outlives the run, so without that the title dial would still
  be sticky after a modified game.
- **HAIR TRIGGER / FOUR TUMBLERS / SCRAMBLED** — `checkTumbler`, via `cfg.maxEngage`,
  `cfg.tumblers` and `Run.dirs`. SCRAMBLED also fires `Sfx.wrongDir()` — a soft low thud, once per
  entry into a zone, meaning *it is here but not this way*. Audio only, by design.
- **DECOY** — `checkDecoy`, run alongside the real tumblers. Latches like a real spot, plays
  `sweet-fake.wav`, shows the same `K-CHIK!`, and **never sets `shakeStart`**. The dud in the tail
  and the missing shake are the only two tells.
- **WANDERING** — `driftTargets`, only while the dial is under `DEAD_SPEED`. Unlatched spots only.
- **GUARD** — `updateGuard`. A footstep every 5–9 s, then `GUARD_GRACE_MS` (3000) to stop. Still
  moving when the grace expires and the run ends. The grace is what makes an audio-only hard-fail
  fair.
- **NITRO** — `updateNitro`. X axis only. The first 30 frames calibrate whatever angle the player
  actually holds the device at, so nobody is punished for their grip; past `NITRO_LIMIT` (0.35 g
  from neutral) the run ends. Exposes `Run.tilt` for the water layer to draw.
- **ONE SHOT** — `tryHandle`. A wrong pull calls `loseRun` instead of resetting progress.

**Ending a run early.** `loseRun(reason)` is the single path for every non-clock ending, using the
same slide-down as a time-out with a different word: `CAUGHT!` for ONE SHOT and GUARD, `BOOM!` for
NITRO. The lose panel draws `cfg.tumblers` dots, not always three.

**Not yet verified.** The effects compile and the simulator boots clean, but no modifier has been
played through. `Mods.buildCfg` and the pair rules are cross-checked against this document
(12 modifiers, 38 banned / 38 hard / 144 normal triples); the *feel* of every constant above —
friction, stiction, drift, grace, tilt limit — is a first guess awaiting a device.

### 12c. Visual layer — implemented

Five modifiers draw something.

**BLACKOUT** — `buildBlackout()` bakes the whole dark room once. A flashlight at `(300, 272)`,
below the bottom edge, throws a cone drawn in two passes:

- `Art.drawLightBeam` paints the beam itself onto the black room, sparsely (12%→42%), so the cone
  is visible hanging in the empty dark and not only where it happens to land on a card.
- `Art.drawLightMask` builds the same cone as a stencil for the cards, with a **floor of 80%** —
  a card dithered below roughly 70% loses its black text against the black room, and which
  modifiers are running is information the player cannot do without.

The timer is drawn after `clearStencil`, so the blackout never touches it. No dial, no shake, no
SFX text, no Ⓐ prompt: the run is played by ear.

Both passes use nested wedges of decreasing dither rather than a per-pixel falloff — 400×240 is
96k Lua iterations, a visible stall at run start, and at 1-bit a stepped ramp looks the same.

> Two Playdate gotchas, both found the hard way and both silent:
> **`setDitherPattern(a)` takes transparency, not coverage** — `0.1` is nearly solid, `0.9` nearly
> invisible. Getting it backwards inverts an entire falloff with no error.
> **`setDitherPattern` resets the draw colour to black.** `setColor` must be re-set *inside* the
> band loop; hoisting it out paints every band after the first in black and eats the ones before.

**TOO LOUD** — `Art.makeNoteBurst` bakes a music-note glyph flanked by `// \\` once. Notes launch
off the top edge on a random diagonal, left or right, and simply leave the screen — no fade, so
nothing pops out mid-flight. They spawn only in `x = 45..175` and are culled past `x = 205`:
**a note crossing a card wrecks the one thing the player must always be able to read.**

**ONE SHOT** — the `Ⓐ OPEN?` prompt trembles, `sin(now()/26) * 1.6` px, forever. Flavour, not
information — the card already states the rule, which is why losing it under BLACKOUT costs
nothing.

**GUARD** — `Art.makeMarks` bakes the manga `// \\` with **no glyph between the strokes**, and one
fires alongside every footstep. Built by hand rather than set in the SFX font, which has no slash
glyphs, but with the same frames/fades shape so it wiggles in and dithers out like `K-CHIK` does.

It does **not** lift the TOO LOUD + GUARD ban. The marks say a sound happened, not that it was
footsteps, and carry none of the three-second deadline that actually decides the run — so they are
atmosphere, not a telegraph, and no substitute for hearing the cue.

**NITRO** — `Art.drawWaterLayer` draws last, over everything. The surface is a damped spring
(`vel = (vel + (target - angle) * 0.06) * 0.88`) so it overshoots and settles instead of snapping;
that lag is what reads as liquid. X axis only, so it is a left/right balance. Waterline sits at
`y = 210` and the fill is sparse: it is a hazard overlay, not a curtain, and burying the card
column would hide the run's own rules.

> **A hang that only four tumblers could reach.** `genTargets` used to guess positions and reject
> the bad ones. That is fine at three and a trap at four: the start plus four targets each wanting
> 18 units of clearance needs 90 of the dial's 100, so valid arrangements are rare enough that the
> loop effectively never terminates. Every FOUR TUMBLERS run froze. It raised no Lua error, so
> `pcall` could not see it and the simulator simply stopped — which is exactly why it survived a
> clean build, a clean boot and three earlier screenshot runs that happened never to roll it.
>
> It now hands out `count+1` gaps that each clear the minimum and sum to exactly 100, then walks
> them round the dial: one pass, no loop, cannot fail. Verified at 0 violations in 20,000 rolls at
> both counts. The result is shuffled, or the tumblers would always appear in rotational order
> from the start — a pattern worth learning.

**Still first-guess numbers.** Every constant here — cone radii and alphas, note speed and spawn
rate, tremble frequency, waterline height, slosh stiffness and damping — was tuned against
simulator screenshots, not a device in hand.

### Per-modifier implementation

**1 · BLACKOUT** — the screen goes **pitch black**. The only lit things are the timer and the
three modifier cards, the cards illuminated by a **cone of light from a flashlight below the
bottom edge**, sold with a dither ramp.

**Nothing else is drawn.** No dial, no screen shake, and **no manga SFX text at all** — not
`K-CHIK!`, not `TOO FAST`, not `RESET!`, not `LOCKED!`, not the tiny `tik`. The run is played
purely by ear. This is the only modifier that removes a channel completely rather than degrading
it.

Build: bake the cone once at load as a Bayer-dithered mask (density falling off with distance and
angle), then `gfx.setStencilImage()` so card drawing only lands inside the cone. Order: fill black
→ cards through the stencil → timer on top, unstencilled. Static mask, so it costs nothing per
frame. Skip `addEffect` at the call sites rather than just skipping `drawEffects`, so no effect
objects are allocated for something that can never be seen. The shake becomes moot on its own —
`shakeStart` only ever offsets the dial.

**Audio must cover every event, and it already does:** hit → `sweet.wav`, graze → the dulled
half-rate tick, reset → `resetVoice`, wrong handle → `lockedVoice`, movement → `tick.wav`. Five
events, five distinct sounds, no gaps. BLACKOUT is what the tick design was always for.

**2 · TOO LOUD** — `nightclub.wav` loops loud; mechanism sounds duck via a `cfg.mechVolume`
multiplier inside `Sfx.tick/sweetSpot/graze` (ticks ~0.1, K-CHIK ~0.35 so hits still cut through).
Adds a recurring **music-note SFX** (Pictogrammers *music-note*) that launches from the **top
edge** at a random diagonal, left or right, flanked by `// \\` emphasis strokes.

**3 · HAIR TRIGGER** — `cfg.maxEngage = 0.15`. No UI.

**4 · GREASED** — `readCrank` keeps a velocity: `vel = vel * 0.90 + delta`; the dial advances by
`vel`. Coasting still ticks and still grazes. No UI — the coasting is self-evident.

**5 · STICKY** — accumulate sub-threshold input; release it in one pop when it breaks stiction.
The pop can shove you through a zone; that is the point. No UI.

**6 · SCRAMBLED** — `cfg.dirs` randomised per tumbler. **No UI tell.** Ships with an *audio*
wrong-direction cue only, since `if dir ~= need then return end` is currently silent.

**7 · FOUR TUMBLERS** — `cfg.tumblers = 4`; de-hardcodes `genTargets`, `cfg.dirs` length,
`tryHandle`'s `tumbler == 4`, and `Art.drawDots` (currently 3 dots at `(i-2)*28`; needs
`(i-(n+1)/2)*28`). No UI tell beyond the dots.

**8 · WANDERING** — drift the current target only while `speed < ε`, ~2 units/sec. Invisible.

**9 · DECOY** — a 4th fake target, same generation rules. Fires `sweet-fake.wav` and the **same**
`K-CHIK!` text, but **no screen shake** and no tumbler advance. Two subtle tells, one per channel.
Fires every time it is crossed properly, so it is a learnable landmark rather than a one-off trap.

**10 · ONE SHOT** — `tryHandle`'s failure branch jumps straight to lose, with a `CAUGHT` end
screen. UI detail: the **Ⓐ Open? element trembles** — a fast, small, indefinitely repeating
left-right shake, like it is scared of being pressed.

**11 · GUARD** — `ambience.wav` loops for the whole run. `footstep.wav` fires occasionally; from
that moment the player has a **3-second grace** to bring the crank to a stop. Still moving when
the grace expires is a **hard game over** — the guard found you. Resume freely once the footsteps
pass. The grace exists so the cue is always reactable.

**12 · NITRO** — `playdate.startAccelerometer()`, **x-axis only**, so the player tilts only left
and right. Drawn as the **top layer over everything**: a water level with real sloshing physics,
like a glass of water. A damped spring on the surface angle gives the slosh; the surface stays
level as the device tilts. Rendered as a dithered fill so the game stays readable underneath.
Tilt past the limit and it spills — run over.

### Axes (descriptive only)

Perception 2 · Motor 3 · Memory 3 · Risk 2 · Event 1 · Body 1

Kept as a way to talk about what a modifier twists, and as a rough guide when adding new ones —
Event and Body have one member each, so those are the thin spots. They no longer gate any draw.

---

## 12b. Also not built yet

Score/best-time persistence, any story or characters, and no index pointer on the dial (§5).

---

## 13. Code map

    source/
      main.lua      state machine, crank read, tumbler logic, HUD, screens, transitions
                    Run.mods / Run.has(id) — the rolled modifiers, for the effects work
      dial.lua      Art.*  — dial, vault door, dial well, timer plate, modifier cards,
                    manga SFX baking, progress dots, fonts, icons
      modifiers.lua Mods.* — the 12 modifiers, their icons, pair scoring. Data + art only
      images/modifiers/          12 standalone 14x14 icons
      images/mod-icons-table-14-14.png  the same 12 as an imagetable (loads as images/mod-icons)
      sound.lua   Sfx.*  — samples, synths, BGM
      sounds/     tick, sweet, sweet-fake, cleared, bgm, nightclub, ambience, footstep
      pdxinfo     name=Safu, bundleID=com.vincent.safu

---

## 14. Performance

The play screen must fit **20 ms per frame** to hold 50 fps. Measured on the device (not the
simulator — the simulator runs on the host CPU and reports roughly 50x faster):

| Stage | Before | After |
|---|---|---|
| Modifier cards | 27.21 ms | baked |
| Dial | 10.98 ms | 10.98 ms |
| Door | 2.91 ms | baked |
| Timer plate chrome | 1.73 ms | baked |
| Dial well | 1.49 ms | baked |
| **Whole frame** | **44.32 ms (22 fps)** | **15.70 ms (50 fps)** |

The cards were the cost: three concave-polygon fills each, plus `drawTextInRect` and
`getTextSizeForMaxWidth`, which are pure-Lua text layout re-run every frame.

**The rule: nothing static gets drawn per frame.** The door, the dial well, the timer plate chrome
and the three modifier cards are drawn once into `bgImage` at `startGame()` and blitted. Only the
dial (it rotates), the timer digits, the Ⓐ prompt and the manga SFX are live. `bgImage` is
invalidated by setting it to `nil` — do that if anything static changes mid-run.

To measure: wrap `pd.update` in `pd.resetElapsedTime()` / `pd.getElapsedTime()`, write the average
to a file with `pd.file.open`, and read it back from
`/Volumes/PLAYDATE/Data/com.vincent.safu/` after `pdutil <port> datadisk`.

---

## 15. Deploying to the device

`pdutil` has **no `install` action** — only `datadisk`, `recoverydisk` and `run`, and `run` takes a
path *on the device*. Copy the build over the data partition:

    pdc source Safu.pdx
    pdutil /dev/cu.usbmodemPDU1_XXXXXXX datadisk
    rsync -a --delete Safu.pdx/ /Volumes/PLAYDATE/Games/Safu.pdx/
    find /Volumes/PLAYDATE/Games/Safu.pdx -name "._*" -delete
    diskutil eject /Volumes/PLAYDATE
    pdutil /dev/cu.usbmodemPDU1_XXXXXXX run /Games/Safu.pdx

The Playdate's port is the one named `cu.usbmodemPDU1_*`. Other `cu.usbmodem*` ports on the machine
are different devices — `pdutil` accepts them and fails quietly. Piping `pdutil` into `tail` hides
its exit code, so check `$?` on the command itself.

---

## 16. What "good" means

The prototype succeeds if simply turning the crank for a few minutes feels satisfying:

- The dial feels physically attached to the crank.
- Slow rotation gives distinct mechanical detents; fast rotation gives a satisfying rip.
- A sweet spot is instantly recognisable, and a graze is instantly distinguishable from a hit.
- Reversing direction feels natural.
- Three hits form a satisfying short arc, and pulling the handle feels like a commitment.
- The player immediately wants to beat their time.

The design question is not *"is there enough content?"* — it is **"does turning this dial feel good?"**
