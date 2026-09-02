// Six HUD layout experiments for the Safu play screen.
// Every one shows: the dial, the run timer, the Ⓐ prompt, and slots for exactly 3 modifiers.
const fs = require('fs');
const path = require('path');
const H = require('./hud.js');
const { txt, icon, dial, btnA, rivet, concaveRect, modCard, MODS, TIME } = H;
const OUT = __dirname;

const V = {};

/* ============================================================
   1 — VAULT DOOR
   The whole screen is the safe door (bank-safe.jpg): riveted
   plate, engraved timer plate, dial recessed left of centre,
   modifiers as three bolted-on name plates down the right.
   ============================================================ */
V['hud-01-vault-door'] = `
  <rect width="400" height="240" fill="#000"/>
  <rect x="3" y="3" width="394" height="234" fill="#fff"/>
  <rect x="3" y="3" width="394" height="234" fill="none" stroke="#000" stroke-width="2"/>
  <rect x="7" y="7" width="386" height="226" fill="none" stroke="#000" stroke-width="2"/>
  ${[...Array(13)].map((_, i) => rivet(28 + i * 28, 16)).join('')}
  ${[...Array(13)].map((_, i) => rivet(28 + i * 28, 224)).join('')}
  ${[...Array(6)].map((_, i) => rivet(16, 44 + i * 29)).join('')}
  ${[...Array(6)].map((_, i) => rivet(384, 44 + i * 29)).join('')}

  <!-- engraved timer plate, over the same flat checkered offset the cards use -->
  <rect x="28" y="28" width="120" height="26" rx="4" fill="url(#d50)"/>
  <rect x="24" y="24" width="120" height="26" rx="4" fill="#000"/>
  ${icon('clock', 29, 28, { fill: '#fff', scale: 0.8 })}
  ${txt(50, 43, TIME, 15, { mono: true, fill: '#fff', ls: 0.4 })}

  <!-- recessed dial well -->
  <circle cx="122" cy="128" r="64" fill="url(#d25)"/>
  <circle cx="122" cy="128" r="64" fill="none" stroke="#000" stroke-width="2"/>
  ${dial(122, 128, 52, 63)}
  ${btnA(98, 208)}${txt(112, 212, 'OPEN?', 12)}

  <!-- modifier plates -->
  ${MODS.map((m, i) => modCard(246, 34 + i * 58, 126, 44, m)).join('')}
`;

/* ============================================================
   2 — LEFT RAIL
   Black rail owns the left 112px: clock on top, three modifier
   cards under it. The dial gets the rest of the screen and is
   the biggest it can be while staying fully visible.
   ============================================================ */
V['hud-02-left-rail'] = `
  ${dial(262, 118, 82, 63)}
  <rect x="0" y="0" width="112" height="240" fill="#000"/>
  ${icon('clock', 8, 10, { fill: '#fff' })}
  ${txt(36, 27, 'TIME', 11, { fill: '#fff', ls: 1.4 })}
  ${txt(56, 50, TIME, 17, { mono: true, fill: '#fff', anchor: 'middle', ls: 0 })}
  <rect x="10" y="60" width="92" height="2" fill="#fff"/>
  ${txt(56, 76, 'MODIFIERS', 9, { fill: '#fff', anchor: 'middle', ls: 1.2 })}
  ${MODS.map((m, i) => {
    const y = 84 + i * 50;
    return `<rect x="6" y="${y}" width="100" height="44" fill="none" stroke="#fff" stroke-width="2"/>
      ${icon(m.icon, 12, y + 11, { fill: '#fff', bg: '#000', slash: m.slash })}
      ${m.name.split(' ').map((word, k, all) => txt(39, y + 26 + (k - (all.length - 1) / 2) * 12, word, 9.5, { fill: '#fff' })).join('')}`;
  }).join('')}
  ${btnA(232, 228)}${txt(246, 232, 'OPEN?', 13)}
`;

/* ============================================================
   3 — BOTTOM DECK
   Arcade console: dial floats high, a black deck across the
   bottom carries three chips. Nothing crowds the dial sides,
   so shake and manga SFX keep their room.
   ============================================================ */
V['hud-03-bottom-deck'] = `
  ${dial(200, 96, 74, 63)}
  <rect x="8" y="8" width="126" height="28" rx="6" fill="#000"/>
  ${icon('clock', 13, 11, { fill: '#fff', scale: 1 })}
  ${txt(40, 29, TIME, 16, { mono: true, fill: '#fff', ls: 0 })}
  ${btnA(346, 22)}${txt(358, 26, 'OPEN?', 12)}

  <rect x="0" y="184" width="400" height="56" fill="#000"/>
  <rect x="0" y="184" width="400" height="2" fill="#fff"/>
  ${[...Array(14)].map((_, i) => rivet(14 + i * 28, 192, { fill: '#fff' })).join('')}
  ${MODS.map((m, i) => {
    const x = 10 + i * 128, y = 198, w = 116, h = 34;
    return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="4" fill="#fff"/>
      ${icon(m.icon, x + 6, y + 6, { slash: m.slash })}
      ${txt(x + 33, y + 16, m.name, 11)}
      ${txt(x + 33, y + 28, m.sub, 8, { ls: 0.2 })}`;
  }).join('')}
`;

/* ============================================================
   4 — BOLT RING
   The three modifiers ARE the door's locking bolts: icon-only
   discs on short bolt-work spokes around the dial. Maximum
   dial, zero text furniture — the reading is diegetic.
   ============================================================ */
const bolts = [[104, 56], [296, 56], [200, 216]];
V['hud-04-bolt-ring'] = `
  ${bolts.map(([x, y]) => {
    const dx = x - 200, dy = y - 116, L = Math.hypot(dx, dy);
    const ux = dx / L, uy = dy / L;
    return `<line x1="${200 + ux * 74}" y1="${116 + uy * 74}" x2="${x - ux * 18}" y2="${y - uy * 18}" stroke="#000" stroke-width="6"/>
            <line x1="${200 + ux * 74}" y1="${116 + uy * 74}" x2="${x - ux * 18}" y2="${y - uy * 18}" stroke="#fff" stroke-width="2"/>`;
  }).join('')}
  ${dial(200, 116, 65, 63)}
  ${MODS.map((m, i) => {
    const [x, y] = bolts[i];
    return `<circle cx="${x}" cy="${y}" r="22" fill="#000"/>
      <circle cx="${x}" cy="${y}" r="17" fill="none" stroke="#fff" stroke-width="1"/>
      ${icon(m.icon, x - 11, y - 11, { fill: '#fff', bg: '#000', slash: m.slash })}
      ${[0, 90, 180, 270].map(a => rivet(x + Math.cos(a * Math.PI / 180) * 19.5, y + Math.sin(a * Math.PI / 180) * 19.5, { fill: '#fff' })).join('')}`;
  }).join('')}
  ${icon('clock', 10, 10)}
  ${txt(36, 27, TIME, 17, { mono: true, ls: 0 })}
  ${btnA(330, 222)}${txt(344, 226, 'OPEN?', 13)}
`;

/* ============================================================
   5 — LCD CONSOLE
   The iso-vault reference: modern safe with a readout panel.
   Timer lives in an inverted LCD window; the three modifiers
   are listed under it like alarm conditions.
   ============================================================ */
V['hud-05-lcd-console'] = `
  <rect x="0" y="0" width="400" height="240" fill="url(#d12)"/>
  <rect x="6" y="6" width="388" height="228" fill="#fff" stroke="#000" stroke-width="3"/>
  ${dial(120, 122, 74, 63)}

  <rect x="222" y="18" width="164" height="60" fill="#000"/>
  <rect x="228" y="24" width="152" height="48" fill="none" stroke="#fff" stroke-width="1"/>
  ${txt(236, 38, 'TIME LEFT', 9, { fill: '#fff', ls: 1.6 })}
  ${txt(304, 64, TIME, 22, { mono: true, fill: '#fff', anchor: 'middle', ls: 0 })}

  ${txt(222, 96, 'ACTIVE', 9, { ls: 1.6 })}
  <rect x="266" y="91" width="120" height="1" fill="#000"/>
  ${MODS.map((m, i) => {
    const x = 222, y = 102 + i * 40, w = 164, h = 34;
    return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff" stroke="#000" stroke-width="2"/>
      <rect x="${x}" y="${y}" width="30" height="${h}" fill="#000"/>
      ${icon(m.icon, x + 4, y + 6, { fill: '#fff', bg: '#000', slash: m.slash })}
      ${txt(x + 38, y + 15, m.name, 11)}
      ${txt(x + 38, y + 27, m.sub, 9, { ls: 0.3 })}`;
  }).join('')}
  ${btnA(90, 226)}${txt(104, 230, 'OPEN?', 12)}
`;

/* ============================================================
   6 — MINIMAL CORNERS
   Closest to the current build: nothing but the dial, as big
   as the screen allows. The modifiers are a small icon stack
   in the right margin, the timer a bare corner readout.
   ============================================================ */
V['hud-06-minimal'] = `
  ${dial(196, 120, 98, 63)}
  ${icon('clock', 8, 8)}
  ${txt(34, 25, TIME, 17, { mono: true, ls: 0 })}
  <line x1="368" y1="62" x2="368" y2="178" stroke="#000" stroke-width="1" stroke-dasharray="2 3"/>
  ${MODS.map((m, i) => {
    const y = 62 + i * 58;
    return `<circle cx="368" cy="${y}" r="18" fill="#fff" stroke="#000" stroke-width="2"/>
      ${icon(m.icon, 357, y - 11, { slash: m.slash })}`;
  }).join('')}
  ${btnA(20, 222)}${txt(34, 226, 'OPEN?', 13)}
`;

const NAMES = Object.keys(V);
for (const n of NAMES) fs.writeFileSync(path.join(OUT, n + '.svg'), H.page(V[n]));

/* ---------------- contact sheet ---------------- */
const CAPS = {
  'hud-01-vault-door': '1 · VAULT DOOR — plates bolted to the door',
  'hud-02-left-rail': '2 · LEFT RAIL — black column, biggest dial that still fits',
  'hud-03-bottom-deck': '3 · BOTTOM DECK — console strip, dial sides stay clear',
  'hud-04-bolt-ring': '4 · BOLT RING — modifiers as the door bolts, icon only',
  'hud-05-lcd-console': '5 · LCD CONSOLE — readout panel, modifiers as a list',
  'hud-06-minimal': '6 · MINIMAL — max dial, icon stack in the margin',
};
const CW = 400, CH = 240, GAP = 10, CAP = 18;
const cols = 2, rows = 3;
const SW = cols * CW + (cols + 1) * GAP;
const SH = rows * (CH + CAP) + (rows + 1) * GAP;
const sheet = NAMES.map((n, i) => {
  const cx = GAP + (i % cols) * (CW + GAP);
  const cy = GAP + Math.floor(i / cols) * (CH + CAP + GAP);
  return `<g transform="translate(${cx},${cy})">
    ${txt(0, 12, CAPS[n], 11, { ls: 0.4 })}
    <g transform="translate(0,${CAP})"><rect width="${CW}" height="${CH}" fill="#fff"/>${V[n]}</g>
    <rect y="${CAP}" width="${CW}" height="${CH}" fill="none" stroke="#000" stroke-width="1"/>
  </g>`;
}).join('');
fs.writeFileSync(path.join(OUT, 'hud-contact-sheet.svg'),
  `<svg xmlns="http://www.w3.org/2000/svg" width="${SW}" height="${SH}" viewBox="0 0 ${SW} ${SH}">${H.DEFS}<rect width="${SW}" height="${SH}" fill="#fff"/>${sheet}</svg>`);

console.log(NAMES.join('\n') + '\nhud-contact-sheet');
