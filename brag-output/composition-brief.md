# Hyperframes Composition Brief: Safu

## Objective
Create a short launch-style brag video for Safu, a Playdate safe-cracking game played with the crank.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape — 1920x1080, 30fps
- Duration: 21.6 seconds

## Source Material
- Project root: `/Users/vincent/Desktop/work/playdate-test/safu`
- Primary files read: `AGENTS.md`, `game.md`, `source/modifiers.lua`, `marketing/itch/description.html`,
  `marketing/itch/reddit-post.md`, `marketing/itch/*.png`, `marketing/itch/*.gif`, `source/sounds/*`
- Product name: Safu
- Tagline / strongest claim: "Crack the safe. With the crank." — the crank *is* the dial, 1:1,
  with a tick for every detent.
- Key UI or visual moment to recreate: nothing is recreated. Every frame of product on screen is
  real captured footage or a real screenshot from the shipping build, cut out of
  `marketing/itch/safu-trailer.gif` and the four modifier GIFs, plus `shot-title.png`,
  `banner-960x240.png` and `device-hero.png`.
- Copy that must appear verbatim:
  - `THE CRANK IS THE DIAL.`
  - `A SAFE-CRACKING GAME FOR PLAYDATE.`
  - `TOO FAST? START OVER.`
  - `LISTEN FOR THE CLICK.`
  - `13 MODIFIERS. 3 DEALT PER RUN.`
  - `KEYPAD` / `NITRO` / `GEAR MESH` / `BLACKOUT`
  - `FREE FOR PLAYDATE`
  - `vincentconsole.itch.io/safu`

## Creative Direction
- Tone preset: cinematic
- Creative direction: 1-bit heist-film trailer, cut for a handheld
- Interpretation: black frames, big white type, few words, hard cuts landing on the game's own
  latch samples. Copy slams in over 0.28–0.34s and then holds past its reading floor; the pace
  comes from cuts and audio hits, never from pulling text early.
- Angle: every other Playdate game treats the crank as a joystick. Safu treats it as a safe dial,
  and the game is played by ear. Open on the dial alone with the game's real tick and real latch,
  let the mechanism sell itself, then show a real run, the modifier wall, and the safe opening.
- Hook: the real dial turning on black, ticking, with `THE CRANK IS THE DIAL.` slamming in — then
  a real latch at 2.35s that jolts the dial and punches `K-CHK!` over it.
- Outro / punchline: the real Playdate device render, the real `SAFU` wordmark, and the itch.io
  URL. No claim on the last card.
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Any colour, gradient, glow or gloss — the console is 1-bit and so is this video
  - Recreating game UI in HTML when real footage exists (it does, for every beat)

## Visual Identity
- Background: `#000000`
- Text: `#FFFFFF`
- Accent: none — emphasis is inversion, not hue
- Display font: Archivo Black, shipped locally at `assets/fonts/ArchivoBlack-Regular.ttf`
  (the game's own Bouncy/Nontendo are Playdate bitmap fonts and cannot be used on the web; the
  real `SAFU` wordmark is used as an image instead of being retyped)
- Body font: Archivo Bold / SemiBold, shipped locally at `assets/fonts/Archivo-*.ttf`
- Visual references from the project: the recessed 0–99 dial and its tick ring; the manga `K-CHK!`
  sound-effect lettering; the scooped modifier plates on the right rail; the `SAFE OPEN!` screen;
  the masked-robber title plate.
- Pixel rule: every media element is `image-rendering: pixelated` and every clip was upscaled with
  nearest-neighbour at encode time (400x240 → integer or near-integer multiples). Do not introduce
  smoothing, blur or CSS filters on game footage.

## Storyboard
Use the storyboard in `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. THE DIAL — 3.40s (0.00) — real dial rotating on black, ticking; `THE CRANK IS THE DIAL.`;
   latch jolt + `K-CHK!` at 2.35s
2. THE GAME — 2.76s (3.40) — real title screen footage; `A SAFE-CRACKING GAME FOR PLAYDATE.`
3. THE RULE — 5.70s (6.16) — real gameplay run; `TOO FAST? START OVER.` on the game's own TOO FAST,
   `LISTEN FOR THE CLICK.` on the first K-CHK!, held through K-CHUNK!
4. THE REPLAY VALUE — 4.60s (11.86) — `13 MODIFIERS. 3 DEALT PER RUN.` over a 2x2 wall of four real
   modifier clips arriving one by one
5. THE PAYOFF — 1.80s (16.46) — the real `SAFE OPEN!` screen
6. THE CARD — 3.34s (18.26) — device render, `SAFU` wordmark, `FREE FOR PLAYDATE`,
   `vincentconsole.itch.io/safu`

## Audio
- Audio role: cinematic support built entirely from the game's own sound design
- Audio arc: a dry ticking dial in the dark → the theme opens on the title cut → the theme steps
  back and the latches lead through the run → tiles accumulate → the clear jingle releases →
  the theme carries the end card alone and fades out
- Music: `assets/audio/music-title.mp3` — the game's own `source/sounds/title.wav`, loudness
  normalised to -18 LUFS, trimmed to 22s. The bundled Happy Beats library was deliberately not
  used: upbeat corporate music over a 1-bit noir heist game is a tonal lie.
- Music treatment: `data-start="0"`, `data-volume="0.30"`, 1.2s fade-in, 1.4s fade-out at the end.
- Music cue guidance: no bundled preset for a custom track. Beat grid detected at composition time
  with `npx hyperframes beats`. Advisory only — the edit is locked to the game's own latch samples,
  which are this product's actual rhythm. No tween is beat-locked to the music by design;
  the equivalent lock is `sweet.wav` on the exact frames where the shipping footage latches.
- Audio-reactive treatment: none, by deliberate creative choice. A 1-bit frame carries two values
  and no glow, depth or warmth to modulate; RMS-driven motion on a white plate reads as a flicker
  artefact, not as musicality. This is not an extraction failure — ffmpeg and the helper are
  available and were not used.
- Audio-coupled moments:
  - Scene 1, 0.20–2.16s — eight dial detent ticks 0.28s apart (simulated crank turn, game's own
    `tick.wav`)
  - Scene 1, 2.35s — the latch: `latch.wav` on the exact frame the dial jolts
  - Scene 2, 3.40s — `confirm.wav`, the game's own menu accept, on the cut to the title screen
  - Scene 3, 8.51s / 9.71s — `latch.wav` on each in-footage `K-CHK!`
  - Scene 3, 11.16s — `latch.wav` louder + `impactSoft_medium_001.ogg` on `K-CHUNK!`
  - Scene 4, 11.96 / 12.51 / 13.06 / 13.61s — `card-place-2.ogg` per modifier tile
  - Scene 5, 16.46s — `cleared.wav`, the game's own safe-opened jingle, on the cut
  - Scene 6, 18.81s — one soft impact under the wordmark slam
- SFX selection guidance: diegetic first. Every cue that the shipping game has a sample for uses
  that sample. Only two library files are allowed, and only where the game has no equivalent:
  weight under the `K-CHUNK!`, and a card-place under the modifier tiles.
- SFX analysis guidance: `<skill-dir>/assets/sfx/sfx-analysis.md` applies only to the two library
  files; both are low high-frequency risk.
- Exact SFX choice: fixed above, because the cue points are dictated by frames in pre-existing
  footage rather than by animation Hyperframes authors.
- Audio files: all copied into `brag-output/composition/assets/audio/`.

## Hyperframes Instructions
Load `hyperframes-core`, `hyperframes-animation`, `hyperframes-creative`, `hyperframes-keyframes`,
`hyperframes-cli`. This is the /brag workflow — do not enter the `hyperframes` entry-point intent
interview or route into its generic promo / launch-video workflow.

Requirements:
- Show real UI, copy and visuals from the source project. Every product frame in this video is real
  captured footage or a real screenshot; nothing is mocked.
- Keep all text readable in the final render (floors: short label ~0.8s settled, sentence ~0.3s per
  word with a ~1.2s minimum; the hook line gets the most).
- Duration 21.6s.
- Include the planned music/SFX layer.
- Music cue metadata is advisory; the game's own latch frames are the locks.
- Use local assets only — no absolute paths, no remote fonts or media.
- `npx hyperframes check` must pass with zero errors before render.
