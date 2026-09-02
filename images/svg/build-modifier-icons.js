// Icon decision sheet: all 12 modifiers (game.md §12) drawn on the real vault-door
// card at true device size, with one alternate icon each.
const fs = require('fs');
const path = require('path');
const H = require('./hud.js');
const { txt, icon, modCard } = H;

const PICKS = [
  { axis: 'PERCEPTION', name: 'BLACKOUT', sub: 'DIAL HIDDEN', icon: 'eye', slash: true, src: 'memory', why: 'approved' },
  { axis: 'PERCEPTION', name: 'TOO LOUD', sub: 'TICKS DUCKED', icon: 'music-note', src: 'memory', why: 'approved (the alt)' },
  { axis: 'MOTOR', name: 'HAIR TRIGGER', sub: 'CRAWL TO LATCH', pix: 'crosshair', why: 'a crosshair — the margin you have to land inside' },
  { axis: 'MOTOR', name: 'GREASED', sub: 'DIAL COASTS', pix: 'oil-slip', why: 'a drop of oil throwing speed lines' },
  { axis: 'MOTOR', name: 'STICKY', sub: 'NO CREEPING', pix: 'goo-drip', why: 'glue that will not let the dial go' },
  { axis: 'MEMORY', name: 'SCRAMBLED', sub: 'RANDOM DIRS', pix: 'both-ways', why: 'one arrow each way — you do not know which it wants' },
  { axis: 'MEMORY', name: 'FOUR TUMBLERS', sub: 'ONE MORE SPOT', pix: 'four-pins', why: 'four pins across the shear line' },
  { axis: 'MEMORY', name: 'WANDERING', sub: 'TARGETS DRIFT', pix: 'drift-target', why: 'the target and the track it left' },
  { axis: 'RISK', name: 'DECOY', sub: 'FAKE 4TH SPOT', pix: 'twin-marks', why: 'two identical marks, one hollow' },
  { axis: 'RISK', name: 'ONE SHOT', sub: 'NO SECOND TRY', icon: 'skull', src: 'memory', why: 'approved' },
  { axis: 'EVENT', name: 'GUARD', sub: 'STOP CRANKING', pix: 'peaked-cap', why: "an officer's cap — someone is walking the building" },
  { axis: 'BODY', name: 'NITRO', sub: 'KEEP IT LEVEL', icon: 'flask', src: 'memory', why: 'approved' },
];


const CW = 126, CH = 44, ALT = 60, COL = CW + 16 + ALT, GAP = 16, TOP = 34;
const ROWS = Math.ceil(PICKS.length / 2), COLS = 2;
const W = COLS * COL + (COLS + 1) * GAP;
const Hh = TOP + ROWS * (CH + 16) + GAP;

const body = PICKS.map((m, i) => {
  const cx = GAP + (i % COLS) * (COL + GAP);
  const cy = TOP + Math.floor(i / COLS) * (CH + 16);
  const zoomX = cx + CW + 16;
  const big = m.pix
    ? H.pixIcon(m.pix, zoomX, cy + 2, { zoom: 3 })
    : icon(m.icon, zoomX, cy + 2, { slash: m.slash, scale: 42 / 22 });
  return `<g>
    ${txt(cx, cy - 4, `${i + 1}. ${m.axis}${m.src === 'memory' ? '  ·  memory' : '  ·  drawn'}`, 8, { ls: 1 })}
    ${modCard(cx, cy, CW, CH, m)}
    ${big}
  </g>`;
}).join('');

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${Hh}" viewBox="0 0 ${W} ${Hh}">${H.DEFS}
  <rect width="${W}" height="${Hh}" fill="#fff"/>
  ${txt(GAP, 20, 'MODIFIER ICONS — true card size, then the glyph at 3x', 11)}
  ${body}</svg>`;
fs.writeFileSync(path.join(__dirname, 'hud-modifier-icons.svg'), svg);
console.log(`hud-modifier-icons ${W}x${Hh}`);
