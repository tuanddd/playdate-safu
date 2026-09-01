const fs = require('fs');
const path = require('path');
const N = require('./neko.js');

const OUT = path.join(__dirname);
const COLS = 6;
const ROWS = Math.ceil(N.EXPRESSIONS.length / COLS);
const CELL = 100;

// ---- 1. contact sheet (with labels, for humans) ----
let cells = '';
N.EXPRESSIONS.forEach((e, i) => {
  const cx = (i % COLS) * CELL;
  const cy = Math.floor(i / COLS) * (CELL + 18);
  cells += `<g transform="translate(${cx},${cy})">${N.face(e)}</g>
    <text x="${cx + 50}" y="${cy + CELL + 12}" font-family="Menlo,monospace" font-size="9"
      text-anchor="middle" fill="#000">${e.id}</text>`;
});
const labelled = `<svg xmlns="http://www.w3.org/2000/svg" width="${COLS*CELL}" height="${ROWS*(CELL+18)}"
  viewBox="0 0 ${COLS*CELL} ${ROWS*(CELL+18)}">
  ${N.DEFS}<rect width="100%" height="100%" fill="#fff"/>
  <g stroke="#000" stroke-width="0.6" opacity="0.25" fill="none">
  ${N.EXPRESSIONS.map((_,i)=>{const cx=(i%COLS)*CELL,cy=Math.floor(i/COLS)*(CELL+18);
    return `<rect x="${cx+0.5}" y="${cy+0.5}" width="${CELL-1}" height="${CELL+17}"/>`;}).join('')}
  </g>
  ${cells}</svg>`;
fs.writeFileSync(path.join(OUT, 'neko-expressions-labelled.svg'), labelled);

// ---- 2. game sprite sheet (no labels, exact grid, Playdate imagetable naming) ----
let raw = '';
N.EXPRESSIONS.forEach((e, i) => {
  const cx = (i % COLS) * CELL;
  const cy = Math.floor(i / COLS) * CELL;
  raw += `<g transform="translate(${cx},${cy})">${N.face(e)}</g>`;
});
const sheet = `<svg xmlns="http://www.w3.org/2000/svg" width="${COLS*CELL}" height="${ROWS*CELL}"
  viewBox="0 0 ${COLS*CELL} ${ROWS*CELL}">
  ${N.DEFS}<rect width="100%" height="100%" fill="#fff"/>${raw}</svg>`;
fs.writeFileSync(path.join(OUT, 'neko-expressions-sheet.svg'), sheet);

// ---- 3. individual faces ----
fs.mkdirSync(path.join(OUT, 'faces'), { recursive: true });
N.EXPRESSIONS.forEach(e => {
  const one = `<svg xmlns="http://www.w3.org/2000/svg" width="${CELL}" height="${CELL}" viewBox="0 0 ${CELL} ${CELL}">
    ${N.DEFS}<rect width="100%" height="100%" fill="#fff"/>${N.face(e)}</svg>`;
  fs.writeFileSync(path.join(OUT, 'faces', `neko-${e.id}.svg`), one);
});

console.log(`sheet: ${COLS}x${ROWS} = ${N.EXPRESSIONS.length} expressions`);
console.log(N.EXPRESSIONS.map(e=>e.id).join(', '));
