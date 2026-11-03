// The recording browser for the AI player. Copied in spirit from research/osz_promo/capture.mjs: real gameplay,
// the page is the live game, frames come from the browser's own CDP screencast with their capture times.
// Python owns the brain and talks over stdin/stdout, one JSON object per line. Input goes through the game's own
// client (__osz.fire, G.goal), so what is on screen is what a player would see if they pressed those buttons.
//   node capture.mjs OUTDIR
import fs from 'node:fs';
import readline from 'node:readline';
const { chromium } = await import(process.env.PW || 'playwright');
const out = process.argv[2], base = process.env.BASE_URL || 'http://127.0.0.1:8120';
const W = Number(process.env.W || 1280), H = Number(process.env.H || 720), DSF = Number(process.env.DSF || 1.5), FPS_DIR = `${out}/frames`;
fs.rmSync(FPS_DIR, { recursive: true, force: true }); fs.mkdirSync(FPS_DIR, { recursive: true });
const tell = (o) => process.stdout.write(JSON.stringify(o) + '\n');
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'] });
const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: DSF });
await ctx.addInitScript(() => {
  try { localStorage.setItem('osz.hint.first', '1'); for (const k of ['desk', 'down', 'grab', 'quiet', 'spot', 'stick']) { localStorage.setItem('osz.hint.' + k, '9'); localStorage.setItem('hint.' + k, '9'); } } catch { /* fine */ }
});
const page = await ctx.newPage();
const cdp = await ctx.newCDPSession(page);
page.on('websocket', (ws) => ws.on('framereceived', (f) => tell({ k: 'ws', p: f.payload })));
page.on('pageerror', (e) => tell({ k: 'pageerror', m: e.message.slice(0, 200) }));
const frames = [], writes = []; let recording = false;
cdp.on('Page.screencastFrame', (f) => {
  const file = `f${String(frames.length).padStart(6, '0')}.jpg`; frames.push({ file, t: f.metadata.timestamp });
  writes.push(fs.promises.writeFile(`${FPS_DIR}/${file}`, Buffer.from(f.data, 'base64')));
  cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {});
});
async function stop(why) {
  if (recording) { recording = false; await cdp.send('Page.stopScreencast').catch(() => {}); }
  await Promise.all(writes);
  fs.writeFileSync(`${out}/frames.json`, JSON.stringify({ why, viewport: [W, H], dsf: DSF, note: 't is the screencast timestamp in seconds of wall clock, the same clock as wall_ts in events.jsonl', frames }));
  tell({ k: 'stopped', frames: frames.length, seconds: frames.length ? frames.at(-1).t - frames[0].t : 0 });
  await browser.close(); process.exit(0);
}
// The search drawer covers half the screen. A person closes it after taking things; so does this, for the edit.
let drawerSince = 0;
setInterval(async () => { try {
  const open = await page.evaluate(() => { const d = document.getElementById('sceneDrawer'); return !!d && !d.hidden; });
  if (!open) { drawerSince = 0; return; }
  drawerSince ||= Date.now();
  if (Date.now() - drawerSince > 1500) { await page.evaluate(() => document.getElementById('drawerClose')?.click()); drawerSince = 0; }
} catch { /* page closing */ } }, 400);
setInterval(() => { const m = /MemAvailable:\s+(\d+)/.exec(fs.readFileSync('/proc/meminfo', 'utf8')); if (m && Number(m[1]) / 1024 < 2048) { tell({ k: 'lowmem' }); stop('memory under 2 GB'); } }, 3000);
readline.createInterface({ input: process.stdin }).on('line', async (line) => {
  const j = JSON.parse(line);
  try {
    if (j.k === 'begin') {
      await page.goto(base + '/');
      await page.waitForFunction(() => window.__osz, null, { timeout: 30000 });
      await page.evaluate(() => document.getElementById('goWalk').click());
      await page.waitForSelector(`button[data-start="${j.start}"]`, { timeout: 30000, state: 'visible' });
      await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 88, maxWidth: Math.round(W * DSF), maxHeight: Math.round(H * DSF), everyNthFrame: 1 }); recording = true;
      await page.waitForTimeout(800);
      await page.evaluate((id) => document.querySelector(`button[data-start="${id}"]`).click(), j.start);
      tell({ k: 'token', token: await page.evaluate(() => window.__osz.G.token) });
    } else if (j.k === 'fire') {
      await page.evaluate(({ a, args }) => window.__osz.fire(a, args), j);
    } else if (j.k === 'goal') {
      await page.evaluate((p) => { const G = window.__osz.G; G.route = []; G.goal = p; }, j.p);
    } else if (j.k === 'state') {
      tell({ k: 'state', fps: await page.evaluate(() => window.__osz.G.fps) });
    } else if (j.k === 'stop') await stop('asked');
  } catch (e) { tell({ k: 'error', m: String(e.message).slice(0, 200), on: j.k }); }
});
tell({ k: 'ready' });
