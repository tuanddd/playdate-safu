// Neko — modelled directly on the WAGMI comic pages
// (wagmi-interest-rate-01, wagmi-pay-raise-01, wagmi-6jars-01).
//
// Head : tall rounded rectangle, flat-ish top, wide soft chin.  x 20..80, y 28..92
// Ears : LARGE, tall, rounded-tip triangles rising to y ~8, light-grey inner
// Eyes : small-to-mid solid black rounded ovals, set WIDE (x 33 / 67)
// Line : thin and even. Nothing below 2.2 units — Playdate is a Retina-class
//        panel (donaldhays.com/2019/12/30/playdate-art-scale), 1px detail vanishes.

const S = 100;
const LW  = 3.2;   // silhouette
const LW2 = 2.6;   // features
const LW3 = 2.2;   // whiskers / ticks

const DEFS = `
<defs>
  <pattern id="d12" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
  <pattern id="d25" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
  <pattern id="d50" width="2" height="2" patternUnits="userSpaceOnUse"><rect width="2" height="2" fill="#fff"/></pattern>
  <pattern id="d75" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff"/></pattern>
</defs>`;

// ---- geometry helpers -------------------------------------------------------
// rounded polygon: every corner gets a real arc, so a triangle reads soft, not spiky
function roundPoly(pts, r) {
  const n = pts.length, out = [];
  const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  const dist = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
  for (let i = 0; i < n; i++) {
    const V = pts[i], P = pts[(i - 1 + n) % n], Nx = pts[(i + 1) % n];
    const rp = Math.min(r, dist(V, P) * 0.45), rn = Math.min(r, dist(V, Nx) * 0.45);
    out.push({ in: lerp(V, P, rp / dist(V, P)), V, out: lerp(V, Nx, rn / dist(V, Nx)) });
  }
  let d = `M ${out[0].out[0].toFixed(1)},${out[0].out[1].toFixed(1)}`;
  for (let i = 1; i <= n; i++) {
    const c = out[i % n];
    d += ` L ${c.in[0].toFixed(1)},${c.in[1].toFixed(1)}`;
    d += ` Q ${c.V[0].toFixed(1)},${c.V[1].toFixed(1)} ${c.out[0].toFixed(1)},${c.out[1].toFixed(1)}`;
  }
  return d + ' Z';
}
// squircle: a square with corners rounded hard enough to read as one shape
function squircle(x0, y0, x1, y1, r) {
  return `M ${x0 + r},${y0} L ${x1 - r},${y0} Q ${x1},${y0} ${x1},${y0 + r}
          L ${x1},${y1 - r} Q ${x1},${y1} ${x1 - r},${y1}
          L ${x0 + r},${y1} Q ${x0},${y1} ${x0},${y1 - r}
          L ${x0},${y0 + r} Q ${x0},${y0} ${x0 + r},${y0} Z`;
}
const mirror = (pts) => pts.map(([x, y]) => [100 - x, y]);

// ---- the head: a SQUIRCLE, wider than tall, softly rounded — wagmi-neko-1/2/4 ----
const HEAD = squircle(13, 32, 87, 92, 27);

// ---- the ears: ROUNDED triangles, no hard tip ----
const EAR_PTS_L = [[20, 8], [26, 44], [48, 30]];
const EAR_L = roundPoly(EAR_PTS_L, 8);
const EAR_R = roundPoly(mirror(EAR_PTS_L), 8);
const EAR_IN_PTS_L = [[24, 15], [28, 38], [43, 29]];
const EAR_L_IN = roundPoly(EAR_IN_PTS_L, 5);
const EAR_R_IN = roundPoly(mirror(EAR_IN_PTS_L), 5);

// long, thin, attached at the cheek — a WAGMI signature
const WHISKERS = `<g stroke="#000" stroke-width="${LW3}" stroke-linecap="round" fill="none">
  <path d="M 15,60 L 2,55"/><path d="M 14,68 L 0,68"/><path d="M 15,76 L 2,80"/>
  <path d="M 85,60 L 98,55"/><path d="M 86,68 L 100,68"/><path d="M 85,76 L 98,80"/></g>`;

const nose = (y) => `<path d="M 46.6,${y} Q 50,${y - 1.1} 53.4,${y} Q 50,${y + 3.6} 46.6,${y} Z"
  fill="#000" stroke="#000" stroke-width="1.4" stroke-linejoin="round"/>`;

const blush = () => `<g stroke="#000" stroke-width="${LW3}" stroke-linecap="round" fill="none">
  <path d="M 25,74 L 28,79"/><path d="M 30,73 L 33,78"/>
  <path d="M 75,74 L 72,79"/><path d="M 70,73 L 67,78"/></g>`;

const drop = (x, y, s = 1) => `<g transform="translate(${x},${y}) scale(${s})">
  <path d="M 0,-8 C 4.4,-1.6 6.6,2 6.6,4.7 A 6.6,6.6 0 0 1 -6.6,4.7 C -6.6,2 -4.4,-1.6 0,-8 Z"
    fill="#fff" stroke="#000" stroke-width="${LW2}" stroke-linejoin="round"/></g>`;

const sparkle = (x, y, r) => `<path d="M ${x},${y - r} Q ${x + r * 0.2},${y - r * 0.2} ${x + r},${y}
  Q ${x + r * 0.2},${y + r * 0.2} ${x},${y + r} Q ${x - r * 0.2},${y + r * 0.2} ${x - r},${y}
  Q ${x - r * 0.2},${y - r * 0.2} ${x},${y - r} Z" fill="#000"/>`;

// ---------------- eyes: small-to-mid solid black ovals, set wide ----------------
const EW = 11, EH = 14;
const oval = (x, y, w, h) =>
  `<rect x="${x - w / 2}" y="${y - h / 2}" width="${w}" height="${h}" rx="${w / 2}" fill="#000"/>`;

const EYE = {
  oval:    (x, y) => oval(x, y, EW, EH),
  small:   (x, y) => oval(x, y, 8, 10),
  shine:   (x, y) => oval(x, y, EW + 2, EH + 2) + `<circle cx="${x - 2.4}" cy="${y - 3.4}" r="2.4" fill="#fff"/>`,
  big:     (x, y) => oval(x, y, EW + 5, EH + 5) + `<circle cx="${x - 3}" cy="${y - 4.4}" r="3.2" fill="#fff"/>`,
  sparkle: (x, y) => oval(x, y, EW + 4, EH + 4)
                   + `<circle cx="${x - 2.8}" cy="${y - 4}" r="3" fill="#fff"/>`
                   + `<circle cx="${x + 2.8}" cy="${y + 3.6}" r="1.7" fill="#fff"/>`,
  arcUp:   (x, y) => `<path d="M ${x - 7.5},${y + 3.5} Q ${x},${y - 7} ${x + 7.5},${y + 3.5}"
                        fill="none" stroke="#000" stroke-width="${LW + 0.6}" stroke-linecap="round"/>`,
  arcDown: (x, y) => `<path d="M ${x - 7.5},${y - 3.5} Q ${x},${y + 7} ${x + 7.5},${y - 3.5}"
                        fill="none" stroke="#000" stroke-width="${LW + 0.6}" stroke-linecap="round"/>`,
  line:    (x, y) => `<path d="M ${x - 7.5},${y} L ${x + 7.5},${y}"
                        fill="none" stroke="#000" stroke-width="${LW + 0.6}" stroke-linecap="round"/>`,
  lid:     (x, y) => oval(x, y + 2, EW, EH - 6)
                   + `<path d="M ${x - 7.5},${y - 4} L ${x + 7.5},${y - 4}" stroke="#000"
                        stroke-width="${LW + 0.6}" stroke-linecap="round" fill="none"/>`,
  angry:   (x, y, s) => oval(x, y + 1.5, EW, EH - 2)
                      + `<path d="M ${x + (s < 0 ? -8.5 : 8.5)},${y - 10} L ${x + (s < 0 ? 6.5 : -6.5)},${y - 4.5}"
                          stroke="#000" stroke-width="${LW + 0.8}" stroke-linecap="round" fill="none"/>`,
  focus:   (x, y, s) => oval(x, y + 2.5, EW, EH - 5)
                      + `<path d="M ${x + (s < 0 ? -8.5 : 8.5)},${y - 8.5} L ${x + (s < 0 ? 6.5 : -6.5)},${y - 5}"
                          stroke="#000" stroke-width="${LW + 0.8}" stroke-linecap="round" fill="none"/>`,
  sqz:     (x, y, s) => `<path d="M ${x + (s < 0 ? -7 : 7)},${y - 5.5} L ${x + (s < 0 ? 4.5 : -4.5)},${y} L ${x + (s < 0 ? -7 : 7)},${y + 5.5}"
                          fill="none" stroke="#000" stroke-width="${LW + 0.6}" stroke-linecap="round" stroke-linejoin="round"/>`,
  glance:  (x, y, s) => `<rect x="${x - (EW + 2) / 2}" y="${y - (EH + 2) / 2}" width="${EW + 2}" height="${EH + 2}"
                           rx="${(EW + 2) / 2}" fill="#fff" stroke="#000" stroke-width="${LW2}"/>
                         ${oval(x + (s < 0 ? -2.4 : 2.4), y, 6.5, 8.5)}`,
  teary:   (x, y, s) => oval(x, y, EW + 2, EH + 2)
                      + `<circle cx="${x - 2.6}" cy="${y - 3.6}" r="2.6" fill="#fff"/>`
                      + `<path d="M ${x + (s < 0 ? -6 : 6)},${y + 6} q ${s < 0 ? -4 : 4},7 ${s < 0 ? -2 : 2},12"
                          fill="none" stroke="#000" stroke-width="${LW2}" stroke-linecap="round"/>`,
  swirl:   (x, y) => `<path d="M ${x},${y - 1.6} a 1.8,1.8 0 1 1 -1.9,1.9 a 4,4 0 1 0 4.1,-4.1 a 6.4,6.4 0 1 0 -6.4,6.4"
                        fill="none" stroke="#000" stroke-width="${LW2 + 0.3}" stroke-linecap="round"/>`,
};

// ---------------- mouths (sit low on the muzzle) ----------------
const M = {
  w:        (y) => `<path d="M 43,${y} q 3.5,4.4 7,0 q 3.5,4.4 7,0" fill="none" stroke="#000" stroke-width="${LW2}" stroke-linecap="round"/>`,
  cat:      (y) => `<path d="M 42,${y - 1.5} q 4,5.6 8,0 q 4,5.6 8,0" fill="none" stroke="#000" stroke-width="${LW2 + 0.3}" stroke-linecap="round"/>`,
  smile:    (y) => `<path d="M 42.5,${y - 1} q 7.5,7 15,0" fill="none" stroke="#000" stroke-width="${LW2 + 0.3}" stroke-linecap="round"/>`,
  frown:    (y) => `<path d="M 42.5,${y + 3.5} q 7.5,-7 15,0" fill="none" stroke="#000" stroke-width="${LW2 + 0.3}" stroke-linecap="round"/>`,
  flat:     (y) => `<path d="M 43.5,${y + 1} L 56.5,${y + 1}" fill="none" stroke="#000" stroke-width="${LW2 + 0.3}" stroke-linecap="round"/>`,
  smirk:    (y) => `<path d="M 43,${y + 1} q 7.5,6 14,-3.5" fill="none" stroke="#000" stroke-width="${LW2 + 0.3}" stroke-linecap="round"/>`,
  wobble:   (y) => `<path d="M 41.5,${y + 1} q 2.9,-4.4 5.7,0 q 2.9,4.4 5.7,0 q 2.9,-4.4 5.7,0" fill="none" stroke="#000" stroke-width="${LW2}" stroke-linecap="round"/>`,
  openO:    (y) => `<ellipse cx="50" cy="${y + 2}" rx="4.6" ry="6" fill="#000"/>`,
  talk:     (y) => `<path d="M 43,${y - 1} q 7,9 14,0 q -7,3.2 -14,0 Z" fill="#000" stroke="#000" stroke-width="${LW2}" stroke-linejoin="round"/>`,
  grin:     (y) => `<g><path d="M 39,${y - 3} q 11,14 22,0 q -11,4.5 -22,0 Z" fill="#000" stroke="#000" stroke-width="${LW2}" stroke-linejoin="round"/>
                      <path d="M 45,${y + 5.5} q 5,6 10,0 q -5,2.2 -10,0 Z" fill="url(#d50)" stroke="#000" stroke-width="1.6" stroke-linejoin="round"/></g>`,
  gape:     (y) => `<path d="M 50,${y - 5} C 58,${y - 5} 60,${y + 1} 59,${y + 5}
                      C 57.5,${y + 11} 42.5,${y + 11} 41,${y + 5} C 40,${y + 1} 42,${y - 5} 50,${y - 5} Z"
                      fill="#000" stroke="#000" stroke-width="${LW2}" stroke-linejoin="round"/>`,
  grit:     (y) => `<g><path d="M 40,${y - 3.5} h 20 v 8 h -20 Z" fill="#fff" stroke="#000" stroke-width="${LW2}" stroke-linejoin="round"/>
                      <g stroke="#000" stroke-width="1.7" fill="none"><path d="M 40,${y + 0.5} h 20"/>
                      <path d="M 46.6,${y - 3.5} v 8"/><path d="M 53.3,${y - 3.5} v 8"/></g></g>`,
};

// ---------------- heist mask ----------------
const MASK = `<g>
  <path d="M 13,49 C 28,42 72,42 87,49 L 87,68 C 72,75 28,75 13,68 Z"
    fill="#000" stroke="#000" stroke-width="${LW2}" stroke-linejoin="round"/>
  <rect x="26.5" y="50" width="17" height="19" rx="8.5" fill="#fff" stroke="#000" stroke-width="1.8"/>
  <rect x="56.5" y="50" width="17" height="19" rx="8.5" fill="#fff" stroke="#000" stroke-width="1.8"/></g>`;

// ---------------- corner marks ----------------
const halo = (g) => `<g stroke="#fff" stroke-width="5" stroke-linejoin="round" stroke-linecap="round">${g}</g>${g}`;
const X = {
  none: '',
  sweat1: drop(90, 24, 1.0),
  sweat2: drop(90, 24, 1.0) + drop(10, 30, 0.82),
  anger: `<g transform="translate(89,17)" stroke="#000" stroke-width="${LW2}" fill="none" stroke-linecap="round">
            <path d="M -6,-6 L 6,6"/><path d="M 6,-6 L -6,6"/><path d="M 0,-8.5 L 0,8.5"/><path d="M -8.5,0 L 8.5,0"/></g>`,
  excl: `<g transform="translate(90,14)">
           <path d="M -2.8,-10 L 2.8,-10 L 1.6,2.5 L -1.6,2.5 Z" fill="#000"/><circle cx="0" cy="7.5" r="2.8" fill="#000"/></g>`,
  quest: `<g transform="translate(90,14)">
            <path d="M -5,-5 a 5.2,5.2 0 1 1 5.6,6.2 l 0,2.6" fill="none" stroke="#000" stroke-width="3.4"
              stroke-linecap="round" stroke-linejoin="round"/><circle cx="0.6" cy="7.5" r="2.6" fill="#000"/></g>`,
  zzz: `<g transform="translate(85,10)" fill="none" stroke="#000" stroke-width="2.3" stroke-linejoin="round" stroke-linecap="round">
          <path d="M 0,4 h 7 l -7,7 h 7"/><path d="M 8.5,-5 h 5 l -5,5 h 5"/></g>`,
  sparks: sparkle(91, 15, 6.5) + sparkle(9, 22, 4.6) + sparkle(93, 33, 3),
  speed: `<g stroke="#000" stroke-width="${LW3}" stroke-linecap="round" fill="none">
            <path d="M 9,16 L 1,8"/><path d="M 19,9 L 15,1"/>
            <path d="M 91,16 L 99,8"/><path d="M 81,9 L 85,1"/></g>`,
};

// ---------------- expressions ----------------
const EXPRESSIONS = [
  { id:'neutral',      eyes:'oval',    mouth:'w',      ey:58, extra:'none' },
  { id:'smiling',      eyes:'arcUp',   mouth:'smile',  ey:58, extra:'none' },
  { id:'happy',        eyes:'arcUp',   mouth:'grin',   ey:57, extra:'none', blush:true },
  { id:'laugh',        eyes:'sqz',     mouth:'gape',   ey:56, extra:'speed' },
  { id:'sad',          eyes:'arcDown', mouth:'frown',  ey:59, extra:'none' },
  { id:'crying',       eyes:'teary',   mouth:'wobble', ey:57, extra:'none' },
  { id:'upset',        eyes:'angry',   mouth:'frown',  ey:59, extra:'anger' },
  { id:'raged',        eyes:'angry',   mouth:'grit',   ey:58, extra:'anger' },
  { id:'surprise',     eyes:'big',     mouth:'openO',  ey:57, extra:'excl' },
  { id:'shocked',      eyes:'big',     mouth:'gape',   ey:56, extra:'sweat1' },
  { id:'talking',      eyes:'oval',    mouth:'talk',   ey:58, extra:'none' },
  { id:'thinking',     eyes:'lid',     mouth:'smirk',  ey:58, extra:'quest' },
  { id:'focused',      eyes:'focus',   mouth:'flat',   ey:58, extra:'none' },
  { id:'smug',         eyes:'lid',     mouth:'smirk',  ey:58, extra:'none' },
  { id:'shifty',       eyes:'glance',  mouth:'cat',    ey:58, extra:'none', same:1 },
  { id:'nervous',      eyes:'glance',  mouth:'wobble', ey:58, extra:'sweat2' },
  { id:'excited',      eyes:'sparkle', mouth:'grin',   ey:56, extra:'sparks', blush:true },
  { id:'wink',         eyes:'wink',    mouth:'smile',  ey:58, extra:'none' },
  { id:'dizzy',        eyes:'swirl',   mouth:'wobble', ey:58, extra:'none' },
  { id:'sleepy',       eyes:'line',    mouth:'cat',    ey:60, extra:'zzz' },
  { id:'mask-neutral', eyes:'oval',    mouth:'w',      ey:59, extra:'none',   mask:true },
  { id:'mask-focused', eyes:'focus',   mouth:'flat',   ey:59, extra:'none',   mask:true },
  { id:'mask-smug',    eyes:'lid',     mouth:'smirk',  ey:59, extra:'none',   mask:true },
  { id:'mask-panic',   eyes:'big',     mouth:'gape',   ey:59, extra:'sweat1', mask:true },
];

function drawEyes(kind, y, o = {}) {
  const L = 35, R = 65;
  if (o.mask) {
    const k = 0.62;
    const wrap = (x, g) => `<g transform="translate(${x},${y}) scale(${k}) translate(${-x},${-y})">${g}</g>`;
    if (kind === 'wink') return wrap(L, EYE.arcUp(L, y)) + wrap(R, EYE.oval(R, y));
    const fm = EYE[kind];
    if (fm.length >= 3) { const sm = o.same === 1 ? [-1, -1] : [-1, 1];
      return wrap(L, fm(L, y, sm[0])) + wrap(R, fm(R, y, sm[1])); }
    return wrap(L, fm(L, y)) + wrap(R, fm(R, y));
  }
  if (kind === 'wink') return EYE.arcUp(L, y) + EYE.oval(R, y);
  const f = EYE[kind];
  if (f.length >= 3) { const s = o.same === 1 ? [-1, -1] : [-1, 1]; return f(L, y, s[0]) + f(R, y, s[1]); }
  return f(L, y) + f(R, y);
}

function face(e) {
  const eyeY = e.mask ? 59 : e.ey;
  const mouthY = e.mask ? 82 : e.ey + 18;
  return `
  <g transform="translate(50,58) scale(0.9) translate(-50,-58)">
  ${WHISKERS}
  <path d="${EAR_L}" fill="#fff" stroke="#000" stroke-width="${LW}" stroke-linejoin="round"/>
  <path d="${EAR_R}" fill="#fff" stroke="#000" stroke-width="${LW}" stroke-linejoin="round"/>
  <path d="${EAR_L_IN}" fill="url(#d50)" stroke="#000" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="${EAR_R_IN}" fill="url(#d50)" stroke="#000" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="${HEAD}" fill="#fff" stroke="#000" stroke-width="${LW}" stroke-linejoin="round"/>
  ${e.mask ? MASK : ''}
  ${drawEyes(e.eyes, eyeY, e)}
  ${e.mask ? '' : nose(e.ey + 12)}
  ${M[e.mouth](mouthY)}
  ${e.blush && !e.mask ? blush() : ''}
  </g>
  ${X[e.extra] ? halo(X[e.extra]) : ''}`;
}

module.exports = { S, DEFS, EXPRESSIONS, face, HEAD, roundPoly, squircle, EAR_L, EAR_R, EAR_L_IN, EAR_R_IN,
  WHISKERS, MASK, EYE, M, LW, LW2, LW3, nose, drop, sparkle, blush, drawEyes, oval };
