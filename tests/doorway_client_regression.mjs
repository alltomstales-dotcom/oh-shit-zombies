// Run with: node tests/doorway_client_regression.mjs
// The thumb stick against walls and door frames, on buildings turned from the compass (tools/doorway_precision.mjs).
import assert from 'node:assert/strict';
import { table, trial, slide } from '../tools/doorway_precision.mjs';

for (const pace of [2, 6, 24]) for (const r of table(slide, pace)) {      // in a fight, exploring, sprinting
  const at = ` (building turned ${r.turn} degrees, ${pace} m/s)`;
  assert.equal(r.clean[0], r.clean[1], 'a push aimed through the doorway goes in' + at);
  assert.equal(r.frame[0], r.frame[1], 'a push that clips the door frame goes round it and in' + at);
  assert.equal(r.towards[0], r.towards[1], 'a push that meets the wall leaning towards the doorway slides in' + at);
  assert.equal(r.away[0], 0, 'a push that meets the wall leaning away from the doorway stays out' + at);
}
// creeping at 1.2 m/s with the gentlest lean (5 degrees) only needs longer than the table's eight seconds
assert(trial(Math.PI / 6, 2.5, 5 * Math.PI / 180, slide, 40, 1.2), 'a five degree lean at a creep slides in within forty seconds');
console.log('Client doorway regression passed.');
