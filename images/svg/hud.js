// Shared drawing primitives for the Safu HUD mockups.
// Authored at Playdate native 400x240, 1:1, pure black & white.
const fs = require('fs');
const path = require('path');

const ICONS = JSON.parse(fs.readFileSync(path.join(__dirname, 'memory-icons.json'), 'utf8'));
const { pixPath } = require('./icons-pixel.js');

const UI = `'Helvetica Neue',Helvetica,Arial,sans-serif`;
const MONO = `'Menlo','DejaVu Sans Mono','Courier New',monospace`;

const DEFS = `
<defs>
  <pattern id="d50" width="2" height="2" patternUnits="userSpaceOnUse">
    <rect width="2" height="2" fill="#fff"/><rect width="1" height="1" fill="#000"/><rect x="1" y="1" width="1" height="1" fill="#000"/>
  </pattern>
  <pattern id="d25" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="4" fill="#fff"/><rect width="1" height="1" fill="#000"/><rect x="2" y="2" width="1" height="1" fill="#000"/>
  </pattern>
  <pattern id="d12" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="4" fill="#fff"/><rect x="1" y="1" width="1" height="1" fill="#000"/>
  </pattern>
  <pattern id="d75" width="2" height="2" patternUnits="userSpaceOnUse">
    <rect width="2" height="2" fill="#000"/><rect x="1" width="1" height="1" fill="#fff"/>
  </pattern>
</defs>`;

const page = (body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240" viewBox="0 0 400 240">${DEFS}<rect width="400" height="240" fill="#fff"/>${body}</svg>`;

const txt = (x, y, s, fs_, o = {}) =>
  `<text x="${x}" y="${y}" font-family="${o.mono ? MONO : UI}" font-size="${fs_}" font-weight="${o.w || 700}" fill="${o.fill || '#000'}" text-anchor="${o.anchor || 'start'}" letter-spacing="${o.ls ?? 0.6}">${s}</text>`;

// Hand-drawn 14x14 pixel icon, always 1:1 — scaling it would defeat the point.
function pixIcon(name, x, y, o = {}) {
  const fill = o.fill || '#000', bg = o.bg || '#fff';
  const z = o.zoom || 1;
  const halo = bg === '#000' ? fill : bg;
  const cut = bg === '#000' ? bg : fill;
  const slash = o.slash
    ? `<path d="M 1,0 L 13,12" stroke="${halo}" stroke-width="4"/><path d="M 1,0 L 13,12" stroke="${cut}" stroke-width="2"/>`
    : '';
  return `<g transform="translate(${x},${y})${z !== 1 ? ` scale(${z})` : ''}" shape-rendering="crispEdges"><path d="${pixPath(name)}" fill="${fill}"/>${slash}</g>`;
}

// Memory icon, native 22x22 pixel grid.
function icon(name, x, y, o = {}) {
  const s = o.scale || 1;
  const d = ICONS[name];
  const fill = o.fill || '#000', bg = o.bg || '#fff';
  const halo = bg === '#000' ? fill : bg;   // on a dark plate the slash is cut, not drawn
  const cut = bg === '#000' ? bg : fill;
  const slash = o.slash
    ? `<path d="M 2,1 L 21,20" stroke="${halo}" stroke-width="6"/><path d="M 2,1 L 21,20" stroke="${cut}" stroke-width="3"/>`
    : '';
  return `<g transform="translate(${x},${y}) scale(${s})"><path d="${d}" fill="${fill}"/>${slash}</g>`;
}

// The dial, mirroring Art.drawDial in source/dial.lua.
function dial(cx, cy, r, pos) {
  const rim = Math.floor(r * 0.12) + 2;
  const hub = Math.floor(r * 0.3);
  const nr = r - Math.floor(r * 0.36);
  const P = [];
  P.push(`<circle cx="${cx}" cy="${cy}" r="${r + rim}" fill="#000"/>`);
  P.push(`<circle cx="${cx}" cy="${cy}" r="${r}" fill="#fff"/>`);
  for (let n = 0; n < 100; n += 2) {
    const a = ((pos - n) * 3.6 * Math.PI) / 180, sa = Math.sin(a), ca = Math.cos(a);
    P.push(`<line x1="${(cx + sa * (r + 2)).toFixed(2)}" y1="${(cy - ca * (r + 2)).toFixed(2)}" x2="${(cx + sa * (r + rim - 1)).toFixed(2)}" y2="${(cy - ca * (r + rim - 1)).toFixed(2)}" stroke="#fff" stroke-width="2"/>`);
  }
  for (let n = 0; n < 100; n++) {
    const a = ((pos - n) * 3.6 * Math.PI) / 180, sa = Math.sin(a), ca = Math.cos(a);
    let w, inner;
    if (n % 10 === 0) { w = 3; inner = r - r * 0.2; }
    else if (n % 5 === 0) { w = 2; inner = r - r * 0.15; }
    else { w = 1; inner = r - r * 0.09; }
    P.push(`<line x1="${(cx + sa * (r - 2)).toFixed(2)}" y1="${(cy - ca * (r - 2)).toFixed(2)}" x2="${(cx + sa * inner).toFixed(2)}" y2="${(cy - ca * inner).toFixed(2)}" stroke="#000" stroke-width="${w}"/>`);
  }
  const fsz = Math.max(9, Math.round(r * 0.2));
  for (let n = 0; n <= 90; n += 10) {
    const ang = (pos - n) * 3.6, a = (ang * Math.PI) / 180;
    const x = cx + Math.sin(a) * nr, y = cy - Math.cos(a) * nr;
    P.push(`<g transform="translate(${x.toFixed(2)},${y.toFixed(2)}) rotate(${ang.toFixed(2)})">${txt(0, fsz * 0.36, String(n).padStart(2, '0'), fsz, { anchor: 'middle', ls: 0 })}</g>`);
  }
  P.push(`<circle cx="${cx}" cy="${cy}" r="${hub}" fill="#000"/>`);
  for (let i = 0; i < 4; i++) {
    const a = ((pos * 3.6 + i * 90) * Math.PI) / 180, sa = Math.sin(a), ca = Math.cos(a);
    P.push(`<line x1="${(cx + sa * hub * 0.35).toFixed(2)}" y1="${(cy - ca * hub * 0.35).toFixed(2)}" x2="${(cx + sa * hub * 0.86).toFixed(2)}" y2="${(cy - ca * hub * 0.86).toFixed(2)}" stroke="#fff" stroke-width="3"/>`);
  }
  P.push(`<circle cx="${cx}" cy="${cy}" r="${Math.max(3, hub * 0.25).toFixed(1)}" fill="#fff"/>`);
  P.push(`<circle cx="${cx}" cy="${cy}" r="${Math.max(2, hub * 0.13).toFixed(1)}" fill="#000"/>`);
  return P.join('');
}

// Ⓐ glyph
const btnA = (x, y, o = {}) => {
  const f = o.fill || '#000', bg = o.bg || '#fff';
  return `<circle cx="${x}" cy="${y}" r="9" fill="${f}"/><circle cx="${x}" cy="${y}" r="6.5" fill="${bg}"/>${txt(x, y + 3.6, 'A', 9.5, { anchor: 'middle', fill: f, ls: 0 })}`;
};

// Rect whose corners are scooped inward instead of rounded off: each corner arc is
// centred ON the corner point, so it bites into the shape. All four sweeps are 0.
const concaveRect = (x, y, w, h, r) =>
  `M ${x + r},${y} L ${x + w - r},${y} A ${r} ${r} 0 0 0 ${x + w},${y + r}` +
  ` L ${x + w},${y + h - r} A ${r} ${r} 0 0 0 ${x + w - r},${y + h}` +
  ` L ${x + r},${y + h} A ${r} ${r} 0 0 0 ${x},${y + h - r}` +
  ` L ${x},${y + r} A ${r} ${r} 0 0 0 ${x + r},${y} Z`;

const rivet = (x, y, o = {}) =>
  `<rect x="${x - 2}" y="${y - 2}" width="4" height="4" fill="${o.fill || '#000'}"/>`;

// One modifier card: two flex rows — [icon | title], then the subtitle indented
// to the title's x. Corners are scooped inward, over a flat checkered offset shadow.
function modCard(x, y, w, h, m, o = {}) {
  const PAD = 9, ICON = 14, GAP = 6, NOTCH = o.notch ?? 6;
  const TITLE = m.name.length > 11 ? 9.5 : 10.5;   // long names step down a size
  const textX = x + PAD + ICON + GAP;
  const base = y + 20;
  const iconY = base - (TITLE * 0.72) / 2 - ICON / 2;
  const glyph = m.pix
    ? pixIcon(m.pix, x + PAD, Math.round(iconY), { slash: m.slash })
    : icon(m.icon, x + PAD, iconY, { slash: m.slash, scale: ICON / 22 });
  return `<path d="${concaveRect(x + 4, y + 4, w, h, NOTCH)}" fill="url(#d50)"/>
    <path d="${concaveRect(x, y, w, h, NOTCH)}" fill="#fff" stroke="#000" stroke-width="2" stroke-linejoin="miter"/>
    ${glyph}
    ${txt(textX, base, m.name, TITLE)}
    ${txt(textX, y + 33, m.sub, 8.5, { ls: 0.2 })}`;
}

// The three modifiers shown in every mockup, so the layouts stay comparable.
const MODS = [
  { icon: 'eye', slash: true, name: 'BLACKOUT', sub: 'DIAL HIDDEN', short: 'BLACKOUT' },
  { icon: 'music-note', name: 'TOO LOUD', sub: 'TICKS DUCKED', short: 'TOO LOUD' },
  { pix: 'footsteps', name: 'GUARD', sub: 'STOP CRANKING', short: 'GUARD' },
];

const TIME = '00:47.31';

module.exports = { DEFS, UI, MONO, page, txt, icon, pixIcon, dial, btnA, rivet, concaveRect, modCard, MODS, TIME, ICONS };
