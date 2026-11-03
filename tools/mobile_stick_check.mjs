// Thumb steering on a phone-sized touch browser, against an unmodified server.
//   OSZ_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tools/mobile_stick_check.mjs [base] [shots-prefix]
// Checks: the stick and tap-to-walk share one mode; a second finger can swing while steering;
// a gentle push creeps; release stops; QUIET, SPRINT and Knock work; nothing overlaps or overflows.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8019', shots = process.argv[3] || '/tmp/osz-stick';
const HOME = { latitude: 44.9778, longitude: -93.265, accuracy: 8 };
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
const out = {};

async function open(viewport, geolocation, name) {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport, permissions: ['geolocation'], geolocation });
  const p = await c.newPage(), errors = [];
  p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(`${base}/?auto=desk&name=${name}`);
  await p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping, null, { timeout: 90000 });
  const cdp = await c.newCDPSession(p);
  const touch = (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map(([x, y, id]) => ({ x, y, id })) });
  return { c, p, errors, touch };
}
const you = (p) => p.evaluate(() => ({ ...__osz.G.you, stick: __osz.G.stick, goal: __osz.G.goal, desk: __osz.G.desk }));
const eastM = (a, b) => (b.lng - a.lng) * 111320 * Math.cos(a.lat * Math.PI / 180);
const box = (p, id) => p.locator(id).evaluate((e) => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height }; });
const apart = (a, b) => a.r <= b.l || b.r <= a.l || a.b <= b.t || b.b <= a.t;

try {
  // ---------------------------------------------------------------- portrait: layout and steering
  const { c, p, errors, touch } = await open({ width: 393, height: 851 }, HOME, 'StickCheck');
  const [shove, swing, sprint, pack, belt, quiet, stop] = await Promise.all(['#bShove', '#bSwing', '#bSprint', '#bPack', '#quickBelt', '#bQuiet', '#bStop'].map((id) => box(p, id)));
  assert(shove.l > 393 / 2 - 20 && shove.r <= swing.l, 'SHOVE sits beside SWING under the right thumb');
  assert(sprint.r <= shove.l && sprint.h >= 30 && quiet.h >= 44, 'SPRINT and QUIET are full-size touch targets');
  for (const [name, b] of Object.entries({ shove, swing, sprint, pack })) assert(apart(b, belt), name + ' must not cover the quick belt');
  assert(apart(shove, swing) && apart(sprint, shove) && apart(pack, shove) && apart(quiet, stop));
  assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'no horizontal overflow');
  assert(await p.locator('#stick').evaluate((e) => e.classList.contains('rest')));
  assert(!(await p.locator('#bScream').isVisible()), 'SCREAM is not on the play screen');
  out.layout = true;

  // a tap inside the stick zone is still a tap: it sets a walking goal
  await touch('touchStart', [[120, 620, 1]]); await touch('touchEnd', []);
  await p.waitForFunction(() => __osz.G.goal, null, { timeout: 3000 });
  await p.locator('#bStop').tap(); await p.waitForFunction(() => !__osz.G.goal);
  out.tapStillWalks = true;

  // full push east: the survivor moves east at the normal pace, and is not creeping
  await p.waitForTimeout(600);
  const a0 = await you(p);
  await touch('touchStart', [[120, 620, 1]]);
  for (const dx of [8, 20, 40, 60]) await touch('touchMove', [[120 + dx, 620, 1]]);
  await p.waitForFunction(() => __osz.G.stick && __osz.G.stick.m === 1 && !document.getElementById('stick').classList.contains('rest'));
  await p.waitForTimeout(1500);
  const a1 = await you(p);
  assert(eastM(a0, a1) > 3, `full push should cover ground (moved ${eastM(a0, a1).toFixed(1)} m)`);
  assert(!a1.quiet && a1.heard_m >= 11 && !a1.goal, 'full push is the normal, audible pace');
  out.fullPush = { movedM: +eastM(a0, a1).toFixed(1), heardM: a1.heard_m };

  // a second finger swings while the first keeps steering
  const swingAt = await p.evaluate(() => __osz.G.swingAt);
  const sx = swing.l + swing.w / 2, sy = swing.t + swing.h / 2;
  // in Chromium's protocol a touchEnd names the finger being lifted; the other stays down
  await touch('touchStart', [[180, 620, 1], [sx, sy, 2]]); await touch('touchEnd', [[sx, sy, 2]]);
  await p.waitForFunction((t) => __osz.G.swingAt > t, swingAt, { timeout: 3000 });
  assert((await you(p)).stick?.m === 1, 'steering survives the second finger');
  // and again, to prove the second finger really lifted
  await p.waitForFunction(() => __osz.G.you.busy === 0 && __osz.G.busyUntil < performance.now(), null, { timeout: 4000 });
  const again = await p.evaluate(() => __osz.G.swingAt);
  await touch('touchStart', [[180, 620, 1], [sx, sy, 2]]); await touch('touchEnd', [[sx, sy, 2]]);
  await p.waitForFunction((t) => __osz.G.swingAt > t, again, { timeout: 3000 });
  out.swingWhileSteering = true;

  // ease off: a gentle push creeps: slow, quiet, and the ring turns green
  await touch('touchMove', [[146, 620, 1]]);
  await p.waitForFunction(() => __osz.G.you.quiet && __osz.G.you.heard_m <= 3 && document.getElementById('stick').classList.contains('creep'), null, { timeout: 5000 });
  const b0 = await you(p); await p.waitForTimeout(2000); const b1 = await you(p);
  const creepSpeed = eastM(b0, b1) / 2;
  assert(creepSpeed > 0.2 && creepSpeed <= 1.35, `creeping pace ${creepSpeed.toFixed(2)} m/s`);
  assert((await p.locator('#noiseChip').textContent()).includes('Creeping'));
  await p.screenshot({ path: shots + '-portrait.png' });
  out.creep = { speed: +creepSpeed.toFixed(2), heardM: b1.heard_m };

  // let go: steering stops, the ring goes back to rest, creeping ends
  await touch('touchEnd', []);
  await p.waitForFunction(() => !__osz.G.stick && document.getElementById('stick').classList.contains('rest') && !__osz.G.you.quiet && __osz.G.you.speed < 0.2, null, { timeout: 6000 });
  const c0 = await you(p); await p.waitForTimeout(900); const c1 = await you(p);
  assert(Math.abs(eastM(c0, c1)) < 0.2, 'release stops the survivor');
  out.releaseStops = true;

  // QUIET holds a creep for tap walking; SPRINT cancels it; both show their state
  await p.locator('#bQuiet').tap();
  await p.waitForFunction(() => __osz.G.you.quiet && document.getElementById('bQuiet').getAttribute('aria-pressed') === 'true');
  assert((await you(p)).walk_speed <= 1.21);
  await p.locator('#bSprint').tap();
  await p.waitForFunction(() => __osz.G.you.sprinting && !__osz.G.you.quiet && document.getElementById('bSprint').getAttribute('aria-pressed') === 'true');
  await p.locator('#bSprint').tap(); await p.waitForFunction(() => !__osz.G.you.sprinting);
  out.quietAndSprint = true;

  // SCREAM is a deliberate second step, in the pack sheet
  await p.locator('#bMenu').tap(); assert(await p.locator('#bScream').isVisible()); await p.locator('#panelClose').tap();
  out.screamInSheet = true;

  // ---------------------------------------------------------------- knock on a closed front door
  await p.waitForFunction(() => __osz.G.buildings.some((b) => b.openings.some((o) => o.label === 'Entrance' && !o.open && !o.broken)), null, { timeout: 65000 });
  const door = await p.evaluate(() => {
    const G = __osz.G, mid = (o) => [(o.a[0] + o.b[0]) / 2, (o.a[1] + o.b[1]) / 2];
    const all = G.buildings.flatMap((b) => b.openings.filter((o) => o.label === 'Entrance' && !o.open && !o.broken).map((o) => ({ o, b })));
    const near = all.map((x) => ({ ...x, d: Math.hypot((mid(x.o)[0] - G.you.lat) * 111320, (mid(x.o)[1] - G.you.lng) * 111320 * Math.cos(G.you.lat * Math.PI / 180)) })).sort((a, b) => a.d - b.d)[0];
    const c = near.b.outline.reduce((s, q) => [s[0] + q[0] / near.b.outline.length, s[1] + q[1] / near.b.outline.length], [0, 0]), m = mid(near.o);
    const k = Math.cos(m[0] * Math.PI / 180), dx = (m[1] - c[1]) * 111320 * k, dy = (m[0] - c[0]) * 111320, n = Math.hypot(dx, dy) || 1;
    return { id: near.o.id, lat: m[0], lng: m[1], out: [m[0] + dy / n * 1.6 / 111320, m[1] + dx / n * 1.6 / (111320 * k)] };
  });
  await c.close();
  const k = await open({ width: 393, height: 851 }, { latitude: door.out[0], longitude: door.out[1], accuracy: 8 }, 'KnockCheck');
  await k.p.waitForFunction((id) => __osz.G.buildings.some((b) => b.openings.some((o) => o.id === id)), door.id, { timeout: 65000 });
  const xy = await k.p.evaluate(({ lat, lng }) => { const G = __osz.G, o = G.screenOrigin, ll = G.screenLL; return [o[0] + (lng - ll[1]) * 111320 * Math.cos(ll[0] * Math.PI / 180) * G.cam.ppm, o[1] - (lat - ll[0]) * 111320 * G.cam.ppm]; }, door);
  await k.touch('touchStart', [[xy[0], xy[1], 1]]); await k.touch('touchEnd', []);
  await k.p.waitForFunction((id) => __osz.G.selection?.kind === 'opening' && __osz.G.selection.id === id, door.id, { timeout: 5000 });
  const actions = await k.p.locator('#worldActions button').allTextContents();
  assert(actions.length <= 3 && actions.includes('Knock'), 'door card: ' + actions.join(', '));
  await k.p.getByRole('button', { name: 'Knock', exact: true }).tap();
  await k.p.waitForFunction(() => [...document.querySelectorAll('.toast')].some((t) => t.textContent.includes('You knock')), null, { timeout: 4000 });
  await k.p.waitForFunction(() => [...document.querySelectorAll('.toast')].some((t) => /No answer|moving toward the door/.test(t.textContent)), null, { timeout: 8000 });
  assert(await k.p.evaluate((id) => !__osz.G.buildings.flatMap((b) => b.openings).find((o) => o.id === id).open, door.id), 'a knock does not open the door');
  await k.p.screenshot({ path: shots + '-knock.png' });
  out.knock = { actions, verdict: await k.p.evaluate(() => [...document.querySelectorAll('.toast')].map((t) => t.textContent).find((t) => /No answer|moving toward/.test(t))) };
  assert.deepEqual([...errors, ...k.errors], []);
  await k.c.close();

  // ---------------------------------------------------------------- landscape and a short phone
  for (const [name, viewport] of [['landscape', { width: 851, height: 393 }], ['short', { width: 360, height: 560 }]]) {
    const v = await open(viewport, HOME, 'Stick' + name);
    const ids = ['#bShove', '#bSwing', '#bSprint', '#bPack', '#quickBelt', '#bQuiet'];
    const b = Object.fromEntries(await Promise.all(ids.map(async (id) => [id, await box(v.p, id)])));
    for (const id of ['#bShove', '#bSwing', '#bSprint', '#bPack']) {
      assert(apart(b[id], b['#quickBelt']), `${name}: ${id} covers the quick belt`);
      assert(b[id].l >= 0 && b[id].r <= viewport.width && b[id].b <= viewport.height, `${name}: ${id} is on screen`);
    }
    assert(apart(b['#bShove'], b['#bSwing']) && apart(b['#bSprint'], b['#bShove']) && apart(b['#bPack'], b['#bShove']), name + ': buttons overlap');
    assert(!(await v.p.evaluate(() => document.documentElement.scrollWidth > innerWidth)), name + ': horizontal overflow');
    const s0 = await you(v.p);
    const y0 = Math.round(viewport.height * 0.7);
    await v.touch('touchStart', [[90, y0, 1]]); for (const dx of [15, 35, 60]) await v.touch('touchMove', [[90 + dx, y0, 1]]);
    await v.p.waitForTimeout(1200); await v.p.screenshot({ path: `${shots}-${name}.png` });
    const s1 = await you(v.p); await v.touch('touchEnd', []);
    assert(eastM(s0, s1) > 2, `${name}: stick moves the survivor`);
    assert.deepEqual(v.errors, []);
    out[name] = true; await v.c.close();
  }
  console.log(JSON.stringify(out));
} finally { await browser.close(); }
