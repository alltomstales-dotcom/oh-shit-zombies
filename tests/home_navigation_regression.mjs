import assert from 'node:assert/strict';
import {floorName,homeApproach} from '../app/static/js/home-navigation.js';
const home={building:'house',lat:44,lng:-93,floor_level:1},b={id:'house',stairs:[44,-93]};
assert.equal(floorName(0),'Ground floor');assert.equal(floorName(2),'Floor 3');
assert.equal(homeApproach({you:{floor:0},inside:'house',buildings:[b]},home).mode,'stairs');
assert.equal(homeApproach({you:{floor:1},inside:'house',buildings:[b]},home).mode,'cupboard');
assert.equal(homeApproach({you:{floor:1},inside:'other',buildings:[b]},home).mode,'exit');
assert.equal(homeApproach({you:{floor:0},inside:null,buildings:[]},home).mode,'cupboard');
console.log('Home navigation identifies its floor, stairs, cupboard and exit step.');
