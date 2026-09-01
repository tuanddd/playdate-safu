const fs = require('fs');
const path = require('path');
const C = require('./comic.js');
const OUT = __dirname;
const W = 400, H = 240;
const page = (b) => `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
${C.DEFS}<rect width="100%" height="100%" fill="#fff"/>${b}</svg>`;
const BW = 2.6;

/* ==========================================================
   PAGE 1 — flat line art. Midnight over the sleeping city;
   Neko already perched in silhouette on a foreground roof.
   ========================================================== */
const p1 = `
  ${C.starfield(7, 8, 6, 380, 104, 20)}
  <g stroke="#000" stroke-width="1.6" stroke-linecap="round">
    <path d="M 186,22 L 224,36"/><path d="M 196,18 L 220,27"/></g>
  ${C.star(228, 39, 4.2)}
  ${C.moon(298, 58, 34)}
  ${C.cloud(226, 90, 1.3)}
  ${C.cloud(30, 66, 1.0)}
  ${C.skyline(21, -6, 398, 196, 34, 96, '#fff')}
  <g><path d="M 306,142 L 348,142 L 343,130 L 311,130 Z" fill="#fff" stroke="#000" stroke-width="2" stroke-linejoin="round"/>
     <rect x="309" y="142" width="36" height="15" fill="#fff" stroke="#000" stroke-width="2"/>
     <path d="M 317,157 L 317,170 M 337,157 L 337,170" stroke="#000" stroke-width="2"/></g>
  <rect x="-10" y="196" width="420" height="60" fill="#fff"/>
  <path d="M -10,196 L 410,196" stroke="#000" stroke-width="2.6"/>
  <g fill="#fff" stroke="#000" stroke-width="1.8">
    <rect x="12" y="189" width="16" height="8"/><rect x="150" y="189" width="16" height="8"/>
    <rect x="262" y="189" width="16" height="8"/><rect x="372" y="189" width="16" height="8"/></g>
  ${C.nekoSilhouette(70, 194, 0.92, true)}
`;
fs.writeFileSync(path.join(OUT, 'comic-01-midnight.svg'), page(`
  ${C.panel('p1', C.rectQuad(6, 6, 388, 228), p1, { tx: 6, ty: 6, bw: BW })}
  <rect x="18" y="18" width="150" height="52" fill="#fff" stroke="#000" stroke-width="2"/>
  ${C.txt(28, 39, '00:00.', 13)}
  ${C.txt(28, 58, 'THE CITY SLEEPS.', 11)}
`));

/* ==========================================================
   PAGE 2 — rooftop crouch / mask close-up / inside with the note
   ========================================================== */
const qA = [[6, 6], [194, 11], [187, 116], [6, 111]];
const qB = [[202, 11], [394, 6], [394, 111], [195, 116]];
const qC = [[6, 122], [394, 117], [394, 234], [6, 229]];

const pA = `
  ${C.starfield(3, 2, 2, 186, 60, 10)}
  ${C.moon(152, 27, 20)}
  <g stroke="#000" stroke-width="1.5" stroke-linecap="round" fill="none">
    <path d="M 8,40 q 14,-3 26,0"/><path d="M 20,52 q 12,-3 22,0"/></g>
  <g transform="translate(30,21) scale(0.82)">${C.nekoCrouch({ eyes: 'focus' })}</g>
  <rect x="-12" y="94" width="230" height="60" fill="#fff" stroke="#000" stroke-width="2.4"/>
  <path d="M -12,101 L 218,101" stroke="#000" stroke-width="1.4"/>
  <g fill="#fff" stroke="#000" stroke-width="1.2"><rect x="14" y="108" width="6" height="7"/><rect x="34" y="108" width="6" height="7"/>
     <rect x="152" y="110" width="6" height="7"/><rect x="172" y="110" width="6" height="7"/></g>
`;

const pB = `
  ${C.rayTicks(100, 62, 26, 150, 70, 11)}
  ${C.speedLines(11, 100, 62, 60, 118, 18)}
  <circle cx="100" cy="62" r="54" fill="#fff" stroke="#000" stroke-width="2.4"/>
  <g transform="translate(41,-2) scale(1.14)">
    ${C.head({ mask: true, eyes: 'focus', mouth: 'flat' })}
  </g>
  ${C.star(146, 22, 5)}
  ${C.star(52, 96, 3.6)}
`;

const noteInPaw = `
  <g transform="translate(-38,86) rotate(-10)">
    <rect x="0" y="0" width="46" height="34" fill="#fff" stroke="#000" stroke-width="2.6"/>
    <path d="M 46,0 L 35,8 L 38,-1 Z" fill="#fff" stroke="#000" stroke-width="1.8" stroke-linejoin="round"/></g>
  <path d="M 34,96 C 24,100 16,102 9,102" fill="none" stroke="#000" stroke-width="12" stroke-linecap="round"/>
  <path d="M 34,96 C 24,100 16,102 9,102" fill="none" stroke="#fff" stroke-width="7.2" stroke-linecap="round"/>
  <ellipse cx="7" cy="102" rx="7" ry="6.4" fill="#fff" stroke="#000" stroke-width="2.6"/>`;

const pC = `
  ${C.room(-30, 430, 100, { })}
  ${C.windowFrame(24, 6, 52, 40)}
  <g transform="translate(300,12)">
    <rect x="0" y="0" width="60" height="44" fill="#fff" stroke="#000" stroke-width="2.4"/>
    <rect x="5" y="5" width="50" height="34" fill="#fff" stroke="#000" stroke-width="1.6"/>
    <path d="M 10,32 L 22,18 L 32,28 L 42,14 L 50,32 Z" fill="#fff" stroke="#000" stroke-width="1.6" stroke-linejoin="round"/></g>
  <g transform="translate(112,-14) scale(0.85)">
    ${C.nekoFull({ mask: true, eyes: 'glance', same: 1, mouth: 'wobble', armL: noteInPaw })}
  </g>
  ${C.quest(196, 14, 1.15)}
  ${C.txt(240, 52, 'A NOTE...', 12)}
  ${C.txt(240, 70, 'NOTHING ON IT.', 12)}
  <path d="M 234,44 L 234,76" stroke="#000" stroke-width="2.4"/>
`;

fs.writeFileSync(path.join(OUT, 'comic-02-heist.svg'), page(`
  ${C.panel('p2a', qA, pA, { tx: 6, ty: 6, bw: BW })}
  ${C.panel('p2b', qB, pB, { tx: 195, ty: 6, bw: BW })}
  ${C.panel('p2c', qC, pC, { tx: 6, ty: 117, bw: BW })}
  <rect x="12" y="84" width="132" height="26" fill="#fff" stroke="#000" stroke-width="2"/>
  ${C.txt(20, 102, 'ENTER: THE CAT.', 11)}
`));

/* ==========================================================
   PAGE 3 — POV on the note; the note drops, the safe was
   right there the whole time. Cut.
   ========================================================== */
const qD = [[6, 6], [394, 6], [394, 104], [6, 104]];
const qE = [[6, 110], [394, 110], [394, 208], [6, 208]];

const pD = `
  ${C.room(-30, 430, 62, { })}
  ${C.windowFrame(22, 2, 44, 32)}
  ${C.safe(302, 12, 56, 52)}
  ${C.povNote({ x: 112, y: 6, w: 160, h: 86, pawAt: 0.52 })}
  ${C.N.drop(268, 22, 1.0)}
  ${C.quest(290, 34, 1.0)}
`;

const pE = `
  ${C.room(-30, 430, 84, { })}
  ${C.rayTicks(194, 42, 30, 220, 78, 31)}
  ${C.speedLines(31, 194, 42, 60, 104, 16)}
  ${C.safe(152, 4, 84, 80)}
  ${C.star(126, 14, 5)}
  ${C.star(266, 26, 4)}
  ${C.star(142, 66, 3.4)}
  <g transform="translate(88,74) rotate(14)">
    <rect x="0" y="0" width="44" height="30" fill="#fff" stroke="#000" stroke-width="2.4"/></g>
  <g stroke="#000" stroke-width="1.5" fill="none" stroke-linecap="round">
    <path d="M 100,44 q -6,12 2,24"/><path d="M 118,48 q 6,12 -2,22"/></g>
  ${C.excl(48, 30, 1.3)}
  ${C.excl(340, 30, 1.3)}
`;

fs.writeFileSync(path.join(OUT, 'comic-03-reveal.svg'), page(`
  ${C.panel('p3a', qD, pD, { tx: 6, ty: 6, bw: BW })}
  <rect x="14" y="66" width="130" height="30" fill="#fff" stroke="#000" stroke-width="2"/>
  ${C.txt(23, 87, 'STILL BLANK...', 12)}
  ${C.panel('p3b', qE, pE, { tx: 6, ty: 110, bw: BW })}
  <rect x="6" y="214" width="388" height="20" fill="#000"/>
  ${C.txt(200, 229, 'CUT.', 13, 'middle', '#fff')}
`));
console.log('comic pages written');
