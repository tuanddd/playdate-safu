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
- The player must **press D-pad Down to pull the handle**. Pulling it before all 3 are found resets the
  whole progress.

---

## 3. Current build at a glance

| | |
|---|---|
| Dial | 0–99, front-facing, recessed in the vault door at (122,128) r=52 |
| HUD | The screen **is** the safe door: timer plate, dial well, 3 modifier plates |
| Sweet spots | 3 to find; one real spot is generated at a time |
| Directions | CW → CCW → CW |
| Timer | **3 minutes** (counts down, `mm:ss.cc`) |
| Open the safe | Press D-pad Down after all 3 are found |
| Refresh rate | 50 fps |
| Screens | Title → Play → Win / Lose → (Ⓑ) → Title |
| Tutorial | **Ⓑ on the title** — 2 scripted untimed runs: bare dial, then BLACKOUT alone |
| Modifiers | 3 rolled per run — **effects and custom UI both live** |

### Tuning constants (`source/main.lua`)

| Constant | Value | Meaning |
|---|---|---|
| `GAME_MS` | `180000` | Run length, 3 minutes |
| `Spots.MIN_GAP` | `18` | New real spot's minimum circular distance from the current dial and fixed decoy; defined in `source/spots.lua` |
| `DEG_PER_UNIT` | `3.6` | Crank degrees per dial unit → **1 crank revolution = 1 dial revolution** |
| `TOL` | `2.2` | Sweet spot half-width in dial units (full zone is 4.4 units ≈ 15.84° wide) |
| `Keypad.LENGTH` | `4` | Directional inputs required to secure each spot with KEYPAD |
| `Keypad.HOLD_TOL` | `4.4` | Allowed distance from a found spot during arrow entry: ±15.84° of crank rotation |
| `cfg.maxEngage` | `25` | Max speed to latch — 25 units/**sec** ≈ **90°/sec**. Per-run, so it lives in `Mods.buildCfg`, not `main.lua` |
| `RESET_SPEED` | `80` | Speed above which progress resets — 80 units/sec ≈ **288°/sec** |
| `DEAD_SPEED` | `1.5` | Below this the dial counts as stationary |
| `TICK_STEP` | `4` | A tick every 4 dial units → 25 ticks per revolution |
| `DIRS` | `{1, -1, 1}` | Required direction per tumbler |
| `EXIT_MS` | `420` | Length of the slide-up back to the title screen |
| `TITLE_AUTO_UPS` | `11` | Title screen: dial units per second while the dial turns itself, clockwise |
| `TITLE_IDLE_MS` | `4000` | Title screen: silence from the crank before auto turning resumes |
| `TITLE_LATCH_MIN/MAX` | `2600` / `5200` | Title screen: gap between the auto-turn's idle latches |
| `DROP_IN/HOLD/OUT_MS` | `300` / `100` / `300` | Sound-cue entrance, hold and exit — 700 ms in total |
| `DROP_MAX` | `2` | Most sound cues on screen at once; they may never overlap |

---

## 4. Screens & flow

### Title
Full-screen background plate (`source/images/title-screen-bg.png`, `Art.titleBg`) blitted at
0,0, then the rotating dial (r=62 at 200,126) + big `SAFU` logotype + two calls to action drawn
on top of it. The crank already ticks here, so the mechanism is alive before the run starts.

- **Ⓐ CRACK IT** — a normal run: three modifiers rolled, three minutes on the clock.
- **Ⓑ TUTORIAL** — the scripted pair of untimed runs, below.

The two pills are **sized to their own labels** (`ctaWidth` / `drawCta`) rather than to a fixed
width, so the row stays centred and balanced if either label ever changes.

`sounds/title.wav` (`titleBgm`, volume `0.35`, 93.6 s) loops under it. `Sfx.titleAudio()` starts
it — on cold boot and on every route back to the title — and always from the top; `Sfx.bgmStart()`
stops it as the run begins. It is a separate `fileplayer` from `bgm`, so coming back to the title
never has to know which of the three run tracks was loaded.

The plate is a brick wall with a round vault door set into it — stone jamb, voussoir joints,
16 bolts, dithered door face — standing on a receding floor, with the two masked robbers at
the left and right edges. The dial, wordmark and CTA are cut out of it as white, following
each element's actual contour plus a 3px halo, so the three live elements drop into their
holes with no seam. Generated by `images/svg/gen-title-variants.py` (variant 14 +
`plate()`); regenerate there, never by hand.

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
    │        ↓ OPEN?         ╚════════════╝ │
    │ · · · · · · · · · · · · · · · · · ·  │
    └──────────────────────────────────────┘

| Element | Where |
|---|---|
| Timer plate | (24,20), sized from the fixed string `00:00.00` so it cannot twitch |
| Dial well | (122,120) r=64, 25% dither, 2px rim |
| Dial | (122,120) r=52 — centred in the door's inner area (y 8–232) |
| Modifier plates | x=232, y=20 + i·68, 140x58, corners **scooped inward** (r=6) |
| ↓ OPEN? | centred under the dial at y=186 |
| Ⓑ MENU | directly below it at y=204 |

Card fill, shadow and outline are all the **same polygon** (`notchedPoly` in `dial.lua`), so the
checkered shadow follows the scooped corners instead of squaring them off.

Each plate is two rows: a 14x14 icon centred against the title, then the subtitle wrapped to **at
most 2 lines**. Title and subtitle are the same family at two sizes and weights —
**Nontendo-Bold 13** over **Nontendo-Light 13** — same size, one weight apart. `FOUR TUMBLERS` is the widest title that fits; there is
no smaller weight to fall back to, so names must stay at or under 13 characters.

`Run.mods` is rolled in `startGame()` via `Mods.roll(3)`, and `Mods.buildCfg` turns the set into
`Run.cfg` — the tunables the run plays by. Effects and their visuals are both implemented (§12b).

**There is no progress indicator during normal play or the BLACKOUT tutorial.** The player tracks their own progress from the
audio/visual cues. `↓ Open?` is therefore a genuine gamble.

### Tutorial

**Ⓑ on the title screen.** Two scripted runs, in order, both **untimed** — the clock is drawn as
`--:--.--` and never moves, so nothing can end a tutorial run except opening the safe.

| Step | Modifiers | Teaches |
|---|---|---|
| 1 | **none** | The dial on its own: turn, feel the detents, hear the latch |
| 2 | **BLACKOUT** only | One modifier, alone, so it is the only new thing to read |

**The right column guides the player.** Lesson 1 replaces the empty modifier area with one
148×194 scooped plate at (226,20), using the existing card fonts and checkered shadow.
`TUTORIAL 1/2` and `No timer. Take your time.` frame a live instruction and a `0 / 3 SPOTS FOUND`
readout. This is the only lesson that reveals progress:

| Event / progress | Instruction |
|---|---|
| Start | `FIND A SWEET SPOT` — turn clockwise slowly; a loud click and dial shake mean a sweet spot; find 3 to open |
| First latch | `NICE! ONE FOUND` — turn counterclockwise slowly and listen for another loud click |
| Second latch | `ONE MORE TO GO` — clockwise again, slowly; listen for one last loud click |
| Third latch | `YOU FOUND ALL 3!` — stop turning the crank and press D-pad Down to open |
| Graze | `TRY A SLOWER TURN` — the turn was too fast and progress reset; try clockwise more slowly |
| Overspeed | `EASY DOES IT` — turning too fast makes you start over; turn clockwise slowly to find the first spot |
| Early Down | `NOT READY YET` — opening too soon resets progress; find all 3 spots first, starting clockwise slowly |

The tutorial calls the goals **sweet spots**, and teaches the loud click and dial shake that
identify one. It uses full sentences and small encouragements instead of mechanism jargon or
requiring the player to interpret the `K-CHIK!` sound-effect lettering.

Error instructions remain until the next successful latch (or another error), so the player can
read them at their own pace. The count follows the real tumbler state; an error returns it to
zero even if it happened before the first latch. Pausing and docking preserve the instruction.
The panel draws after manga SFX so latch lettering cannot cover the instructions.

Lesson 2 keeps its **BLACKOUT card** in the top slot and fills the two slots below with a
148×126 instruction plate headed `TUTORIAL 2/2`: turn clockwise slowly, turn the other way after
clicks 1 and 2, press Down on click 3, and start clockwise again if progress resets. The BLACKOUT
card above explains that it is too dark to see and to listen for loud clicks. These instructions are
**static**, including on hits, errors and completion: the player must learn to count by ear.
They appear in the lit opening and through the flashlight with the card once it turns on;
the existing fade and dark beat still hide the whole room. No dial or live progress cue is
added to BLACKOUT.

`source/tutorial.lua` owns copy, error feedback and cached panel images. Lesson 1 changes its
image only on a latch or error; lesson 2 is baked into the run background. Text layout is never
repeated per frame. `startGame` clears tutorial feedback for every entry into a new run.

The win screen carries the sequence:

- Step 1 cleared → the panel says `TUTORIAL / 1 OF 2` and **Ⓐ says NEXT**, which starts step 2.
- Step 2 cleared → the panel says `TUTORIAL / 2 OF 2` and **Ⓐ says NEW GAME**, which rolls a
  normal run — the same thing Ⓐ on the title screen does. Finishing the tutorial therefore costs
  no extra press.

**Ⓐ is labelled for what it will actually do, three ways:** `NEXT` while a tutorial step is left,
`NEW GAME` on the last step, and `AGAIN` outside the tutorial. `AGAIN` on the last step would
promise a replay of the BLACKOUT run and deliver a random one.

`TUTORIAL` is the step table and `tutorialStep` is nil for every normal run. **`startGame` clears
`tutorialStep`, and `startTutorial` sets it after the call** — so no other entry point (the debug
picker, Ⓐ on a win, Ⓑ to the title) has to remember to reset it, and a stale step cannot leak into
a normal run.

`Run.untimed` is the flag, also cleared by `startGame`. Only two things read it: `updatePlay`, which
stops decrementing `remaining`, and `timerText()`, which draws dashes. **Dashes, not a frozen
`03:00.00`** — a clock that is not moving reads as a bug, one that is not there reads as the rule
it is. Nothing else in the game special-cases an untimed run: `remaining` keeps its full value, so
the win panel and the timeup check need no changes.

Losing a tutorial step is not reachable (untimed, and BLACKOUT has no lose condition), but Ⓐ on the
lose screen restarts **the same step** rather than rolling a random run, so the path is not a trap
if a future step adds a modifier that can end a run.

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
3. Panel, top to bottom: the SFX word (`TIME'S UP` / `CAUGHT!` / `BOOM!`) / `TUMBLERS FOUND` /
   the progress dots / the run's modifiers as chips / `Ⓐ TRY AGAIN` / `Ⓑ TITLE`.

**The lose panel is not the win panel.** `TUMBLERS FOUND` is set one size down (`Art.numFont`,
Roobert-10-Bold) rather than in the win panel's `Art.uiFont`, and sits 38 px above the dots
instead of 28: it labels the dots, it is not the headline — the SFX word above it is.

**The modifier recap.** Below the dots, the panel replays the modifiers the run was played under
as a centred row of **chips** at y=172 — one pill per modifier, 20 px tall, 8 px apart, each a
1 px white rounded-rect outline (radius 10) around its 14x14 icon and its name in `Art.subFont`,
with 8 px of padding either side. The plates are gone with the scene the panel slid over, so this
is what tells the player what beat them.

The outline is doing the legibility work: three filled white pills would out-shout the SFX word
the panel is built around, and an unenclosed row reads as one long string of icons and words
rather than three separate things. There is deliberately **no rule** between the dots and the
chips — the outlines already close the section off. If the names cannot fit 388 px (never true at
three modifiers, possible if the count is ever raised) the chips shrink to icon-only pills. The
win panel has no such section — a cracked safe does not need excuses.

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

**Only one real sweet spot exists at a time.** The dial starts at a random position
(`rawPos = math.random(0, 99)`). `spawnTarget()` calls `Spots.pick` to choose the active `target`
uniformly from the integer positions 0–99 that are **at least 18 dial units from the current
dial position**, measured around the circle. With DECOY, it must also be at least 18 units from
the fixed fake spot. A real latch discards this target and spawns the next one from the newly
snapped dial position. After the final latch, `target` is nil. FOUR TUMBLERS changes the required
count to four; it does not place more targets on the dial at once.

`Spots.pick` lists the valid positions in one bounded 100-position pass and chooses one. Two
18-unit exclusion arcs cannot cover the circle, so a candidate always exists. There is no
retry limit, placement failure, or silent loss of a modifier. The exclusions move with the dial,
so no fixed sector of the dial becomes permanently safe to skip.

**DECOY is a fixed landmark.** At run start, its position is chosen first, at least 18 units from
the starting dial. All later real targets avoid it. Its position and armed state persist across
latches and resets; finding or ignoring it does not spawn a new real spot. Thus FOUR TUMBLERS +
DECOY means four real latches to earn, one at a time, with one recurring fake spot alongside them.
It does not guarantee exactly five sounds: the fake may be missed or crossed repeatedly.

**A loss of progress starts a fresh search.** A graze, overspeed, or early handle pull after one
or more real latches clears the count and generates a new first target away from the current
dial. Previously found real positions are not replayed. Required directions and the decoy stay
the same for the run. At zero progress, errors keep the existing target so spinning or pressing
Down cannot repeatedly reroll the search. A zero-progress graze stays disarmed until leaving its
zone; a newly spawned distant target is armed immediately.

WANDERING moves only the active real target while the dial is still. With DECOY it reflects at
18-unit clearance from the fixed fake, so the real and fake zones cannot merge. Without DECOY,
the target can drift freely around the circle. Drifting under a stationary dial still cannot
latch until the player actually turns the crank.

Per frame, in order:

0. `speed > RESET_SPEED` → reset progress to tumbler 1, `RESET!`. This still applies after
   all three are found, which is why the tutorial says to stop cranking before pressing Down. *(§7)*
1. `tumbler > cfg.tumblers` → **stop** all sweet spot detection, including the decoy.
   An active KEYPAD bubble instead checks its hold range and returns (§6b). Otherwise check
   the fixed decoy, then the current real target below.
2. Not inside `±TOL` of the current target → **re-arm** and stop.
3. Not armed → stop. *(prevents re-triggering while sitting inside the zone)*
4. `speed < DEAD_SPEED` (1.5 units/sec) → stop. *(can't latch a stationary dial)*
5. Wrong direction → stop.
6. `speed > MAX_ENGAGE_SPEED` → **graze**. *(§7)*
7. With KEYPAD, **begin arrow entry** (§6b); otherwise **hit**.

On a hit:
- The dial **snaps exactly onto the target** (via `posOffset`), so it lands on a clean number.
- 220 ms decaying screen shake (`sin`/`cos`, amplitude 4.5 → 0).
- `sweet.wav` + a `K-CHIK!` manga SFX placed randomly around the dial.
- Advance to the next tumbler and spawn a new real target at least 18 units away, armed.
  On the final latch, remove the real target and stop fake clicks too. The existing overspeed
  reset still applies until the player presses Down.

### 6b. KEYPAD: find, hold, enter

The correct approach direction and ordinary entry speed/tolerance still apply. Entering a real
spot with KEYPAD snaps the dial to its center, opens a **four-arrow speech bubble**, and plays
the quiet UI hover cue. It does **not** shake, play the real latch sound, or advance the count.

Keep the crank within **±4.4 dial units** of that spot and enter the displayed D-pad directions
in order. The hold range is twice the normal entry tolerance, leaving room to settle the crank
after discovering the spot. A marker in the bubble shows the signed offset and both limits.
The crank remains live and one-to-one; the game does not lock the player's input.

- Each accepted arrow inverts its cell; an underline marks the next arrow.
- One wrong direction clears **only the arrow progress**, plays the supplied `sound-fxs/error.ogg`
  through `sounds/keypad-error.wav`, and displays `TRY AGAIN / START FROM THE FIRST ARROW`.
  The spot, code, and earlier real latches remain intact. There is no separate input deadline.
- Leaving the hold range dismisses the bubble and clears arrow progress. Find the same spot
  again using the required approach direction; it keeps the same code. Normal global overspeed
  resets still apply, so a wild spin can still lose earlier latches.
- Four correct inputs perform the normal real latch, including its sound/shake and the next
  target spawn. Only that final feedback counts as a found spot.
- Codes are generated once per new real target. Adjacent repeated directions are allowed and
  require separate taps. Retry errors and ordinary departures never reroll a code.
- A chord/diagonal is a single invalid input, never an arbitrary choice of one direction.
  Release all directions to continue after a chord. Holding a direction never auto-repeats.

**Input ownership prevents accidental opening.** While the bubble is active, all D-pad input
belongs to it. A frame that dismisses or completes the bubble also consumes its input, including
Down. The player must release the D-pad before a later fresh Down can pull the handle. Direction
buttons held when the bubble appears must first be released. A is inactive during play.

Pausing or docking suspends entry and the run clock. The normal run clock continues during
active entry. WANDERING freezes the acquired target while its bubble is open and resumes
wandering after the player leaves. GUARD still checks crank movement only, so a stopped player
can enter arrows during a guard warning.

`source/keypad.lua` owns code/progress/retry state. `Keypad.updateInput` in `main.lua` handles
device input after the crank/zone checks, so an out-of-range final arrow cannot latch a spot.
`source/keypad-ui.lua` owns the cached speech bubble: body `(28,121)` at `186×76`, an upward tail
toward the dial hub, a 4px checkered shadow, four native 16px arrows, and a live position marker.
It covers the lower dial and hides the open prompt while keeping the timer, modifier cards,
upper dial, and menu prompt visible. The bubble draws above ordinary SFX; its static image is
rebuilt only when the code, accepted count, or error state changes.

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
If progress was lost, the fresh first target is armed; at zero progress the grazed target stays
in place and disarmed until the player leaves its zone.

**Reset — `speed > RESET_SPEED` anywhere.**
Cranking wildly resets progress to tumbler 1 with `RESET!`. Punishes spinning the crank to brute
force the dial.

At tumbler 1 neither gate can cost progress (there is none), and neither rerolls the target.

---

## 8. The handle (D-pad Down)

D-pad **Down** pulls the handle during play, except while the crank is docked, BLACKOUT is
opening, or a KEYPAD sequence owns the D-pad:

- **All 3 found** → the safe opens.
- **Otherwise** → `LOCKED!` + a two-note thud, and **progress resets to tumbler 1**.

Down uses the left thumb while the right hand stays on the crank. A retains its title, menu
and end-screen actions, but does nothing during play.

The handle intentionally reverses the original crank-only design. It converts a pure execution task
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
- **Modifiers** opens the catalogue of **all 10**, not just the run's three — a reference the
  player can browse. Two pages of six, laid out 2 columns x 3 rows, each cell carrying the same
  icon + title + subtitle as a door card. Left/Right (or Up/Down) flips pages, Ⓐ or Ⓑ goes back.
- The panel is sized to its content: `menuBox()` measures **every** string that has to fit, each in
  the font it will be drawn in — including the subtitles, which are wider than the names above them.

---

## 9. Feedback

### Audio (`source/sound.lua`)

| Sound | Source | Notes |
|---|---|---|
| `tick` | `tick.wav` | **6 round-robin voices** so fast cranking never cuts itself off. Rate `0.94 + speed*0.05` + random jitter, volume `gain("tick") * (1 + speed*0.2308)` — faster cranking is higher and louder |
| `sweet` | `sweet.wav` | Full volume, unpitched. The K-CHIK |
| `graze` | `tick.wav` @ rate 0.45 | Deliberately a *dulled* tick — the near miss |
| `handle` | `sweet` then `cleared.wav` after 1 s | The opening sequence |
| `locked` / `fail` / `reset` / `start` | square-wave synths | Two- and three-note descending motifs |
| `bgm` | `bgm.wav` | Loops during play, stops on win/lose |
| `titleAudio` | — | Every route back to the title calls it: it silences the run's music and is the single place a title track should start |
| `uiConfirm` | `ui-confirm.wav` | Going *in*: opening the menu, entering the catalogue, Quit |
| `uiBack` | `ui-cancel-back.wav` | Coming *out*: Resume, leaving the catalogue, Ⓑ to the title |
| `uiHover` | `ui-hover.wav` | The cursor moving between menu rows, and catalogue page flips |
| `keypadError` | `keypad-error.wav` | Supplied `sound-fxs/error.ogg`, converted to mono 44.1 kHz 16-bit PCM; wrong-arrow retry, with visible reset |

KEYPAD also uses the quiet `uiHover` cue for discovery and accepted intermediate arrows;
the real `sweet` sound is reserved for a completed code. Rebuild the error asset with:

    ffmpeg -i sound-fxs/error.ogg -ar 44100 -ac 1 -c:a pcm_s16le source/sounds/keypad-error.wav
| `flashlight` | `flashlight-turn-on.mp3` | BLACKOUT's opening only. Never ducked. Trimmed to 0.32 s; two clicks 210 ms apart |

#### The mix — one table, `Sfx.mix`

**Every level the game can emit lives in `Sfx.mix` and nowhere else.** Nothing in `main.lua` or
`modifiers.lua` sets a volume any more; they name a sound or a track and the mix supplies the
level. That is what makes the debug **Audio** page possible — one table to edit, live, and hear.

Levels are stored **in dB on a 0..40 scale: 0 dB is silence, 40 dB is the device maximum.**

    linear = 10 ^ ((dB - 40) / 20)          0 dB -> 0, forced silent

This is **not dBFS.** The SDK exposes no gain above unity on `sampleplayer` / `fileplayer` /
`synth:playNote`, so full scale is a hard ceiling and the useful way to express a level is as a
height above silence, not an attenuation below a ceiling you can never exceed. The scale runs
**one display dB per real dB**: 40 dB is unity, 20 dB is −20 dBFS, and 0 dB sits at −40 dBFS,
which is silent on the device speaker and is forced to a hard zero anyway. A sound still too quiet
at 40 dB has to be fixed in the asset (see `ui-cancel-back`, below).

**`Sfx.gain(id)` is the only way to read a level.** Nothing outside `sound.lua` touches `Sfx.mix`
except the debug page.

| Entry | dB | Entry | dB |
|---|---|---|---|
| `tick` | 28.4 | `footstep` | 40.0 |
| `graze` | 34.0 | `flashlight` | 40.0 |
| `sweet` | 40.0 | `uiConfirm` | 40.0 |
| `decoy` | 40.0 | `uiBack` | 40.0 |
| `wrong` | 24.0 | `uiHover` | 33.0 |
| `locked` | 29.6 | `bgmTitle` | 30.8 |
| `reset` | 28.4 | `bgmDefault` | 21.6 |
| `fail` | 29.6 | `bgmClub` | 40.0 |
| `handle` | 40.0 | `bgmNight` | 28.4 |
| `cleared` | 33.0 | `start` | 29.6 |
| `keypadError` | 40.0 | — | — |

**These defaults are not precious.** They are the pre-mixer levels converted across; the debug Audio
page exists to replace them by ear.

Two levels are **multiplied**, not replaced, so an entry set to 0 dB really is silent:

- `tick` scales its speed term (`* (1 + s*0.2308)`) instead of adding to it. 0.2308 reproduces the
  old `+0.06`-at-full-speed curve exactly.
- `sweet` / `decoy` multiply their mix level by `mechVol`; TOO LOUD skips both voices entirely.

`Sfx.mixList` is the same set again as an **ordered, labelled list** — that is what the debug page
walks. The four beds carry a `track` field; everything else is a one-shot.

UI sounds are keyed to **intent, not to the button**. Ⓐ on `Resume` plays the *back* sound because
it leaves the menu; Ⓑ opening the menu plays *confirm* because it goes in. `↓ OPEN?` during play is
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

#### Sound cues — one entrance for both (`drops` in `main.lua`)

TOO LOUD's `// note \\` and GUARD's `// \\` are the same event to the player - something outside
the safe made a noise - so they animate identically. `Art.makeSlashes(icon, scale)` builds both
(the only difference is the glyph between the pairs) and returns a **drop set**: six scale steps
from 80% to 100%, rather than the rotation frames a wiggle set carries.

The entrance, 700 ms end to end, all of it ease-out (`easeOut()`, cubic):

| Phase | Length | Y | Opacity | Scale |
|---|---|---|---|---|
| In | `DROP_IN_MS` 300 ms | fully above the top edge → `DROP_REST_Y` 34 | 20% → 100% | 80% → 100% |
| Hold | `DROP_HOLD_MS` 100 ms | 34 | 100% | 100% |
| Out | `DROP_OUT_MS` 300 ms | 34 → 24 | 100% → 0% | 100% |

Rules: at most `DROP_MAX` = 2 alive at once, and a new one is only placed where it clears every
live cue by `DROP_GAP` - stacked cues read as one smear. `addDrop()` makes 14 attempts inside the
strip and gives up rather than overlap.

**The strip is chosen so a collision is impossible rather than repaired.** `DROP_L`-`DROP_R`
(118-221) is the gap between the clock badge with its dropped shadow (which ends at x=113) and the
card column (whose border starts at x=225); `addDrop()` insets it further by the cue's own
half-width, so no part of a cue can ever reach either. Nothing load-bearing sits under one, so
nothing has to be drawn back over the top of it.

That strip is 103px against an 84px cue, so the second slot is usually refused and one cue at a
time is the normal case. Widening it means crossing the clock or the cards; a second visible cue
would have to come from smaller art, not a wider band.

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

**Icons:** modifier icons, the clock, and Ⓐ/Ⓑ buttons are 14x14. The four user-supplied D-pad
arrows stay at their native 16x16 size, copied unchanged into `source/images/dpad-*.png`. Down
replaces A in the open prompt, whose alignment now measures each icon's actual size. KEYPAD
has a cached 14x14 six-button icon drawn by `Mods.iconImage`.

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
| 5:00 timer | **3:00** | 5 min was slack even for a ~20 s loop; 1:00 left no room once three modifiers were stacked on it |
| Crank-only, no buttons | **D-pad Down pulls the handle** | Adds a real decision + a way to fail by nerve, not just by clock |
| `○ ○ ○` progress shown during play | **Hidden** (shown only on the lose screen) | Forces the player to track their own count; makes Down a gamble |
| Tolerance ±1 (36–38) | **±2.2** | Tuned to how precise the crank actually feels |
| No speed rules | **Graze + reset gates** | The "turn too fast" rule — gives fast cranking a real cost |
| Tick per dial unit | **Every 4 units** | 100/rev was mush; 25/rev reads as distinct detents |
| Door swings open | **Panel slides down** over a frozen scene | Cheaper, and reads well at 1-bit |
| No title screen | **Title screen** with a live, tickable dial | Mechanism is alive before you press start |
| No music | **Looping BGM** at low volume | — |
| "No audio tool available" | **Real WAV assets** in `source/sounds/` | Obsolete note; assets exist |

---

## 12. Modifiers

Ten active modifiers. **Every normal run draws 3.** Their effects are implemented below.

### The set

| # | Name | Axis | Tags | Icon | What it does |
|---|---|---|---|---|---|
| 1 | **BLACKOUT** | Perception | `channel` | `eye` + slash | The dial is not drawn. Crack it by ear |
| 2 | **TOO LOUD** | Perception | `channel` | `volume-high` | Ticks ducked to near-silent under loud club BGM |
| 6 | **SCRAMBLED** | Memory | — | `arrow-left-right` | `dirs` randomised per tumbler instead of `{1,-1,1}` |
| 7 | **FOUR TUMBLERS** | Memory | `time` | `lock` | 4 real latches instead of 3, generated one at a time |
| 8 | **WANDERING** | Memory | — | `compass` | The active real target drifts while you are *not* cranking, reflecting before it reaches the decoy. **Drift ≤ `Mods.MAX_DRIFT` (5 units/sec)** |
| 9 | **DECOY** | Risk | — | `help` | One fixed fake spot: a click ending in a buzz, no dial shake, no progress |
| 10 | **ONE SHOT** | Risk | `fail` | `skull` | A wrong Down handle pull ends the run instead of resetting progress |
| 11 | **GUARD** | Event | `fail` | `bell` | Footsteps: stop cranking within 3 s or you're caught |
| 12 | **NITRO** | Body | `fail` | `flask` | Tilt left/right to keep the liquid from spilling; a spill ends the run |
| 13 | **KEYPAD** | Input | — | six-button keypad | Hold a found spot while entering four visible D-pad arrows to latch it |

### Player-facing descriptions

Modifier names keep their character; descriptions explain what changes or what to do in plain
language. These are the exact two-line descriptions shared by the door cards, pause catalogue
and debug picker. Each line fits the narrowest text column (110 px) in Nontendo-Light:

| Modifier | First line | Second line |
|---|---|---|
| BLACKOUT | It is too dark to see. | Listen for loud clicks. |
| TOO LOUD | The clicks are silent. | Watch for dial shakes. |
| SCRAMBLED | Try both directions | for each sweet spot. |
| FOUR TUMBLERS | Find 4 sweet spots | then press Down. |
| WANDERING | Sweet spots move | when you stop turning. |
| DECOY | Fake clicks end in a | buzz, with no shake. |
| ONE SHOT | Press Down too soon | and you lose. |
| GUARD | When you hear steps, | stop for 3 seconds. |
| NITRO | Tilt to keep the | liquid from spilling. |
| KEYPAD | Hold the dial still. | Enter the arrows. |

The clicks in this copy are the sweet-spot sounds taught in the tutorial, not the quiet ticks
while the crank turns. TOO LOUD mutes those sounds, so it directs attention to the dial shake.
DECOY explains both clues to its fake spot. GUARD asks for a full three-second stop, and NITRO
asks the player to balance the liquid rather than hold the device still. DECOY names the audible
buzz introduced with the one-at-a-time target change.

**Icons are chosen and exported.** 14x14, 1-bit, transparent: eight hand-drawn on the 14 grid,
four from [Pictogrammers Memory](https://github.com/Pictogrammers/Memory). Assets live at
`source/images/modifiers/<icon-id>.png` and as the imagetable
`source/images/mod-icons-table-14-14.png`; `images/icons-manifest.json` maps id → file, and
`images/README.md` documents the pipeline. Contact sheet: `images/hud-modifier-icons.png`.

`source/modifiers.lua` carries the catalogue (id, name, sub, icon, axis, tags), the icon loaders,
the pair-scoring rules as `Mods.pairClass` / `Mods.score` / `Mods.roll`, and per-run configuration
through `Mods.buildCfg`. Effect behavior lives in `main.lua`. Its rule tables reproduce the
41 banned / 25 hard / 54 normal split stated below; change the two together.

### Modes and combinations

Axes are **flavour, not rules** — they were only ever a proxy for "these conflict." Compatibility
is now judged directly, per pair, and drives two modes.

**Every pair of modifiers is classified once:**

| Class | Weight | Meaning |
|---|---|---|
| **banned** | — | Impossible, overloaded, or the combination defeats a modifier's purpose. Never offered in normal rolls |
| **hard ×2** | 2 | On its own makes a run hard mode |
| **hard ×1** | 1 | Needs a second friction to qualify |
| normal | 0 | Everything else — 28 of the 45 pairs |

**A drawn triple is scored by its three pairs:** any banned pair → discard; total ≥ 2 → **HARD**;
otherwise → **NORMAL**.

**120 possible triples → 41 banned, 25 hard, 54 normal. 79 playable runs.**

**Ten active modifiers.** HAIR TRIGGER, GREASED and STICKY were cut after playtesting: all
three were the same idea — degrade the player's control of the dial — and the loop already
punishes speed errors brutally, since a graze and an over-speed both wipe progress. So they never
added a challenge, they multiplied an existing punishment. They failed the test the rest of the
set passes: **a modifier has to hand the player a new way to play, not worse hands.** Revising was
not an option, because every "make the dial harder to control" idea lands in the same place.
KEYPAD fills one replacement slot; two remain open.

#### Banned — incompatible or counterproductive (6 pairs)

| Pair | Why |
|---|---|
| BLACKOUT + TOO LOUD | Both continuous channels gone; only discrete SFX text remains |
| TOO LOUD + GUARD | GUARD's *only* warning before a hard game over is audio, and TOO LOUD exists to bury audio |
| BLACKOUT + NITRO | The water layer would have to render over a pitch-black screen with no readable contrast, while a hidden tilt limit kills the run |
| KEYPAD + BLACKOUT | The required visible arrow sequence cannot be read |
| KEYPAD + NITRO | User-requested ergonomic exclusion: holding the dial, entering arrows, and balancing liquid overload the hands |
| KEYPAD + DECOY | A bubble appears only at real spots, immediately giving the fake away. Excluded to preserve DECOY's purpose, not because the pair is too hard |

#### Hard ×2 — stacked death (3 pairs)

ONE SHOT + GUARD · ONE SHOT + NITRO · GUARD + NITRO

Two ways to lose instantly in one run. Beatable, but the run becomes about not dying.
All three together scores 6 — the signature hard-mode draw.

#### Hard ×1 — friction (8 pairs)

| Pair | Why |
|---|---|
| BLACKOUT + DECOY | BLACKOUT eats DECOY's *visual* tell — no dial means no missing shake. Audio tell survives |
| TOO LOUD + DECOY | The mirror: TOO LOUD buries DECOY's *audio* tell. Visual tell survives |
| TOO LOUD + SCRAMBLED | SCRAMBLED's wrong-direction tell is audio-only, so it gets buried |
| BLACKOUT + WANDERING | Targets moving with no visual reference |
| SCRAMBLED + WANDERING | Unknown direction *and* a moving target |
| FOUR TUMBLERS + WANDERING | Four successive drifting targets to catch on one clock |
| FOUR TUMBLERS + GUARD | More work against a clock that freezes |
| DECOY + ONE SHOT | A poisoned count where a wrong press is fatal |

#### DECOY's two tells are load-bearing

DECOY has one tell per channel — the distinct buzz at the end of `sweet-fake.wav`, and the
missing screen shake. **BLACKOUT removes the visual tell; TOO LOUD mutes the audio tell.** Either
alone leaves one cue, so both pairs remain allowed and classified hard. BLACKOUT + TOO LOUD is
still banned. The previous bass-only fake was too hard to distinguish on the user's device;
the new buzz is a concrete sound-design change, not a claim that measurements prove fairness.

#### KEYPAD's allowed pairings

- **WANDERING:** the acquired target freezes during entry; searching still has drift. This also
  keeps KEYPAD + WANDERING + GUARD answerable while the crank must be stopped.
- **GUARD:** D-pad entry is permitted while the crank is stopped. Guard warnings and deadlines
  continue; input errors themselves never trigger the guard.
- **TOO LOUD:** arrows, inverted progress cells, and the retry message provide complete visual
  feedback. Final latch shake remains visible, even when the latch sound is muted.
- **SCRAMBLED:** the correct crank direction is still needed to reveal the code.
- **FOUR TUMBLERS:** four spots, each with the same four-input code length.
- **ONE SHOT:** only a separate fresh Down outside entry can pull the handle. A wrong arrow
  or a Down on a completion/cancellation frame never becomes a fatal handle pull.

These six new allowed pairs have weight 0; existing pair weights still determine the triple's
mode. Extra typing alone does not create a hidden speed requirement or a new instant loss.

#### BLACKOUT and other UI tells

Under BLACKOUT only the timer and the three cards are lit, so any tell drawn elsewhere goes dark.

- **ONE SHOT + BLACKOUT is allowed.** The trembling Down element is invisible and that tell is
  deliberately sacrificed — ONE SHOT's rule is stated on its card, and the tremble is flavour
  rather than information the player needs to survive.
- **DECOY + BLACKOUT leaves exactly one tell.** With no `K-CHIK!` text and no shake, the player
  listens for the fake click's short buzz and keeps turning through it. Only real clicks advance
  progress. Device listening must validate the new contrast.
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
    ║   ↓ Open?          │ ◆ NAME    │ ║
    ║                    │   subtitle│ ║
    └══════════════════════════════════┘

Dial left, a column of three modifier cards right (icon + title + subtitle), everything wrapped in
a bordered container resembling the vault door. `CX`, `CY` and `R` all change; BLACKOUT and NITRO
are specified against this layout, so it lands first.

### The audio bed — one track, ever

This is about the **run** bed. The title screen has its own player (`titleBgm` / `sounds/title.wav`)
which is stopped before any run track starts, so the two can never overlap.

`bgm.wav` currently loops for every run at volume 0.12. TOO LOUD wants `nightclub.wav` loud and
GUARD wants `ambience.wav` looping, so all three would stack.

**They never can.** TOO LOUD + GUARD is a banned pair, so at most one of them is ever active.
That means there is exactly **one background slot**, chosen once at run start — no mixing, no
ducking between tracks, no priority logic:

| Active modifier | Track | Mix entry | Level |
|---|---|---|---|
| TOO LOUD | `nightclub.wav` | `bgmClub` | 40.0 dB — full playback volume |
| GUARD | `ambience.wav` | `bgmNight` | 28.4 dB, under the footsteps |
| neither | `bgm.wav` | `bgmDefault` | 21.6 dB |

`Sfx.bgmStart(track)` takes **only a track**; the single `fileplayer` swaps its file with `load()`
and looks the level up in `Sfx.mix` through an internal track→entry map. `Mods.buildCfg` therefore
names `bgmTrack` and no longer carries a `bgmVol` — a volume in two places is a volume that drifts,
and the debug Audio page has to own all of them.

**BLACKOUT needs no change here.** Its tell is the mechanism audio, and the default bed at 0.12
does not mask it — measured below.

### Nightclub loudness

TOO LOUD plays at `bgmClub = 40.0` (unity). The nightclub master uses +12 dB gain
and a −0.3 dB peak limiter (5 ms attack, 30 ms release, latency compensated).
Measured loudness is **−7.6 LUFS**, up 1.9 LU from the previous −9.5 LUFS master;
true peak is **−0.3 dBFS**. Stronger limiting makes the bed denser. The loop retains
1,303,949 samples at 44.1 kHz, mono, 16-bit PCM. The original MP3 is untouched.
Regenerate with:

```sh
ffmpeg -y -i sound-fxs/nightclub-bgm.mp3 -af 'aformat=channel_layouts=mono,aresample=44100,volume=12dB,alimiter=limit=0.966051:attack=5:release=30:level=false:latency=true' -ar 44100 -ac 1 -c:a pcm_s16le source/sounds/nightclub.wav
```

TOO LOUD **completely mutes real and fake latch voices**. Visual feedback carries
hit confirmation. Every run explicitly sets the latch mute flag, restoring normal
latches outside TOO LOUD. Ticks, graze and wrong-direction cues retain the 0.10 duck.
The handle opening sound is separate and retains its normal level.
Perceived loudness still needs a listening check on the device.

### Decoy sound: click followed by a buzz

The original real and fake files matched for their first 105 ms and differed mainly in bass.
The user's physical-device feedback was that they were almost indistinguishable. The earlier
claim that a 14 dB gap in the 80–110 Hz band proved fairness was unsupported by that experience;
frequency measurements alone do not establish what the player can hear.

`source/sounds/sweet-fake.wav` now uses the curated `sound-fxs/fake-obvious.wav` as its base and
adds a short **falling midrange buzz**. The real `sweet.wav` and curated originals are unchanged.
The first click still sounds mechanical, but the fake has an explicit audible ending to learn.
It is one click followed by a buzz, rather than two full clicks that could muddle the count.

| Parameter | Value |
|---|---|
| Buzz window | 165–305 ms into the fake sound (140 ms duration) |
| Fundamental | Linear sweep from 550 to 350 Hz |
| Harmonics | Fundamental / 3rd / 5th, relative weights 1 / 0.45 / 0.20 |
| Envelope | 8 ms attack, 32 ms release, half-cosine edges |
| Added buzz peak | 0.18, before PCM quantization |
| Output format | Mono 44.1 kHz, 16-bit PCM, 20,584 frames (0.466757 s) |
| Whole sample peak / RMS | −2.66 / −22.68 dBFS; zero clipped samples |

The buzz window has 25.44 dB more energy above 600 Hz than the corresponding real-click tail.
This measures the files, not the Playdate speaker or perceived difficulty. **Device listening
still needs to establish whether the cue is clear enough during BLACKOUT.** That pair stays
allowed with its existing hard classification; no modifier bans or scoring changed.

Rebuild deterministically with `python3 scripts/build-decoy-sound.py`. Add
`--comparison /tmp/safu-decoy-comparison.wav` to export the real click, 0.7 seconds of silence,
then the new fake. The buzz is baked into the existing sample, so the same player, mixer level,
stop behavior, and TOO LOUD mute cover the entire cue; no delayed callback can outlive it.
Pause → Debug → Audio has adjacent LATCH and DECOY rows, with A to replay. Compare them from an
ordinary or BLACKOUT run: TOO LOUD deliberately mutes both, including their auditions.

### 12b. Effects layer — implemented

`Mods.buildCfg(mods)` returns one `Run.cfg` table holding every tunable a modifier touches,
defaulted to the unmodified game. `main.lua` reads `Run.cfg.x` instead of a constant, so no effect
needs a special case at its call site.

| Field | Default | Set by |
|---|---|---|
| `drawDial` `showEffects` `shake` | `true` | BLACKOUT → all false *(renderer reads these; not yet consumed)* |
| `bgmTrack` `bgmVol` `mechVol` | `sounds/bgm` `0.12` `1.0` | TOO LOUD → nightclub/1.00/0.10 · GUARD → ambience/**0.26** |
| `tumblers` | `3` | FOUR TUMBLERS → `4` |
| `randomDirs` | `false` | SCRAMBLED |
| `keypad` | `false` | KEYPAD requires four D-pad inputs after finding each real spot |
| `drift` | `0` | WANDERING → `Mods.MAX_DRIFT` (5) |
| `decoy` `oneShot` `guard` `nitro` | `false` | their own modifiers |

**Where each effect lives**

- **FOUR TUMBLERS / SCRAMBLED** — `checkTumbler`, via
  `cfg.tumblers` and `Run.dirs`. SCRAMBLED also fires `Sfx.wrongDir()` — a soft low thud, once per
  entry into a zone, meaning *it is here but not this way*. Audio only, by design.
- **DECOY** — `checkDecoy`, run alongside the real tumblers. Latches like a real spot, plays
  `sweet-fake.wav`, shows the same `K-CHIK!`, and **never sets `shakeStart`**. The buzz in the tail
  and missing shake are its two tells. A fixed position is guaranteed when DECOY is active.
- **WANDERING** — `driftTargets`, only while the dial is under `DEAD_SPEED`. The active real
  target moves at 5 units/sec, reflecting at 18-unit clearance from the fixed decoy; it pauses
  while a KEYPAD bubble is open.
- **KEYPAD** — `checkTumbler` enters/validates the hold; `Keypad.updateInput` consumes arrows;
  `latchTarget` awards the real latch after completion. See §6b.
- **GUARD** — `updateGuard`. A footstep every 5–9 s, then `GUARD_GRACE_MS` (3000) to stop. Still
  moving when the grace expires and the run ends. The grace is what makes an audio-only hard-fail
  fair. The ambience bed sits well back at **0.26** so the steps cut through it: missing one is a
  hard game over, so it has to be the loudest thing in the run.
- **NITRO** — `updateNitro`. X axis only. The first 30 frames calibrate whatever angle the player
  actually holds the device at, so nobody is punished for their grip; past `NITRO_LIMIT` (0.35 g
  from neutral) the run ends. Exposes `Run.tilt` for the water layer to draw.
- **ONE SHOT** — `tryHandle`. A wrong pull calls `loseRun` instead of resetting progress.

**Ending a run early.** `loseRun(reason)` is the single path for every non-clock ending, using the
same slide-down as a time-out with a different word: `CAUGHT!` for ONE SHOT and GUARD, `BOOM!` for
NITRO. The lose panel draws `cfg.tumblers` dots, not always three, and lists `Run.mods` under them.

**Validation scope.** Automated checks exercise target placement, complete runs, resets, keypad
input ownership, and modifier compatibility. The ten-modifier catalogue has 41 banned / 25 hard /
54 normal triples. Hold tolerance, bubble readability, and error-sound balance still need playtesting
on the physical device; passing logic checks does not establish their feel.

The input suite passes 25 groups / 505,865 checks. SDK render checks cover the full-game bubble,
accepted arrows, retry, Down prompt, both tutorial panels, modifier picker, and audio mixer.
The simulator renders those screens but crashes on its scripted exit; an unchanged HEAD build
reproduces that exit crash too. The isolated graphics-only preview exits cleanly.

### Debug modifier picker

Pause menu → **Debug**, which is a branch rather than a page:

    Menu
     └ Debug
        ├ Screens      Safe open · Time's up · Caught · Boom
        ├ Modifiers    force any 3
        └ Audio        live mixer over Sfx.mix

**Screens** drops straight into a finished end screen. It builds the *real* panel — the clock and
tumbler count it reads are already set — so what you inspect is the shipping screen, not a mock of
it. The four end states are the only screens worth a jump: the title is already one Ⓑ away, the
docked notice appears by docking the crank, and the rest are reachable by playing.

**Modifiers** is the picker. A 2×3 grid over two pages of all modifiers; d-pad moves, Ⓐ toggles,
Ⓑ backs out to Debug. The cursor runs past the last modifier onto a **START** button, which only goes live
on exactly three picks — confirming is its own deliberate move, so a mis-tap on the third
modifier costs nothing. The header counts the picks and, once there are three, names the verdict
the pair rules give them.

**The page resets every time it is opened.** No debug run ever inherits the previous one's
selection.

The cursor **inverts** a cell and a pick **outlines** it, so both states read at once.

**Illegal sets are deliberately allowed.** Being able to force BLACKOUT + TOO LOUD and watch what
actually happens is the whole reason the tool exists, so the header labels the selection `BANNED`
rather than refusing it.

`startGame(forced)` takes the override; with no argument it rolls as usual, so the normal path is
untouched.

### Debug audio mixer

Pause menu → **Debug → Audio**. Every entry in `Sfx.mix`, one per row, edited in dB and auditioned
on the spot.

    ┌──────────────────────────────────────────────┐
    │ AUDIO                                   1/21 │
    │ ─────────────────────────────────────────────│
    │ ☞ TICK        ████████████░░░░░░    28.4 dB  │
    │   GRAZE       ██████████████░░░░    34.0 dB  │
    │   LATCH       ██████████████████    40.0 dB  │
    │   …                                          │
    │ ─────────────────────────────────────────────│
    │ DIAL DETENT                 Sfx.mix.tick = 28.4│
    │ L/R LEVEL   Ⓐ PLAY   Ⓑ BACK                  │
    └──────────────────────────────────────────────┘

- **Up/Down** move between sounds (wraps). 21 entries do not fit on 240px, so the list shows
  **8 rows** and scrolls to keep the cursor in view. Moving **silences** whatever the last row was
  playing — otherwise a bed keeps looping under the next entry.
- **Left/Right** move the level and **re-trigger the sound immediately**. Held, it ramps: 300 ms
  before the repeat starts, then a step every 55 ms — and after 1.2 s of holding, **0.5 dB a step**
  instead of 0.1, because 400 steps at 55 ms is a 22 second sweep.
- **Ⓐ** plays the selected entry again. No `uiConfirm` here — it would mask what Ⓐ is playing.
- **Ⓑ** hands the bus back and returns to Debug.

**The scale is the mix's own: 0.0 to 40.0 dB in 0.1 dB steps, 0 dB being silence.** The page edits
`Sfx.mix` directly — no conversion, no snapping, so the number on screen is the number in the table.
The grid index is held as an integer tenth so a run of presses cannot drift the value.

**The page owns the whole audio bus while it is up** (`Sfx.auditionBegin` / `auditionEnd`). It stops
the run's bed on entry so a level is judged on that one sound and nothing else, and restarts it —
still ducked, since the pause menu is still up — on the way out. Previews call the **real** `Sfx`
functions, so what you hear is exactly what the game will play.

One-shots and beds are re-triggered differently: a bed is already looping, so it only needs its gain
moved; a one-shot has to be **re-struck**, on a slower clock (260 ms) than the steps land on, or
holding the button is just a burst of noise. A last strike fires on **release**, so the value you
stopped on is always the one you last heard.

The footer prints the selected entry as `Sfx.mix.<id> = 28.4` — the exact line to paste back into
`sound.lua` once a level is settled on. **Nothing here persists**; the page is a listening tool, not
a settings screen.

**All of `Mixer`'s state, constants and helpers hang off one table.** `main.lua`'s main chunk sits
close to Lua's **200-local ceiling** (it was hit, at 220, on the first pass) — spelling this page
out as a dozen file locals does not compile.

### Menu audio

Opening the pause menu ducks the run's music to **28%** (`Sfx.bgmDuck`), so the run audibly moves
into the background; closing it restores the exact volume that run was using, whichever of the
three beds it happens to be. Quitting to the title stops the bed outright, and a new run's
`bgmStart` sets the volume fresh, so no path can leave it stuck ducked.

| Sound | Level | Why |
|---|---|---|
| `ui-cancel-back` | asset **+15 dB** (peak −8.3) | was ~7 dB under its siblings, and all three already play at full volume, so it had to be fixed in the asset |
| `ui-hover` | played at **0.45** | fires on every cursor move; at full volume a held d-pad turns the menu into a machine gun |
| `ui-confirm` | 1.0 | unchanged |

**`footstep` is normalised with `loudnorm`, not compression.** Missing a step is a hard game over,
so it has to be the loudest thing in a GUARD run, and the obvious `acompressor` + makeup-gain +
`alimiter` chain made it *quieter* — the limiter pulled the whole signal down faster than the gain
raised it. `loudnorm=I=-10:TP=-1.0` took it from mean −28.4 dB to **−20.2 dB** with a −1.0 dB peak
and no clipping. Reach for loudness targeting here, not a compressor chain.

### Performance probe

On the **system menu** (`perf` checkmark), because there is no spare button during play and the
numbers only mean anything on the device.

    50 FPS  work 6.2/9 of 20ms  bake 98  start 12

**It reports work, not the frame interval.** Interval is the obvious thing to measure and it is
almost useless: the SDK sleeps to hold the refresh rate, so a frame doing 4 ms of work and one
doing 19 both report 20 ms. Interval only ever tells you a frame was *dropped*. Work time tells
you how much room is left, which is the question worth asking before adding the next effect.

`bake` is the one-off image build (`buildBackground` / `buildBlackout`) and `start` is
`startGame` itself — audio load, target generation, the roll. Both are run-start costs, kept
separate from the per-frame number so a startup hitch cannot be mistaken for a frame-rate problem.

**A single bad frame reads as a full second of them.** The window is 50 frames, so one 120 ms
hitch sits in `worst` for a second before rolling out. Watch whether it recurs, not whether it
appears.

### 12c. Visual layer — implemented

Six modifiers draw something.

**BLACKOUT** — `buildBlackout()` bakes the whole dark room once. A flashlight at `(300, 272)`,
below the bottom edge.

**The room is dark, not empty.** A torch still picks the vault door out of the black, so the door
and its dial well are drawn through the beam — present, but far too dim to read anything off. The
dial itself is never drawn; only the fixed chrome is.

**The beam is a frustum, not a wedge.** Sweeping from a single point made it vanishingly narrow at
the source, which clipped the bottom card. It now starts from a base segment `BASE_HALF` (88) wide
— already wider than the card column — so the throw itself can stay tight at `CONE_HALF` (0.16 rad).

Three passes down that same cone, because the three things it touches want different curves:

| Pass | Range | Why |
|---|---|---|
| `BEAM` | 8%→32% | light hanging in the air, so the cone is visible in empty dark |
| `DOOR` | 10%→58% | falls away steeply, so the vault reads as picked out of the dark rather than floodlit |
| `CARD` | **78%→100%** | a card below ~70% loses its black text against the black room |

That high card floor is why the door needs its own mask: one shared curve either flattens the
door's falloff or makes the cards unreadable.

The timer is drawn after `clearStencil`, so the blackout never touches it. No dial, no shake, no
SFX text, no Down prompt: the run is played by ear.

**The opening.** A BLACKOUT run does not start dark — it *goes* dark, in front of the player, so
losing the dial reads as something that happens to them rather than a screen they were handed.
`blackoutClock` runs the sequence and the whole run is frozen for it: the clock does not count
down, no detent ticks, nothing can be latched. The crank is still read, so the dial does not jump
when play starts.

| Phase | ms | Screen |
|---|---|---|
| Lit | 400 | The normal room — door, dial, cards, HUD. `drawLitScene()`, the same path every other run uses |
| Fade | 650 | That room under a Bayer 8×8 dither thickening from nothing to solid black |
| Dark | 260 | `buildBlackoutDark()` — flat black, no cone, no timer |
| Click | 210 | Still dark. `Sfx.flashlight()` fired at the top of it |

At 1520 ms the cone layer replaces the dark one and the run begins. **The two layers are separate
images on purpose:** the cut from one to the other *is* the torch coming on, and there is nothing
to animate.

`flashlight.wav` is two clicks — the switch going down, then the beam catching — `BLACKOUT_CLICK_MS`
(210 ms) apart. The sound starts one gap before the cone appears, so the beam lands on the second
click. Retime that constant if the file is ever replaced. `buildBlackout()` is baked during the
dark phase, where a dropped frame cannot be seen, so the reveal itself is never a stall.

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

**ONE SHOT** — the `↓ OPEN?` prompt trembles, `sin(now()/26) * 1.6` px, forever. Flavour, not
information — the card already states the rule, which is why losing it under BLACKOUT costs
nothing.

**GUARD** — `Art.makeMarks` bakes the manga `// \\` with **no glyph between the strokes**, and the
pairs are spaced apart or they read as one four-stroke smear at this size. One fires every
`GUARD_MARK_MS` (320) for the **whole grace window**, not once on the step, so the warning is
present the entire time it is still answerable.

They are **pinned along the top edge**, not scattered around the dial: the steps come from outside
the room, and a cue that lands somewhere different every time reads as noise rather than a
direction. Built by hand rather than set in the SFX font, which has no slash
glyphs, but with the same frames/fades shape so it wiggles in and dithers out like `K-CHIK` does.

It does **not** lift the TOO LOUD + GUARD ban. The marks say a sound happened, not that it was
footsteps, and carry none of the three-second deadline that actually decides the run — so they are
atmosphere, not a telegraph, and no substitute for hearing the cue.

**NITRO** — `Art.drawWater` draws last, over everything. The surface is a **one-dimensional height
field**: 21 columns, each a mass on a spring pulled toward the tilted plane, each shoving its
neighbours twice per frame. That coupling is the whole point — it lets a disturbance travel across
the surface, pile up against an end and come back.

Summed sine waves were tried first and always read as a moving graph rather than liquid: a formula
has no memory of being disturbed, so nothing ever sloshes *from* anywhere.

Swinging the device injects velocity at the two ends (`wv[1] += kick`, `wv[N] -= kick`), the way
water climbs the side of a real glass. Held steady at any angle it flattens on its own. Tilt
itself is a separate damped spring, so the plane lags the device.

**Surges make it an active balance, not a stillness test.** Every few seconds the liquid is shoved
toward one end and held there for about a second, so holding the device dead level is no longer
safe — you have to tilt *into* a surge to cancel it and then recover as it passes. What spills is
the **water's** angle (`NITRO_SPILL`, 0.30 rad), not the device's; that distinction is the whole
modifier. Holding still through a single surge survives, but only just — measured, not assumed.

**The failure is armed late.** Calibration averages the first 30 frames, and a hand still moving
then produces a garbage neutral — the player would be killed a moment into a run for a tilt they
never made. `NITRO_ARM_FRAMES` (45) holds the fail condition back while the neutral keeps trimming
toward where they actually hold the device. The level itself is live and sloshing from frame one;
only the death is delayed. X axis only, so it is a left/right balance. Waterline sits at
`y = 210` and the fill is sparse: it is a hazard overlay, not a curtain, and burying the card
column would hide the run's own rules.

> **Why the game now spawns one real spot at a time.** The original rejection sampler could
> freeze while placing four targets. Its replacement built all real targets from bounded gaps,
> but left almost no room for DECOY's separate 18-unit spacing rule. In 10,000 four-tumbler runs
> checked before this change, zero fake spots spawned; the card still appeared and its effect
> silently disappeared. The current `Spots.pick` only has to avoid the current dial and fixed
> decoy, so it always finds room. Regression checks cover complete runs and modifier interactions,
> not just whether the initial generation terminates.

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

The cone is identical in every run — only the cards beneath it change — so both passes are baked
once per boot and reused (`Art.lightImages`). Eight dithered polygon fills at up to 350 px is the
expensive part of a BLACKOUT run's first frame, and paying it once instead of once per run is free.

Build: bake the cone once at load as a Bayer-dithered mask (density falling off with distance and
angle), then `gfx.setStencilImage()` so card drawing only lands inside the cone. Order: fill black
→ cards through the stencil → timer on top, unstencilled. Static mask, so it costs nothing per
frame. Skip `addEffect` at the call sites rather than just skipping `drawEffects`, so no effect
objects are allocated for something that can never be seen. The shake becomes moot on its own —
`shakeStart` only ever offsets the dial.

**Audio must cover every event, and it already does:** hit → `sweet.wav`, graze → the dulled
half-rate tick, reset → `resetVoice`, wrong handle → `lockedVoice`, movement → `tick.wav`. Five
events, five distinct sounds, no gaps. BLACKOUT is what the tick design was always for.

**2 · TOO LOUD** — `nightclub.wav` loops loud; mechanism sounds duck via a `cfg.mechVol`
multiplier of 0.10 inside `Sfx.tick/graze/wrongDir`. Real and fake latch sounds are
completely muted; visual feedback confirms the hit.
Adds a recurring **music-note SFX** (Pictogrammers *music-note*) that launches from the **top
edge** at a random diagonal, left or right, flanked by `// \\` emphasis strokes.

**6 · SCRAMBLED** — `Run.dirs` randomised per tumbler at run start. **No UI tell.** The wrong
direction cue is audio-only. Spawning a new real target or resetting progress keeps these directions.

**7 · FOUR TUMBLERS** — `cfg.tumblers = 4`; four real latches are required, generated one at a
time by `spawnTarget`. Direction count, handle readiness and end-screen dots follow that count.
The optional fixed decoy still exists alongside the one active real spot.

**8 · WANDERING** — drift the active target while `speed < DEAD_SPEED`, at 5 units/sec. Invisible.
With DECOY, reflect at its 18-unit clearance boundary so the two spots cannot overlap.

**9 · DECOY** — one guaranteed fixed fake target, chosen before the first real target. Fires
`sweet-fake.wav` (click then buzz) and the **same** `K-CHIK!` text, but **no dial shake**, progress
or direction advance. Fires again on a valid re-entry, so it is a learnable landmark. It survives
progress resets in the same place. Once every real spot is found, it stops firing.

**13 · KEYPAD** — the four-arrow spot confirmation in §6b. Wrong arrows retry only the code;
leaving the hold area requires reacquiring the same target. Its bubble is the visual layer;
BLACKOUT, NITRO, and DECOY are excluded from normal rolls with it.

**10 · ONE SHOT** — `tryHandle`'s failure branch jumps straight to lose, with a `CAUGHT` end
screen. UI detail: the **↓ Open? element trembles** — a fast, small, indefinitely repeating
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

Perception 2 · Memory 3 · Risk 2 · Event 1 · Body 1 · Input 1 — **Motor is empty**

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
      modifiers.lua Mods.* — the 10 modifiers, their icons, pair scoring. Data + art only
      tutorial.lua  Tutorial.* — lesson prompts, error feedback, cached guidance plates
      spots.lua     Spots.* — guaranteed active-target placement and drift around the fixed decoy
      keypad.lua    Keypad.* — one four-arrow code per real target, progress and retry state
      keypad-ui.lua KeypadUI.* — cached speech bubble, arrow cells, signed hold-range marker
      images/modifiers/          12 standalone 14x14 icons
      images/mod-icons-table-14-14.png  the same 12 as an imagetable (loads as images/mod-icons)
      sound.lua   Sfx.*  — samples, synths, BGM, and Sfx.mix: every level in the game
      sounds/     tick, sweet, sweet-fake (click + buzz), cleared, bgm, nightclub, ambience, footstep
      launcher/   card.png 350x155 · icon.png 32x32 · launchImage.png 400x240
      pdxinfo     name=Safu, bundleID=com.vincent.safu, imagePath=launcher

Run `luajit tests/keypad.lua` from the project root for the input/state/compatibility suite,
including the placement, complete runs, fixed decoys, resets, SCRAMBLED, and WANDERING checks
from `tests/spots.lua` against the game logic.
`scripts/build-decoy-sound.py` rebuilds the click-and-buzz sample; see §12 for its comparison option.

---

## 13b. Launcher art (`source/launcher/`)

`pdxinfo`'s `imagePath=launcher` points the system at the folder; `pdc` converts each PNG to `.pdi`
and copies the folder into the `.pdx`.

| File | Size | Where it shows |
|---|---|---|
| `launchImage.png` | 400 × 240 | Full screen while the game loads, and the last frame of the launch animation |
| `card.png` | 350 × 155 | The launcher carousel, in "cards" view |
| `icon.png` | 32 × 32 | The launcher list, in "list" view |

**The card and the launch image come from the art master, not from a live render.**
`images/title-bg-14-vault-brick.png` (400 × 240, with an `@4x` companion) is the finished title
composition — wall, vault, both robbers, dial, wordmark and CTA already in it.

Rendering them out of the running game was the first attempt and it was wrong: `title-screen-bg.png`
carries a **white knockout** where the live dial and wordmark get drawn, sized and positioned for
the title screen's own layout. Re-laying those elements out for a 350 × 155 card leaves the knockout
showing as an **empty contour** around the dial and behind SAFU. The master has no knockout, so it
crops and scales cleanly.

- **`launchImage.png` is the master, copied verbatim.** It is already exactly 400 × 240, and it
  matches the title screen the game draws a moment later, so the hand-off has nothing to flash.
- **`card.png` is the master scaled to 0.875, point-sampled.** 350 × 155 cannot hold the content
  1:1 — SAFU tops out at y≈8 and the dial bottoms out at y≈190, 182px of content in a 155px box — so
  the card takes `400 × 186 + 0 + 6` and scales it down.

      magick title-bg-14-vault-brick.png -crop 400x186+0+6 +repage \
             -filter Point -resize 350x155! -depth 1 card.png

  **`-filter Point` is the whole trick.** Area-averaging a 1-bit halftone and re-dithering the result
  (`-ordered-dither o4x4`) turns the vault's shading into speckle and the dial's numerals to mush;
  thresholding instead (`-threshold 70%`) blows the shading out to flat white. Point sampling just
  drops every eighth row and column, which keeps the dither texture and the line art crisp at the
  cost of a few broken hairlines nobody sees at card size.
- **`icon.png` is a purpose-drawn dial**, exported from the game with an offscreen-draw harness and
  `playdate.simulator.writeToFile(image, path)` (simulator-only). Downscaling the real dial to 32px
  turns the numerals and tick ring to mush, so the icon keeps only the silhouette: filled disc,
  white inner ring, 8 ticks, centre dot.

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
dial (it rotates), the timer digits, the Down prompt, KEYPAD bubble and the manga SFX are live. `bgImage` is
invalidated by setting it to `nil` — do that if anything static changes mid-run.
The first tutorial's guidance is a separate cached image selected on progress/error changes;
the BLACKOUT tutorial's static guide is baked alongside its modifier card.

To measure: wrap `pd.update` in `pd.resetElapsedTime()` / `pd.getElapsedTime()`, write the average
to a file with `pd.file.open`, and read it back from
`/Volumes/PLAYDATE/Data/com.vincent.safu/` after `pdutil <port> datadisk`.

---

## 15. Deploying to the device

`pdutil` has **no `install` action** — only `datadisk`, `recoverydisk` and `run`, and `run` takes a
path *on the device*. Copy the build over the data partition:

    pdc source Safu.pdx
    pdutil /dev/cu.usbmodemPDU1_XXXXXXX datadisk
    COPYFILE_DISABLE=1 rsync -rlt --exclude='._*' --exclude='.DS_Store' Safu.pdx/ /Volumes/PLAYDATE/Games/Safu.pdx/
    diskutil eject /Volumes/PLAYDATE
    pdutil /dev/cu.usbmodemPDU1_XXXXXXX run /Games/Safu.pdx

Verify the copied build files against the local build before ejecting. This copy does not delete
device files; any cleanup on the physical device needs the user's approval.

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
