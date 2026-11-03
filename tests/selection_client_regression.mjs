import assert from 'node:assert/strict';
import {nearestTarget} from '../app/static/js/selection.js';
const shelf={kind:'stash',id:'shelf',hit:1},door={kind:'opening',id:'door',hit:14};
assert.equal(nearestTarget([door,shelf,null]),shelf);
assert.equal(nearestTarget([{...door,hit:0},shelf]).kind,'opening');
assert.equal(nearestTarget([null,false]),null);
assert.equal(nearestTarget([{...shelf,hit:0},{...door,hit:0}]).kind,'stash');
console.log('Nearest world target wins over object-type priority.');
