import assert from 'node:assert/strict';
import {corpseHit} from '../app/static/js/body-hit.js';
for(const h of [22,48,72,120])for(const variant of [0,1]){
 const angle=variant%2?-1.5:1.5;
 // Fallen head, torso and feet must all respond, including far beyond the old 25px circle.
 for(const t of [.05,.5,.95])assert.notEqual(corpseHit(200+Math.sin(angle)*h*t,300-Math.cos(angle)*h*t,200,300,h,.55,variant),null);
 assert.notEqual(corpseHit(230,312,200,300,h,.55,variant),null,'label accepts taps');
 assert.equal(corpseHit(200,500,200,300,h,.55,variant),null,'distant ground stays walkable');
}
console.log('Body head, torso, feet and label taps match both fallen orientations at all zoom sizes.');
