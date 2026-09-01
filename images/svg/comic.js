// WAGMI-style comic scene library for Safu.
// Light and airy: white characters, thin black line, soft dither washes, speech bubbles.
// Authored at Playdate native 400x240 so dither cells land on exact device pixels.
const N = require('./neko.js');

const DEFS = `
<defs>
  <pattern id="p12" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
  <pattern id="p25" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
  <pattern id="p50" width="2" height="2" patternUnits="userSpaceOnUse"><rect width="2" height="2" fill="#fff"/></pattern>
  <pattern id="p75" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
  <pattern id="d12" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
  <pattern id="d25" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
  <pattern id="d50" width="2" height="2" patternUnits="userSpaceOnUse"><rect width="2" height="2" fill="#fff"/></pattern>
  <pattern id="d75" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
</defs>`;

const FONT = `'Chalkboard SE','Chalkboard',sans-serif`;
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

// ---------------- panels ----------------
function panel(id, quad, body, opts = {}) {
  const d = `M ${quad.map(p => p.join(',')).join(' L ')} Z`;
  const tx = opts.tx || 0, ty = opts.ty || 0;
  return `
  <clipPath id="clip-${id}"><path d="${d}"/></clipPath>
  <g clip-path="url(#clip-${id})">
    <rect x="-40" y="-40" width="1400" height="1400" fill="${opts.bg || '#fff'}"/>
    <g transform="translate(${tx},${ty})">${body}</g>
  </g>
  <path d="${d}" fill="none" stroke="#000" stroke-width="${opts.bw ?? 3}" stroke-linejoin="miter"/>`;
}
const rectQuad = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];

// ---------------- lettering ----------------
const txt = (x, y, str, fs, anchor = 'start', fill = '#000') =>
  `<text x="${x}" y="${y}" font-family="${FONT}" font-size="${fs}" font-weight="700"
     fill="${fill}" text-anchor="${anchor}" letter-spacing="0.3">${str}</text>`;

function caption(x, y, lines, opts = {}) {
  const fs = opts.fs || 11, lh = opts.lh || 13, pad = 5;
  const w = opts.w || (Math.max(...lines.map(l => l.length)) * fs * 0.58 + pad * 2);
  const h = lines.length * lh + pad * 2 - 2;
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="#fff" stroke="#000" stroke-width="2"/>
    ${lines.map((l, i) => txt(x + pad, y + pad + lh - 2 + i * lh, l, fs)).join('')}`;
}

// rounded speech bubble with a tail pointing at (tx,ty)
function bubble(x, y, lines, opts = {}) {
  const fs = opts.fs || 11, lh = opts.lh || 13, pad = 7;
  const w = opts.w || (Math.max(...lines.map(l => l.length)) * fs * 0.58 + pad * 2);
  const h = lines.length * lh + pad * 2 - 2;
  const cx = x + w / 2, cy = y + h / 2;
  const t = opts.tail;
  let tail = '';
  if (t) {
    const dx = t[0] - cx, dy = t[1] - cy, L = Math.hypot(dx, dy) || 1;
    const nx = -dy / L, ny = dx / L, b = opts.tailW || 7;
    const ex = cx + dx * 0.42, ey = cy + dy * 0.42;
    tail = `<path d="M ${ex + nx * b},${ey + ny * b} L ${t[0]},${t[1]} L ${ex - nx * b},${ey - ny * b} Z"
      fill="#fff" stroke="#000" stroke-width="2" stroke-linejoin="round"/>
      <path d="M ${ex + nx * (b - 1.4)},${ey + ny * (b - 1.4)} L ${ex - nx * (b - 1.4)},${ey - ny * (b - 1.4)}" stroke="#fff" stroke-width="3"/>`;
  }
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${Math.min(h / 2, 11)}"
      fill="#fff" stroke="#000" stroke-width="2"/>${tail}
    ${lines.map((l, i) => txt(cx, y + pad + lh - 2 + i * lh, l, fs, 'middle')).join('')}`;
}

// spiky shout bubble
function shout(cx, cy, rx, ry, lines, opts = {}) {
  const fs = opts.fs || 11, lh = opts.lh || 13, n = opts.spikes || 16;
  let d = '';
  for (let i = 0; i < n * 2; i++) {
    const a = (i / (n * 2)) * Math.PI * 2 - Math.PI / 2;
    const k = i % 2 ? 1 : 0.78;
    const px = cx + Math.cos(a) * rx * k, py = cy + Math.sin(a) * ry * k;
    d += (i ? ' L ' : 'M ') + px.toFixed(1) + ',' + py.toFixed(1);
  }
  const y0 = cy - (lines.length * lh) / 2 + lh - 3;
  return `<path d="${d} Z" fill="#fff" stroke="#000" stroke-width="2" stroke-linejoin="round"/>
    ${lines.map((l, i) => txt(cx, y0 + i * lh, l, fs, 'middle')).join('')}`;
}

// ---------------- WAGMI backdrops ----------------
// alternating light wedges radiating from a point — the house style for "impact"
function rays(cx, cy, n, r, opts = {}) {
  let d = '';
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2, a1 = a0 + (Math.PI * 2) / n * 0.5;
    d += `M ${cx},${cy} L ${cx + Math.cos(a0) * r},${cy + Math.sin(a0) * r}
          L ${cx + Math.cos(a1) * r},${cy + Math.sin(a1) * r} Z `;
  }
  return `<path d="${d}" fill="${opts.fill || 'url(#p25)'}"/>`;
}
function speedLines(seed, cx, cy, r0, r1, n) {
  const r = rng(seed); let o = '';
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + r() * 0.15;
    o += `<path d="M ${cx + Math.cos(a) * r0},${cy + Math.sin(a) * r0} L ${cx + Math.cos(a) * (r1 + r() * 34)},${cy + Math.sin(a) * (r1 + r() * 34)}"/>`;
  }
  return `<g stroke="#000" stroke-width="1.5" stroke-linecap="round" fill="none">${o}</g>`;
}
// manga impact rays: black wedges, base on an outer ring, tip pointing inward
function rayTicks(cx, cy, n, rOuter, rInner, seed = 5) {
  const r = rng(seed); let d = '';
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2 + r() * 0.22;
    const w = 0.022 + r() * 0.02, ri = rInner + r() * 16;
    d += `M ${(cx + Math.cos(a - w) * rOuter).toFixed(1)},${(cy + Math.sin(a - w) * rOuter).toFixed(1)}
          L ${(cx + Math.cos(a) * ri).toFixed(1)},${(cy + Math.sin(a) * ri).toFixed(1)}
          L ${(cx + Math.cos(a + w) * rOuter).toFixed(1)},${(cy + Math.sin(a + w) * rOuter).toFixed(1)} Z `;
  }
  return `<path d="${d}" fill="#000"/>`;
}
// soft bumpy WAGMI cloud
function cloud(x, y, s, fill = '#fff') {
  return `<g transform="translate(${x},${y}) scale(${s})">
    <path d="M 0,0 C -3,-9 4,-15 12,-12 C 15,-22 30,-23 34,-13 C 43,-18 52,-11 50,-2 C 55,-1 55,0 54,0 Z"
      fill="${fill}" stroke="#000" stroke-width="2" stroke-linejoin="round"/></g>`;
}
function star(x, y, r) {
  return `<path d="M ${x},${y - r} Q ${x + r * 0.2},${y - r * 0.2} ${x + r},${y}
    Q ${x + r * 0.2},${y + r * 0.2} ${x},${y + r} Q ${x - r * 0.2},${y + r * 0.2} ${x - r},${y}
    Q ${x - r * 0.2},${y - r * 0.2} ${x},${y - r} Z" fill="#fff" stroke="#000" stroke-width="1.2" stroke-linejoin="round"/>`;
}
function starfield(seed, x0, y0, x1, y1, n) {
  const r = rng(seed); let o = '';
  for (let i = 0; i < n; i++) {
    const x = x0 + r() * (x1 - x0), y = y0 + r() * (y1 - y0);
    o += r() > 0.7 ? star(x, y, 2.6 + r() * 1.6)
       : `<circle cx="${x}" cy="${y}" r="${1 + r() * 0.8}" fill="#fff" stroke="#000" stroke-width="0.9"/>`;
  }
  return o;
}
function moon(cx, cy, r) {
  return `<g>
    <circle cx="${cx}" cy="${cy}" r="${r + 9}" fill="url(#p12)"/>
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="#fff" stroke="#000" stroke-width="2.4"/>
    <circle cx="${cx - r * 0.32}" cy="${cy - r * 0.26}" r="${r * 0.20}" fill="url(#p25)" stroke="#000" stroke-width="1.4"/>
    <circle cx="${cx + r * 0.28}" cy="${cy + r * 0.12}" r="${r * 0.14}" fill="url(#p25)" stroke="#000" stroke-width="1.4"/>
    <circle cx="${cx - r * 0.04}" cy="${cy + r * 0.44}" r="${r * 0.11}" fill="url(#p25)" stroke="#000" stroke-width="1.4"/></g>`;
}
function skyline(seed, x0, x1, baseY, minH, maxH, fill = 'url(#p50)') {
  const r = rng(seed); let x = x0, o = '', win = '';
  while (x < x1) {
    const w = 24 + r() * 30, h = minH + r() * (maxH - minH), top = baseY - h;
    o += `<rect x="${x}" y="${top}" width="${w}" height="${h + 40}" fill="${fill}" stroke="#000" stroke-width="2"/>`;
    if (r() > 0.66) o += `<rect x="${x + w * 0.4}" y="${top - 13}" width="2.4" height="13" fill="#000"/>`;
    for (let wy = top + 8; wy < baseY - 8; wy += 12)
      for (let wx = x + 6; wx < x + w - 7; wx += 11)
        if (r() > 0.5) win += `<rect x="${wx}" y="${wy}" width="4.5" height="5.5" fill="#fff" stroke="#000" stroke-width="1"/>`;
    x += w + 4 + r() * 5;
  }
  return `<g>${o}</g>${win}`;
}
function room(x0, x1, floorY, opts = {}) {
  return `<g>
    <rect x="${x0 - 30}" y="-60" width="${x1 - x0 + 90}" height="${floorY + 60}" fill="url(#${opts.wall || 'p12'})"/>
    <rect x="${x0 - 30}" y="${floorY}" width="${x1 - x0 + 90}" height="500" fill="url(#${opts.floor || 'p25'})"/>
    <path d="M ${x0 - 30},${floorY} L ${x1 + 60},${floorY}" stroke="#000" stroke-width="2.4"/>
    <rect x="${x0 - 30}" y="${floorY - 7}" width="${x1 - x0 + 90}" height="7" fill="#fff" stroke="#000" stroke-width="1.6"/></g>`;
}
// moonlight falling in through a window — a soft dithered wedge
function beam(x, y, w, floorY, spread = 46) {
  return `<path d="M ${x},${y} L ${x + w},${y} L ${x + w + spread},${floorY + 40} L ${x - spread},${floorY + 40} Z"
    fill="#fff" opacity="0.9"/>`;
}
// hand-drawn window with 4 panes and a sill
function windowFrame(x, y, w, h) {
  return `<g>
    <rect x="${x - 3}" y="${y - 3}" width="${w + 6}" height="${h + 6}" rx="2" fill="#fff" stroke="#000" stroke-width="2.4"/>
    <rect x="${x}" y="${y}" width="${w}" height="${h}" fill="url(#p50)" stroke="#000" stroke-width="1.8"/>
    <path d="M ${x + w / 2},${y} V ${y + h} M ${x},${y + h / 2} H ${x + w}" stroke="#000" stroke-width="1.8"/>
    <rect x="${x - 6}" y="${y + h + 3}" width="${w + 12}" height="5" fill="#fff" stroke="#000" stroke-width="1.8"/></g>`;
}
// exclamation / question marks with a white halo so they pop off any wash
const halo = (g) => `<g stroke="#fff" stroke-width="6" stroke-linejoin="round" stroke-linecap="round">${g}</g>${g}`;
function excl(x, y, s = 1) {
  const core = `<path d="M -3,-13 L 3,-13 L 1.8,3 L -1.8,3 Z" fill="#000"/><circle cx="0" cy="9.5" r="3" fill="#000"/>`;
  return `<g transform="translate(${x},${y}) scale(${s})">
    <g stroke="#fff" stroke-width="5.5" stroke-linejoin="round">${core}</g>${core}</g>`;
}
function quest(x, y, s = 1) {
  const core = `<path d="M -5.5,-6 a 5.8,5.8 0 1 1 6.2,6.8 l 0,3" fill="none" stroke="#000" stroke-width="3.6"
    stroke-linecap="round" stroke-linejoin="round"/><circle cx="0.7" cy="9.5" r="2.8" fill="#000"/>`;
  return `<g transform="translate(${x},${y}) scale(${s})">
    <g stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round">
      <path d="M -5.5,-6 a 5.8,5.8 0 1 1 6.2,6.8 l 0,3" fill="none"/><circle cx="0.7" cy="9.5" r="2.8"/></g>${core}</g>`;
}
// tiny solid-black cat silhouette (crouched, facing left) for far shots
function nekoSilhouette(x, y, s = 1, flip = false) {
  return `<g transform="translate(${x},${y}) scale(${flip ? -s : s},${s})">
    <path d="M 56,8 C 70,6 78,-6 72,-20" fill="none" stroke="#000" stroke-width="6" stroke-linecap="round"/>
    <path d="M 10,0 L 4,-14 L 20,-6 Z" fill="#000"/>
    <path d="M 28,-3 L 32,-16 L 42,-4 Z" fill="#000"/>
    <path d="M 4,24 C 0,6 12,-6 28,-6 C 46,-6 58,2 62,12 C 64,18 62,24 56,24 Z" fill="#000"/>
    <ellipse cx="16" cy="6" rx="2.6" ry="3.4" fill="#fff"/>
    <ellipse cx="28" cy="6" rx="2.6" ry="3.4" fill="#fff"/>
  </g>`;
}

// ---------------- Neko: head + WAGMI blob body ----------------// ---------------- Neko: head + WAGMI blob body ----------------
function head(o = {}) {
  const ey = o.mask ? 59 : (o.ey ?? 58);
  const e = { ...o, ey, mask: o.mask !== false && o.mask };
  return `
    ${N.WHISKERS}
    <path d="${N.EAR_L}" fill="#fff" stroke="#000" stroke-width="${N.LW}" stroke-linejoin="round"/>
    <path d="${N.EAR_R}" fill="#fff" stroke="#000" stroke-width="${N.LW}" stroke-linejoin="round"/>
    <path d="${N.EAR_L_IN}" fill="url(#d50)" stroke="#000" stroke-width="${N.LW3}" stroke-linejoin="round"/>
    <path d="${N.EAR_R_IN}" fill="url(#d50)" stroke="#000" stroke-width="${N.LW3}" stroke-linejoin="round"/>
    <path d="${N.HEAD}" fill="#fff" stroke="#000" stroke-width="${N.LW}" stroke-linejoin="round"/>
    ${o.mask ? N.MASK : ''}
    ${N.drawEyes(o.eyes || 'oval', ey, e)}
    ${o.mask ? '' : N.nose(ey + 12)}
    ${N.M[o.mouth || 'w'](o.mask ? 82 : ey + 18)}
    ${o.blush && !o.mask ? N.blush() : ''}`;
}

// Full figure — slim and upright with arms, legs and a long tail, the way Neko is
// drawn in wagmi-pay-raise-01 / wagmi-interest-rate-01. Head keeps the 100-unit space;
// the body runs from y 90 down to y 176.
function nekoFull(o = {}) {
  const fill = o.fill || '#fff';
  const arm = (d, px, py) => `
    <path d="${d}" fill="none" stroke="#000" stroke-width="12" stroke-linecap="round"/>
    <path d="${d}" fill="none" stroke="${fill}" stroke-width="7.2" stroke-linecap="round"/>
    <ellipse cx="${px}" cy="${py}" rx="7" ry="6.4" fill="${fill}" stroke="#000" stroke-width="2.6"/>`;
  return `<g>
    ${o.tail === false ? '' : `
      <path d="M 66,124 C 86,128 96,112 92,94" fill="none" stroke="#000" stroke-width="9" stroke-linecap="round"/>
      <path d="M 66,124 C 86,128 96,112 92,94" fill="none" stroke="${fill}" stroke-width="4.8" stroke-linecap="round"/>`}
    <ellipse cx="40" cy="137" rx="9.5" ry="5.5" fill="${fill}" stroke="#000" stroke-width="2.6"/>
    <ellipse cx="60" cy="137" rx="9.5" ry="5.5" fill="${fill}" stroke="#000" stroke-width="2.6"/>
    <path d="M 33,86 C 30,94 29,104 29,113 C 29,127 36,134 50,134
             C 64,134 71,127 71,113 C 71,104 70,94 67,86 Z"
      fill="${fill}" stroke="#000" stroke-width="3" stroke-linejoin="round"/>
    <path d="M 50,125 L 50,133" stroke="#000" stroke-width="1.8" stroke-linecap="round"/>
    ${o.armL ?? arm('M 34,96 C 26,100 22,108 23,116', 24, 118)}
    ${o.armR ?? arm('M 66,96 C 74,100 78,108 77,116', 76, 118)}
    ${head(o)}
  </g>`;
}

// Crouching side-on, perched on a ledge — white body, thin outline, long tail up.
// Crouching: nendoroid crouch — the head IS most of the cat, a small bean body
// tucked behind, tiny paws on the ledge, thin tail up.
function nekoCrouch(o = {}) {
  const fill = o.fill || '#fff';
  return `<g>
    <path d="M 88,74 C 106,72 114,52 106,32" fill="none" stroke="#000" stroke-width="8" stroke-linecap="round"/>
    <path d="M 88,74 C 106,72 114,52 106,32" fill="none" stroke="${fill}" stroke-width="4.4" stroke-linecap="round"/>
    <path d="M 20,88 C 16,72 26,62 46,60 C 70,58 86,68 90,79 C 91,84 88,88 84,88 Z"
      fill="${fill}" stroke="#000" stroke-width="3" stroke-linejoin="round"/>
    <ellipse cx="76" cy="89" rx="9" ry="4.5" fill="${fill}" stroke="#000" stroke-width="2.4"/>
    <ellipse cx="22" cy="89" rx="7.5" ry="4.5" fill="${fill}" stroke="#000" stroke-width="2.4"/>
    <ellipse cx="37" cy="89" rx="7.5" ry="4.5" fill="${fill}" stroke="#000" stroke-width="2.4"/>
    <g transform="translate(-8,-14) scale(0.82)">${head({ mask: true, eyes: o.eyes || 'focus', mouth: 'flat' })}</g>
  </g>`;
}

// POV: two paws gripping a blank note
function povNote(o = {}) {
  const x = o.x ?? 110, y = o.y ?? 10, w = o.w ?? 180, h = o.h ?? 84;
  const suit = o.suit || '#fff';
  const py = y + h * (o.pawAt ?? 0.5);
  const fa = (d) => `
    <path d="${d}" fill="none" stroke="#000" stroke-width="16" stroke-linecap="round"/>
    <path d="${d}" fill="none" stroke="${suit}" stroke-width="10.8" stroke-linecap="round"/>`;
  const paw = (cx, cy, sgn) => `
    <path d="M ${cx},${cy - 12} C ${cx + sgn * 15},${cy - 12} ${cx + sgn * 16},${cy + 10}
             ${cx + sgn * 2},${cy + 12} C ${cx - sgn * 10},${cy + 13.5} ${cx - sgn * 12},${cy - 8} ${cx},${cy - 12} Z"
      fill="#fff" stroke="#000" stroke-width="2.8" stroke-linejoin="round"/>
    <g stroke="#000" stroke-width="1.8" fill="none" stroke-linecap="round">
      <path d="M ${cx + sgn * 3},${cy - 4} q ${sgn * 8},1.5 ${sgn * 11},0"/>
      <path d="M ${cx + sgn * 2},${cy + 3} q ${sgn * 8},1.5 ${sgn * 11},-0.5"/></g>`;
  return `<g>
    ${fa(`M ${x - 46},${y + h + 70} C ${x - 34},${y + h + 30} ${x - 22},${py + 30} ${x - 8},${py + 4}`)}
    ${fa(`M ${x + w + 46},${y + h + 70} C ${x + w + 34},${y + h + 30} ${x + w + 22},${py + 30} ${x + w + 8},${py + 4}`)}
    <path d="M ${x},${y + 3} L ${x + w},${y} L ${x + w - 3},${y + h} L ${x + 3},${y + h + 4} Z"
      fill="#fff" stroke="#000" stroke-width="2.8" stroke-linejoin="round"/>
    <path d="M ${x + w},${y} L ${x + w - 14},${y + 11} L ${x + w - 9},${y - 1} Z"
      fill="url(#p25)" stroke="#000" stroke-width="2" stroke-linejoin="round"/>
    ${o.ink || ''}
    ${paw(x + 1, py, -1)}${paw(x + w - 1, py, 1)}</g>`;
}

// ---------------- the safe ----------------
function safe(x, y, w, h, o = {}) {
  const s = w / 100, hs = h / 100, k = (v) => (v / s).toFixed(2);
  return `<g transform="translate(${x},${y}) scale(${s},${hs})">
    <rect x="0" y="0" width="100" height="100" rx="4" fill="url(#p25)" stroke="#000" stroke-width="${k(3.4)}" stroke-linejoin="round"/>
    <rect x="8" y="8" width="84" height="84" rx="3" fill="#fff" stroke="#000" stroke-width="${k(2.6)}"/>
    <rect x="14" y="14" width="72" height="72" fill="none" stroke="#000" stroke-width="${k(1.4)}" stroke-dasharray="5 4"/>
    <circle cx="50" cy="46" r="21" fill="url(#p12)" stroke="#000" stroke-width="${k(3)}"/>
    <circle cx="50" cy="46" r="13" fill="#fff" stroke="#000" stroke-width="${k(2.2)}"/>
    <g stroke="#000" stroke-width="${k(1.5)}" stroke-linecap="round">
      ${Array.from({ length: 12 }, (_, i) => { const a = (i / 12) * Math.PI * 2;
        return `<path d="M ${50 + Math.cos(a) * 17.5},${46 + Math.sin(a) * 17.5} L ${50 + Math.cos(a) * 20.5},${46 + Math.sin(a) * 20.5}"/>`; }).join('')}</g>
    <path d="M 50,46 L ${50 + Math.cos(o.dial ?? -2.1) * 10.5},${46 + Math.sin(o.dial ?? -2.1) * 10.5}"
      stroke="#000" stroke-width="${k(2.8)}" stroke-linecap="round"/>
    <circle cx="50" cy="46" r="3.2" fill="#000"/>
    <g stroke="#000" stroke-width="${k(2.6)}" fill="#fff" stroke-linejoin="round">
      <rect x="42" y="74" width="16" height="6"/><rect x="28" y="71" width="13" height="11" rx="2"/><rect x="59" y="71" width="13" height="11" rx="2"/></g>
    <g fill="url(#p50)" stroke="#000" stroke-width="${k(2)}"><rect x="1" y="20" width="7" height="9"/><rect x="1" y="66" width="7" height="9"/></g>
    <g fill="url(#p50)" stroke="#000" stroke-width="${k(2)}"><rect x="11" y="99" width="13" height="7"/><rect x="76" y="99" width="13" height="7"/></g></g>`;
}

// vertical tone ramp — stands in for WAGMI's airbrushed grey washes
function wash(x, y, w, h, steps = ['p50', 'p25', 'p12', '#fff']) {
  const bh = h / steps.length;
  return steps.map((t, i) => `<rect x="${x}" y="${(y + i * bh).toFixed(1)}" width="${w}" height="${(bh + 1).toFixed(1)}"
    fill="${t.startsWith('#') ? t : `url(#${t})`}"/>`).join('');
}

module.exports = { DEFS, FONT, wash, panel, rectQuad, txt, caption, bubble, shout, rays, speedLines,
  rayTicks, cloud, star, starfield, moon, skyline, room, beam, windowFrame, excl, quest, nekoSilhouette,
  head, nekoFull, nekoCrouch, povNote, safe, rng, N };
