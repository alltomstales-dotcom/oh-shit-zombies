export const zoomFactor=v=>Math.max(.5,Math.min(8,Number.isFinite(v)?v:1));
// Capture canvas gestures only: a second finger on Swing/Shove still attacks.
export function installIndoorZoom(canvas,api){
 const fingers=new Map();let pinch=null,blocked=false,first=null,stick=false;
 const span=()=>{const [a,b]=[...fingers.values()];return a&&b?Math.hypot(a.x-b.x,a.y-b.y):0;};
 const consume=e=>{e.preventDefault();e.stopImmediatePropagation();};
 canvas.addEventListener('wheel',e=>{
  if(!api.enabled())return;consume(e);
  const delta=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?innerHeight:1);
  api.set(zoomFactor(api.get()*Math.exp(-Math.max(-240,Math.min(240,delta))*.0025)));
 },{capture:true,passive:false});
 canvas.addEventListener('pointerdown',e=>{
  if(e.pointerType!=='touch'||!api.enabled())return;consume(e);
  fingers.set(e.pointerId,{x:e.clientX,y:e.clientY});
  try{canvas.setPointerCapture(e.pointerId);}catch(_){}
  if(fingers.size===1&&!blocked){first={x:e.clientX,y:e.clientY};stick=api.start(e);}
  if(fingers.size===2&&!blocked){blocked=true;api.end(false);api.stop();pinch={distance:Math.max(1,span()),factor:api.get()};}
 },{capture:true,passive:false});
 canvas.addEventListener('pointermove',e=>{
  if(!fingers.has(e.pointerId))return;consume(e);fingers.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(pinch&&fingers.size>=2)api.set(zoomFactor(pinch.factor*span()/pinch.distance));
  else if(!blocked&&stick)api.move(e.clientX,e.clientY);
 },{capture:true,passive:false});
 const end=e=>{
  if(e.type==='lostpointercapture'&&blocked)return;
  if(!fingers.has(e.pointerId))return;consume(e);fingers.delete(e.pointerId);
  if(!blocked){if(stick)api.end(e.type==='pointerup');else if(e.type==='pointerup'&&Math.hypot(e.clientX-first.x,e.clientY-first.y)<12)api.tap(first.x,first.y);}
  if(!fingers.size){pinch=null;blocked=false;first=null;stick=false;}
 };
 for(const type of ['pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(type,end,{capture:true,passive:false});
}
