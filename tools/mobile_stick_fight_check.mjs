// A real fight steered with the thumb stick, against an unmodified server and natural zombies.
//   OSZ_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tools/mobile_stick_fight_check.mjs [base]
// The left finger closes on a zombie and backs away from it; the right finger swings and shoves.
// Passes when the survivor's own kill count rises, having both retreated and struck with the stick held.
// If a zombie is seen chasing from 10 to 16 m, the Area overview is opened once and must close itself
// as it arrives (areaClosedOnThreat; absent from the result when that chance never came).
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8019';
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
try {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width: 393, height: 851 }, permissions: ['geolocation'], geolocation: { latitude: 44.9778, longitude: -93.265, accuracy: 8 } });
  const p = await c.newPage(), errors = [];
  p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(base + '/?auto=desk&name=StickFighter');
  await p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping, null, { timeout: 90000 });
  const cdp = await c.newCDPSession(p);
  const touch = (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map(([x, y, id]) => ({ x, y, id })) });
  const centre = async (id) => { const b = await p.locator(id).boundingBox(); return [b.x + b.width / 2, b.y + b.height / 2]; };
  const swing = await centre('#bSwing'), shove = await centre('#bShove');
  const O = [110, 640];                                   // where the left thumb rests
  let held = false, knob = O;
  const steer = async (ux, uy, m = 1) => {                // unit vector in metres east/north; m is how far the stick is pushed
    const projected=await p.evaluate(([x,y])=>__osz.screenVector(x,y),[ux,uy]);
    ux=projected[0];uy=-projected[1];
    knob = [O[0] + ux * (10 + 44 * m), O[1] - uy * (10 + 44 * m)];
    if (!held) { await touch('touchStart', [[...O, 1]]); await touch('touchMove', [[O[0] + ux * 14, O[1] - uy * 14, 1]]); held = true; }
    await touch('touchMove', [[...knob, 1]]);
  };
  const centreStick = async () => { if (held) { knob = O; await touch('touchMove', [[...O, 1]]); } };
  const hit = async (at) => {                             // second finger down and up, the first stays where it is
    if (held) { await touch('touchStart', [[...knob, 1], [...at, 2]]); await touch('touchEnd', [[...at, 2]]); }   // touchEnd names the finger lifted
    else { await touch('touchStart', [[...at, 2]]); await touch('touchEnd', []); }
  };

  const start = await p.evaluate(() => ({ kills: __osz.G.you.kills, lat: __osz.G.you.lat, lng: __osz.G.you.lng }));
  const tally = { swingsWhileSteering: 0, shovesWhileSteering: 0, retreatM: 0, ticks: 0, finishSeen:false };
  // count what the server accepted, not what the harness attempted
  await p.evaluate(() => { window.__sent = { swing: 0, shove: 0 }; const ws = __osz.G.ws; ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (m.t === 'r' && m.ok && (m.a === 'swing' || m.a === 'shove') && __osz.G.stick && __osz.G.stick.m > 0) window.__sent[m.a]++; }); });
  let last = null, heading = 0, legUntil = 0;
  const trace = [];
  const deadline = Date.now() + 300000;
  while (Date.now() < deadline) {
    const s = await p.evaluate(() => ({ ...__osz.state(), stick: __osz.G.stick, t: performance.now() }));
    if(await p.locator('#swingLabel').textContent()==='FINISH')tally.finishSeen=true;
    trace.push(`${tally.ticks} hp${Math.round(s.you.hp)} end${Math.round(s.you.end)} eng${s.engaged} ch${s.chasing} busy${s.you.busy} z${s.zeds.slice(0,3).map((z)=>z.state[0]+z.d).join('/')} k${s.you.kills} m${s.stick?s.stick.m.toFixed(1):'-'}`);
    if (s.dead) { console.log(trace.slice(-45).join('\n')); throw Error('the test survivor died ' + JSON.stringify(tally)); }
    const sent = await p.evaluate(() => window.__sent); tally.swingsWhileSteering = sent.swing; tally.shovesWhileSteering = sent.shove;
    if (s.you.kills > start.kills && tally.retreatM > 2 && tally.swingsWhileSteering > 0) break;
    const z = s.zeds.find((z) => !['down', 'rising'].includes(z.state)) || s.zeds[0];
    const down = s.zeds.find((z) => ['down', 'rising'].includes(z.state) && z.d < 5);
    if (last && s.stick && s.stick.m > 0 && last.retreating) tally.retreatM += Math.hypot((s.you.lat - last.lat) * 111320, (s.you.lng - last.lng) * 111320 * Math.cos(s.you.lat * Math.PI / 180));
    let retreating = false;
    // once, if a zombie is walking at us from a little way off: read the map and let it come
    if (tally.areaClosedOnThreat === undefined && z && z.mine && z.state === 'chase' && z.d > 9.5 && z.d < 16 && !s.engaged) {
      if (held) { await touch('touchEnd', []); held = false; knob = O; }
      await p.locator('#bArea').tap();
      await p.waitForFunction(() => __osz.area.on, null, { timeout: 3000 });
      tally.areaClosedOnThreat = await p.waitForFunction(() => !__osz.area.on && [...document.querySelectorAll('.toast')].some((t) => t.textContent.includes('Back to the street')), null, { timeout: 30000 }).then(() => true, () => false);
      if (!tally.areaClosedOnThreat) await p.locator('#areaBack').tap().catch(() => {});
      continue;
    }
    if (!z) {                                             // nothing in sight: wander by stick until something is
      if (Date.now() > legUntil) { heading = Math.random() * 6.283; legUntil = Date.now() + 6000; }
      await steer(Math.cos(heading), Math.sin(heading), 0.8);
    } else if (down) {                                    // one on the ground: stand and finish it
      await centreStick();
      if (s.you.busy === 0) await hit(swing);
    } else if (z.d > 3.1) {                               // close the distance, creeping the last few metres
      await steer(z.dx / z.d, z.dy / z.d, z.d > 9 ? 1 : 0.75);
    } else {                                              // in reach: back away from it while striking
      retreating = z.d < 2.6;
      if (retreating) await steer(-z.dx / z.d, -z.dy / z.d, 0.7); else await centreStick();
      if (s.you.busy === 0) {
        await hit(s.engaged >= 2 ? shove : swing);
      }
    }
    last = { lat: s.you.lat, lng: s.you.lng, retreating };
    tally.ticks++;
    await p.waitForTimeout(140);
  }
  if (held) await touch('touchEnd', []);
  const end = await p.evaluate(() => ({ kills: __osz.G.you.kills, hp: __osz.G.you.hp, stick: __osz.G.stick }));
  await p.screenshot({ path: '/tmp/osz-stick-fight.png' });
  assert(end.kills > start.kills, 'the survivor must finish a zombie of its own');
  assert(tally.swingsWhileSteering > 0, 'at least one swing lands while the stick is held off centre');
  assert(tally.retreatM > 2, `backing away must cover ground (${tally.retreatM.toFixed(1)} m)`);
  assert.equal(end.stick, null, 'lifting the thumb ends steering');
  assert(tally.areaClosedOnThreat !== false, 'the overview must close by itself when a chasing zombie gets close');
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ ownKill: true, kills: end.kills - start.kills, hp: end.hp, ...tally, retreatM: +tally.retreatM.toFixed(1), errors }));
} finally { await browser.close(); }
