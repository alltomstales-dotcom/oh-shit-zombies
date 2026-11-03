import { deltaM, shiftLL } from './map.js';

const sub=(a,b)=>[a[0]-b[0],a[1]-b[1]];
const cross=(a,b)=>a[0]*b[1]-a[1]*b[0];
function pointSeg(p,a,b){const d=sub(b,a),n=d[0]*d[0]+d[1]*d[1],t=n?Math.max(0,Math.min(1,((p[0]-a[0])*d[0]+(p[1]-a[1])*d[1])/n)):0;return Math.hypot(p[0]-a[0]-d[0]*t,p[1]-a[1]-d[1]*t);}
function segments(a,b,c,d){const ab=sub(b,a),cd=sub(d,c),det=cross(ab,cd);if(Math.abs(det)>1e-8){const t=cross(sub(c,a),cd)/det,u=cross(sub(c,a),ab)/det;if(t>=-1e-7&&t<=1+1e-7&&u>=-1e-7&&u<=1+1e-7)return 0;}return Math.min(pointSeg(a,c,d),pointSeg(b,c,d),pointSeg(c,a,b),pointSeg(d,a,b));}
export function contains(poly,ll){const p=deltaM(...poly[0],...ll),points=poly.map(v=>deltaM(...poly[0],...v));let yes=false;for(let i=0,j=points.length-1;i<points.length;j=i++){const a=points[j],b=points[i];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])yes=!yes;}return yes;}
export function buildingAt(buildings,ll){return buildings.find(b=>b.outline.length>=3&&contains(b.outline,ll));}
const barriers=b=>[...b.walls,...b.openings.filter(o=>o.barricaded||(!o.open&&!o.broken)).map(o=>[o.a,o.b])];
export function clear(buildings,start,end){
 if(buildings.some(b=>b.floor>0)&&!buildings.some(b=>b.floor>0&&contains(b.outline,end)))return false;
 const q=deltaM(...start,...end);
 for(const b of buildings){
  for(const [a,c] of barriers(b)){const p=deltaM(...start,...a),r=deltaM(...start,...c);// Leave 1cm for coordinate rounding; the server enforces the full .28m radius.
  if(segments([0,0],q,p,r)<=.27)return false;}
 }
 return true;
}
export function move(buildings,start,end){if(clear(buildings,start,end))return end;for(const p of [[start[0],end[1]],[end[0],start[1]]])if(clear(buildings,start,p))return p;return start;}
// The thumb stick's step. Blocked, it keeps the part of the step that runs along whatever blocks it,
// so a push that meets a wall slides along it and one that clips a door frame goes round the frame.
// `move` only manages that for walls square to the compass.
export function slide(buildings,start,end){
 if(clear(buildings,start,end))return end;
 const q=deltaM(...start,...end),hits=[];
 for(const b of buildings)for(const [a,c] of barriers(b)){
  const p=deltaM(...start,...a),r=deltaM(...start,...c);
  if(segments([0,0],q,p,r)>.27)continue;
  const d=sub(r,p),n=d[0]*d[0]+d[1]*d[1],t=n?Math.max(0,Math.min(1,-(p[0]*d[0]+p[1]*d[1])/n)):0,near=[p[0]+d[0]*t,p[1]+d[1]*t],far=Math.hypot(...near);
  if(far>1e-6)hits.push([far,-near[0]/far,-near[1]/far]);
 }
 for(const [,nx,ny] of hits.sort((x,y)=>x[0]-y[0])){
  const into=q[0]*nx+q[1]*ny;if(into>=0)continue;
  // a hair off the wall as it goes, so that rounding can never leave the survivor stuck to it; a push square on goes nowhere
  const x=q[0]-into*nx,y=q[1]-into*ny,off=Math.min(.001,.04*Math.hypot(x,y)),p=shiftLL(start[0],start[1],x+off*nx,y+off*ny);
  if(off<1e-6)continue;
  if(clear(buildings,start,p))return p;
 }
 return start;
}
export function entranceApproach(b,you){
 const door=b.openings.find(o=>o.label==='Entrance');if(!door)return null;
 const center=[(door.a[0]+door.b[0])/2,(door.a[1]+door.b[1])/2],d=deltaM(...door.a,...door.b),n=Math.hypot(...d);
 const options=[-2,2].map(t=>shiftLL(...center,-d[1]/n*t,d[0]/n*t));
 return options.find(p=>!contains(b.outline,p))||options[0];
}
export function drawBuildings(ctx,buildings,inside,P,ppm,iso=false){
 for(const b of buildings){
  if(b.construction){for(const [a,c] of b.walls){ctx.beginPath();ctx.moveTo(...P(...a));ctx.lineTo(...P(...c));ctx.strokeStyle="#a28b64";ctx.lineWidth=Math.max(4,ppm*.45);ctx.stroke();}continue;}
  const entered=b.id===inside,points=b.outline.map(p=>P(...p));
  ctx.save();ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.closePath();
  ctx.fillStyle=entered?'#756a50':'#4e5551';ctx.shadowColor='#111b';ctx.shadowBlur=5;ctx.fill();ctx.shadowBlur=0;
  ctx.strokeStyle='#292f2b';ctx.lineWidth=Math.max(2,.45*ppm);ctx.stroke();
  // Raised wall faces with a low cutaway inside. Ground coordinates remain the
  // collision and touch plane; this is depth shading, not an isometric camera.
  const lift=entered?Math.min(9,ppm*.5):Math.min(30,Math.max(7,ppm*2.2));
  if(!iso)for(const [a,c] of b.walls){
   const p=P(...a),q=P(...c);
   ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.lineTo(q[0],q[1]-lift);ctx.lineTo(p[0],p[1]-lift);ctx.closePath();
   ctx.fillStyle=q[0]>p[0]?'#948e77':'#6b7167';ctx.fill();
   ctx.beginPath();ctx.moveTo(p[0],p[1]-lift);ctx.lineTo(q[0],q[1]-lift);ctx.strokeStyle='#d0c6a4';ctx.lineWidth=2;ctx.stroke();
  }

  if(entered){
   for(const [a,c] of b.walls){ctx.beginPath();ctx.moveTo(...P(...a));ctx.lineTo(...P(...c));ctx.strokeStyle='#c3ba9a';ctx.lineWidth=Math.max(3,.45*ppm);ctx.stroke();}
   ctx.font='bold 10px system-ui';ctx.textAlign='center';ctx.fillStyle='#fff9';
   for(const r of b.rooms){const [x,y]=P(...r.pos);ctx.fillText(r.name,x,y-38);}
  }else{
   const x=points.reduce((n,p)=>n+p[0],0)/points.length,y=points.reduce((n,p)=>n+p[1],0)/points.length;
   ctx.font='bold 11px system-ui';ctx.textAlign='center';ctx.fillStyle='#e5e5d7';ctx.fillText(b.source==='generated'?'SHELTER':'BUILDING',x,y);
  }
  for(const o of b.openings){
   ctx.beginPath();ctx.moveTo(...P(...o.a));ctx.lineTo(...P(...o.b));
   ctx.strokeStyle=o.barricaded?'#b69463':o.curtain_closed?'#b697ba':o.broken?'#d09868':o.open?'#8bbc7a':o.kind==='window'?'#9bd1d5':'#d9ac67';
   ctx.lineWidth=Math.max(3,.5*ppm);if((o.open||o.broken)&&!o.barricaded)ctx.setLineDash([2,3]);ctx.stroke();ctx.setLineDash([]);
   if(o.barricaded){const a=P(...o.a),b=P(...o.b),dx=b[0]-a[0],dy=b[1]-a[1],n=Math.hypot(dx,dy)||1;ctx.strokeStyle='#d5ae78';ctx.lineWidth=Math.max(2,.16*ppm);for(const offset of [-.25,0,.25]){const x=-dy/n*offset*ppm,y=dx/n*offset*ppm;ctx.beginPath();ctx.moveTo(a[0]+x,a[1]+y);ctx.lineTo(b[0]+x,b[1]+y);ctx.stroke();}}
   if(o.label==='Entrance'){const [x,y]=P((o.a[0]+o.b[0])/2,(o.a[1]+o.b[1])/2);ctx.fillStyle='#ead3a0';ctx.font='bold 9px system-ui';ctx.textAlign='center';ctx.fillText(o.open?'OPEN':o.barricaded?'BOARDED':o.locked?'LOCKED':'DOOR',x,y-7);}
  }
  ctx.restore();
 }
}

// Wall faces join the same depth queue as standing actors and furniture.
export function buildingFaces(buildings,inside,P,ppm,you){
 const faces=[];
 for(const b of buildings){
  if(b.construction)continue;
  const entered=b.id===inside;
  for(const edge of [...b.walls.map(w=>({a:w[0],b:w[1]})),...b.openings.filter(o=>o.barricaded||o.curtain_closed||!o.open&&!o.broken)]){
   const a=P(...edge.a),c=P(...edge.b),h=entered?Math.min(8,ppm*.45):Math.min(80,Math.max(12,ppm*2.8));
   // Cut away a foreground face that would cover the survivor; never obscure a thumb target indoors.
   const dx=c[0]-a[0],dy=c[1]-a[1],t=dx?Math.max(0,Math.min(1,(you[0]-a[0])/dx)):.5,wallY=a[1]+dy*t;
   const covers=you[0]>=Math.min(a[0],c[0])-12&&you[0]<=Math.max(a[0],c[0])+12&&you[1]<=wallY+8&&you[1]>=wallY-h-60;
   faces.push({a,c,h:covers?Math.min(8,h):h,edge,x:(a[0]+c[0])/2,y:(a[1]+c[1])/2});
  }
 }
 return faces;
}
export function drawBuildingFace(ctx,f){
 const {a,c,h,edge}=f;ctx.save();
 const quad=(lo,hi,color)=>{ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(a[0],a[1]-lo*h);ctx.lineTo(c[0],c[1]-lo*h);ctx.lineTo(c[0],c[1]-hi*h);ctx.lineTo(a[0],a[1]-hi*h);ctx.closePath();ctx.fill();};
 quad(0,1,c[0]>a[0]?'#a69c80':'#737c70');
 if(edge.kind==='window'&&h>10){quad(.35,.8,edge.barricaded?'#a68255':edge.curtain_closed?'#b697ba':'#6aadb7');ctx.strokeStyle='#d6e4dc';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo((a[0]+c[0])/2,(a[1]+c[1])/2-h*.35);ctx.lineTo((a[0]+c[0])/2,(a[1]+c[1])/2-h*.8);ctx.stroke();}
 if(edge.kind==='door')quad(0,.87,edge.barricaded?'#9e7c50':'#785e3b');
 ctx.strokeStyle='#d9cba9';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(a[0],a[1]-h);ctx.lineTo(c[0],c[1]-h);ctx.stroke();ctx.restore();
}
