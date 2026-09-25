# Brag Plan: Safu

## What is this app?
Safu is a Playdate game about cracking a safe where the crank *is* the dial — one turn of the
crank is one turn of the knob, and you find three sweet spots by ear before pulling the handle.

## The angle
Almost every Playdate game treats the crank as a substitute joystick. Safu's whole pitch is that
it doesn't: the crank is a physical safe dial, and the game is played with your ears. So the video
opens on the dial alone, in silence-adjacent black, with the game's *real* tick and *real* latch
sound, and lets the mechanism sell itself before a single feature is named. Everything on screen
after that is genuine 1-bit Playdate footage from the shipping build — no mockups, no renders of a
game that doesn't exist.

## Hook (first 2-3 seconds)
The real dial from the title screen, alone on black, turning slowly, ticking in the game's own
tick sample. One line slams in: **THE CRANK IS THE DIAL.** At 2.35s the game's real latch sample
fires, the dial jolts, and `K-CHK!` punches over it. That jolt is the whole game in one second.

## Key moments (the middle)
- The real title screen — two masked robbers, brick wall, vault door, `SAFU` — held long enough
  to register as a game and not a graphic.
- Real gameplay footage of an actual run: the dial turning, `TOO FAST` punishing a rush,
  two `K-CHK!` latches, then `K-CHUNK!` on the third. Two captions carry the rules over it.
- A 2×2 wall of four real modifier clips arriving one by one — KEYPAD, NITRO, GEAR MESH,
  BLACKOUT — under the claim `13 MODIFIERS. 3 DEALT PER RUN.` BLACKOUT's lights going out inside
  a tile is the strongest single frame in the scene.
- The real `SAFE OPEN!` end screen with the game's own clear jingle.

## Outro / punchline
The real Playdate device render with the game running, the `SAFU` wordmark, and
`FREE FOR PLAYDATE · vincentconsole.itch.io/safu`. No claim, no exclamation — the game already
made its case.

## User flow worth showing
Entry → key action → result, all from the shipping build's own capture:
1. **Entry** — title screen, dial already turning, `Ⓐ CRACK IT`.
2. **Key action** — turn the dial slowly, eat a `TOO FAST` reset, latch `K-CHK!` twice, then
   `K-CHUNK!` on the third spot while three modifier plates sit on the right rail.
3. **Result** — `SAFE OPEN! / TIME LEFT 02:47.36`.
The centrepiece scenes (3 and 5) are this flow verbatim; the modifier wall (scene 4) is the
replayability claim and the only scene that is a frame around the flow rather than the flow itself.

## Tone
- Preset: cinematic
- Creative direction: 1-bit heist-film trailer, cut for a handheld
- Interpretation: black frames, big white type, few words, hard cuts on the game's own latch
  sounds. The pace comes from the cuts and the audio hits, not from flashing copy — every line
  slams in fast (0.28–0.34s) and then holds well past its reading floor. No colour, no gradients,
  no gloss: the palette is the console's palette.

## Format: landscape — 1920x1080
## Duration: 21.6s

## Visual identity (from the project)
- Background: `#000000` (Playdate 1-bit black; the game's play screen is a black surround)
- Accent: none — the game has no third value. Emphasis comes from inversion (white plate on black).
- Text: `#FFFFFF`
- Display font: the game ships bitmap fonts (Bouncy, Nontendo) that cannot be used on the web, so
  added type uses **Archivo Black** (OFL, shipped locally) — a heavy grotesk that sits next to the
  game's chunky display lettering without pretending to be it. The real `SAFU` wordmark is used as
  an image (cropped from `marketing/itch/banner-960x240.png`), not retyped.
- Body font: Archivo Bold / SemiBold (OFL, shipped locally)
- Strongest visual element: the recessed dial with its 0–99 tick ring, and the manga `K-CHK!`
  sound-effect lettering that punches over it on a latch.

## Share copy (draft)
Safu — a Playdate game where the crank is a safe dial. Turn slowly, listen for the click, find
three sweet spots, pull the handle. 13 modifiers, 3 dealt per run. Free on itch.io.

## Audio direction
- Role: cinematic support built entirely from the game's own sound design
- Music: `source/sounds/title.wav` — the game's actual title theme, loudness-normalised to
  -18 LUFS and trimmed to 22s. The bundled "Happy Beats / Business Moves" library was rejected:
  upbeat corporate music over a 1-bit noir heist game is a tonal lie, and this game's identity is
  its audio.
- Music treatment: starts at 0.0 under the hook at 0.30 gain with a 1.2s fade-in, sits at 0.30
  through the body, fades out over the last 1.4s of the outro.
- Music cue guidance: no bundled preset exists for a custom track; beat grid detected at
  composition time with `npx hyperframes beats`. Cue use is deliberately minimal — the edit is
  locked to the game's own latch samples, which are the real rhythm of this product, not to the
  music's pulse. Treat detected beats as advisory only.
- Audio-reactive treatment: none. A 1-bit frame has two values; there is no glow, depth or
  warmth to modulate, and any pulsing of the white plate would read as a flicker artefact rather
  than as musicality. Documented here as a deliberate creative choice, not an extraction failure.
- SFX posture: sparse and diegetic. Every cue except two is a file lifted straight out of the
  shipping game: `tick.wav` (dial detent), `sweet.wav` (the latch), `cleared.wav` (safe opened),
  `ui-confirm.wav`. Two library files carry weight the game has no sample for: one soft impact on
  the `K-CHUNK!` and one card-place under the modifier tiles.
- Audio-coupled moments: the hook's ticking dial (8 ticks, 0.28s apart); the hook's latch jolt;
  the two in-footage `K-CHK!` latches and the `K-CHUNK!`; four modifier tiles arriving one by one;
  the `SAFE OPEN!` clear jingle.
- Restraint rule: no whooshes, no risers, no stingers that aren't in the game. If Safu can't make
  the sound, the video doesn't make it either.

## Storyboard

### Scene 1 — THE DIAL — 3.4s (0.0 → 3.4)
Black frame. The real dial, cropped from the shipping title screen, 560px, centred left-of-middle,
rotating slowly clockwise (0° → 26°, linear) — the same 1:1 feel the crank has. At 0.35s
**THE CRANK IS THE DIAL.** slams down from above (0.32s, power4.out) and holds 2.2s.
At 2.35s the dial jolts 12px and `K-CHK!` punches in at 1.15 scale beside it, holding 0.85s.
Sequential/interaction: yes — 8 dial detent ticks 0.28s apart, then the latch. This is a simulated
crank turn, played with the game's own samples.
Audio intent: mechanical, close, dry. The viewer should feel a physical object before seeing a game.
Audio-coupled idea: tick per detent; `sweet.wav` exactly on the jolt frame.
Music: game title theme, entering under it at 0.30 with a 1.2s fade-in.
Transition mood: hard cut → Scene 2

### Scene 2 — THE GAME — 2.76s (3.40 → 6.16)
The real title screen as footage (masked robbers, brick, vault door, `SAFU`, `Ⓐ CRACK IT`),
1600×960, scaling 1.05 → 1.00 over 0.5s. At 4.15s a lower line arrives on a black bar:
`A SAFE-CRACKING GAME FOR PLAYDATE.` — held 1.85s.
Sequential/interaction: none. The dial in the footage is already turning itself.
Audio intent: the theme opens up; the room gets bigger.
Audio-coupled idea: one `ui-confirm` accent on the cut, matching the game's own menu sound.
Transition mood: hard cut → Scene 3

### Scene 3 — THE RULE — 5.70s (6.16 → 11.86)
Real gameplay, 1600×960: dial turning, three modifier plates on the right rail, the clock running.
Two captions in the lower band, each timed to what the footage actually does:
- 6.81s `TOO FAST? START OVER.` — lands on the game's own `TOO FAST` overlay. Settled 1.30s.
- 8.51s `LISTEN FOR THE CLICK.` — lands on the first `K-CHK!`. Settled 3.00s, holding through the
  second `K-CHK!` (9.71s) and the `K-CHUNK!` (11.16s).
Sequential/interaction: yes — this is a real run being played; the captions annotate it rather
than narrate over it.
Audio intent: the latches are the beat. The music steps back and the mechanism leads.
Audio-coupled idea: `sweet.wav` on both `K-CHK!` frames (8.51s, 9.71s); `sweet.wav` louder plus one
soft impact on `K-CHUNK!` (11.16s).
Transition mood: hard cut → Scene 4

### Scene 4 — THE REPLAY VALUE — 4.60s (11.86 → 16.46)
Header: `13 MODIFIERS. 3 DEALT PER RUN.` at 11.91s, held 4.25s. Below it a 2×2 grid of four real
modifier clips (560×336 each) with a name under each, arriving one by one:
KEYPAD 11.96 · NITRO 12.51 · GEAR MESH 13.06 · BLACKOUT 13.61. Each tile fades and scales in over
0.3s and keeps playing to the end of the scene, so by 13.91s all four runs are moving at once.
Sequential/interaction: yes — four tiles arriving one by one, 0.55s apart, each with a card-place cue. Not snapped to the music grid: 0.55s is set by the reading floor for the tile labels.
Audio intent: accumulating. Four different games happening at once.
Audio-coupled idea: `card-place-2.ogg` per tile, first and last slightly louder.
Transition mood: hard cut → Scene 5

### Scene 5 — THE PAYOFF — 1.80s (16.46 → 18.26)
The real `SAFE OPEN! / TIME LEFT 02:47.36 / Ⓐ AGAIN Ⓑ TITLE` end screen, full 1600×960, punching
in 1.00 → 1.03. No added copy — the game's own screen is the line.
Sequential/interaction: none.
Audio intent: release. The game's own clear jingle over the theme.
Audio-coupled idea: `cleared.wav` exactly on the cut.
Transition mood: hard cut → Scene 6

### Scene 6 — THE CARD — 3.34s (18.26 → 21.60)
Black. The real Playdate device render (game running on the screen, `K-CHK!` visible on it) slides
in from the right at 18.36s and settles. On the left, stacked: the real `SAFU` wordmark (18.81s, slam),
`FREE FOR PLAYDATE` (19.21s), `vincentconsole.itch.io/safu` (19.61s). All three hold to 21.6s.
Sequential/interaction: none.
Audio intent: the theme carries alone, then fades out over the last 1.4s.
Audio-coupled idea: one soft impact under the wordmark slam.

**Music mood for this video:** cinematic — the game's own title theme, unaltered except for level.
**Audio summary:** a dial ticking in the dark, three latches, a safe opening, and the game's own
theme underneath the whole thing.
