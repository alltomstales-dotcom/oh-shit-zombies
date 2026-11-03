// The rendered raised opening face, with the same generous touch margin as its ground edge.
const segment=(x,y,a,b)=>{const dx=b[0]-a[0],dy=b[1]-a[1],t=Math.max(0,Math.min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy||1)));return Math.hypot(x-a[0]-dx*t,y-a[1]-dy*t);};
export function openingHit(x,y,a,b,height=0){
 const q=[a,b,[b[0],b[1]-height],[a[0],a[1]-height]];
 let inside=false;
 for(let i=0,j=q.length-1;i<q.length;j=i++)if((q[i][1]>y)!==(q[j][1]>y)&&x<(q[j][0]-q[i][0])*(y-q[i][1])/(q[j][1]-q[i][1])+q[i][0])inside=!inside;
 const d=inside?0:Math.min(...q.map((p,i)=>segment(x,y,p,q[(i+1)%q.length])));
 return d<18?d:null;
}

export const isWindowOpening=o=>o.openingKind==='window'||o.kind==='window';
