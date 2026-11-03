// Run with: node tests/building_client_regression.mjs
import assert from 'node:assert/strict';
import {clear} from '../app/static/js/buildings.js';
const lat=44.9778,lng=-93.26499995500001;
const mx=111320*Math.cos(lat*Math.PI/180);
const point=[lat,lng+.2801/mx];
const rounded=[lat,Math.round(point[1]*1e7)/1e7];
const building={walls:[[[lat-.001,lng],[lat+.001,lng]]],openings:[]};
assert(clear([building],rounded,[lat,point[1]+.1/mx]),'rounded valid pose must move away');
assert(!clear([building],rounded,[lat,lng-.5/mx]),'wall crossing must remain blocked');
console.log('Client wall rounding regression passed.');
