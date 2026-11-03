// M4: the player's own pins on the remembered-area map, on a phone-sized touch browser.
//   OSZ_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tools/mobile_pin_check.mjs [base] [shots-prefix]
// A tap on empty ground offers four kinds of pin; a tap on a pin offers to remove it. Pins are kept
// with the player's memory of the map, so they are still there after the page is loaded again.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8019', prefix = process.argv[3] || '/tmp/osz-pin';
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
try {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width: 393, height: 851 }, permissions: ['geolocation'], geolocation: { latitude: 44.9778, longitude: -93.265, accuracy: 8 } });
  const p = await c.newPage(), errors = []; p.on('pageerror', (e) => errors.push(e.message));
  const ready = () => p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping, null, { timeout: 90000 });
  const openArea = async () => {
    await p.locator('#bArea').tap();
    await p.waitForFunction(() => __osz.area.on && __osz.area.data, null, { timeout: 8000 });
    await p.waitForTimeout(2600);                           // let the camera finish pulling out: a pin is compared to the pixel
  };
  await p.goto(base + '/?auto=desk&name=PinCheck'); await ready();
  const cdp = await c.newCDPSession(p);
  const tap = async (x, y) => { await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y, id: 1 }] }); await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); await p.waitForTimeout(250); };
  const pins = () => p.evaluate(() => (__osz.area.data.pins || []).map((q) => ({ id: q.id, kind: q.kind, at: __osz.area.P(q.lat, q.lng).map(Math.round) })));
  const put = async (x, y, label, n) => {
    await tap(x, y);
    await p.waitForFunction(() => !document.getElementById('areaInfo').hidden && __osz.area.spot, null, { timeout: 3000 });
    const offer = await p.locator('#areaInfo').textContent();
    assert(/Pin this spot/.test(offer), 'empty ground offers a pin: ' + offer);
    const sizes = await p.locator('#areaInfo button').evaluateAll((bs) => bs.map((b) => { const r = b.getBoundingClientRect(); return [b.textContent, Math.round(r.width), Math.round(r.height), r.right <= innerWidth]; }));
    assert.equal(sizes.length, 4); for (const s of sizes) assert(s[1] >= 44 && s[2] >= 44 && s[3], 'a thumb-sized button on screen: ' + s);
    await p.locator('#areaInfo button', { hasText: label }).tap();
    await p.waitForFunction((n) => (__osz.area.data.pins || []).length === n, n, { timeout: 4000 });
    assert(await p.locator('#areaInfo').isHidden());
    return sizes;
  };
  const out = {};
  await openArea();
  const at0 = await p.evaluate(() => [__osz.G.you.lat, __osz.G.you.lng]);
  assert.deepEqual(await pins(), []);
  out.buttons = await put(300, 620, 'Supplies', 1);
  await p.screenshot({ path: `${prefix}-offer.png` });
  await put(110, 300, 'Danger', 2);
  const two = await pins();
  assert.deepEqual(two.map((q) => q.kind), ['supplies', 'danger']);
  assert(Math.hypot(two[0].at[0] - 300, two[0].at[1] - 620) < 3, 'the pin stands where the finger was: ' + two[0].at);

  // ---- a tap on a pin names it and offers to take it off
  await tap(two[1].at[0], two[1].at[1] - 10);
  await p.waitForFunction(() => /Your pin: Danger/.test(document.getElementById('areaInfo').textContent), null, { timeout: 3000 });
  out.info = await p.locator('#areaInfo span').textContent();
  assert.equal(await p.locator('#areaInfo button').count(), 1);
  await p.waitForTimeout(300); await p.screenshot({ path: `${prefix}-picked.png` });
  const still = await p.evaluate(() => ({ at: [__osz.G.you.lat, __osz.G.you.lng], goal: __osz.G.goal }));
  assert.deepEqual(still.at, at0); assert.equal(still.goal, null);          // pinning is not walking

  // ---- a used-up resource spot is drawn and named. Its place is set by hand here: the rule that
  // produces it (a felled tree in the home record) is covered by a server test, not by this check.
  const sp = await p.evaluate(() => { const y = __osz.G.you; __osz.area.data.spent = [{ id: 'x', kind: 'tree', lat: y.lat + 0.0009, lng: y.lng + 0.0012 }]; return __osz.area.P(y.lat + 0.0009, y.lng + 0.0012); });
  await tap(sp[0], sp[1]);
  await p.waitForFunction(() => /Felled trees/.test(document.getElementById('areaInfo').textContent), null, { timeout: 3000 });
  out.spent = await p.locator('#areaInfo span').textContent();
  assert.equal(await p.locator('#areaInfo button').count(), 0);
  await p.waitForTimeout(300); await p.screenshot({ path: `${prefix}-spent.png` });

  // ---- they are kept with the map: load the page again
  await p.locator('#areaBack').tap(); await p.waitForTimeout(7000);          // survivors and maps are saved every few seconds
  await p.reload(); await ready(); await openArea();
  const kept = await pins();
  assert.deepEqual(kept.map((q) => [q.id, q.kind]), two.map((q) => [q.id, q.kind]), 'both pins are there after a reload');
  await tap(kept[0].at[0], kept[0].at[1] - 10);
  await p.waitForFunction(() => /Your pin: Supplies/.test(document.getElementById('areaInfo').textContent), null, { timeout: 3000 });
  await p.locator('#areaInfo button', { hasText: 'Remove pin' }).tap();
  await p.waitForFunction(() => __osz.area.data.pins.length === 1, null, { timeout: 4000 });
  assert.deepEqual((await pins()).map((q) => q.kind), ['danger']);
  assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ ...out, keptAfterReload: 2, leftAfterRemove: 1, fps: await p.evaluate(() => Math.round(__osz.G.fps)), errors }));
} finally { await browser.close(); }
