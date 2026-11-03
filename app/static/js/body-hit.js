// Match drawSprite's rotation about the feet, including the BODY label.
export function corpseHit(px,py,x,y,height,ratio,variant){
 const angle=variant%2===1?-1.5:1.5,dx=px-x,dy=py-y,c=Math.cos(angle),s=Math.sin(angle);
 const u=dx*c+dy*s,v=-dx*s+dy*c,w=height*ratio;
 const outside=Math.hypot(Math.max(Math.abs(u)-w/2,0),Math.max(-height-v,v,0));
 const label=Math.hypot(Math.max(Math.abs(dx)-43,0),Math.max(Math.abs(dy-12)-10,0));
 if(Math.min(outside,label)>10)return null;
 return Math.min(outside,label)+Math.hypot(u,v+height/2)*.01;
}
