// Exports every modifier icon as a standalone 14x14 SVG, plus one strip for the
// Playdate imagetable, plus the id -> file manifest that ties them together.
//
//   images/svg/icons/<icon-id>.svg          one file per icon, 14x14
//   images/svg/mod-icons-table-14-14.svg    all 12 in frame order, 168x14
//   images/icons-manifest.json              icon id -> paths + frame + modifier
//
// Rendering to PNG is _run-hud.sh; see the jobs array printed by --jobs.
const fs = require('fs');
const path = require('path');
const H = require('./hud.js');

const ROOT = path.join(__dirname, '..', '..');
const SIZE = 14;

// icon id -> how to draw it. `pix` are hand-drawn on the 14 grid; `memory` are
// Pictogrammers Memory paths scaled from their native 22 grid.
const ICONS = [
  { id: 'eye-off', src: 'memory', name: 'eye', slash: true, modifier: 'blackout' },
  { id: 'music-note', src: 'memory', name: 'music-note', modifier: 'too-loud' },
  { id: 'crosshair', src: 'pix', modifier: 'hair-trigger' },
  { id: 'oil-slip', src: 'pix', modifier: 'greased' },
  { id: 'goo-drip', src: 'pix', modifier: 'sticky' },
  { id: 'both-ways', src: 'pix', modifier: 'scrambled' },
  { id: 'four-pins', src: 'pix', modifier: 'four-tumblers' },
  { id: 'drift-target', src: 'pix', modifier: 'wandering' },
  { id: 'twin-marks', src: 'pix', modifier: 'decoy' },
  { id: 'skull', src: 'memory', name: 'skull', modifier: 'one-shot' },
  { id: 'peaked-cap', src: 'pix', modifier: 'guard' },
  { id: 'flask', src: 'memory', name: 'flask', modifier: 'nitro' },
];

const glyph = (ic, x = 0, y = 0) =>
  ic.src === 'pix'
    ? H.pixIcon(ic.id, x, y)
    : H.icon(ic.name, x, y, { slash: ic.slash, scale: SIZE / 22 });

const wrap = (w, h, body) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">` +
  `<rect width="${w}" height="${h}" fill="#fff"/>${body}</svg>`;

const outDir = path.join(__dirname, 'icons');
fs.mkdirSync(outDir, { recursive: true });
for (const ic of ICONS) {
  fs.writeFileSync(path.join(outDir, `${ic.id}.svg`), wrap(SIZE, SIZE, glyph(ic)));
}

// One row of frames, in the order the modifiers are listed in game.md §12.
const strip = ICONS.map((ic, i) => glyph(ic, i * SIZE, 0)).join('');
fs.writeFileSync(path.join(__dirname, 'mod-icons-table-14-14.svg'),
  wrap(ICONS.length * SIZE, SIZE, strip));

const manifest = {
  note: 'Safu modifier icons. Frames are 1-indexed to match Playdate imagetable:getImage().',
  size: [SIZE, SIZE],
  imagetable: {
    // pdc strips the -table-w-h suffix, so the runtime path is images/mod-icons.
    // The name must NOT be "modifiers" — that would collide with the folder of
    // individual icons and produce images/modifiers.pdt next to images/modifiers/.
    lua: 'images/mod-icons',
    png: 'source/images/mod-icons-table-14-14.png',
    svg: 'images/svg/mod-icons-table-14-14.svg',
    frames: ICONS.length,
  },
  icons: Object.fromEntries(ICONS.map((ic, i) => [ic.id, {
    frame: i + 1,
    modifier: ic.modifier,
    source: ic.src === 'pix' ? 'drawn on the 14x14 grid in images/svg/icons-pixel.js'
                             : `Pictogrammers Memory "${ic.name}"${ic.slash ? ' + slash' : ''}, scaled from 22px`,
    lua: `images/modifiers/${ic.id}`,
    png: `source/images/modifiers/${ic.id}.png`,
    svg: `images/svg/icons/${ic.id}.svg`,
  }])),
};
fs.writeFileSync(path.join(ROOT, 'images', 'icons-manifest.json'), JSON.stringify(manifest, null, 2));

// Not a modifier icon, but it lives on the same grid and ships the same way.
for (const extra of ['clock-14', 'btn-a', 'btn-b']) {
  fs.writeFileSync(path.join(outDir, `${extra}.svg`), wrap(SIZE, SIZE, H.pixIcon(extra, 0, 0)));
}

if (process.argv.includes('--jobs')) {
  const jobs = ICONS.map(ic => ({
    svg: `images/svg/icons/${ic.id}.svg`,
    png: `source/images/modifiers/${ic.id}.png`,
    w: SIZE, h: SIZE, transparent: true,
  }));
  for (const [id, png] of [['clock-14', 'clock-14'], ['btn-a', 'btn-a-14'], ['btn-b', 'btn-b-14']]) {
    jobs.push({ svg: `images/svg/icons/${id}.svg`, png: `source/images/${png}.png`, w: SIZE, h: SIZE, transparent: true });
  }
  jobs.push({
    svg: 'images/svg/mod-icons-table-14-14.svg',
    png: 'source/images/mod-icons-table-14-14.png',
    w: ICONS.length * SIZE, h: SIZE, transparent: true,
  });
  process.stdout.write(JSON.stringify(jobs));
} else {
  console.log(`${ICONS.length} icons -> images/svg/icons/, strip, manifest`);
}
