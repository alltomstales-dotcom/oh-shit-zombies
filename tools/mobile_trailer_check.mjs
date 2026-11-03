// The trailer on the title screen, on a phone-sized touch browser.
//   OSZ_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tools/mobile_trailer_check.mjs [base] [shots-prefix]
// The card must cost nothing until it is tapped (no request leaves for YouTube), then play in
// place with the Play button still on screen, stay reachable on a small phone, and be gone once
// the game starts so its sound does not carry on under the street.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8019', prefix = process.argv[3] || '/tmp/osz-trailer';
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
try {
  const out = {};
  const open = async (width, height) => {
    const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width, height }, permissions: ['geolocation'], geolocation: { latitude: 44.9778, longitude: -93.265, accuracy: 8 } });
    const p = await c.newPage(), errors = [], away = new Set(), home = new URL(base).hostname;
    p.on('pageerror', (e) => errors.push(e.message));
    p.on('request', (r) => { const h = new URL(r.url()).hostname; if (h !== home) away.add(h); });
    await p.goto(base + '/', { waitUntil: 'networkidle' });
    return { c, p, errors, away };
  };
  const rect = (p, s) => p.locator(s).evaluate((e) => { const r = e.getBoundingClientRect(); return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) }; });
  const onScreen = (r, w, h) => r.x >= 0 && r.y >= 0 && r.x + r.w <= w && r.y + r.h <= h;

  // A usual phone.
  let { c, p, errors, away } = await open(393, 851);
  assert.deepEqual([...away], [], 'the title asks nothing of another site before the tap');
  const card = await rect(p, '#trailerPlay');
  assert(card.h >= 44 && onScreen(card, 393, 851), 'a thumb-sized card on screen: ' + JSON.stringify(card));
  assert(onScreen(await rect(p, '#title h1'), 393, 851) && onScreen(await rect(p, '#goWalk'), 393, 851));
  await p.screenshot({ path: `${prefix}-card.png` });
  await p.locator('#trailerPlay').tap();
  await p.waitForSelector('#trailer iframe');
  assert.equal(p.url(), base + '/', 'the tap stays on the title');
  assert.equal(c.pages().length, 1, 'and opens no second tab');
  let player; for (let i = 0; i < 40 && !player; i++) { player = p.frames().find((f) => f.url().includes('youtube-nocookie.com/embed/')); if (!player) await p.waitForTimeout(250); }
  assert(player, 'the player is YouTube\'s no-cookie embed');
  await player.waitForSelector('video', { timeout: 20000 });
  await p.waitForTimeout(5000);
  out.title = await player.title();
  out.playerError = await player.evaluate(() => document.querySelector('.ytp-error')?.innerText || '');
  out.seconds = await player.evaluate(() => document.querySelector('video').currentTime);
  assert(/Zombies/.test(out.title), 'the right video: ' + out.title);
  assert.equal(out.playerError, '');
  assert(out.seconds > 1, 'it is playing: ' + out.seconds);
  out.frame = await rect(p, '#trailer iframe');
  assert(onScreen(out.frame, 393, 851) && Math.abs(out.frame.w / out.frame.h - 16 / 9) < .05, 'a 16:9 player on screen');
  assert(onScreen(await rect(p, '#title h1'), 393, 851) && onScreen(await rect(p, '#goWalk'), 393, 851), 'the name and Play are still on screen while it plays');
  await p.screenshot({ path: `${prefix}-playing.png` });
  await p.locator('#name').fill('TrailerCheck');
  await p.locator('#goWalk').tap();
  assert.equal(await p.locator('#trailer iframe').count(), 0, 'Play takes the player out at once');
  await p.waitForFunction(() => document.getElementById('title').hidden && !document.getElementById('hud').hidden, null, { timeout: 30000 });   // the server has answered and the street is up
  assert(!p.frames().some((f) => f.url().includes('youtube')), 'nothing of the video is left under the game');
  assert.deepEqual(errors, []);
  await c.close();

  // A small phone: the title is taller than the screen once the video is open, so it has to scroll.
  ({ c, p, errors, away } = await open(360, 640));
  assert.deepEqual([...away], []);
  assert(onScreen(await rect(p, '#title h1'), 360, 640) && onScreen(await rect(p, '#goWalk'), 360, 640), 'small phone: the name and Play are on screen');
  await p.locator('#trailerPlay').scrollIntoViewIfNeeded();
  await p.locator('#trailerPlay').tap();
  await p.waitForSelector('#trailer iframe');
  out.small = await p.locator('.titleBox').evaluate((e) => ({ tall: e.scrollHeight, shown: e.clientHeight }));
  await p.locator('.titleBox').evaluate((e) => { e.scrollTop = e.scrollHeight; });
  assert(onScreen(await rect(p, '.titleBox p.fine:last-child'), 360, 640), 'small phone: the last line can be reached');
  await p.locator('.titleBox').evaluate((e) => { e.scrollTop = 0; });
  assert(onScreen(await rect(p, '#title h1'), 360, 640), 'small phone: and so can the top');
  await p.screenshot({ path: `${prefix}-small.png` });
  assert.deepEqual(errors, []);
  await c.close();
  console.log(JSON.stringify(out));
  console.log('The title trailer costs nothing until tapped, plays in place, scrolls on a small phone and stops when the game starts.');
} finally { await browser.close(); }
