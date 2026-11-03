// The thumb stick against a real wall that is not square to the compass, on a phone-sized touch browser.
//   OSZ_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tools/mobile_doorway_check.mjs [base] [shots-prefix]
// Walks to a spot beside a long wall of a real building, holds the stick at 45 degrees into the wall,
// and checks that the survivor slides along it to its far end (instead of stopping against it),
// stays outside and a body's width off it, and that the server's body keeps up with the phone.
// Then opens a front door, stands three metres out and far enough to one side that a straight push
// clips the door frame by about twelve centimetres, pushes straight in, and checks that the phone
// and the server's body both end up indoors.
// The numbers behind the rule come from tools/doorway_precision.mjs, which needs no browser.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8019', shots = process.argv[3] || '/tmp/osz-doorway';
const HOME = { latitude: 44.9778, longitude: -93.265, accuracy: 8 };
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
const out = {};

try {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width: 393, height: 851 }, permissions: ['geolocation'], geolocation: HOME });
  const p = await c.newPage(), errors = [];
  p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(`${base}/?auto=desk&name=DoorwayCheck`);
  await p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping && __osz.G.buildings.length, null, { timeout: 90000 });
  const cdp = await c.newCDPSession(p);
  const touch = (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map(([x, y, id]) => ({ x, y, id })) });

  // long walls turned at least 15 degrees from both compass axes, with open ground along the outside
  const walls = await p.evaluate(async () => {
    const { clear, contains, buildingAt } = await import('/js/buildings.js'), { deltaM, shiftLL } = await import('/js/map.js');
    window.__doorway = { deltaM };       // a waiting test cannot import
    const G = __osz.G, found = [];
    for (const b of G.buildings) for (const [a, e] of b.walls) {
      const [dx, dy] = deltaM(...a, ...e), length = Math.hypot(dx, dy);
      if (length < 10) continue;
      const turn = Math.abs(Math.atan2(dy, dx) * 180 / Math.PI) % 90;
      if (turn < 15 || turn > 75) continue;
      const along = [dx / length, dy / length];
      let out = [-along[1], along[0]];
      const mid = shiftLL(a[0], a[1], dx / 2, dy / 2);
      if (contains(b.outline, shiftLL(mid[0], mid[1], out[0], out[1]))) out = [-out[0], -out[1]];
      const beside = (k, n) => shiftLL(a[0], a[1], along[0] * k + out[0] * n, along[1] * k + out[1] * n);
      const start = beside(1.5, 1.5);
      if (buildingAt(G.buildings, start) || !clear(G.buildings, start, beside(9, 1.5)) || !clear(G.buildings, beside(1.5, .6), beside(9, .6))) continue;
      found.push({ id: b.id, name: b.name, a, along, out, start, length: +length.toFixed(1), turn: +turn.toFixed(0), far: Math.hypot(...deltaM(...G.desk, ...start)) });
    }
    return found.sort((x, y) => x.far - y.far).slice(0, 8);
  });
  assert(walls.length, 'no long turned wall with open ground beside it near the start');

  const state = () => p.evaluate(() => __doorway.read());
  let done = null;
  for (const w of walls) {
    await p.evaluate((ll) => __osz.walkTo(ll), w.start);
    const there = await p.waitForFunction((ll) => { const G = __osz.G; return !G.goal && !G.routePending && Math.hypot(...__doorway.deltaM(...G.desk, ...ll)) < .7 && Math.hypot(...__doorway.deltaM(...G.desk, G.you.lat, G.you.lng)) < .3; }, w.start, { timeout: 90000 }).then(() => true, () => false);
    if (!there) { await p.locator('#bStop').tap().catch(() => {}); continue; }
    await p.waitForTimeout(800);
    // every frame: where the phone and the server's body are, along the wall and out from it
    await p.evaluate((w) => {
      const G = __osz.G, rel = (ll) => { const [x, y] = __doorway.deltaM(...w.a, ...ll); return [x * w.along[0] + y * w.along[1], x * w.out[0] + y * w.out[1]]; };
      __doorway.read = () => ({ phone: rel(G.desk), body: rel([G.you.lat, G.you.lng]), apart: Math.hypot(...__doorway.deltaM(...G.desk, G.you.lat, G.you.lng)), dead: G.dead, hp: G.you.hp, pace: G.you.walk_speed });
      __doorway.rows = []; __doorway.arrived = false; __doorway.on = true;
      const tick = () => { if (!__doorway.on) return; const r = __doorway.read(); __doorway.rows.push([...r.phone, ...r.body, r.apart]); if (r.phone[0] >= w.length - 3) __doorway.arrived = true; requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    }, w);
    const before = await state();
    // Project a world push 45 degrees into the wall to the current camera.
    const [east,down]=await p.evaluate(w=>__osz.screenVector((w.along[0]-w.out[0])*Math.SQRT1_2,(w.along[1]-w.out[1])*Math.SQRT1_2),w),north=-down;
    await touch('touchStart', [[120, 620, 1]]);
    for (const k of [.2, .5, .8, 1]) await touch('touchMove', [[120 + east * 70 * k, 620 - north * 70 * k, 1]]);
    const arrived = await p.waitForFunction(() => __doorway.arrived, null, { timeout: Math.ceil((w.length-3-before.phone[0])/Math.max(.5,before.pace*Math.SQRT1_2)*1000+4000), polling: 'raf' }).then(() => true, () => false);
    await touch('touchEnd', []);
    await p.screenshot({ path: shots + '-held.png' });
    await p.waitForTimeout(1500);
    const rows = await p.evaluate(() => { __doorway.on = false; return __doorway.rows; }), after = await state();
    if (process.env.OSZ_DEBUG) console.error(JSON.stringify({ w, before, after, rows: rows.filter((_, i) => i % 6 === 0).map((r) => r.map((v) => +v.toFixed(2))) }));
    if (after.dead || after.hp < before.hp) continue;              // something attacked: the run says nothing about walls
    // the stretch where the survivor ought to be sliding: two metres past the start to three short of the far end
    const sliding = rows.filter((r) => r[0] > before.phone[0] + 2 && r[0] < w.length - 3);
    done = { wall: { building: w.name, lengthM: w.length, turnedDeg: w.turn }, paceMs: before.pace, arrived, reachedM: +Math.max(...rows.map((r) => r[0])).toFixed(2), frames: sliding.length,
      phoneOffM: sliding.length ? [+Math.min(...sliding.map((r) => r[1])).toFixed(3), +Math.max(...sliding.map((r) => r[1])).toFixed(3)] : null,
      bodyOffM: sliding.length ? [+Math.min(...sliding.map((r) => r[3])).toFixed(3), +Math.max(...sliding.map((r) => r[3])).toFixed(3)] : null,
      bodyBehindM: sliding.length ? +Math.max(...sliding.map((r) => r[4])).toFixed(2) : null, bodyApartAfterM: +after.apart.toFixed(2) };
    break;
  }
  assert(done, 'no undisturbed run beside a wall');
  out.slide = done;
  assert(done.arrived, `the survivor should slide along the wall to its far end (got ${done.reachedM} m along a ${done.wall.lengthM} m wall)`);
  assert(done.frames > 10 && done.phoneOffM[0] >= .26 && done.phoneOffM[1] < .6, `the phone stays outside, a body's width off the wall (${done.phoneOffM} m)`);
  assert(done.bodyOffM[0] >= .27 && done.bodyBehindM < 3 && done.bodyApartAfterM < .5, `the server's body stays outside and keeps up (${done.bodyOffM} m off the wall, at most ${done.bodyBehindM} m behind, ${done.bodyApartAfterM} m apart once stopped)`);

  // ---------------------------------------------------------------- through a doorway, clipping the frame
  const doors = await p.evaluate(async () => {
    const { clear, contains, buildingAt } = await import('/js/buildings.js'), { deltaM, shiftLL } = await import('/js/map.js');
    const G = __osz.G, found = [];
    __doorway.indoors = (id, ll) => { const b = G.buildings.find((b) => b.id === id); return !!b && contains(b.outline, ll); };
    for (const b of G.buildings) for (const o of b.openings) {
      if (o.label !== 'Entrance' || o.barricaded || b.source === 'generated') continue;
      const [dx, dy] = deltaM(...o.a, ...o.b), width = Math.hypot(dx, dy), half = width / 2;
      if (half < .6) continue;
      const along = [dx / width, dy / width], mid = shiftLL(o.a[0], o.a[1], dx / 2, dy / 2);
      let out = [-along[1], along[0]];
      if (contains(b.outline, shiftLL(mid[0], mid[1], out[0], out[1]))) out = [-out[0], -out[1]];
      const at = (k, n) => shiftLL(mid[0], mid[1], along[0] * k + out[0] * n, along[1] * k + out[1] * n);
      // the body is 0.27 m round: a line 0.15 m inside the jamb clips the frame by 0.12 m
      const start = at(half - .15, 3), room = at(0, -1.5);
      const open = { ...b, openings: b.openings.map((x) => x.id === o.id ? { ...x, open: true } : x) }, others = G.buildings.filter((x) => x.id !== b.id);
      if (buildingAt(G.buildings, start) || !clear(G.buildings, start, at(half - .15, .6)) || !clear([open, ...others], at(0, 1), room)) continue;
      found.push({ id: o.id, building: b.id, name: b.name, a: mid, along, out, start, knock: at(0, 1.2), width: +width.toFixed(2), turn: +(Math.abs(Math.atan2(dy, dx) * 180 / Math.PI) % 90).toFixed(0), far: Math.hypot(...deltaM(...G.desk, ...start)) });
    }
    return found.sort((x, y) => x.far - y.far).slice(0, 6);
  });
  assert(doors.length, 'no front door with open ground in front of it near the start');
  const arrive = (ll) => p.evaluate((ll) => __osz.walkTo(ll), ll).then(() => p.waitForFunction((ll) => { const G = __osz.G; return !G.goal && !G.routePending && Math.hypot(...__doorway.deltaM(...G.desk, ...ll)) < .7 && Math.hypot(...__doorway.deltaM(...G.desk, G.you.lat, G.you.lng)) < .3; }, ll, { timeout: 90000 })).then(() => true, () => false);
  let through = null;
  for (const d of doors) {
    if (!(await arrive(d.knock))) { await p.locator('#bStop').tap().catch(() => {}); continue; }
    const isOpen = () => p.evaluate((id) => __osz.G.buildings.flatMap((b) => b.openings).some((o) => o.id === id && (o.open || o.broken) && !o.barricaded), d.id);
    if (!(await isOpen())) await p.evaluate((id) => __osz.fire('opening', { opening: id, op: 'open' }), d.id);
    if (!(await p.waitForFunction((id) => __osz.G.buildings.flatMap((b) => b.openings).some((o) => o.id === id && (o.open || o.broken) && !o.barricaded), d.id, { timeout: 8000 }).then(() => true, () => false))) continue;
    if (!(await arrive(d.start))) { await p.locator('#bStop').tap().catch(() => {}); continue; }
    await p.waitForTimeout(800);
    await p.evaluate((d) => {
      const G = __osz.G, rel = (ll) => { const [x, y] = __doorway.deltaM(...d.a, ...ll); return [x * d.along[0] + y * d.along[1], x * d.out[0] + y * d.out[1]]; };
      __doorway.read = () => ({ phone: rel(G.desk), body: rel([G.you.lat, G.you.lng]), apart: Math.hypot(...__doorway.deltaM(...G.desk, G.you.lat, G.you.lng)), phoneIn: __doorway.indoors(d.building, G.desk), bodyIn: __doorway.indoors(d.building, [G.you.lat, G.you.lng]), dead: G.dead, hp: G.you.hp });
      __doorway.rows = []; __doorway.arrived = false; __doorway.on = true;
      const tick = () => { if (!__doorway.on) return; const r = __doorway.read(); __doorway.rows.push([...r.phone, ...r.body]); if (r.phone[1] < -1) __doorway.arrived = true; requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    }, d);
    const before=await state(),entryScreen=await p.evaluate(d=>__osz.screenVector(-d.out[0],-d.out[1]),d),alongScreen=await p.evaluate(d=>__osz.screenVector(d.along[0],d.along[1]),d);
    await touch('touchStart', [[120, 620, 1]]);
    for(const k of [.2,.5,.8,1])await touch('touchMove',[[120+entryScreen[0]*70*k,620+entryScreen[1]*70*k,1]]);
    const arrived = await p.waitForFunction(() => __doorway.arrived, null, { timeout: 4000, polling: 'raf' }).then(() => true, () => false);
    // the moment the phone is a metre indoors, turn hard along the inside of the wall it has just come round:
    // the body is a tick or two behind and still outside, with that wall now between it and the phone
    if (arrived) { await touch('touchMove', [[120+alongScreen[0]*70,620+alongScreen[1]*70, 1]]); await p.waitForTimeout(450); }
    await touch('touchEnd', []);
    await p.screenshot({ path: shots + '-door.png' });
    await p.waitForTimeout(2500);
    const rows = await p.evaluate(() => { __doorway.on = false; return __doorway.rows; }), after = await state();
    if (process.env.OSZ_DEBUG) console.error(JSON.stringify({ d, before, after, rows: rows.filter((_, i) => i % 4 === 0).map((r) => r.map((v) => +v.toFixed(2))) }));
    if (after.dead || after.hp < before.hp) continue;
    through = { door: { building: d.name, widthM: d.width, turnedDeg: d.turn }, startedM: before.phone.map((v) => +v.toFixed(2)), phoneWentIn: arrived, phoneIndoors: after.phoneIn, bodyIndoors: after.bodyIn, apartAfterM: +after.apart.toFixed(2), endedM: after.phone.map((v) => +v.toFixed(2)) };
    break;
  }
  assert(through, 'no undisturbed run at a front door');
  out.door = through;
  assert(through.phoneWentIn && through.phoneIndoors, `a push that clips the door frame should go round it and in (ended ${through.endedM} from the middle of the doorway; negative is indoors)`);
  assert(through.bodyIndoors && through.apartAfterM < .5, `the server's body should follow round the frame (indoors ${through.bodyIndoors}, ${through.apartAfterM} m from the phone)`);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify(out));
} finally { await browser.close(); }
