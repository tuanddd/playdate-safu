# Safu — new modifier proposals

**SPOTLIGHT (8) and DUST JAM (9) are implemented in the game.** Their current mechanics and tuning
are documented in [SPOTLIGHT](game.md#6d-spotlight-tilt-to-inspect) and
[DUST JAM](game.md#6e-dust-jam-clear-a-stuck-spring-pin). The other eight ideas remain proposals.
This file retains the design exploration; proposed numbers are starting points, not tested tuning.

The strongest next experiments are **BALL RUN**, **WIND UP**, and **KNOCK KNOCK**: a physical toy,
a satisfying change of pace, and a small musical challenge. Prototype each alone before combining it.

## Hardware and presentation boundaries

Playdate has a **400×240, 1-bit screen**, crank, D-pad, A/B buttons, three-axis accelerometer,
mono speaker, and microphone. Every idea below uses those actual capabilities.
([Official hardware specifications](https://help.play.date/hardware/the-specs/))

The SDK exposes crank angle/change, held/pressed/released buttons, and three acceleration values.
Tilt controls should estimate gravity with filtering and calibrate a comfortable holding position;
these designs do not assume a gyroscope or physical force feedback.
([SDK input reference](https://sdk.play.date/inside-playdate/#_accelerometer),
[crank reference](https://sdk.play.date/inside-playdate/#_crank))

- **Any future mockup must first work at native 400×240.** Enlargement is only for presentation.
  Preserve the existing timer, three readable modifier cards, and B MENU. A challenge uses the
  existing approximately 186×76 bubble over the lower dial, with about 160×48 available for its toy.
  Use a few large shapes, 8px or larger moving pieces, and existing readable fonts. No tiny instructions.
- **B and crank docking still pause everything.** No proposal uses docking, Sleep, or Menu as a
  gameplay gesture. The SDK can detect docking, but Safu already assigns it a valuable pause behavior.
  ([Crank docking API](https://sdk.play.date/inside-playdate/#f-isCrankDocked))
- Use the **left-hand D-pad** for secondary controls, keeping the right hand on the crank.
  Do not require A or B while cranking. Down must never confirm a challenge and pull the handle
  on the same press; release and a new press are required after leaving a challenge.
- An acquired-spot challenge reserves that target, freezes WANDERING, and preserves earlier latches
  on a local mistake. The real latch sound happens only when the challenge succeeds. The run timer
  continues. If a challenge reassigns the crank to another mechanism, it temporarily disconnects
  the dial and its speed-reset checks; return without an accumulated crank jump.
- Initially exclude acquired-spot challenges from **KEYPAD / GEAR MESH / DUST JAM** (competing confirmations),
  **DECOY** (a real-only challenge identifies the fake), and **BLACKOUT** when visuals are essential.
  Test three-way combinations as well as pairs. These are proposed restrictions, not current roll rules.

## 1. BALL RUN — tilt a ball; crank a bridge

**Loop:** Finding a sweet spot reveals a tiny marble track. Tilt to roll an 8px steel ball toward
the exit; turn the crank to rotate one bridge that connects the two halves. Roll across and settle
the ball in the socket to secure the click. Each spot gets a different simple track orientation.

**Why it could be fun:** The Playdate becomes a pocket mechanical toy. One hand positions the bridge
while both hands gently steer the ball. The challenge has physical cause and effect the player can learn.

**Forgiveness:** Raised walls keep the ball on the board. Falling into the single drain respawns it
at the entrance; the bridge stays where you left it. No hard loss or lost earlier clicks.

**Native view / compatibility:** One channel, one bridge, one socket in the bubble—no miniature maze
full of branches. Exclude NITRO because both would demand different tilt responses. GUARD can work:
stop turning the bridge when warned; the ball may wait against a wall. Calibrate and test pitch/roll
with the device comfortably readable, rather than requiring it to lie flat.

## 2. WIND UP — charge fast, crack slowly

**Loop:** A spring powers the lock. Hold **Up** to engage its winding socket and spin the crank freely;
release Up to reconnect the ordinary dial and spend that charge searching. Start full. An initial
prototype could give two winding revolutions about twelve seconds of power, capped at twelve seconds.

**Why it could be fun:** Short, enthusiastic winding bursts punctuate delicate searching. Choosing
when to refill creates a rhythm the player owns; quick cranking finally has a useful job.

**Forgiveness:** Empty power stops the dial mechanism until recharged; it never clears found spots.
Winding is an explicit separate mode, so its fast spins never trigger the normal overspeed punishment.
Drain power only while the lock is usable, not during pause or another modifier's forced wait.

**Native view / compatibility:** A spring gauge in the modifier plate plus a large winding symbol
over the lower dial while Up is held. Exclude GUARD initially because it orders the player to stop
the motion needed for power. Exclude KEYPAD / GEAR MESH until mode transitions have a clear rule.
With WANDERING, winding counts as stopping the safe dial, so the target drifts; state that interaction.

## 3. KNOCK KNOCK — answer the safe's rhythm

**Loop:** At a sweet spot, the safe knocks a three-tap phrase: for example, **tap-tap … tap**.
Repeat its spacing with **Up** to latch. The first player tap starts the comparison, so reaction
time after listening is irrelevant. The same phrase repeats on retry.

**Why it could be fun:** It feels like a mischievous safe talking back. Players reproduce a rhythm
instead of reading an arrow code, and can get quicker as the little phrases become familiar.

**Forgiveness:** Generous timing windows; a wrong phrase gets a soft wooden rattle and a replay.
No separate deadline or loss of earlier clicks. Three pads flash with the demonstration so hearing
is helpful without being the only usable channel.

**Native view / compatibility:** Three large knock pads and one short instruction fit the bubble.
GUARD permits answering because the crank is stopped. Start with TOO LOUD excluded to preserve the
call-and-response experience. BLACKOUT is a plausible later audio-only variant after device testing.

## 4. PINBALL — launch a bolt into its socket

**Loop:** A sweet spot opens a tiny pinball chamber. Turning the crank draws a spring plunger back;
reverse to ease it forward. **Down** launches the ball. Choose enough power to bounce it off one
sloped wall into a broad socket. Landing secures the click.

**Why it could be fun:** The crank measures a shot instead of merely moving a cursor. Watching a
slightly wrong shot carom off the wall invites an immediate, informed retry.

**Forgiveness:** A miss returns the ball to the plunger. The chamber does not reroll. No new speed
penalty, tilt requirement, or lost earlier clicks. Success should take seconds, not several ricochets.

**Native view / compatibility:** One 8px ball, one ramp, one cup; draw a clear spring-length gauge.
Use the shared challenge exclusions above. GUARD remains answerable by leaving the plunger alone;
Down may fire an already prepared shot while the crank is stopped. Exclude NITRO initially to keep
the first physical test focused on the plunger.

## 5. LOOT DROP — optional greed while cracking

**Loop:** After each secured click, three clock tokens fall across the left play area for two seconds.
Tilt left/right to slide a small sack beneath them while choosing whether to keep searching.
Each caught token adds two seconds, up to the run's original time limit. Each tumbler position
awards its shower only once per run; resetting progress never restores those bonus opportunities.

**Why it could be fun:** A click becomes a small celebration with an optional juggling opportunity.
The decision is whether six possible bonus seconds are worth dividing attention from the next spot.

**Forgiveness:** Missed tokens simply disappear. No hazard, mandatory catch, or lost progress.
Tokens never make the real dial harder to control.

**Native view / compatibility:** Three chunky falling shapes confined to the dial side; a short sack
track above B MENU. Exclude NITRO (opposing tilt goals), BLACKOUT (unreadable catches), and initially
KEYPAD / GEAR MESH (the shower would compete with the next challenge's space). Good first pairing:
FOUR TUMBLERS, where the extra work also creates an extra opportunity.

## 6. SHELL GAME — keep your eye on the bolt

**Loop:** At a sweet spot, a bolt drops under one of three cups. The cups make two or three readable
swaps. Choose a cup with **Left/Right**, then press **Down** to lift it and secure the click if right.
Each retry briefly reveals the bolt before repeating the same short shuffle.

**Why it could be fun:** It changes the challenge to visual tracking, with an obvious little reveal
and space for playful cup animation. It can be understood without reading a symbolic puzzle.

**Forgiveness:** The wrong cup goes back down; repeat the demonstration. Earlier clicks remain safe.
Keep motion trajectories separated and cap the shuffle speed rather than making misses mysterious.

**Native view / compatibility:** Three roughly 28px cups in the bubble; selection uses a thick frame.
Use the shared challenge exclusions. TOO LOUD is fine because every instruction is visual. GUARD is
fine because the player can stop cranking throughout the shuffle and selection.

## 7. DOUBLE AGENT — choose which lock to work on

**Loop:** The door has two lock cartridges: one needs two clicks, the other needs one. **Left/Right**
switches which cartridge the main dial drives; each remembers its dial position and next direction.
Crack them in any order, then pull the usual handle. There is still one large dial and three total clicks.

**Why it could be fun:** The player chooses a route through the work. A promising cartridge can be
finished first, or parked when it becomes awkward. Progress is remembered by the player across two
small jobs instead of one fixed chain.

**Forgiveness:** A speed error resets only the active cartridge. The finished cartridge stays secured.
An early handle pull keeps the existing normal/ONE SHOT consequence; this must be stated explicitly.

**Native view / compatibility:** Two clear cartridge tabs above the dial, showing selection but no
live completion count. Exclude FOUR TUMBLERS until its split is designed, and KEYPAD / GEAR MESH
until switching ownership is resolved. SCRAMBLED is an interesting later pairing; WANDERING should
affect only the active cartridge so off-screen drift does not become bookkeeping.

## 8. SPOTLIGHT — aim your own light

**Implemented:** tilt to reveal the real pin while cranking normally. The inspection gives a clue;
light alignment is never required to latch. [Actual simulator output](images/spotlight-revealed-400x240.png).

Original Imagegen reference: [native 400×240](images/modifier-concept-spotlight.png) ·
[4× pixel preview](images/modifier-concept-spotlight@4x.png). These are concept images, not game captures.

**Loop:** A small inspection beam reveals the safe's interior through a window beside the dial.
Gently tilt to sweep the beam. When it passes over the active target's physical pin, the pin glints;
keep cranking normally to search and latch. The beam gives a useful clue but needs aiming.

**Why it could be fun:** The player actively discovers information with their hands. It adds a
second way to investigate the safe rather than suppressing the existing feedback.

**Forgiveness:** Missing the pin costs only an opportunity to see the clue. Normal clicks and dial
visibility remain. No darkness timer, death threshold, or demand to hold a precise angle to latch.

**Native view / compatibility:** A small cutaway replaces the lower-dial bubble region while the
main dial's upper face stays readable. Exclude NITRO (two incompatible tilt jobs), BLACKOUT (opposed
visual premise), and DECOY (revealing the real pin exposes the fake). WANDERING lets the player
rediscover a moving pin. DUST JAM, KEYPAD and GEAR MESH are allowed: their confirmation bubbles
temporarily replace the inspection, which returns when searching resumes.

**Implemented moving-beam rendering:** A solid core and two restrained Bayer bands stay inside a
160×48 window. Thirty-one beam directions share the same fixed pixel pattern and are selected from
smoothed tilt with hysteresis. The beam shape moves while its dither dots stay in place. The revealed
pin is a solid 9px shape with a glint. This follows the existing cached BLACKOUT stencil approach;
its hardware frame cost still needs measurement.
([Panic's dither-flashing guidance](https://help.play.date/developer/designing-for-playdate/#dither-flashing))

## 9. DUST JAM — blow dust out of the dial

**Implemented:** the microphone starts automatically when a jam appears; blow or hold Up to clear
dust for 1.4 accumulated seconds,
then the pin seats and earns one latch. [Actual simulator output](images/dust-jam-jammed-400x240.png).
The current compatibility rules and lifecycle behavior are in [game.md §6e](game.md#6e-dust-jam-clear-a-stuck-spring-pin).

Original Imagegen references: [dust jammed, native 400×240](images/modifier-concept-dust-jam-v2.png) ·
[pin latched, native 400×240](images/modifier-concept-dust-jam-cleared.png) ·
[dust jammed, 4× pixel preview](images/modifier-concept-dust-jam-v2@4x.png) ·
[pin latched, 4× pixel preview](images/modifier-concept-dust-jam-cleared@4x.png).
These are concept images, not game captures.
The earlier [plug](images/modifier-concept-air-lock.png) and
[balloon](images/modifier-concept-air-lock-balloon-v2.png) mockups are retained as discarded directions.

**Loop:** Finding a sweet spot reveals a close-up inside the dial: a spring-loaded pin with dust
packed beneath it, blocking its notch. Short puffs toward the microphone dislodge small clumps;
visible dust clouds escape from the mechanism. Once the obstruction is clear, the spring pushes
the pin into its notch: **K-CHIK!** secures one latch. The player may put the crank hand back on the
device while clearing the jam.

**Why it could be fun:** The player frees a visibly stuck part of the lock. Each puff removes
something tangible, and the pin snapping into place finishes the action with a satisfying mechanical
response. Neither shouting nor holding a musical note is required.

**Forgiveness:** Cleared dust stays cleared between breaths, and earlier clicks remain safe.
**Hold Up to clear dust** is a complete alternative. The microphone starts automatically at a jam,
with Playdate's access prompt if needed and no extra A press. This
measures input level, not words, pitch, or actual breath; a pause between puffs never resets the jam.

**Native view / compatibility:** One chunky spring, one pin, one notch, and a few large dust clumps
fit the existing 186×76 bubble. Show the actual mechanism clearly; remaining dust communicates progress
without a gauge. Caption: `BLOW OR HOLD ↑`. Card: `DUST JAM` / `Puff the dust away.` /
`Free the stuck pin.` Excludes KEYPAD / GEAR MESH, DECOY, BLACKOUT, NITRO (competing physical tasks),
and TOO LOUD (speaker playback contaminates input). SPOTLIGHT is allowed; the jam temporarily owns
its bubble. GUARD is allowed, with microphone clearing and calibration suppressed while footsteps
play; Up still works. The game calibrates room noise, mutes music while monitoring, stops listening
outside the challenge, and keeps Up available if microphone access fails. It reads input level
without recording or saving audio.
([Official microphone API](https://sdk.play.date/inside-playdate/#_mic_input))

## 10. INSURANCE — buy a second chance with time

**Loop:** After a secured click, the modifier plate briefly offers **Up: insure / −8s**. Buying it
protects the existing click count from the next speed reset: that mistake consumes the policy and
restarts the current search instead. At most one policy can be held; each secured target offers once.

**Why it could be fun:** The player judges their own confidence. Spending scarce time can rescue an
awkward run, but buying automatically slows every clear. It adds a decision, not another reflex test.

**Forgiveness:** Declining costs nothing. The policy covers dial mistakes only; it never silently
changes an early handle pull, GUARD, or NITRO loss. The offer closes on any reset, and cannot be used
when fewer than eight seconds remain.

**Native view / compatibility:** A short offer replaces the modifier subtitle; an obvious policy
stamp shows when protection is held, without a tumbler count. Exclude DECOY because a real-only offer
gives away the fake. FOUR TUMBLERS gives the time-versus-security choice more weight. ONE SHOT is
possible only with especially clear copy that handle pulls are not insured.

## First playable experiments

| Order | Prototype | What the physical Playdate session should answer |
|---|---|---|
| 1 | BALL RUN, alone | Can gentle, comfortable tilting steer a large ball while the crank controls one bridge? Is solving it satisfying within roughly 3–6 seconds? |
| 2 | WIND UP + FOUR TUMBLERS | Is the switch from fast winding to slow searching enjoyable, or does recharging become a chore after the second cycle? |
| 3 | KNOCK KNOCK, alone | Can three broad rhythms be heard on the built-in speaker and repeated without staring at timing marks? Does a retry feel fair? |

PINBALL is the next fallback if tilt-plus-crank coordination feels awkward. The implemented DUST JAM
still needs hands-on tuning for room noise and microphone ergonomics; its Up alternative is complete.
The eight remaining proposals should be prototyped before adding them to random runs.
