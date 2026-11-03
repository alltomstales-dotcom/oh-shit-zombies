// M5: a street that got placeholder shelters gets its real map while a survivor stays on it.
//   node tools/mobile_map_refresh_check.mjs [base] [shots-prefix] [wait-seconds]
// Needs a local server whose database was seeded by tools/seed_placeholders.py a moment before it
// started, and a map server that answers. The survivor stands still the whole time: nothing but
// the loader's own clock brings the real outlines in.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8022', prefix = process.argv[3] || '/tmp/osz-refresh', wait = Number(process.argv[4] || 240);
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
try {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width: 393, height: 851 }, permissions: ['geolocation'], geolocation: { latitude: 44.9778, longitude: -93.265, accuracy: 8 } });
  await c.addInitScript(() => {             // keep every toast: they are gone from the page in under three seconds
    window.__toasts = [];
    new MutationObserver((ms) => { for (const m of ms) for (const n of m.addedNodes) if (n.classList && n.classList.contains('toast')) window.__toasts.push(n.textContent); })
      .observe(document, { childList: true, subtree: true });      // the root element does not exist yet when this runs
  });
  const p = await c.newPage(), errors = []; p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(base + '/?auto=desk&name=MapRefresh');
  await p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping && __osz.G.buildings.length, null, { timeout: 90000 });
  const seen = () => p.evaluate(() => ({ shelters: __osz.G.buildings.filter((b) => b.source === 'generated').length, real: __osz.G.buildings.filter((b) => b.source !== 'generated').length,
    at: [__osz.G.you.lat, __osz.G.you.lng], inside: __osz.G.inside, orphans: __osz.G.stashes.filter((s) => s[5] && !__osz.G.buildings.some((b) => b.id === s[5])).length }));
  const before = await seen();
  assert(before.shelters > 0 && before.real === 0, 'the street starts with placeholder shelters only: ' + JSON.stringify(before));
  await p.screenshot({ path: `${prefix}-before.png` });
  const t0 = Date.now();
  await p.waitForFunction(() => __osz.G.buildings.some((b) => b.source !== 'generated'), null, { timeout: wait * 1000 });
  const seconds = Math.round((Date.now() - t0) / 1000);
  await p.waitForFunction(() => window.__toasts.some((t) => /real map/.test(t)), null, { timeout: 5000 })
    .catch(() => assert.fail('the survivor is told the map changed'));       // their own region is asked for first
  await p.waitForTimeout(600); await p.screenshot({ path: `${prefix}-after.png` });
  const after = await seen(), toasts = await p.evaluate(() => window.__toasts);
  assert(after.real > 5, 'real outlines arrived');
  assert.equal(after.orphans, 0, 'no supplies are left pointing into shelters that are gone');
  const moved = Math.hypot((after.at[0] - before.at[0]) * 111320, (after.at[1] - before.at[1]) * 78700);
  assert(moved < 1, 'the survivor was not moved');
  // the neighbouring regions follow, one every few seconds
  await p.waitForFunction(() => !__osz.G.buildings.some((b) => b.source === 'generated'), null, { timeout: 60000 });
  await p.waitForTimeout(1000);
  const later = await seen();
  assert.equal(later.orphans, 0); assert.equal(later.shelters, 0);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ before, after, later, seconds, told: toasts.filter((t) => /real map/.test(t)).length, fps: await p.evaluate(() => Math.round(__osz.G.fps)), errors }));
} finally { await browser.close(); }
