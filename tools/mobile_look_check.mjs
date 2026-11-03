// C9 on a phone-sized touch browser: the survivor sprite shows what it holds, wears and has suffered.
//   node tools/mobile_look_check.mjs [base] [shots-prefix]
// First the real state of a new survivor (the starting weapon is in the hand). Then the drawing
// alone: the connection is muted in the page and wounds, health, a helmet, a bag and each weapon
// are set by hand, so every overlay can be photographed. That second part proves the drawing, not
// the game rules that produce those states.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8019', prefix = process.argv[3] || '/tmp/osz-look';
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
try {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width: 393, height: 851 }, permissions: ['geolocation'], geolocation: { latitude: 44.9778, longitude: -93.265, accuracy: 8 } });
  const p = await c.newPage(), errors = []; p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(base + '/?auto=desk&name=LookCheck');
  await p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping && __osz.G.body, null, { timeout: 90000 });
  await p.waitForTimeout(1500);
  const out = { real: await p.evaluate(() => __osz.state().look) };
  assert.equal(out.real.held, await p.evaluate(() => __osz.G.you.hands && __osz.G.you.hands.code), 'the hand shows what the server says is held');
  assert.equal(out.real.hurt, 0); assert.deepEqual(out.real.wounds, []);
  const shot = async (name) => { await p.waitForTimeout(350); const b = await p.locator('canvas').first().boundingBox(); await p.screenshot({ path: `${prefix}-${name}.png`, clip: { x: b.x + b.width / 2 - 60, y: b.y + b.height / 2 - 78, width: 120, height: 100 } }); };
  await p.evaluate(() => { __osz.G.ws.onmessage = null; __osz.G.zeds.clear(); });       // hold the picture still
  await shot('fresh');
  const set = (o) => p.evaluate((o) => {
    const G = __osz.G; G.you.hp = o.hp; G.you.hands = o.held ? { id: 'w', code: o.held, cond: 5 } : null;
    G.body.wounds = (o.wounds || []).map(([part, bandaged, clean, bleeding], i) => ({ id: i, kind: 'bite', part, bandaged, clean, bleeding }));
    G.body.items = [{ id: 'b', code: o.bag || 'x' }, { id: 'h', code: 'helmet' }]; G.body.worn = { ...(o.bag ? { back: 'b' } : {}), ...(o.helmet ? { head: 'h' } : {}) };
    G.faceLeft = !!o.left;
  }, o);
  const looks = {
    hurt1: { hp: 70, held: 'crowbar' },
    hurt3: { hp: 15, held: 'axe', wounds: [['left forearm', false, false, true], ['torso', false, false, false]] },
    bandaged: { hp: 45, held: 'knife', wounds: [['right upper arm', true, true, false], ['head', true, false, false], ['left thigh', true, true, false], ['right shin', false, false, true]] },
    geared: { hp: 100, held: 'bat', bag: 'rucksack', helmet: true },
    knife: { hp: 100, held: 'knife' }, pistol: { hp: 100, held: 'pistol' }, crowbar: { hp: 100, held: 'crowbar' }, axe: { hp: 100, held: 'axe', left: true },
    gearedLeft: { hp: 60, held: 'pistol', bag: 'schoolbag', helmet: true, left: true, wounds: [['neck', true, true, false]] },
  };
  for (const [name, o] of Object.entries(looks)) {
    await set(o); await shot(name);
    const look = await p.evaluate(() => __osz.state().look);
    assert.equal(look.held, o.held); assert.equal(look.wounds.length, (o.wounds || []).length); assert.equal(look.bag, o.bag || null); assert.equal(look.head, o.helmet ? 'helmet' : null);
    out[name] = { hurt: look.hurt, wounds: look.wounds.map((w) => w.join(':')).join(' ') };
  }
  out.cached = await p.evaluate(() => __osz.state().look.cached);
  out.fps = await p.evaluate(() => Math.round(__osz.G.fps));
  assert(out.cached >= 3 && out.cached <= 40, 'painted frames are kept, and not without limit');
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ ...out, errors }));
} finally { await browser.close(); }
