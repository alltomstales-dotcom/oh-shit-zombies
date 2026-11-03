// Vehicle controls keep the map visible; all motion and cargo are server judged.
import {unprojectM,worldPoint} from './projection.js';
import {shiftLL} from './map.js';
let api;
const $=id=>document.getElementById(id);
export function setupVehicles(actions){
 api=actions;
 $('vehicleEngine').onclick=()=>act('engine');
 $('vehicleExit').onclick=()=>act('exit');
 $('vehicleReverse').onclick=()=>{api.G.vehicleReverse=!api.G.vehicleReverse;renderVehicles();};
 $('vehicleBrake').onclick=()=>{api.G.keys.clear();api.G.stick=null;api.G.vehicleGoal=null;drive(0,0,0);};
 $('vehicleCargo').onclick=()=>api.drawer('cargo',api.G.you.vehicle);
}
function act(op){api.G.vehicleGoal=null;api.fire('vehicle',{vehicle:api.G.you.vehicle,op});}
function drive(east,north,throttle){api.send({t:'act',a:'vehicle',vehicle:api.G.you.vehicle,op:'drive',east,north,throttle});}
export function vehicleFrame(now){
 const G=api.G;if(!G.you?.vehicle)return false;
 G.desk=[G.you.lat,G.you.lng];G.goal=null;G.route=[];G.routePending=false;
 if(now-(G.vehicleSent||0)<160)return true;
 G.vehicleSent=now;
 const car=G.vehicles?.find(v=>v.id===G.you.vehicle);
 if(!car||car.seat!==0)return true;
 let x=0,y=0,m=0;
 for(const k of G.keys){if(['KeyA','ArrowLeft'].includes(k))x--;if(['KeyD','ArrowRight'].includes(k))x++;if(['KeyW','ArrowUp'].includes(k))y--;if(['KeyS','ArrowDown'].includes(k))y++;}
 if(G.stick?.m){x=G.stick.x;y=-G.stick.y;m=G.stick.m;G.vehicleGoal=null;}
 else if(x||y){m=1;G.vehicleGoal=null;}
 let east,north;
 if(m){[east,north]=unprojectM(x,y,!!G.cam.iso);const n=Math.hypot(east,north)||1;east/=n;north/=n;}
 else if(G.vehicleGoal){
  const [lat,lng]=G.vehicleGoal;east=(lng-G.you.lng)*111320*Math.cos(G.you.lat*Math.PI/180);north=(lat-G.you.lat)*111320;
  const d=Math.hypot(east,north);if(d<3){G.vehicleGoal=null;}else{east/=d;north/=d;m=Math.min(1,d/18);}
 }
 if(G.vehicleReverse&&G.vehicleGoal){east=-east;north=-north;}
 drive(east||0,north||0,m*(G.vehicleReverse?-1:1));return true;
}
export function renderVehicles(){
 if(!api)return;const G=api.G,car=G.vehicles?.find(v=>v.id===G.you?.vehicle),seated=!!G.you?.vehicle;
 $('vehicleBar').hidden=!seated;
 $('bar').hidden=seated; // Driving buttons take the combat controls' place.
 if(!car)return;
 $('vehicleStatus').textContent=car.name+' · '+Math.round(Math.abs(car.speed)*3.6)+'km/h · Fuel '+car.fuel.toFixed(1)+'/'+car.tank+' · Hull '+Math.round(car.hull)+'%';
 $('vehicleEngine').textContent=car.engine?'Stop engine':'Start engine';
 $('vehicleEngine').disabled=car.seat!==0;$('vehicleReverse').disabled=car.seat!==0;$('vehicleBrake').disabled=car.seat!==0;
 $('vehicleReverse').setAttribute('aria-pressed',String(!!G.vehicleReverse));$('vehicleExit').disabled=Math.abs(car.speed)>.8;
}
export function vehicleHit(G,x,y){
 return (G.vehicles||[]).map(v=>{const [cx,cy]=worldPoint(G,v.lat,v.lng);return {kind:'vehicle',id:v.id,hit:Math.hypot(x-cx,y-(cy-7))};}).filter(v=>v.hit<Math.max(25,G.cam.ppm*2.5)).sort((a,b)=>a.hit-b.hit)[0];
}
export function drawVehicle(ctx,G,v){
 const P=(e,n,z=0)=>{const [x,y]=worldPoint(G,...shiftLL(v.lat,v.lng,e*Math.cos(v.heading)-n*Math.sin(v.heading),e*Math.sin(v.heading)+n*Math.cos(v.heading)));return [x,y-z];};
 const len=v.kind==='van'?2.7:2.2,width=1.05,height=Math.max(5,G.cam.ppm*.8);
 const polygon=(points,fill)=>{ctx.beginPath();for(const [i,p] of points.entries()){if(!i)ctx.moveTo(...p);else ctx.lineTo(...p);}ctx.closePath();ctx.fillStyle=fill;ctx.fill();ctx.strokeStyle='#0b1518';ctx.lineWidth=1.5;ctx.stroke();};
 ctx.save();
 polygon([P(-len,-width),P(len,-width),P(len,width),P(-len,width)],'#0b1117');
 polygon([P(-len,-width),P(len,-width),P(len,-width,height),P(-len,-width,height)],v.kind==='van'?'#66796b':'#445b70');
 polygon([P(-len,-width,height),P(len,-width,height),P(len,width,height),P(-len,width,height)],v.kind==='van'?'#9bac91':'#7898b3');
 polygon([P(-.8,-.85,height+2),P(.9,-.85,height+2),P(.9,.85,height+2),P(-.8,.85,height+2)],'#263e4b');
 if(v.hull<30){ctx.strokeStyle='#aa6658';ctx.beginPath();ctx.moveTo(...P(-1,-.6,height+3));ctx.lineTo(...P(1,.6,height+3));ctx.stroke();}
 const [x,y]=worldPoint(G,v.lat,v.lng);ctx.font='700 10px system-ui';ctx.textAlign='center';ctx.strokeStyle='#08100e';ctx.lineWidth=3;ctx.strokeText(v.name,x,y-height-G.cam.ppm-8);ctx.fillStyle='#d7e8cd';ctx.fillText(v.name,x,y-height-G.cam.ppm-8);
 ctx.restore();
}
