// Five candidate title-screen backgrounds.
//
// The dither patterns are declared HERE rather than in comic.js: that file is
// deliberately in FLAT mode (every p*/d* is solid white) so the comic shapes
// could be iterated without tone, and turning them on globally would silently
// restyle every comic page. The primitives emit url(#p50) and friends, so a
// local <defs> gives them real tone in this document only.
const C = require('./comic.js');
const fs = require('fs');

const cell = (id, size, dots, bg = '#fff', ink = '#000') =>
  `<pattern id="${id}" width="${size}" height="${size}" patternUnits="userSpaceOnUse">` +
  `<rect width="${size}" height="${size}" fill="${bg}"/>` +
  dots.map(([x, y]) => `<rect x="${x}" y="${y}" width="1" height="1" fill="${ink}"/>`).join('') +
  `</pattern>`;

// Bayer 4x4 ordered thresholds, so the ramp is even and the cells land on device pixels
const DEFS = `<defs>
${cell('p12', 4, [[0,0],[2,2]])}
${cell('p25', 4, [[0,0],[2,0],[0,2],[2,2]])}
${cell('p50', 2, [[0,0],[1,1]])}
${cell('p75', 4, [[1,0],[3,0],[0,1],[2,1],[1,2],[3,2],[0,3],[2,3],[0,0],[2,2],[1,1],[3,3]])}
${cell('d12', 4, [[0,0],[2,2]])}
${cell('d25', 4, [[0,0],[2,0],[0,2],[2,2]])}
${cell('d50', 2, [[0,0],[1,1]])}
${cell('d75', 4, [[1,0],[3,0],[0,1],[2,1],[1,2],[3,2],[0,3],[2,3],[0,0],[2,2],[1,1],[3,3]])}
</defs>`;

const W = 400, H = 240;
// The dial is drawn by the game at (200,126) r=62. Every background keeps a clear
// disc there, or the tick marks turn to mush against the tone behind them.
const DIAL = { x: 200, y: 126, r: 62 };
const safeDisc = (pad = 12) =>
  `<circle cx="${DIAL.x}" cy="${DIAL.y}" r="${DIAL.r + pad}" fill="#fff"/>`;

const svg = (body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
${DEFS}<rect width="${W}" height="${H}" fill="#fff"/>${body}</svg>`;

const wedge = (cx, cy, a0, a1, r, fill) => {
  const p = (a, rr) => `${(cx + Math.cos(a) * rr).toFixed(1)},${(cy + Math.sin(a) * rr).toFixed(1)}`;
  return `<path d="M ${cx},${cy} L ${p(a0, r)} L ${p(a1, r)} Z" fill="${fill}"/>`;
};
const ring = (cx, cy, r, fill) => `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${fill}"/>`;
const D = Math.PI / 180;

const scenes = {};

// 1. MIDNIGHT - the world comic-01-midnight already establishes.
// Skyline is p50, not black: solid black would merge with the black robbers in front.
scenes['bg-01-midnight'] = svg(`
  ${C.wash(0, 0, W, 150, ['p75', 'p50', 'p25', 'p12'])}
  ${C.starfield(7, 8, 8, 392, 96, 26)}
  ${C.moon(330, 44, 20)}
  ${C.skyline(3, -10, 410, 214, 44, 96, 'url(#p50)')}
  ${safeDisc()}`);

// 2. SEARCHLIGHT - the BLACKOUT cone idea, from off-screen, crossing behind the dial.
scenes['bg-02-searchlight'] = svg(`
  <rect width="${W}" height="${H}" fill="url(#p75)"/>
  ${wedge(-60, 300, -70 * D, -26 * D, 560, 'url(#p50)')}
  ${wedge(-60, 300, -58 * D, -38 * D, 560, 'url(#p25)')}
  ${wedge(470, 300, -156 * D, -112 * D, 560, 'url(#p50)')}
  ${wedge(470, 300, -144 * D, -124 * D, 560, 'url(#p25)')}
  ${safeDisc(16)}`);

// 3. RAY BURST - the comic's impact-beat backdrop, aimed at the dial.
scenes['bg-03-rayburst'] = svg(`
  ${C.rays(DIAL.x, DIAL.y, 22, 320, { fill: 'url(#p25)' })}
  ${C.rayTicks(DIAL.x, DIAL.y, 30, 300, 150, 5)}
  ${ring(DIAL.x, DIAL.y, 132, 'url(#p12)')}
  ${safeDisc(22)}`);

// 4. VAULT PLATE - echoes the play screen's door: toned steel, engraved frame, rivets.
scenes['bg-04-vault'] = svg(`
  <rect width="${W}" height="${H}" fill="url(#p25)"/>
  <rect x="14" y="14" width="${W - 28}" height="${H - 28}" fill="url(#p12)" stroke="#000" stroke-width="2.5"/>
  <rect x="26" y="26" width="${W - 52}" height="${H - 52}" fill="none" stroke="#000" stroke-width="1.4"/>
  ${Array.from({ length: 14 }, (_, i) => {
      const t = i / 13;
      return `<circle cx="${(20 + t * (W - 40)).toFixed(1)}" cy="7" r="3" fill="#fff" stroke="#000" stroke-width="1.2"/>` +
             `<circle cx="${(20 + t * (W - 40)).toFixed(1)}" cy="${H - 7}" r="3" fill="#fff" stroke="#000" stroke-width="1.2"/>`;
    }).join('')}
  ${safeDisc(14)}`);

// 5. VIGNETTE - plain radial falloff, dark edges to a clear middle.
scenes['bg-05-vignette'] = svg(`
  <rect width="${W}" height="${H}" fill="url(#p75)"/>
  ${ring(DIAL.x, DIAL.y, 210, 'url(#p50)')}
  ${ring(DIAL.x, DIAL.y, 165, 'url(#p25)')}
  ${ring(DIAL.x, DIAL.y, 122, 'url(#p12)')}
  ${safeDisc(18)}`);

const jobs = [];
for (const [name, s] of Object.entries(scenes)) {
  fs.writeFileSync(`${__dirname}/${name}.svg`, s);
  // renderJobs does path.join(ROOT, j.svg), so these must be root-relative
  jobs.push({ svg: `images/svg/${name}.svg`, png: `images/svg/${name}.png`, w: W, h: H });
}
fs.writeFileSync('/tmp/title-bg-jobs.json', JSON.stringify(jobs));
console.log(`${jobs.length} scenes written`);
