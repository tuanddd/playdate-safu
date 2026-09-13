# AIR LOCK balloon revision — imagegen prompt

Generated 2026-09-08 using the imagegen skill and built-in Image Gen. Proposed mockup only.

- modifier-concept-air-lock-balloon-v2.png:400×240,1-bit native export.
- modifier-concept-air-lock-balloon-v2@4x.png:1600×960, exact nearest-neighbor enlargement.
- Edit reference: modifier-concept-air-lock.png.

Image Gen performed the composition and content edit. Native export uses point resampling and
50% black/white thresholding. The original generated image and prior plug concept are retained.

## Final prompt

Use case: precise-object-edit / ui-mockup. Input image 1 is the AIR LOCK mockup edit target. Redesign only its lower-left minigame and the top-right AIR LOCK card copy. Preserve the vault frame, rivets, timer, dial, WANDERING card, FOUR TUMBLERS card, B MENU, fonts, 1-bit style, and layout exactly.
Output ONE single Playdate screen with 5:3 aspect ratio and an actual400x240 logical-pixel layout; a1600x960 nearest-neighbor4x export is preferred. This is a proposed mockup, not a shipping screenshot. No page around it, no console/hands, no side by side panels.
Replace the unfamiliar pipe and square plug completely with a universally recognizable PARTY BALLOON that the player inflates with little puffs. Keep the existing white scooped bubble body at x28,y121,width186,height76 and its shadow. Inside it, centered near121,151, show a chunky black oval balloon about22px wide and28px tall, a small white highlight, a clear triangular tied neck, and a short curling string. Around the balloon show ONE dotted oval target outline about36px wide and40px tall, with an obvious5px gap around the current undersized balloon. It represents the size to inflate to. Make the balloon instantly recognizable at native resolution, especially its tied neck and curl. NO pipe, no socket, no square piston or plug.
Keep a small microphone symbol at x66,y148 with two soft puff curves pointing toward the balloon; it must be secondary to the balloon. To right of balloon, simple two short outward growth arrows may indicate expansion; do not add gauges, text labels, extra balloons, or a pop explosion. This state shows an undersized balloon being inflated, not a success or failure.
Top card exact text: "AIR LOCK". Exact two-line subtitle: "Puff up the balloon." / "Stop at the outline." Keep the microphone icon at14x14 native. Bottom bubble caption exactly "PUFF / HOLD UP", matching existing legible native pixel font and Up glyph. No Down input for this challenge. Keep all mechanics below y127 and above y178 so the bottom caption remains roomy at y181.
All visual forms use black and white only; sparse ordered Bayer dithering is allowed for shadows. No grayscale shading, no gradient, no anti-aliased typography, no color. Preserve text legibility and all other exact text. Do not make the bubble larger than the reference.

