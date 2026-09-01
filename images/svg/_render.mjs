import fs from 'node:fs'
import path from 'node:path'
export const ROOT = '/Users/vincent/Desktop/work/playdate-test/safu'

// jobs: [{svg, png, w, h, nearest?}]
export async function renderJobs(jobs, ctx) {
  const { js, openOrReuseTab, wait, cliLog } = ctx
  await openOrReuseTab('about:blank', { wait: false })
  await wait(0.6)
  for (const j of jobs) {
    const svg = fs.readFileSync(path.join(ROOT, j.svg), 'utf8')
    const b64 = Buffer.from(svg, 'utf8').toString('base64')
    const out = await js(`(async () => {
      const img = new Image();
      await new Promise((res, rej) => { img.onload = res; img.onerror = () => rej(new Error('load fail')); img.src = 'data:image/svg+xml;base64,' + ${JSON.stringify(b64)}; });
      const c = document.createElement('canvas'); c.width = ${j.w}; c.height = ${j.h};
      const g = c.getContext('2d');
      g.imageSmoothingEnabled = ${j.nearest ? 'false' : 'true'}; g.imageSmoothingQuality = 'high';
      g.fillStyle = '#fff'; g.fillRect(0,0,c.width,c.height);
      g.drawImage(img, 0, 0, c.width, c.height);
      return c.toDataURL('image/png');
    })()`)
    if (typeof out !== 'string' || !out.startsWith('data:image/png')) {
      cliLog('FAIL ' + j.png + ' :: ' + JSON.stringify(out).slice(0, 300)); continue
    }
    fs.writeFileSync(path.join(ROOT, j.png), Buffer.from(out.split(',')[1], 'base64'))
    cliLog('wrote ' + j.png + '  ' + j.w + 'x' + j.h)
  }
}
