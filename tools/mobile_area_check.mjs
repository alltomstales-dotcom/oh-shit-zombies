// The remembered-area overview on a phone-sized touch browser, against an unmodified server.
//   OSZ_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tools/mobile_area_check.mjs [base] [prefix]
//   ... node tools/mobile_area_check.mjs persist [prefix]      after a restart or redeploy of that server
// The first run walks, opens a container and writes a private session and what it remembered to
// <prefix>-storage.json and <prefix>-evidence.json (mode 600). The second proves it is still there.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';
import fs from 'node:fs';

const persist = process.argv[2] === 'persist';
const prefix = process.argv[3] || '/tmp/osz-area';
const saved = persist ? JSON.parse(fs.readFileSync(prefix + '-evidence.json')) : null;
const base = persist ? saved.base : (process.argv[2] || 'http://127.0.0.1:8019');
const HOME = saved ? saved.gps : { latitude: 44.9778, longitude: -93.265, accuracy: 8 };
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
const ready = (p) => p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping, null, { timeout: 90000 });
const openArea = async (p) => {
  await p.locator('#bArea').tap();
  await p.waitForFunction(() => __osz.area.on && __osz.area.data && document.body.classList.contains('area'), null, { timeout: 8000 });
  await p.waitForTimeout(900);                              // let the camera finish pulling out
  return p.evaluate(() => ({ known: __osz.area.data.known, cells: __osz.area.data.cells.length, marks: __osz.area.data.marks, death: __osz.area.data.death, ppm: __osz.area.ppm }));
};
try {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width: 393, height: 851 }, permissions: ['geolocation'], geolocation: HOME,
    ...(persist ? { storageState: prefix + '-storage.json' } : {}) });
  const p = await c.newPage(), errors = []; let sessions = 0;
  p.on('pageerror', (e) => errors.push(e.message));
  p.on('request', (r) => { if (new URL(r.url()).pathname === '/api/session') sessions++; });
  await p.goto(base + '/?auto=desk' + (persist ? '' : '&name=AreaCheck')); await ready(p);
  const cdp = await c.newCDPSession(p);
  const touch = (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map(([x, y, id]) => ({ x, y, id })) });
  const out = {};

  if (persist) {
    assert.equal(sessions, 0, 'the saved session must still be accepted');
    const a = await openArea(p);
    assert(a.known >= saved.known, `remembered ground survived (${a.known} of ${saved.known} cells)`);
    for (const m of saved.marks) assert(a.marks.some((x) => x.id === m.id && x.left === m.left), 'remembered container survived: ' + m.id);
    assert.deepEqual(errors, []);
    await p.screenshot({ path: prefix + '-persist.png' });
    console.log(JSON.stringify({ memorySurvivedRestart: true, known: a.known, marks: a.marks.length, noNewSession: true, errors }));
  } else {
    // ---- opening the overview: the map takes the screen, the fight buttons stay
    const first = await openArea(p);
    assert(first.known >= 6 && first.cells >= 6, 'the ground around the start is remembered at once');
    assert(first.ppm < 1.2, 'the camera pulls out');
    for (const id of ['#navigation', '#quickBelt', '#stick']) assert(!(await p.locator(id).isVisible()), id + ' is hidden in the overview');
    for (const id of ['#bSwing', '#bShove', '#areaBack', '#areaIn', '#areaOut']) assert(await p.locator(id).isVisible(), id + ' stays reachable');
    assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
    out.opens = { known: first.known };

    // ---- dragging pans the camera; tapping the map does not walk; the survivor does not move
    const at0 = await p.evaluate(() => [__osz.G.you.lat, __osz.G.you.lng]);
    await touch('touchStart', [[200, 500, 1]]); for (const dx of [20, 60, 120]) await touch('touchMove', [[200 - dx, 500, 1]]); await touch('touchEnd', []);
    const pan = await p.evaluate(() => __osz.area.pan);
    assert(pan[0] > 100 && Math.abs(pan[1]) < 5, 'a drag to the left moves the view east: ' + pan);
    await touch('touchStart', [[300, 600, 1]]); await touch('touchEnd', []);
    await p.waitForTimeout(700);
    const still = await p.evaluate(() => ({ at: [__osz.G.you.lat, __osz.G.you.lng], goal: __osz.G.goal, stick: __osz.G.stick, on: __osz.area.on }));
    assert.deepEqual(still.at, at0); assert.equal(still.goal, null); assert.equal(still.stick, null); assert(still.on);
    out.panAndTapDoNotMove = true;

    // ---- zoom, then back to the street
    await p.locator('#areaOut').tap(); await p.waitForFunction(() => __osz.area.ppm < 0.36, null, { timeout: 4000 });
    await p.screenshot({ path: prefix + '-wide.png' });
    await p.locator('#areaIn').tap(); await p.locator('#areaIn').tap(); await p.waitForFunction(() => __osz.area.ppm > 0.95, null, { timeout: 4000 });
    await p.locator('#areaBack').tap();
    await p.waitForFunction(() => !__osz.area.on && !document.body.classList.contains('area'));
    assert(await p.locator('#navigation').isVisible());
    out.zoomAndReturn = true;

    // ---- walk a street with the stick: the overview shows more ground than before
    await touch('touchStart', [[110, 640, 1]]); for (const dx of [14, 40, 60]) await touch('touchMove', [[110 + dx, 640, 1]]);
    await p.waitForTimeout(9000); await touch('touchEnd', []);
    await p.waitForFunction(() => __osz.G.you.speed < 0.2, null, { timeout: 6000 });
    const walked = await openArea(p);
    assert(walked.known > first.known + 8, `walking adds remembered ground (${first.known} -> ${walked.known})`);
    await p.screenshot({ path: prefix + '-walked.png' });
    await p.locator('#areaBack').tap();
    out.walkingRemembers = { before: first.known, after: walked.known };

    // ---- open a container, and the overview marks what was left in it
    let marked = null;
    const lead = await p.evaluate(() => { const G = __osz.G, s = (G.stashes || []).filter((s) => !s[4] && !s[5]).map((s) => ({ id: s[0], lat: s[1], lng: s[2], d: Math.hypot((s[1] - G.you.lat) * 111320, (s[2] - G.you.lng) * 111320 * Math.cos(G.you.lat * Math.PI / 180)) })).sort((a, b) => a.d - b.d)[0]; return s || null; });
    if (lead && lead.d < 120) {
      await p.evaluate((s) => __osz.walkTo([s.lat, s.lng]), lead);
      await p.waitForFunction((s) => { const G = __osz.G; return Math.hypot((s.lat - G.you.lat) * 111320, (s.lng - G.you.lng) * 111320 * Math.cos(G.you.lat * Math.PI / 180)) < 4 && G.you.speed < 0.3; }, lead, { timeout: 60000 });
      await p.evaluate((s) => __osz.fire('search', { stash: s.id }), lead);
      await p.waitForFunction((id) => __osz.G.lootShelves.some((s) => s.id === id), lead.id, { timeout: 20000 });
      await p.locator('#drawerClose').tap().catch(() => {});
      await p.waitForTimeout(4500);                         // marks are noted every few seconds
      const withMark = await openArea(p);
      marked = withMark.marks.find((m) => m.id === lead.id);
      assert(marked, 'the opened container is on the remembered map');
      const xy = await p.evaluate((m) => __osz.area.P(m.lat, m.lng), marked);
      await touch('touchStart', [[xy[0], xy[1], 1]]); await touch('touchEnd', []);
      await p.waitForFunction(() => !document.getElementById('areaInfo').hidden, null, { timeout: 3000 });
      const info = await p.locator('#areaInfo').textContent();
      assert(/when you last looked/.test(info) && /It may have changed/.test(info), info);
      await p.screenshot({ path: prefix + '-mark.png' });
      await p.locator('#areaBack').tap();
      out.containerMark = { left: marked.left, info };
    } else out.containerMark = 'SKIPPED: no outdoor container within 120 m of the walk';

    const end = await openArea(p);
    await c.storageState({ path: prefix + '-storage.json' }); fs.chmodSync(prefix + '-storage.json', 0o600);
    fs.writeFileSync(prefix + '-evidence.json', JSON.stringify({ base, gps: HOME, known: end.known, marks: end.marks.map((m) => ({ id: m.id, left: m.left })) })); fs.chmodSync(prefix + '-evidence.json', 0o600);
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ...out, errors }));
  }
} finally { await browser.close(); }
