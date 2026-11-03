// M2 gate: one whole outing on a phone-sized touch browser, against an unmodified server.
//   OSZ_PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs node tools/mobile_outing_check.mjs [base] [shots-prefix]
// A new survivor starts on the street and, using only the object cards, their small drawers and the
// belt, goes in through a door, searches a shelf and takes one thing, drinks, makes the room home,
// stores what was found, takes a chair apart for wood and boards a window with it. The full
// Pack / Home / Work sheet must never open. Walking is by a tap on the map (the same function).
// It picks a building whose shelf is in the room behind the front door; a larger one would need
// exploring, which this check does not do. Zombies are real. The survivor swings at anything within reach, as a player's thumb would, and
// redoes a step that a fight interrupted. If it is killed the run fails and says so; run it again.
const { chromium, devices } = await import(process.env.OSZ_PLAYWRIGHT_MODULE || 'playwright');
import assert from 'node:assert/strict';

const base = process.argv[2] || 'http://127.0.0.1:8019', prefix = process.argv[3] || '/tmp/osz-outing';
const metres = (a, b) => Math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * Math.cos(a[0] * Math.PI / 180));
const browser = await chromium.launch({ headless: false, args: ['--no-sandbox'] });
try {
  const c = await browser.newContext({ ...devices['Pixel 7'], viewport: { width: 393, height: 851 }, permissions: ['geolocation'], geolocation: { latitude: 44.9778, longitude: -93.265, accuracy: 8 } });
  const p = await c.newPage(), errors = []; p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(base + '/?auto=desk&name=OutingCheck');
  await p.waitForFunction(() => __osz.G.you && __osz.G.located && !__osz.G.launchPending && !__osz.G.mapping && __osz.G.body && __osz.G.buildings.length, null, { timeout: 90000 });
  const t0 = Date.now(), out = { steps: [] }, step = (name, extra) => out.steps.push({ step: name, s: Math.round((Date.now() - t0) / 1000), ...extra });
  await p.evaluate(() => {
    window.__r = []; window.__sheet = 0;
    __osz.G.ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (m.t === 'r') window.__r.push(m); });
    new MutationObserver(() => { if (!document.getElementById('panel').hidden) window.__sheet++; }).observe(document.getElementById('panel'), { attributes: true, attributeFilter: ['hidden'] });
  });
  // Zombies are real: swing at whatever comes within reach, from the first step on.
  await p.evaluate(() => { window.__swings = 0; setInterval(() => { const G = __osz.G; if (!G.you || G.dead) return; const z = __osz.state().zeds[0]; if (z && z.d < 2.3) { __osz.press('swing'); window.__swings++; } }, 450); });
  const count = (code) => p.evaluate((code) => __osz.G.body.items.filter((i) => i.code === code).reduce((n, i) => n + i.qty, 0), code);
  const alive = async () => assert(!(await p.evaluate(() => __osz.G.dead)), 'the test survivor was killed after: ' + JSON.stringify(out.steps.slice(-1)) + ' swings ' + (await p.evaluate(() => window.__swings)) + '; run again');
  const verdict = async (action, from) => { await p.waitForFunction(({ action, from }) => window.__r.slice(from).some((m) => m.a === action), { action, from }, { timeout: 9000 }); return p.evaluate(({ action, from }) => window.__r.slice(from).find((m) => m.a === action), { action, from }); };
  const mark = () => p.evaluate(() => window.__r.length);
  // A tap on the map. True on arrival; false when the server says a shut door is in the way.
  async function tryWalk(ll, within, timeout) {
    const until = Date.now() + timeout, from = await mark();
    await p.evaluate((ll) => __osz.walkTo(ll), ll);
    for (;;) {
      const s = await p.evaluate((from) => ({ at: [__osz.G.you.lat, __osz.G.you.lng], speed: __osz.G.you.speed, goal: __osz.G.goal, refused: window.__r.slice(from).some((m) => m.a === 'route' && !m.ok) }), from);
      await alive();
      if (metres(s.at, ll) < within && s.speed < 0.3) return true;
      if (s.refused) return false;
      if (Date.now() >= until) assert.fail(`did not arrive: ${metres(s.at, ll).toFixed(1)} m short; ` + JSON.stringify(await p.evaluate(() => ({ route: window.__r.filter((m) => m.a === 'route').slice(-1).map((m) => [m.ok, m.why, (m.route || []).length]), inside: __osz.G.inside, zeds: __osz.state().zeds.slice(0, 3).map((z) => [z.d, z.state]), hp: __osz.G.you.hp }))));
      if (!s.goal && s.speed < 0.2) await p.evaluate((ll) => __osz.walkTo(ll), ll);
      await p.waitForTimeout(400);
    }
  }
  // Walk there as a player would: when a shut door is in the way, go to it, open it from its card, go on.
  async function walkTo(ll, within = 1.6, timeout = 150000) {
    const tried = [];
    for (let n = 0; n < 6; n++) {
      if (await tryWalk(ll, within, timeout)) return;
      const doors = await p.evaluate(({ ll, tried }) => {
        const G = __osz.G, m = (a, b) => Math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * Math.cos(a[0] * Math.PI / 180)), you = [G.you.lat, G.you.lng];
        return G.buildings.flatMap((b) => b.openings).filter((o) => o.kind === 'door' && !o.open && !o.broken && !o.barricaded && !tried.includes(o.id))
          .map((o) => { const mid = [(o.a[0] + o.b[0]) / 2, (o.a[1] + o.b[1]) / 2]; return { id: o.id, label: o.label, mid, cost: m(you, mid) + m(mid, ll) }; }).sort((a, b) => a.cost - b.cost).slice(0, 3);
      }, { ll, tried });
      let opened = false;
      for (const door of doors) {
        tried.push(door.id);
        const you = await p.evaluate(() => [__osz.G.you.lat, __osz.G.you.lng]), k = 1.3 / Math.max(1.3, metres(door.mid, you));
        const near = [door.mid[0] + (you[0] - door.mid[0]) * k, door.mid[1] + (you[1] - door.mid[1]) * k];
        if (!(await tryWalk(near, 1.4, 40000))) continue;          // that one is behind another wall
        await tapWorld(...door.mid); await card(door.label);
        const from = await mark(); await act('Open');
        const v = await verdict('opening', from); assert(v.ok, 'an inner door opens: ' + v.why);
        out.steps.push({ step: 'opened a ' + door.label.toLowerCase() + ' in the way' }); opened = true; break;
      }
      assert(opened, 'a shut door in the way could be reached and opened: ' + JSON.stringify(await p.evaluate(() => ({ why: window.__r.filter((m) => m.a === 'route').slice(-2).map((m) => m.why), inside: __osz.G.inside }))) + ' doors ' + JSON.stringify(doors.map((d) => [d.label, Math.round(d.cost)])));
    }
    assert.fail('still not there after opening doors');
  }
  async function tapWorld(lat, lng, offset = 0) {         // a finger on the thing itself
    const xy=await p.evaluate(({lat,lng,offset})=>{const [x,y]=__osz.project(lat,lng);return [x,y-offset];},{lat,lng,offset});
    assert(xy[0] > 5 && xy[0] < 388 && xy[1] > 60 && xy[1] < 700, 'the thing to tap is on the screen: ' + xy.map(Math.round));
    await p.touchscreen.tap(...xy); await p.waitForTimeout(350);
  }
  async function card(name) { await p.waitForFunction((name) => !document.getElementById('worldCard').hidden && document.getElementById('worldName').textContent === name, name, { timeout: 4000 }); return (await p.locator('#worldActions button').allTextContents()); }
  function act(label) { return p.locator('#worldActions button', { hasText: new RegExp('^' + label + '$') }).tap(); }
  const drawerButton = (label) => p.locator('#drawerContent button', { hasText: new RegExp('^' + label + '$') }).first();
  const channelDone = (kind) => p.waitForFunction(() => !__osz.G.channel, null, { timeout: 30000 });

  // ---- the nearest building with a way in and a shelf to search
  await p.waitForFunction(() => __osz.G.stashes.some((s) => s[5] && !s[4] && __osz.G.buildings.some((b) => b.id === s[5] && b.source !== 'generated')), null, { timeout: 40000 });
  await p.waitForTimeout(1500);
  const plans = await p.evaluate(async () => {
    const { clear } = await import(document.querySelector('script[type=module]').src.replace(/main\.js.*$/, 'buildings.js'));
    const G = __osz.G, here = [G.you.lat, G.you.lng], m = (a, b) => Math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * Math.cos(a[0] * Math.PI / 180));
    const found = [];
    for (const b of G.buildings) {
      const door = b.openings.find((o) => o.label === 'Entrance'), shelf = G.stashes.find((s) => s[5] === b.id && !s[4]);
      if (!door || !shelf || b.source === 'generated' || !b.openings.some((o) => o.kind === 'window' && !o.barricaded && !o.broken)) continue;
      const mid = [(door.a[0] + door.b[0]) / 2, (door.a[1] + door.b[1]) / 2];
      // a shelf in the room behind the front door: no inner doors to find on the way
      const dy = (door.b[0] - door.a[0]) * 111320, dx = (door.b[1] - door.a[1]) * 111320 * Math.cos(mid[0] * Math.PI / 180), n = Math.hypot(dx, dy) || 1;
      const sides = [1.2, -1.2].map((k) => [mid[0] - (dx / n) * k / 111320, mid[1] + (dy / n) * k / (111320 * Math.cos(mid[0] * Math.PI / 180))]);
      const direct = sides.some((q) => clear(G.buildings, q, [shelf[1], shelf[2]]));
      // and a window of that same room, to board at the end
      const inside = sides.filter((q) => clear(G.buildings, q, [shelf[1], shelf[2]])), kk = Math.cos(mid[0] * Math.PI / 180);
      const lit = b.openings.filter((o) => o.kind === 'window' && !o.barricaded && !o.broken).some((o) => {
        const wm = [(o.a[0] + o.b[0]) / 2, (o.a[1] + o.b[1]) / 2], wy = (o.b[0] - o.a[0]) * 111320, wx = (o.b[1] - o.a[1]) * 111320 * kk, wn = Math.hypot(wx, wy) || 1;
        return [1.3, -1.3].some((k) => { const spot = [wm[0] - (wx / wn) * k / 111320, wm[1] + (wy / wn) * k / (111320 * kk)]; return inside.some((q) => clear(G.buildings, q, spot)) || clear(G.buildings, [shelf[1], shelf[2]], spot); });
      });
      found.push({ id: b.id, name: b.name, rooms: b.rooms.length, door: door.id, mid, a: door.a, b: door.b, centre: b.rooms[0].pos, shelf: shelf[0], d: m(here, mid), direct: direct && lit });
    }
    return found.filter((x) => x.direct).sort((x, y) => x.d - y.d).slice(0, 4);
  });
  assert(plans.length, 'a simple building is in view: an entrance, an unboarded window and an unsearched shelf and an unboarded window in the room behind the front door (a window boarded by an earlier run rules a building out)');
  let plan = null, outside = null;
  for (const cand of plans) {
    const along = [(cand.b[0] - cand.a[0]) * 111320, (cand.b[1] - cand.a[1]) * 111320 * Math.cos(cand.mid[0] * Math.PI / 180)], len = Math.hypot(...along);
    const side = (k) => [cand.mid[0] + (along[1] / len) * k / 111320, cand.mid[1] - (along[0] / len) * k / (111320 * Math.cos(cand.mid[0] * Math.PI / 180))];
    const spot = [side(1.7), side(-1.7)].sort((x, y) => metres(y, cand.centre) - metres(x, cand.centre))[0];
    if (await tryWalk(spot, 1.6, 150000)) { plan = cand; outside = spot; break; }     // refused: no street leads there from here; try the next
    out.steps.push({ step: 'no way to ' + cand.name + ' from here, trying the next building' });
  }
  assert(plan, 'one of the nearest buildings can be walked to');
  step('at the door', { building: plan.name, walked: Math.round(plan.d), shelfBehindFrontDoor: plan.direct });

  // ---- enter: the door's own card
  await tapWorld(...plan.mid);
  const doorActions = await card('Entrance');
  let from = await mark();
  if (doorActions.includes('Close') || doorActions.includes('Broken open')) step('door was already open');   // someone, an earlier run or a zombie left it so
  else {
    assert(doorActions.includes('Open') && doorActions.includes('Knock'), 'the door offers Open and Knock: ' + doorActions);
    await act('Open');
    const opened = await verdict('opening', from);
    assert(opened.ok, 'the door opens: ' + opened.why);
    step('door opened');
  }
  await p.screenshot({ path: `${prefix}-door.png` });

  // From here on things take time. A swing closes every card and stops timed work, as it does for a
  // player, so each step can be done again from its first tap.
  const calm = () => p.waitForFunction(() => { const z = __osz.state().zeds[0]; return __osz.G.dead || !z || z.d > 5; }, null, { timeout: 45000 }).catch(() => {});
  async function attempt(name, fn, tries = 5) {
    let last;
    for (let n = 0; n < tries; n++) {
      try { await fn(); if (n) out.steps.push({ step: name + ' took ' + (n + 1) + ' tries (a zombie interrupted)' }); return; } catch (e) { last = e; await alive(); await calm(); }
    }
    throw last;
  }
  const qty = (code) => count(code);

  // ---- loot: the shelf's card, its drawer, one thing taken
  const shelfAt = await p.evaluate((id) => { const s = __osz.G.stashes.find((s) => s[0] === id); return [s[1], s[2]]; }, plan.shelf);
  let first = null, had = 0;
  await attempt('loot', async () => {
    if (first && await qty(first.code) === had + 1) return;
    await walkTo(shelfAt, 2.2, 60000);
    assert.equal(await p.evaluate(() => __osz.G.inside), plan.id, 'the survivor is indoors');
    await tapWorld(...shelfAt, 12);
    const actions = await p.locator('#worldActions button').allTextContents();
    assert(actions.includes('Search') || actions.includes('Look inside'), 'the shelf offers Search: ' + actions);
    await act(actions.includes('Search') ? 'Search' : 'Look inside');
    await p.waitForFunction((id) => !document.getElementById('sceneDrawer').hidden && __osz.G.lootShelves.some((s) => s.id === id && s.items.length), plan.shelf, { timeout: 15000 });
    if (!first) { first = await p.evaluate((id) => __osz.G.lootShelves.find((s) => s.id === id).items[0], plan.shelf); had = await qty(first.code); }
    await p.locator(`#drawerContent .loot-row[data-item="${first.code}"]`).first().getByRole('button', { name: 'Take 1', exact: true }).tap({ timeout: 4000 });
    await p.waitForFunction(({ code, n }) => __osz.G.body.items.filter((i) => i.code === code).reduce((n, i) => n + i.qty, 0) === n, { code: first.code, n: had + 1 }, { timeout: 6000 });
    await p.screenshot({ path: `${prefix}-loot.png` });
    await p.locator('#drawerClose').tap({ timeout: 3000 }).catch(() => {});
  });
  step('looted', { took: first.code });

  // ---- drink from the belt
  const water = await qty('water');
  await attempt('drink', async () => {
    if (await qty('water') === water - 1) return;
    const from = await mark(); await p.locator('#qWater').tap({ timeout: 4000 });
    const drank = await verdict('use', from);
    assert(drank.ok, 'a drink from the belt: ' + drank.why); assert.equal(await qty('water'), water - 1);
  });
  step('drank');

  // ---- retreat: this room becomes home, from a piece of its furniture
  const furniture = () => p.evaluate((id) => __osz.G.body.survival.objects.filter((o) => o.building === id).map((o) => ({ id: o.id, kind: o.kind, name: o.name, at: [o.lat, o.lng], capacity: o.capacity, d: Math.hypot((o.lat - __osz.G.you.lat) * 111320, (o.lng - __osz.G.you.lng) * 78700) })).sort((a, b) => a.d - b.d), plan.id);
  const things = await furniture();
  const store = things.find((o) => o.capacity > 0), spare = things.find((o) => o.kind === 'chair') || things.find((o) => o.id !== store?.id);
  assert(store && spare, 'the room has a cupboard and something to take apart: ' + things.map((o) => o.kind));
  await attempt('home', async () => {
    if (await p.evaluate(() => !!__osz.G.body.home)) return;
    await walkTo(store.at, 2.0, 60000);
    await tapWorld(...store.at, 12); await card(store.name); await act('More');
    const from = await mark(); await drawerButton('Make this room home').tap({ timeout: 4000 });
    assert((await verdict('home', from)).ok);
    await p.waitForFunction(() => __osz.G.body.home, null, { timeout: 6000 });
    await p.locator('#drawerClose').tap({ timeout: 3000 }).catch(() => {});
  });
  step('home made');

  // ---- store what was found
  const inStore = () => p.evaluate(({ id, code }) => !!__osz.G.body.home.containers.find((c) => c.id === id)?.items.some((i) => i.code === code), { id: store.id, code: first.code });
  await attempt('store', async () => {
    if (await inStore()) return;
    await walkTo(store.at, 2.0, 60000);
    await tapWorld(...store.at, 12);
    const actions = await card(store.name);
    assert(actions.includes('Storage'), 'home furniture offers Storage: ' + actions);
    await act('Storage');
    const carried = await qty(first.code), from = await mark();
    await p.locator(`#drawerContent .loot-row[data-item="${first.code}"]`).last().getByRole('button', { name: 'Store qty', exact: true }).tap({ timeout: 4000 });
    const stored = await verdict('transfer', from);
    assert(stored.ok, 'stored: ' + stored.why); assert.equal(await qty(first.code), carried - 1); assert(await inStore());
    await p.screenshot({ path: `${prefix}-store.png` });
    await p.locator('#drawerClose').tap({ timeout: 3000 }).catch(() => {});
  });
  step('stored', { item: first.code });

  // ---- make: a piece of furniture taken apart for wood and nails
  const planks = await qty('plank'); let sawProgress = false;
  await attempt('dismantle', async () => {
    if (await qty('plank') >= planks + 2) return;
    await walkTo(spare.at, 2.0, 60000);
    await tapWorld(...spare.at, 12); await card(spare.name); await act('More');
    const from = await mark(); await drawerButton('Dismantle').tap({ timeout: 4000 });
    const apart = await verdict('work', from);
    assert(apart.ok, 'dismantling starts: ' + apart.why);
    await p.waitForFunction(() => __osz.G.channel, null, { timeout: 4000 }).catch(() => {});
    sawProgress = sawProgress || await p.locator('#channel').isVisible();
    await p.waitForFunction((n) => __osz.G.body.items.filter((i) => i.code === 'plank').reduce((n, i) => n + i.qty, 0) >= n + 2, planks, { timeout: 14000 });
  });
  assert(sawProgress, 'work shows its progress and a Cancel');
  step(spare.kind + ' dismantled', { planks: await qty('plank'), nails: await qty('nails') });

  // ---- and a window boarded with them, from the window's own card
  // every unboarded window with the two spots beside it; the first one the survivor can walk up to is boarded
  const spots = await p.evaluate((id) => {
    const G = __osz.G, b = G.buildings.find((b) => b.id === id), you = [G.you.lat, G.you.lng], k = Math.cos(you[0] * Math.PI / 180), found = [];
    for (const o of b.openings.filter((o) => o.kind === 'window' && !o.barricaded && !o.broken)) {
      const mid = [(o.a[0] + o.b[0]) / 2, (o.a[1] + o.b[1]) / 2], dy = (o.b[0] - o.a[0]) * 111320, dx = (o.b[1] - o.a[1]) * 111320 * k, n = Math.hypot(dx, dy) || 1;
      for (const side of [1.3, -1.3]) { const spot = [mid[0] - (dx / n) * side / 111320, mid[1] + (dy / n) * side / (111320 * k)]; found.push({ id: o.id, mid, spot, d: Math.hypot((spot[0] - you[0]) * 111320, (spot[1] - you[1]) * 111320 * k) }); }
    }
    return found.sort((x, y) => x.d - y.d).slice(0, 8);
  }, plan.id);
  let win = null;
  const isBoarded = () => p.evaluate((id) => __osz.G.buildings.some((b) => b.openings.some((o) => o.id === id && o.barricaded)), win.id);
  await attempt('board', async () => {
    if (win && await isBoarded()) return;
    if (!win) { for (const cand of spots) if (await tryWalk(cand.spot, 1.2, 40000) && await p.evaluate(() => !!__osz.G.inside)) { win = cand; break; } }
    assert(win, 'a window of the home can be walked up to from inside');
    await walkTo(win.spot, 1.2, 60000);
    await tapWorld(...win.mid); await card('Window'); await act('More');
    const from = await mark(); await drawerButton('Barricade').tap({ timeout: 4000 });
    const boarded = await verdict('work', from);
    assert(boarded.ok, 'boarding starts: ' + boarded.why);
    await p.waitForFunction((id) => __osz.G.buildings.some((b) => b.openings.some((o) => o.id === id && o.barricaded)), win.id, { timeout: 14000 });
  });
  await p.locator('#drawerClose').tap({ timeout: 2000 }).catch(() => {});
  await p.waitForTimeout(600); await p.screenshot({ path: `${prefix}-boarded.png` });
  step('window boarded');
  out.swings = await p.evaluate(() => window.__swings);

  await alive();
  out.fullSheetOpened = await p.evaluate(() => window.__sheet);
  assert.equal(out.fullSheetOpened, 0, 'the whole outing was done without the Pack / Home / Work sheet');
  assert(!(await p.evaluate(() => document.documentElement.scrollWidth > innerWidth)));
  assert.deepEqual(errors, []);
  out.seconds = Math.round((Date.now() - t0) / 1000); out.hp = await p.evaluate(() => Math.round(__osz.G.you.hp)); out.fps = await p.evaluate(() => Math.round(__osz.G.fps));
  console.log(JSON.stringify({ ...out, errors }));
} finally { await browser.close(); }
