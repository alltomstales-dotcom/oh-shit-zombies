// The trailer on the title screen. The card is a plain link to YouTube; a tap swaps it for the
// player in place. Nothing is fetched from YouTube before that tap, so the title still loads fast.
export const TRAILER='MRGjiGp57as';
export const trailerSrc=(id=TRAILER)=>`https://www.youtube-nocookie.com/embed/${id}?autoplay=1&playsinline=1&rel=0`;
let frame=null;
export function setupTrailer(doc=document){
 const box=doc.getElementById('trailer'),card=doc.getElementById('trailerPlay');if(!box||!card)return;
 card.addEventListener('click',(ev)=>{
  ev.preventDefault();if(frame)return;
  frame=doc.createElement('iframe');frame.src=trailerSrc();frame.title='Oh shit, Zombies. trailer';
  frame.allow='autoplay; encrypted-media; picture-in-picture; fullscreen';frame.referrerPolicy='strict-origin-when-cross-origin';
  frame.setAttribute('allowfullscreen','');
  card.hidden=true;box.classList.add('playing');box.append(frame);
 });
}
// A hidden player keeps talking: take it out when the game starts.
export function stopTrailer(doc=document){
 if(!frame)return;
 frame.remove();frame=null;
 const box=doc.getElementById('trailer'),card=doc.getElementById('trailerPlay');
 if(card)card.hidden=false;if(box)box.classList.remove('playing');
}
