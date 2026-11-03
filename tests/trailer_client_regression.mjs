import assert from 'node:assert/strict';
import {TRAILER,trailerSrc,setupTrailer,stopTrailer} from '../app/static/js/trailer.js';
const src=new URL(trailerSrc());
assert.equal(src.origin+src.pathname,'https://www.youtube-nocookie.com/embed/'+TRAILER);
assert.equal(src.searchParams.get('autoplay'),'1');assert.equal(src.searchParams.get('playsinline'),'1');assert.equal(src.searchParams.get('rel'),'0');

// A stand-in page: just enough of the document for the card to be tapped.
const el=(tag)=>({tag,hidden:false,kids:[],on:{},set:new Set(),append(k){this.kids.push(k);k.up=this;},remove(){this.up.kids=this.up.kids.filter((k)=>k!==this);},
 addEventListener(n,f){this.on[n]=f;},setAttribute(n,v){this[n]=v;},classList:null});
const box=el('div'),card=el('a'),made=[];box.append(card);
for(const e of [box,card])e.classList={add:(c)=>e.set.add(c),remove:(c)=>e.set.delete(c)};
const doc={getElementById:(id)=>({trailer:box,trailerPlay:card})[id],createElement:(tag)=>{const e=el(tag);made.push(e);return e;}};
setupTrailer(doc);
assert.equal(made.length,0,'nothing from YouTube before the tap');
let stopped=false;card.on.click({preventDefault(){stopped=true;}});
assert(stopped,'the tap plays here and does not leave the page');
assert.equal(made.length,1);assert.equal(made[0].tag,'iframe');assert.equal(made[0].src,trailerSrc());
assert(/autoplay/.test(made[0].allow)&&/fullscreen/.test(made[0].allow));assert.equal(made[0].referrerPolicy,'strict-origin-when-cross-origin');
assert(card.hidden&&box.kids.includes(made[0])&&box.set.has('playing'));
card.on.click({preventDefault(){}});assert.equal(made.length,1,'a second tap does not stack a second player');
stopTrailer(doc);
assert(!card.hidden&&!box.kids.includes(made[0])&&!box.set.has('playing'),'starting the game removes the player, so its sound stops');
stopTrailer(doc);
console.log('The title trailer loads only when tapped, plays in place and is removed when the game starts.');
