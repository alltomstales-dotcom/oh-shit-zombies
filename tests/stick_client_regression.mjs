import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// The thumb stick, run from the shipped source: a tap stays a tap, a drag steers, a gentle push creeps.
const source = fs.readFileSync(new URL('../app/static/js/main.js', import.meta.url), 'utf8');
const code = source.slice(source.indexOf('// ---- thumb steering'), source.indexOf('function stepDesk('));
const el = { classList: { set: new Set(['rest']), add(c) { this.set.add(c); }, remove(c) { this.set.delete(c); }, toggle(c, on) { on ? this.set.add(c) : this.set.delete(c); } }, style: {}, firstElementChild: { style: {} } };
const G = { you: { quiet: false, sprinting: false }, tune: { quiet_speed: 1.2 }, pending: new Map(), stick: null, stickTouch: null, quietSent: 0, dead: false };
const calls = [];
const context = vm.createContext({ G, Math, W: 393, H: 851, T: () => 10000, $: () => el, cv: { releasePointerCapture() {} },
  clamp: (v, a, b) => Math.max(a, Math.min(b, v)), collapseWorldUI: (why) => calls.push('collapse:' + why),
  sendPos: () => calls.push('pos'), tapWorld: (x, y) => calls.push(`tap:${x},${y}`), fire: (a, args) => calls.push(`${a}:${args.op}`) });
vm.runInContext(code + ';globalThis.api={stickZone,stickPace,stickMove,stickEnd,wantQuiet,STICK};', context);
const { stickZone, stickPace, stickMove, stickEnd, wantQuiet, STICK } = context.api;

assert(stickZone(100, 620) && !stickZone(330, 620) && !stickZone(100, 200), 'only the lower left starts a stick');

// a touch that never travels is a tap where it landed
G.stickTouch = { id: 1, x0: 100, y0: 620, on: false };
stickMove(104, 623);
assert.equal(G.stick, null);
stickEnd(true);
assert.deepEqual(calls, ['tap:100,620']);

// a drag up the screen steers north at full push, and closes whatever card was open
calls.length = 0;
G.stickTouch = { id: 1, x0: 100, y0: 620, on: false };
stickMove(100, 620 - 80);
assert.deepEqual(calls, ['collapse:movement']);
assert.equal(G.stick.m, 1); assert.equal(G.stick.x, 0); assert.equal(G.stick.y, 1);
assert(!el.classList.set.has('rest') && !el.classList.set.has('creep'));
assert.equal(stickPace(1, 6), 6);
assert(stickPace(STICK.creep, 6) >= 3 && stickPace(STICK.creep, 6) < 6, 'past half way is the normal pace, eased');

// a gentle push east creeps: never faster than the quiet pace, and the ring says so
stickMove(100 + 26, 620);
assert(G.stick.m > 0 && G.stick.m < STICK.creep && G.stick.x === 1);
assert(el.classList.set.has('creep'));
assert(stickPace(G.stick.m, 6) <= 1.2 && stickPace(G.stick.m, 6) > 0.3);
assert.equal(stickPace(0.2, 0.8), 0.8 * 0.4, 'a tired survivor creeps no faster than they can walk');
// sprinting overrides the creep zone
G.you.sprinting = true; assert(stickPace(0.3, 24) > 10); G.you.sprinting = false;

// the creeping flag is asked for once, not every frame
calls.length = 0;
wantQuiet(true); wantQuiet(true);
assert.deepEqual(calls, ['quiet:start']);
G.you.quiet = true; wantQuiet(true);
assert.deepEqual(calls, ['quiet:start']);

// letting go ends steering, reports the stop and never taps
calls.length = 0;
stickEnd(true);
assert.equal(G.stick, null); assert.equal(G.stickTouch, null);
assert.deepEqual(calls, ['pos']);
assert(el.classList.set.has('rest') && !el.classList.set.has('creep'));
console.log('Thumb stick: tap stays a tap, drag steers, gentle push creeps, release stops.');
