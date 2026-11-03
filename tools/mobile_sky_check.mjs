// C7 on a phone-sized touch browser: the day chip, rain, and one whole helicopter pass.
// Needs the local fast-sky server (tools/serve_fast_sky.py), because the real schedule has a pass
// about twice a day:   node tools/mobile_sky_check.mjs [base] [shots-prefix]
// On an ordinary server only the day chip is checked; pass `day` as the third argument.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8020', prefix = process.argv[3] || '/tmp/osz-sky', dayOnly = process.argv[4] === 'day';
const phone = { ...devices['Pixel 7'], viewport: { width: 393, height: 851 } };
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
const ready = (p) => p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping && __osz.G.body, null, { timeout: 90000 });
try {
  // find a building to start in: the helicopter treats indoors and outdoors differently
  let c = await browser.newContext({ ...phone, permissions: ['geolocation'], geolocation: { latitude: 44.9778, longitude: -93.265, accuracy: 8 } }), p = await c.newPage();
  await p.goto(base + '/?auto=desk&name=SkyScout'); await ready(p);
  await p.waitForFunction(() => __osz.G.buildings.some((b) => b.rooms.length > 1), null, { timeout: 65000 });
  const b = await p.evaluate(() => __osz.G.buildings.find((b) => b.rooms.length > 1));
  await c.close();
  c = await browser.newContext({ ...phone, permissions: ['geolocation'], geolocation: { latitude: b.rooms[0].pos[0], longitude: b.rooms[0].pos[1], accuracy: 8 } }); p = await c.newPage();
  const errors = []; p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(base + '/?auto=desk&name=SkyCheck'); await ready(p);
  await p.waitForFunction((id) => __osz.G.inside === id, b.id, { timeout: 65000 });
  const out = {};

  // ---- the calendar: a new survivor is on day 1, and the chip fits the top row
  await p.waitForFunction(() => /^Day 1/.test(document.getElementById('dayChip').textContent));
  assert.equal(await p.evaluate(() => __osz.G.body.day), 1);
  assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  out.day = await p.locator('#dayChip').textContent();
  if (dayOnly) {
    // whatever the real sky is doing over this area right now, the chip says the same
    const sky = await p.evaluate(() => __osz.G.body.weather);
    assert.equal(/Rain/.test(out.day), sky.rain);
    await p.getByRole('button', { name: 'EXIT BUILDING', exact: true }).tap();
    await p.waitForFunction(() => !__osz.G.inside, null, { timeout: 120000 });
    await p.waitForTimeout(600);
    await p.screenshot({ path: prefix + '-day.png' });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ...out, realRainNow: sky.rain, helicopterNow: sky.heli, errors }));
  }
  else {
    // ---- rain: said on the chip, drawn only where there is no roof
    assert.equal(out.day, 'Day 1 · Rain');
    assert.equal(await p.evaluate(() => __osz.G.body.weather.rain), true);

    // ---- the helicopter, from indoors: heard first, then overhead, and told to stay put
    await p.waitForFunction(() => __osz.G.body.weather.heli && __osz.G.body.weather.heli.phase === 'coming', null, { timeout: 300000, polling: 250 });
    await p.waitForFunction(() => !document.getElementById('heliChip').hidden && /HELICOPTER coming · get indoors/.test(document.getElementById('heliChip').textContent));
    await p.waitForFunction(() => [...document.querySelectorAll('.toast')].some((t) => /A helicopter, far off/.test(t.textContent)), null, { timeout: 6000 });
    await p.screenshot({ path: prefix + '-coming.png' });
    out.heardFirst = true;
    await p.waitForFunction(() => __osz.G.body.weather.heli && __osz.G.body.weather.heli.phase === 'overhead', null, { timeout: 60000, polling: 250 });
    await p.waitForFunction(() => /Helicopter overhead · \d+ min · stay inside/.test(document.getElementById('heliChip').textContent) && document.getElementById('heliChip').className === 'soft');
    assert.equal(await p.evaluate(() => __osz.G.body.weather.heli.sheltered), true);
    await p.screenshot({ path: prefix + '-inside.png' });
    out.indoorsToldToStay = true;

    // ---- step outside while it is overhead: the warning turns red, and it rains on the street
    await p.getByRole('button', { name: 'EXIT BUILDING', exact: true }).tap();
    await p.waitForFunction(() => !__osz.G.inside, null, { timeout: 120000 });
    const still = await p.evaluate(() => __osz.G.body.weather.heli && __osz.G.body.weather.heli.phase);
    if (still === 'overhead') {
      await p.waitForFunction(() => /HELICOPTER overhead · \d+ min · get indoors/.test(document.getElementById('heliChip').textContent) && document.getElementById('heliChip').className === 'roar', null, { timeout: 5000 });
      await p.waitForFunction(() => __osz.G.body.weather.heli && __osz.G.body.weather.heli.sheltered === false, null, { timeout: 5000 });
      out.outdoorsWarned = true;
    } else out.outdoorsWarned = 'SKIPPED: the pass ended before the door was reached';
    await p.screenshot({ path: prefix + '-outside.png' });
    assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));

    // ---- and it leaves: the chip goes and the game says so
    await p.waitForFunction(() => !__osz.G.body.weather.heli, null, { timeout: 120000, polling: 250 });
    await p.waitForFunction(() => document.getElementById('heliChip').hidden);
    await p.waitForFunction(() => [...document.querySelectorAll('.toast')].some((t) => /moved on/.test(t.textContent)), null, { timeout: 6000 });
    out.gone = true;
    await p.setViewportSize({ width: 851, height: 393 }); await p.waitForTimeout(500);
    assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
    await p.screenshot({ path: prefix + '-landscape.png' });
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({ ...out, errors }));
  }
} finally { await browser.close(); }
