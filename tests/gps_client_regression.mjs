import fs from 'node:fs';
import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('../app/static/js/gps.js',import.meta.url),'utf8');
const {freshFix,acknowledgedPlacement}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const now=1000000,p={coords:{latitude:44.9778,longitude:-93.265,accuracy:12},timestamp:now};
assert.deepEqual(freshFix(p,now),[44.9778,-93.265,12,now]);
assert.equal(freshFix({...p,timestamp:now-16000},now),null);
assert.equal(freshFix({...p,timestamp:now+6000},now),null);
assert.equal(freshFix({...p,coords:{...p.coords,accuracy:150}},now),null);
assert.equal(freshFix({...p,coords:{...p.coords,latitude:NaN}},now),null);
assert.equal(freshFix({...p,coords:{...p.coords,accuracy:0}},now),null);
assert.equal(freshFix(null,now),null);
const pending=[{a:'place',args:{generation:3,source:'gps',lat:44,lng:-93}}],you={lat:44.00001,lng:-93,placement_epoch:2};
assert.deepEqual(acknowledgedPlacement(you,pending,1,3).result,{lat:44.00001,lng:-93,placement_epoch:2,anchor:[44,-93]});
assert.equal(acknowledgedPlacement(you,pending,2,3),null); // a late action reply must not cancel Exit again
assert.equal(acknowledgedPlacement(you,pending,1,4),null);
assert.equal(acknowledgedPlacement({...you,placement_epoch:0},pending,1,3),null);
console.log('GPS fix freshness/accuracy regression passed.');
