// How often does a thumb-stick push carry the survivor through an open doorway?
//   node tools/doorway_precision.mjs
// No browser and no server: the page's own wall rules (app/static/js/buildings.js) are stepped at
// sixty frames a second. A 12 m x 10 m building with one open 2.4 m doorway is turned to several
// angles (real streets are rarely square to the compass). The survivor starts 4 m in front of the
// door, up to 2.5 m to one side, and holds the stick in one direction, up to 35 degrees off the
// straight line in. A run counts if the survivor is indoors at any frame within eight seconds.
// The body is 0.27 m round, so a push whose straight line stays within 0.9 m of the middle of the
// doorway goes clean through; out to 1.2 m it clips the frame; beyond that it meets the wall, and
// ought to slide along it: in, if it leans towards the gap, and away if it does not.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const src = new URL('../app/static/js/', import.meta.url), tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'osz-door-'));
for (const f of ['map.js', 'buildings.js']) fs.writeFileSync(path.join(tmp, f.replace('.js', '.mjs')), fs.readFileSync(new URL(f, src), 'utf8').replace(/from '\.\/(\w+)\.js'/g, "from './$1.mjs'"));
const { move, slide, contains } = await import(pathToFileURL(path.join(tmp, 'buildings.mjs')));
const { shiftLL } = await import(pathToFileURL(path.join(tmp, 'map.mjs')));

// paces from app/game/content.py: creeping 1.2, in a fight 2, exploring 6 (2 x 3), sprinting 24 (6 x 4)
const HERE = [44.9778, -93.265], PACE = 6, DT = 1 / 60;
function building(turn) {
  const c = Math.cos(turn), s = Math.sin(turn), at = (x, y) => shiftLL(HERE[0], HERE[1], x * c - y * s, x * s + y * c);
  const corners = [[-6, 0], [6, 0], [6, 10], [-6, 10]].map(([x, y]) => at(x, y));
  return { b: { outline: corners, walls: [[at(-6, 0), at(-1.2, 0)], [at(1.2, 0), at(6, 0)], [at(6, 0), at(6, 10)], [at(6, 10), at(-6, 10)], [at(-6, 10), at(-6, 0)]], openings: [{ a: at(-1.2, 0), b: at(1.2, 0), open: true, broken: false, barricaded: false }] }, at };
}
export function trial(turn, side, error, mover = move, seconds = 8, pace = PACE) {
  const { b, at } = building(turn), heading = Math.PI / 2 + turn + error;     // straight in is the wall's inward normal
  let p = at(side, -4);
  for (let n = 0; n < seconds / DT; n++) {
    p = mover([b], p, shiftLL(p[0], p[1], Math.cos(heading) * pace * DT, Math.sin(heading) * pace * DT));
    if (contains(b.outline, p)) return true;
  }
  return contains(b.outline, p);
}
export function table(mover = move, pace = PACE) {
  const rows = [];
  for (const deg of [0, 15, 30, 45, 60]) {
    const r = { turn: deg, clean: [0, 0], frame: [0, 0], towards: [0, 0], away: [0, 0] };
    for (let side = -2.5; side <= 2.5; side += 0.25) for (let err = -35; err <= 35; err += 5) {
      // where the push would meet the wall line, measured from the middle of the doorway
      const hit = side + 4 * Math.tan(-err * Math.PI / 180);
      if (Math.abs(hit) > 2.5) continue;
      const good = trial(deg * Math.PI / 180, side, err * Math.PI / 180, mover, 8, pace);
      const kind = Math.abs(hit) <= 0.9 ? 'clean' : Math.abs(hit) <= 1.2 ? 'frame' : (Math.sign(-err) !== Math.sign(hit) && err !== 0 ? 'towards' : 'away');
      r[kind][1]++; r[kind][0] += good;
    }
    rows.push(r);
  }
  return rows;
}
export { move, slide };
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  for (const pace of [2, 6, 24]) for (const [name, mover] of [['the plain rule (tapped walks; the thumb stick until 0.9.4)', move], ['the sliding rule (thumb stick from 0.9.5)', slide]]) {
    console.log(`${pace} m/s, ${name}`);
    console.log('  building turned | clean through | clips the frame | meets the wall leaning towards the gap | meets it leaning away or square on (should stay out)');
    for (const r of table(mover, pace)) console.log('  ' + [String(r.turn).padStart(11) + ' deg', r.clean.join(' of ').padEnd(13), r.frame.join(' of ').padEnd(15), r.towards.join(' of ').padEnd(37), r.away.join(' of ')].join(' | '));
  }
}
