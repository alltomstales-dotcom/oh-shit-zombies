import assert from 'node:assert/strict';
import {characterPose,characterParts} from '../app/static/js/character-pose.js';
for(let n=0;n<8;n++){
 const p=characterPose(n),parts=characterParts(n);
 for(const point of Object.values(p))assert(point.every(v=>v>=0&&v<=1));
 assert.deepEqual(parts['right hand'].slice(0,2),p.hand);
 assert.equal(Object.keys(parts).length,13);
}
assert.notDeepEqual(characterPose(6).hand,characterPose(1).hand);
assert.deepEqual(characterPose(99),characterPose(7));
console.log('Eight character poses have distinct equipment and matching wound anchors.');
