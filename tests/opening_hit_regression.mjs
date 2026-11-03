import assert from 'node:assert/strict';
import {openingHit,isWindowOpening} from '../app/static/js/opening-hit.js';
assert.equal(openingHit(150,145,[100,200],[200,230],80),0,'raised window face is selectable');
assert.equal(openingHit(150,215,[100,200],[200,230],80),0,'ground opening remains selectable');
assert.equal(openingHit(150,120,[100,200],[200,230],0),null,'an open passage has no phantom raised panel');
assert.equal(openingHit(350,100,[100,200],[200,230],80),null);
assert.notEqual(openingHit(150,225,[100,200],[200,230],0),null);
console.log('Opening touches match raised glass/door faces and their ground edges.');

for(const label of ['Window','Window 2','Upper window'])assert(isWindowOpening({kind:'opening',openingKind:'window',label}));
assert(!isWindowOpening({kind:'opening',openingKind:'door',label:'Window shop entrance'}));
