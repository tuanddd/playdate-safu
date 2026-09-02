import fs from 'node:fs'
import path from 'node:path'
export const ROOT = '/Users/vincent/Desktop/work/playdate-test/safu'

// jobs: [{svg, png, w, h, zoom?, transparent?}]  — renders, thresholds to pure 1-bit, and
// optionally writes a nearest-neighbour zoomed preview alongside.
export async function renderHud(jobs, ctx) {
  const { js, openOrReuseTab, wait, cliLog } = ctx
  await openOrReuseTab('about:blank', { wait: false })
  await wait(0.6)
  for (const j of jobs) {
    const svg = fs.readFileSync(path.join(ROOT, j.svg), 'utf8')
    const b64 = Buffer.from(svg, 'utf8').toString('base64')
    const zoom = j.zoom || 0
    const out = await js(`(async () => {
      const img = new Image();
      await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error('load fail')); img.src = 'data:image/svg+xml;base64,' + ${JSON.stringify(b64)}; });
      const c = document.createElement('canvas'); c.width = ${j.w}; c.height = ${j.h};
      const g = c.getContext('2d');
      g.fillStyle = '#fff'; g.fillRect(0,0,c.width,c.height);
      g.drawImage(img, 0, 0, c.width, c.height);
      const d = g.getImageData(0,0,c.width,c.height);
      const p = d.data;
      const clearWhite = ${j.transparent ? 'true' : 'false'};
      for (let i = 0; i < p.length; i += 4) {
        const v = (p[i]*0.299 + p[i+1]*0.587 + p[i+2]*0.114) < 128 ? 0 : 255;
        p[i] = p[i+1] = p[i+2] = v;
        p[i+3] = (clearWhite && v === 255) ? 0 : 255;
      }
      g.putImageData(d, 0, 0);
      const one = c.toDataURL('image/png');
      let big = null;
      if (${zoom}) {
        const z = document.createElement('canvas'); z.width = c.width*${zoom}; z.height = c.height*${zoom};
        const zg = z.getContext('2d'); zg.imageSmoothingEnabled = false;
        zg.drawImage(c, 0, 0, z.width, z.height);
        big = z.toDataURL('image/png');
      }
      return JSON.stringify({one, big});
    })()`)
    let parsed
    try { parsed = JSON.parse(out) } catch { cliLog('FAIL ' + j.png + ' :: ' + String(out).slice(0, 300)); continue }
    if (!parsed.one || !parsed.one.startsWith('data:image/png')) { cliLog('FAIL ' + j.png); continue }
    fs.writeFileSync(path.join(ROOT, j.png), Buffer.from(parsed.one.split(',')[1], 'base64'))
    cliLog('wrote ' + j.png + '  ' + j.w + 'x' + j.h)
    if (parsed.big) {
      const bp = j.png.replace(/\.png$/, `@${zoom}x.png`)
      fs.writeFileSync(path.join(ROOT, bp), Buffer.from(parsed.big.split(',')[1], 'base64'))
      cliLog('wrote ' + bp)
    }
  }
}
