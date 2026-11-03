// C8 on a phone-sized touch browser: a herd heard, then seen as one crowd, then woken by walking up to it.
// Needs the local herd server (tools/serve_herd.py), because the real schedule brings one within reach
// only every several hours of play:
//   node tools/mobile_herd_check.mjs [base] [shots-prefix]          against `serve_herd.py 8021 pass`
//   node tools/mobile_herd_check.mjs [base] [shots-prefix] load     against `serve_herd.py 8021 load 2`
// `load` waits for two herds to be awake around the survivor and times the health check meanwhile.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8021', prefix = process.argv[3] || '/tmp/osz-herd', load = process.argv[4] === 'load';
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
const trace = []; let passed = false;
process.on('exit', () => { if (!passed && trace.length) console.error('trace: ' + trace.slice(-40).join(' | ')); });
const health = async (n, gap) => {
  const ms = [];
  for (let i = 0; i < n; i++) { const t = performance.now(), r = await fetch(base + '/healthz'); await r.json(); ms.push(performance.now() - t); await new Promise((f) => setTimeout(f, gap)); }
  ms.sort((a, b) => a - b);
  return { n, median: +ms[n >> 1].toFixed(1), p95: +ms[Math.floor(n * 0.95)].toFixed(1), max: +ms[n - 1].toFixed(1) };
};
try {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width: 393, height: 851 }, permissions: ['geolocation'], geolocation: { latitude: 44.9778, longitude: -93.265, accuracy: 8 } });
  const p = await c.newPage(), errors = [], toasts = [];
  p.on('pageerror', (e) => errors.push(e.message));
  // The herd can be heard before the game has finished starting: listen from the first message, and keep every toast.
  await p.addInitScript(() => {
    window.__herdEv = []; window.__toasts = [];
    const W = window.WebSocket;
    window.WebSocket = class extends W { constructor(...a) { super(...a); this.addEventListener('message', (e) => { try { const m = JSON.parse(e.data); for (const ev of m.ev || []) if (ev.e === 'herd') window.__herdEv.push(ev); } catch (_) {} }); } };
    new MutationObserver((list) => { for (const r of list) for (const n of r.addedNodes) if (n.classList && n.classList.contains('toast')) window.__toasts.push(n.textContent); }).observe(document, { childList: true, subtree: true });
  });
  const toasted = (re) => p.waitForFunction((src) => window.__toasts.some((t) => new RegExp(src).test(t)), re.source, { timeout: 8000 });
  await p.goto(base + '/?auto=desk&name=' + (load ? 'HerdLoad' : 'HerdScout'));
  await p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping && __osz.G.body, null, { timeout: 90000 });
  const said = (op) => p.evaluate((op) => window.__herdEv.filter((e) => e.op === op), op);
  const state = () => p.evaluate(() => { const s = __osz.state(); return { herds: s.herds || [], zeds: s.zeds, hz: s.zeds.filter((z) => z.id.startsWith('h:')).length, fps: s.fps, inside: __osz.G.inside, hp: s.you.hp, dead: s.dead, at: [s.you.lat, s.you.lng] }; });
  const out = { quietHealth: await health(20, 100) };

  if (load) {
    // ---- two herds awake around one survivor: what the server and the phone make of it
    await p.waitForFunction(() => __osz.state().zeds.filter((z) => z.id.startsWith('h:')).length >= 40, null, { timeout: 180000, polling: 500 });
    await p.waitForTimeout(4000);
    out.awakeHealth = await health(60, 250);
    const s = await state();
    out.zombiesInSight = s.zeds.length; out.ofTheHerds = s.hz; out.fps = s.fps; out.latency = await p.evaluate(() => __osz.latency());
    out.woke = (await said('woke')).length;
    await p.screenshot({ path: prefix + '-load.png' });
    assert(out.woke >= 2, 'both herds woke');
    assert(out.awakeHealth.max < 300, 'the health check stays under 300 ms with two herds awake');
  } else {
    const cdp = await c.newCDPSession(p);
    const touch = (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map(([x, y, id]) => ({ x, y, id })) });
    const O = [110, 640]; let held = false;
    const steer = async (ux, uy, m = 1) => {
      const projected=await p.evaluate(([x,y])=>__osz.screenVector(x,y),[ux,uy]);ux=projected[0];uy=-projected[1];
      if (!held) { await touch('touchStart', [[...O, 1]]); await touch('touchMove', [[O[0] + ux * 14, O[1] - uy * 14, 1]]); held = true; }
      await touch('touchMove', [[O[0] + ux * (10 + 44 * m), O[1] - uy * (10 + 44 * m), 1]]);
    };
    const lift = async () => { if (held) { await touch('touchEnd', []); held = false; } };

    // ---- heard first, as a direction
    await p.waitForFunction(() => window.__herdEv.some((e) => e.op === 'heard' || e.op === 'seen'), null, { timeout: 120000, polling: 250 });
    const first = (await p.evaluate(() => window.__herdEv[0]));
    out.first = first.op; out.count = first.n; out.fromM = first.d;
    if (first.op === 'heard') {
      await toasted(/A herd is passing/);
      await p.screenshot({ path: prefix + '-heard.png' });
    }

    // ---- then seen: one row from the server, a crowd on the screen, and no zombies of its own
    await p.waitForFunction(() => (__osz.state().herds || []).length > 0, null, { timeout: 120000, polling: 250 });
    await toasted(/walking as one/);
    let s = await state();
    out.seenAtM = s.herds[0].d; out.herdRows = s.herds.length; out.herdSize = s.herds[0].count;
    assert.equal(s.hz, 0, 'a walking herd has no zombies of its own');
    assert.equal(s.herds[0].count, first.n);
    out.markerWhenFar = s.herds[0].marker;                         // beyond the lit circle it is an arrow and a distance
    await p.screenshot({ path: prefix + '-seen-far.png' });
    await p.waitForFunction(() => !document.querySelector('.toast'), null, { timeout: 15000 }).catch(() => {});
    await p.screenshot({ path: prefix + '-marker.png' });

    // ---- walk towards it with the thumb stick and stop where the whole crowd is on the screen
    // A corner can hide it on the way: keep on towards where it was last seen.
    let last = null;
    const towards = async () => {
      s = await state();
      trace.push(`${s.herds.map((h) => h.d).join('/') || '-'} hz${s.hz} z${s.zeds.length} hp${Math.round(s.hp)}${s.dead ? ' DEAD' : ''}${s.inside ? ' in' : ''}`);
      if (!s.herds.length && !last) { await lift(); return s; }
      if (s.herds.length) last = [s.at[0] + s.herds[0].dy / 111320, s.at[1] + s.herds[0].dx / (111320 * Math.cos(s.at[0] * Math.PI / 180))];
      const dy = (last[0] - s.at[0]) * 111320, dx = (last[1] - s.at[1]) * 111320 * Math.cos(s.at[0] * Math.PI / 180), n = Math.hypot(dx, dy);
      if (n < 3) await lift(); else await steer(dx / n, dy / n, 1);
      return s;
    };
    for (let i = 0; i < 700; i++) {
      s = await towards();
      if (s.hz || (s.herds.length && s.herds[0].d < 44)) break;
      await p.waitForTimeout(250);
    }
    await lift(); await p.waitForTimeout(900);
    s = await state();
    assert(s.herds.length === 1 && s.hz === 0, 'still one thing at about forty metres: ' + JSON.stringify(s.herds));
    out.closeM = s.herds[0].d; out.figuresDrawn = s.herds[0].drawn; out.fpsWalking = s.fps;
    assert(out.figuresDrawn >= 30, 'most of the crowd is drawn');
    await p.screenshot({ path: prefix + '-seen-near.png' });
    const before = s.zeds.length;

    // ---- and into it: it notices, and the one thing is its zombies
    for (let i = 0; i < 700; i++) {
      s = await towards();
      if (s.hz) break;
      await p.waitForTimeout(200);
    }
    await lift();
    await p.waitForFunction(() => __osz.state().zeds.filter((z) => z.id.startsWith('h:')).length >= 30, null, { timeout: 15000, polling: 200 });
    await toasted(/The herd has seen you/);
    await p.waitForTimeout(700);
    s = await state();
    out.wokeInto = s.hz; out.otherZombiesBefore = before; out.herdRowsAfter = s.herds.length; out.fpsAwake = s.fps;
    assert.equal(s.herds.length, 0, 'the herd row is gone once it has woken');
    assert.equal((await said('woke')).length, 1);
    await p.screenshot({ path: prefix + '-woke.png' });
    out.awakeHealth = await health(20, 150);
    assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  }
  assert.deepEqual(errors, []);
  passed = true;
  console.log(JSON.stringify({ ...out, errors }));
} finally { await browser.close(); }
