import assert from 'node:assert/strict';
import {projectM,unprojectM,worldPoint,screenWorld,groundBounds} from '../app/static/js/projection.js';
for(const iso of [false,true])for(const e of [-100,-2,0,17,100])for(const n of [-100,-3,0,18,100]){
 const p=projectM(e,n,iso),q=unprojectM(...p,iso);assert(Math.hypot(q[0]-e,q[1]-n)<1e-10);
}
for(const iso of [false,true])for(const ppm of [.5,4,12,64]){
 const G={screenLL:[44.9778,-93.265],screenOrigin:[155,330],cam:{iso,ppm}};
 const ll=[44.97793,-93.2648],p=worldPoint(G,...ll),q=screenWorld(G,...p);
 assert(Math.hypot(q[0]-ll[0],q[1]-ll[1])<1e-10,'world objects and walking use the same inverse');
 const bounds=groundBounds(393,851,155,330,iso);assert(bounds.every(Number.isFinite));
}
console.log('Isometric/flat projection and tap-to-world round trips match at every zoom.');
