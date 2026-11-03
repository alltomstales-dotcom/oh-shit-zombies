import {deltaM,shiftLL} from './map.js';
const A=Math.sqrt(3)/2;
// World coordinates are east/north metres. Screen coordinates are right/down.
export function projectM(east,north,iso=true){return iso?[A*(east+north),.5*(east-north)]:[east,-north];}
export function unprojectM(x,y,iso=true){return iso?[x/(2*A)+y,x/(2*A)-y]:[x,-y];}
export function worldPoint(G,lat,lng){
 const ll=G.screenLL||G.desk||[G.you.lat,G.you.lng],o=G.screenOrigin||[innerWidth/2,innerHeight*.46];
 const p=projectM(...deltaM(...ll,lat,lng),!!G.cam.iso);return [o[0]+p[0]*G.cam.ppm,o[1]+p[1]*G.cam.ppm];
}
export function screenWorld(G,x,y){
 const o=G.screenOrigin||[innerWidth/2,innerHeight*.46],ll=G.screenLL||G.desk;
 return shiftLL(...ll,...unprojectM((x-o[0])/G.cam.ppm,(y-o[1])/G.cam.ppm,!!G.cam.iso));
}
export function screenDirection(east,north,iso=true){const p=projectM(east,north,iso),n=Math.hypot(...p)||1;return p.map(v=>v/n);}
export function groundBounds(w,h,cx,cy,iso){
 const p=[[0,0],[w,0],[w,h],[0,h]].map(([x,y])=>unprojectM(x-cx,y-cy,iso)).map(([e,n])=>[cx+e,cy-n]);
 return [Math.min(...p.map(p=>p[0]))-2,Math.min(...p.map(p=>p[1]))-2,Math.max(...p.map(p=>p[0]))+2,Math.max(...p.map(p=>p[1]))+2];
}
export function groundCircle(ctx,x,y,r,iso){ctx.ellipse(x,y,r*(iso?Math.sqrt(1.5):1),r*(iso?Math.SQRT1_2:1),0,0,Math.PI*2);}
