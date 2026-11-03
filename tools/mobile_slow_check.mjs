// C6 slow jobs on a phone-sized touch browser, against an unmodified server. Five stages, each a
// separate run so that real time (or a restart) can pass between them:
//   OSZ_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tools/mobile_slow_check.mjs home [base] [prefix]
//   ... mobile_slow_check.mjs read [prefix]      needs a manual in the pack (found, or seeded in a local test database)
//   ... mobile_slow_check.mjs smoke [prefix]     walks out, gathers, builds a fire, starts smoked rations
//   ... mobile_slow_check.mjs collect [prefix]   an hour later: told on return, collected once
//   ... mobile_slow_check.mjs harvest [prefix]   a day later, if the smoke stage also planted a plot
// A private session and what to expect next are kept in <prefix>-storage.json and
// <prefix>-evidence.json (mode 600; never print them).
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';
import fs from 'node:fs';

const stage = process.argv[2];
assert(['home', 'read', 'smoke', 'collect', 'harvest'].includes(stage), 'stage: home | read | smoke | collect | harvest');
const prefix = (stage === 'home' ? process.argv[4] : process.argv[3]) || '/tmp/osz-slow';
const saved = stage === 'home' ? null : JSON.parse(fs.readFileSync(prefix + '-evidence.json'));
const base = saved ? saved.base : (process.argv[3] || 'http://127.0.0.1:8019');
const phone = { ...devices['Pixel 7'], viewport: { width: 393, height: 851 } };
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
const metres = (a, b) => Math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * Math.cos(a[0] * Math.PI / 180));
const keep = (c, evidence) => c.storageState({ path: prefix + '-storage.json' }).then(() => {
  fs.chmodSync(prefix + '-storage.json', 0o600);
  fs.writeFileSync(prefix + '-evidence.json', JSON.stringify(evidence)); fs.chmodSync(prefix + '-evidence.json', 0o600);
});

async function open(gps, name) {
  const c = await browser.newContext({ ...phone, permissions: ['geolocation'], geolocation: { latitude: gps[0], longitude: gps[1], accuracy: 8 },
    ...(saved ? { storageState: prefix + '-storage.json' } : {}) });
  const p = await c.newPage(), errors = [], hello = []; let sessions = 0;
  p.on('pageerror', (e) => errors.push(e.message));
  p.on('request', (r) => { if (new URL(r.url()).pathname === '/api/session') sessions++; });
  p.on('websocket', (ws) => ws.on('framereceived', (f) => { try { const m = JSON.parse(f.payload); if (m.t === 'hello') hello.push(m); } catch { /* not ours */ } }));
  await p.goto(base + '/?auto=desk' + (name ? '&name=' + name : ''));
  await p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping && __osz.G.body, null, { timeout: 90000 });
  // every verdict the server gives, so a refusal is evidence and not a guess
  await p.evaluate(() => { window.__r = []; __osz.G.ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (m.t === 'r') window.__r.push(m); }); });
  return { c, p, errors, hello, sessions: () => sessions };
}
const you = (p) => p.evaluate(() => [__osz.G.you.lat, __osz.G.you.lng]);
const count = (p, code) => p.evaluate((code) => __osz.G.body.items.filter((i) => i.code === code).reduce((n, i) => n + i.qty, 0), code);
const homeTab = async (p) => { if (!(await p.locator('#panel').isVisible())) await p.locator('#bPack').tap(); await p.locator('[data-pack-tab="home"]').tap(); };
const closePack = async (p) => { if (await p.locator('#panel').isVisible()) await p.locator('#bPack').tap(); };
async function tapAt(p, lat, lng, offset = 15) {
  const xy=await p.evaluate(({lat,lng,offset})=>{const [x,y]=__osz.project(lat,lng);return [x,y-offset];},{lat,lng,offset});
  await p.touchscreen.tap(...xy);
}
async function walkTo(p, ll, within = 2.0, timeout = 150000) {
  const until = Date.now() + timeout;
  await p.evaluate((ll) => __osz.walkTo(ll), ll);
  for (;;) {
    const s = await p.evaluate(() => ({ at: [__osz.G.you.lat, __osz.G.you.lng], speed: __osz.G.you.speed, dead: __osz.G.dead, goal: __osz.G.goal }));
    assert(!s.dead, 'the test survivor died on the way');
    if (metres(s.at, ll) < within && s.speed < 0.3) return;
    assert(Date.now() < until, `did not arrive: ${metres(s.at, ll).toFixed(1)} m short`);
    if (!s.goal && s.speed < 0.2) await p.evaluate((ll) => __osz.walkTo(ll), ll);
    await p.waitForTimeout(400);
  }
}
async function work(p, args, done, timeout = 25000) {
  const before = await p.evaluate(() => window.__r.length);
  await p.evaluate((args) => __osz.fire('work', args), args);
  await p.waitForFunction((n) => window.__r.slice(n).some((m) => m.a === 'work'), before, { timeout: 8000 });
  const verdict = await p.evaluate((n) => window.__r.slice(n).find((m) => m.a === 'work'), before);
  if (!verdict.ok) return verdict;
  await p.waitForFunction(done, null, { timeout });
  return verdict;
}

try {
  const out = {};
  if (stage === 'home') {
    // ---- a survivor who starts indoors makes that room home; the Home tab says nothing is running
    const scout = await open([44.9778, -93.265], 'SlowScout');
    await scout.p.waitForFunction(() => __osz.G.buildings.some((b) => b.rooms.length > 1), null, { timeout: 65000 });
    const b = await scout.p.evaluate(() => __osz.G.buildings.find((b) => b.rooms.length > 1));
    await scout.c.close();
    const { c, p, errors } = await open(b.rooms[0].pos, 'SlowCheck');
    await p.waitForFunction((id) => __osz.G.inside === id, b.id, { timeout: 65000 });
    await homeTab(p);
    await p.locator('#setHome').tap();
    await p.waitForFunction(() => __osz.G.body.home, null, { timeout: 8000 });
    await p.waitForFunction(() => /Nothing yet/.test(document.getElementById('homeJobs').textContent));
    assert(/vegetable plot takes a day/.test(await p.locator('#homeJobs').textContent()));
    assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
    await p.screenshot({ path: prefix + '-home.png' });
    await keep(c, { base, gps: b.rooms[0].pos, building: b.id });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ homeSet: true, emptyListExplains: true, errors }));
  } else if (stage === 'read') {
    // ---- a manual in the pack: Read at home, see it counting, put it down, pick it up again
    const { c, p, errors, sessions } = await open(saved.gps);
    assert.equal(sessions(), 0, 'the saved session must still be accepted');
    const book = await p.evaluate(() => __osz.G.body.items.map((i) => ({ ...i, spec: __osz.G.items[i.code] })).find((i) => i.spec.teaches));
    assert(book, 'this stage needs a manual in the pack');
    await p.locator('#bPack').tap(); await p.locator('[data-pack-tab="pack"]').tap();
    const row = p.locator(`#items .inventory-row[data-item="${book.code}"]`);
    assert(/grows twice as fast/.test(await row.textContent()));
    await row.getByRole('button', { name: 'Read at home', exact: true }).tap();
    await p.waitForFunction(() => __osz.G.body.study && __osz.G.body.study.reading, null, { timeout: 8000 });
    assert.equal(await count(p, book.code), 0, 'the book leaves the pack and stays open at home');
    await closePack(p);
    await p.waitForFunction(() => /^Reading · (60|59) min left$/.test(document.getElementById('noiseChip').textContent), null, { timeout: 6000 });
    await p.screenshot({ path: prefix + '-reading.png' });
    await homeTab(p);
    const job = p.locator('#homeJobs .job-row[data-job="study"]');
    assert(/Reading the .*(60|59) min left/.test(await job.textContent()), await job.textContent());
    await job.getByRole('button', { name: 'Stop', exact: true }).tap();
    await p.waitForFunction(() => __osz.G.body.study && !__osz.G.body.study.reading, null, { timeout: 8000 });
    await p.waitForFunction(() => /paused/.test(document.querySelector('#homeJobs .job-row[data-job="study"]').textContent));
    const paused = await p.evaluate(() => __osz.G.body.study.left_s);
    await p.waitForTimeout(2500);
    assert.equal(await p.evaluate(() => __osz.G.body.study.left_s), paused, 'a closed book does not count');
    await p.screenshot({ path: prefix + '-paused.png' });
    await p.locator('#homeJobs .job-row[data-job="study"]').getByRole('button', { name: 'Keep reading', exact: true }).tap();
    await p.waitForFunction(() => __osz.G.body.study && __osz.G.body.study.reading, null, { timeout: 8000 });
    const ready = await p.evaluate(() => __osz.G.body.study.ready);
    await keep(c, { ...saved, reading: { code: book.code, skill: book.spec.teaches, name: book.spec.name, ready } });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ readStarted: true, bookLeftPack: true, chipCounts: true, stopPauses: true, resumed: true, readyAt: ready, errors }));
  } else if (stage === 'smoke') {
    const { c, p, errors, hello, sessions } = await open(saved.gps);
    assert.equal(sessions(), 0);
    if (saved.reading) {
      // ---- the hour passed with the game closed: told once, and the skill is learned
      const lines = hello[0].away.home;
      assert(lines.some((l) => l.startsWith('You finished the ' + saved.reading.name)), JSON.stringify(lines));
      assert.deepEqual(await p.evaluate(() => [__osz.G.body.study, __osz.G.body.studied]), [null, [saved.reading.skill]]);
      await p.waitForFunction(() => [...document.querySelectorAll('.toast')].some((t) => /You finished the/.test(t.textContent)), null, { timeout: 8000 });
      await p.screenshot({ path: prefix + '-finished.png' });
      out.finishedWhileClosed = true;
    }
    // ---- out of the door, gather stone, wood and food, build a fire where the survivor stands
    if (await p.evaluate(() => !!__osz.G.inside)) {
      await p.getByRole('button', { name: 'EXIT BUILDING', exact: true }).tap();
      await p.waitForFunction(() => !__osz.G.inside, null, { timeout: 120000 });
    }
    const gather = async (kind, want) => {
      for (let n = 0; n < 6 && !(await want()); n++) {
        const here = await you(p);
        const node = await p.evaluate(({ kind, here }) => __osz.G.body.survival.resources.filter((o) => o.kind === kind && o.remaining > 0)
          .map((o) => ({ ...o, d: Math.hypot((o.lat - here[0]) * 111320, (o.lng - here[1]) * 111320 * Math.cos(here[0] * Math.PI / 180)) })).sort((a, b) => a.d - b.d)[0], { kind, here });
        assert(node, 'no ' + kind + ' left in view');
        await walkTo(p, [node.lat, node.lng]);
        const left = node.remaining;
        const v = await work(p, { op: 'forage', object: node.id }, `(() => __osz.G.body.survival.resources.some((o) => o.id === ${JSON.stringify(node.id)} && o.remaining < ${left}))()`);
        assert(v.ok, kind + ': ' + v.why);
      }
    };
    await gather('rubble', async () => (await count(p, 'stone')) >= 4 && (await count(p, 'branch')) >= 3);
    await gather('forage', async () => (await count(p, 'rawfood')) >= 3 && (await count(p, 'branch')) >= 7);
    // seeds for a day-long plot too, if another patch is near enough; the plot is a bonus, never a failure
    await gather('forage', async () => (await count(p, 'seeds')) >= 3 && (await count(p, 'branch')) >= 9).catch((e) => { out.plot = 'SKIPPED: ' + e.message; });
    let fire = null;
    for (const [dx, dy] of [[3, 0], [0, 3], [-3, 0], [0, -3], [4, 4], [-4, 4], [4, -4], [-4, -4], [6, 0], [0, 6]]) {
      const at = await you(p), ll = [at[0] + dy / 111320, at[1] + dx / (111320 * Math.cos(at[0] * Math.PI / 180))];
      const v = await work(p, { op: 'craft', recipe: 'campfire', lat: ll[0], lng: ll[1] }, '(() => __osz.G.body.survival.objects.some((o) => o.kind === "campfire"))()');
      if (v.ok) { fire = await p.evaluate(() => __osz.G.body.survival.objects.find((o) => o.kind === 'campfire')); break; }
    }
    assert(fire, 'no clear place for a fire near here');
    await walkTo(p, [fire.lat, fire.lng], 2.2);
    // ---- the fire's own card: Cook, then the slow job, started with real taps
    await p.waitForTimeout(700);
    await tapAt(p, fire.lat, fire.lng);
    await p.waitForFunction((id) => __osz.G.selection && __osz.G.selection.id === id, fire.id, { timeout: 5000 });
    await p.locator('#worldActions').getByRole('button', { name: 'Cook', exact: true }).tap();
    const slow = p.locator('#drawerContent [data-slow="smoke"]');
    assert(/3 Fresh Ingredients \+ 4 Branch → 3 Smoked Rations · takes 60 min; you need not wait/.test(await slow.textContent()), await slow.textContent());
    await p.screenshot({ path: prefix + '-recipe.png' });
    await slow.getByRole('button', { name: 'Start', exact: true }).tap();
    await p.waitForFunction((id) => __osz.G.body.survival.objects.some((o) => o.id === id && o.job), fire.id, { timeout: 20000 });
    await p.waitForFunction(() => /Smoke rations · (60|59) min left/.test(document.querySelector('#drawerContent [data-slow="smoke"]').textContent), null, { timeout: 5000 });
    assert(await slow.getByRole('button', { name: 'Collect', exact: true }).isDisabled(), 'nothing to collect yet');
    assert.equal(await count(p, 'smoked'), 0); assert.equal(await count(p, 'rawfood') >= 0, true);
    const job = await p.evaluate((id) => __osz.G.body.survival.objects.find((o) => o.id === id).job, fire.id);
    const early = await work(p, { op: 'take', object: fire.id }, 'false');
    assert(!early.ok && /not ready/.test(early.why), JSON.stringify(early));
    await p.locator('#drawerClose').tap();
    await p.waitForFunction(() => /Smoke rations: (60|59) min left/.test(document.getElementById('worldDetail').textContent), null, { timeout: 5000 });
    assert(await p.locator('#worldActions').getByRole('button', { name: 'Collect', exact: true }).isDisabled());
    await p.screenshot({ path: prefix + '-smoking.png' });
    let plot = null;
    if (!out.plot && (await count(p, 'seeds')) >= 3 && (await count(p, 'branch')) >= 2) {
      await p.evaluate(() => { __osz.G.selection = null; });
      for (const [dx, dy] of [[-3, 2], [2, -3], [-2, -3], [3, 3], [-4, 0], [0, -4], [5, 2], [-5, -2]]) {
        const at = await you(p), ll = [at[0] + dy / 111320, at[1] + dx / (111320 * Math.cos(at[0] * Math.PI / 180))];
        const v = await work(p, { op: 'craft', recipe: 'plot', lat: ll[0], lng: ll[1] }, '(() => __osz.G.body.survival.objects.some((o) => o.kind === "plot"))()');
        if (v.ok) { plot = await p.evaluate(() => __osz.G.body.survival.objects.find((o) => o.kind === 'plot')); break; }
      }
      if (plot) {
        await p.waitForTimeout(700);
        await tapAt(p, plot.lat, plot.lng);
        await p.waitForFunction((id) => __osz.G.selection && __osz.G.selection.id === id, plot.id, { timeout: 5000 });
        await p.waitForFunction(() => /ready in 24 h/.test(document.getElementById('worldDetail').textContent), null, { timeout: 5000 });
        assert(await p.locator('#worldActions').getByRole('button', { name: 'Harvest', exact: true }).isDisabled(), 'a day-long crop is not ready the minute it is planted');
        await p.screenshot({ path: prefix + '-plot.png' });
        out.plot = { plantedReadyIn: '24 h' };
      } else out.plot = 'SKIPPED: no clear ground for a plot';
    } else if (!out.plot) out.plot = 'SKIPPED: fewer than 3 seeds found';
    await homeTab(p);
    const row = p.locator('#homeJobs .job-row[data-job="station"]');
    assert(/Smoke rations.*ready in (60|59|58) min/.test(await row.textContent()), await row.textContent());
    if (plot) assert(/Vegetable plot.*ready in 24 h/.test(await p.locator('#homeJobs .job-row[data-job="crop"]').textContent()));
    assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
    await p.screenshot({ path: prefix + '-running.png' });
    await keep(c, { ...saved, gps: await you(p), fire: { id: fire.id, lat: fire.lat, lng: fire.lng, ready: job.ready }, plot: plot && { id: plot.id, lat: plot.lat, lng: plot.lng, ready: plot.ready } });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ...out, gathered: true, fireBuilt: true, smokeStarted: true, earlyCollectRefused: true, cardAndHomeListAgree: true, readyAt: job.ready, errors }));
  } else if (stage === 'harvest') {
    // ---- a day on: the plot is ready, gives its larger harvest once, and starts another day
    assert(saved.plot, 'the smoke stage planted no plot for this survivor');
    const { p, errors, hello, sessions } = await open(saved.gps);
    assert.equal(sessions(), 0);
    const lines = hello[0].away.home;
    assert(lines.some((l) => /^Ready at home: .*Vegetable plot/.test(l)), JSON.stringify(lines));
    await homeTab(p);
    assert(/Vegetable plot.*READY to harvest/.test(await p.locator('#homeJobs .job-row[data-job="crop"]').textContent()));
    await closePack(p);
    await walkTo(p, [saved.plot.lat, saved.plot.lng], 2.2);
    await p.waitForTimeout(700);
    await tapAt(p, saved.plot.lat, saved.plot.lng);
    await p.waitForFunction((id) => __osz.G.selection && __osz.G.selection.id === id, saved.plot.id, { timeout: 5000 });
    assert(/ready to harvest/.test(await p.locator('#worldDetail').textContent()));
    await p.screenshot({ path: prefix + '-grown.png' });
    const before = [await count(p, 'rawfood'), await count(p, 'seeds')];
    await p.locator('#worldActions').getByRole('button', { name: 'Harvest', exact: true }).tap();
    await p.waitForFunction((id) => __osz.G.body.survival.objects.some((o) => o.id === id && o.ready > __osz.G.serverNow + 80000), saved.plot.id, { timeout: 20000 });
    assert.deepEqual([await count(p, 'rawfood'), await count(p, 'seeds')], [before[0] + 10, before[1] + 3]);
    const again = await work(p, { op: 'harvest', object: saved.plot.id }, 'false');
    assert(!again.ok && /still growing/.test(again.why), JSON.stringify(again));
    await p.waitForFunction(() => /ready in 24 h/.test(document.getElementById('worldDetail').textContent), null, { timeout: 5000 });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ toldOnReturn: true, harvestedOnce: { rawfood: 10, seeds: 3 }, secondHarvestRefused: true, replantedForAnotherDay: true, errors }));
  } else {
    // ---- an hour on: said on return, collected once, never twice
    const { p, errors, hello, sessions } = await open(saved.gps);
    assert.equal(sessions(), 0);
    const lines = hello[0].away.home;
    assert(lines.some((l) => /^Ready at home: Smoke rations/.test(l)), JSON.stringify(lines));
    await p.waitForFunction(() => [...document.querySelectorAll('.toast')].some((t) => /Ready at home: Smoke rations/.test(t.textContent)), null, { timeout: 8000 });
    await p.screenshot({ path: prefix + '-returned.png' });
    await homeTab(p);
    assert(/Smoke rations.*READY to collect/.test(await p.locator('#homeJobs .job-row[data-job="station"]').textContent()));
    await closePack(p);
    await walkTo(p, [saved.fire.lat, saved.fire.lng], 2.2);
    await p.waitForTimeout(700);
    await tapAt(p, saved.fire.lat, saved.fire.lng);
    await p.waitForFunction((id) => __osz.G.selection && __osz.G.selection.id === id, saved.fire.id, { timeout: 5000 });
    assert(/Smoke rations: ready/.test(await p.locator('#worldDetail').textContent()));
    const before = await count(p, 'smoked');
    await p.locator('#worldActions').getByRole('button', { name: 'Collect', exact: true }).tap();
    await p.waitForFunction((id) => __osz.G.body.survival.objects.some((o) => o.id === id && !o.job), saved.fire.id, { timeout: 20000 });
    assert.equal(await count(p, 'smoked'), before + 3);
    const again = await work(p, { op: 'take', object: saved.fire.id }, 'false');
    assert(!again.ok && /nothing is waiting/.test(again.why), JSON.stringify(again));
    assert.equal(await count(p, 'smoked'), before + 3);
    assert.equal(await p.locator('#worldActions').getByRole('button', { name: 'Collect', exact: true }).count(), 0);
    await p.locator('#bPack').tap(); await p.locator('[data-pack-tab="pack"]').tap();
    assert(/Smoked Rations × 3/.test(await p.locator('#items .inventory-row[data-item="smoked"]').textContent()));
    await p.screenshot({ path: prefix + '-collected.png' });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ toldOnReturn: true, collectedOnce: 3, secondCollectRefused: true, noNewSession: true, errors }));
  }
} finally { await browser.close(); }
