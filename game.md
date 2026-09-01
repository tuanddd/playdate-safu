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
| Dial | 0–99, front-facing, fills the screen |
| Sweet spots | 3, randomly generated per run |
| Directions | CW → CCW → CW |
| Timer | **60 seconds** (counts down, `mm:ss.cc`) |
| Open the safe | Press Ⓐ after all 3 are found |
| Refresh rate | 50 fps |
| Screens | Title → Play → Win / Lose → (Ⓑ) → Title |

### Tuning constants (`source/main.lua`)

| Constant | Value | Meaning |
|---|---|---|
| `GAME_MS` | `60000` | Run length, 1 minute |
| `DEG_PER_UNIT` | `3.6` | Crank degrees per dial unit → **1 crank revolution = 1 dial revolution** |
| `TOL` | `2.2` | Sweet spot half-width in dial units (zone is 4.4 units ≈ 7.9° wide) |
| `MAX_ENGAGE_SPEED` | `0.5` | Max speed to latch a tumbler — 0.5 units/frame ≈ **90°/sec** of crank |
| `RESET_SPEED` | `1.6` | Speed above which progress resets — 1.6 units/frame ≈ **288°/sec** |
| `TICK_STEP` | `4` | A tick every 4 dial units → 25 ticks per revolution |
| `DIRS` | `{1, -1, 1}` | Required direction per tumbler |
| `EXIT_MS` | `420` | Length of the slide-up back to the title screen |

---

## 4. Screens & flow

### Title
Rotating dial (r=62) + big `SAFU` logotype + `Ⓐ CRACK IT`.
The crank already ticks here, so the mechanism is alive before the run starts.

### Play
    ┌────────────────────────────┐
    │ ▓ 🕐 00:47.31 ▓            │   ← black rounded bar, top-left
    │                            │
    │           ( DIAL )         │   ← centred at (200,128), r=68
    │                            │
    │              K-CHIK!       │   ← manga SFX, random spot around dial
    │                            │
    │          Ⓐ Open?           │   ← bottom centre
    └────────────────────────────┘

**There is no progress indicator during play.** The player tracks their own progress from the
audio/visual cues. `Ⓐ Open?` is therefore a genuine gamble.

### Win
1. Screen shake + `K-CHUNK!` + sweet sound; BGM stops.
2. After 800 ms the live scene is captured, and a black panel **slides down over it** (460 ms,
   cubic ease-out) — the panel *is* the door opening.
3. Panel: `SAFE OPEN!` / `TIME LEFT` / frozen `mm:ss.cc` / `Ⓐ AGAIN` / `Ⓑ TITLE`.

### Lose
Timer hits `00:00.00` → black screen, `TUMBLERS FOUND` + the 3 progress dots revealing how far
they got, `Ⓐ TRY AGAIN` / `Ⓑ TITLE`, with the `TIME'S UP` SFX left on screen.

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

`startToTitle()` captures the live screen with `gfx.getDisplayImage()`; `drawToTitle()` then draws
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
- The pointer is fixed at the top; the numbered dial rotates underneath it.
- Rendering (`Art.drawDial`): black rim, white face, white rim notches every 2 units, black
  tick marks every unit with 3 weights (major every 10, medium every 5, minor otherwise),
  rotated `00`–`90` numerals baked once at load, and a 4-spoke hub that turns with the dial.

---

## 6. Sweet spot detection

Targets are generated at run start: 3 random values `0–99`, each **≥18 units from 0 and from
each other**, so no two tumblers sit on top of one another.

Per frame, in order:

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

Ⓐ pulls the handle at any time during play:

- **All 3 found** → the safe opens.
- **Otherwise** → `LOCKED!` + a two-note thud, and **progress resets to tumbler 1**.

This intentionally reverses the original crank-only design. It converts a pure execution task
into a decision: *"was that third K-CHIK real, or did I miscount?"*

Ⓑ during play toggles the FPS counter (debug only).

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

**Fonts:** Nontendo-Bold (dial numerals + tiny tik) · Bouncy-30 (manga SFX) ·
Asheville-Mono-Light-24 (timer) · Roobert-11-Medium (UI labels).

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

## 12. Not built yet

The replayability layer from §1 — **challenges/modifiers** — does not exist yet. There is one
safe, one difficulty, one run length. This is the main open design area.

Also absent: score/best-time persistence, more than 3 tumblers, any story or characters.

---

## 13. Code map

    source/
      main.lua    state machine, crank read, tumbler logic, HUD, screens, transitions, Sim hooks
      dial.lua    Art.*  — dial rendering, manga SFX baking, progress dots, fonts, icons
      sound.lua   Sfx.*  — samples, synths, BGM
      shots.lua   simulator-only screenshot harness (ENABLED = false)
      pdxinfo     name=Safu, bundleID=com.vincent.safu

`shots.lua` drives a scripted run in the simulator via the `Sim` table exported at the bottom of
`main.lua` and writes PNGs — useful for checking screens without touching the device. Flip
`ENABLED` to `true` and fix the hardcoded output path before using it.

---

## 14. What "good" means

The prototype succeeds if simply turning the crank for a few minutes feels satisfying:

- The dial feels physically attached to the crank.
- Slow rotation gives distinct mechanical detents; fast rotation gives a satisfying rip.
- A sweet spot is instantly recognisable, and a graze is instantly distinguishable from a hit.
- Reversing direction feels natural.
- Three hits form a satisfying short arc, and pulling the handle feels like a commitment.
- The player immediately wants to beat their time.

The design question is not *"is there enough content?"* — it is **"does turning this dial feel good?"**
