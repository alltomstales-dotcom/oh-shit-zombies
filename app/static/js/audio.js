// Recorded Foley and voices; provenance is in /assets/audio/CREDITS.txt.
const CLIPS={"footStreet":["footStreet_0.mp3","footStreet_1.mp3","footStreet_2.mp3"],"footInside":["footInside_0.mp3","footInside_1.mp3","footInside_2.mp3"],"swing":["swing_0.mp3","swing_1.mp3"],"hit":["hit_0.mp3","hit_1.mp3","hit_2.mp3"],"soft":["soft_0.mp3","soft_1.mp3"],"wood":["wood_0.mp3","wood_1.mp3"],"glass":["glass_0.mp3","glass_1.mp3"],"doorOpen":["doorOpen_0.mp3","doorOpen_1.mp3"],"doorClose":["doorClose_0.mp3","doorClose_1.mp3"],"rustle":["rustle_0.mp3","rustle_1.mp3"],"click":["click_0.mp3"],"found":["found_0.mp3"],"hurt":["hurt_0.mp3","hurt_1.mp3","hurt_2.mp3"],"scream":["scream_0.mp3","scream_1.mp3"],"death":["death_0.mp3","death_1.mp3"],"zedDeath":["zedDeath_0.mp3","zedDeath_1.mp3"],"zedAttack":["zedAttack_0.mp3","zedAttack_1.mp3"],"groan":["groan_0.mp3","groan_1.mp3","groan_2.mp3"],"shot":["shot_0.mp3"]};
let ctx=null,master=null,muted=false,loading=null;
const buffers=new Map(),last=new Map(),active=new Set();
const stats={loaded:0,failed:0,played:0,lastGroup:null};
export function audioStatus(){return {...stats,expected:Object.values(CLIPS).flat().length,state:ctx?.state||'uninitialized',voices:active.size};}
export function initAudio(){
 if(ctx){if(ctx.state==='suspended')ctx.resume().catch(()=>{});return;}
 const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;
 ctx=new AC();
 master=ctx.createGain();master.gain.value=muted?0:.6;
 const limiter=ctx.createDynamicsCompressor();limiter.threshold.value=-16;limiter.knee.value=20;limiter.ratio.value=6;limiter.attack.value=.003;limiter.release.value=.18;
 master.connect(limiter);limiter.connect(ctx.destination);
 const files=Object.values(CLIPS).flat();let index=0;
 async function worker(){while(index<files.length){const name=files[index++];try{
  const response=await fetch('/assets/audio/'+name);if(!response.ok)throw Error('audio '+response.status);
  buffers.set(name,await ctx.decodeAudioData(await response.arrayBuffer()));stats.loaded++;
 }catch(_){stats.failed++;}}}
 loading=Promise.all(Array.from({length:4},worker));
}
export async function audioReady(){initAudio();await loading;return audioStatus();}
export function setMuted(m){muted=m;if(master)master.gain.setTargetAtTime(m?0:.6,ctx.currentTime,.025);}
export function isMuted(){return muted;}
function output(pan,gain){
 const node=ctx.createGain();node.gain.value=gain;let p=null;
 if(ctx.createStereoPanner){p=ctx.createStereoPanner();p.pan.value=Math.max(-1,Math.min(1,pan));node.connect(p);p.connect(master);}
 else node.connect(master);
 node.cleanup=()=>{node.disconnect();if(p)p.disconnect();};return node;
}
function sample(group,gain=.5,pan=0,rate=1){
 if(!ctx||muted||ctx.state!=='running'||active.size>=12)return;
 const choices=(CLIPS[group]||[]).filter(name=>buffers.has(name));if(!choices.length)return;
 const pool=choices.filter(name=>name!==last.get(group));const names=pool.length?pool:choices;
 const name=names[Math.floor(Math.random()*names.length)];last.set(group,name);
 const source=ctx.createBufferSource();source.buffer=buffers.get(name);
 source.playbackRate.value=rate*(.97+Math.random()*.06);
 const gainNode=output(pan,gain*(.93+Math.random()*.14));source.connect(gainNode);
 active.add(source);source.onended=()=>{active.delete(source);source.disconnect();gainNode.cleanup();};source.start();
 stats.played++;stats.lastGroup=group;
}
function pulse(frequency,duration,gain,delay=0){
 if(!ctx||muted||ctx.state!=='running')return;const t=ctx.currentTime+delay,o=ctx.createOscillator(),g=output(0,0);
 o.type='sine';o.frequency.value=frequency;g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(gain,t+.015);g.gain.exponentialRampToValueAtTime(.0001,t+duration);
 o.connect(g);o.onended=()=>{o.disconnect();g.cleanup();};o.start(t);o.stop(t+duration);
}
export const sfx={
 scream(){sample('scream',.8);},
 swing(){sample('swing',.45);},
 whiff(){}, // The swing already played its air movement.
 thwack(){sample('hit',.7);},
 finish(){sample('hit',.85);sample('wood',.25,0,.85);},
 shove(){sample('soft',.45);},
 kill(){sample('zedDeath',.5);},
 shot(){sample('shot',.8);},
 click(){sample('click',.1);},
 hurt(){sample('hurt',.6);},
 bite(){sample('hurt',.75);sample('hit',.3);},
 grab(){sample('zedAttack',.4);sample('rustle',.3);},
 sting(){sample('wood',.15,0,.75);},
 free(){sample('rustle',.4);},
 ok(){sample('found',.2);},
 found(){sample('found',.35);sample('rustle',.2);},
 broke(){sample('wood',.6);},
 death(){sample('death',.8);},
 groan(pan=0,vol=.3,loud=false){sample(loud?'zedAttack':'groan',Math.min(.65,vol*1.2),pan,loud?1:.95);},
 glass(pan=0){sample('glass',.65,pan);},
 crash(pan=0){sample('wood',.5,pan);},
 alarm(pan=0){sample('click',.1,pan);},
 // rotor blades: a few seconds of low thumps, repeated by the caller while it is in earshot
 heli(vol=.1){for(let i=0;i<26;i++)pulse(58+(i%2)*7,.08,vol,i*.105);},
 dog(){}, // No imitation bark; the distant event still has its visual sound marker.
 door(open){sample(open?'doorOpen':'doorClose',.45);},
 search(){sample('rustle',.35);},
 step(inside,sprint=false){sample(inside?'footInside':'footStreet',sprint?.3:.19,0,sprint?1.08:1);}
};
let beatTimer=null,beatLevel=0,onBeat=null;
export function setHeart(level,cb){
 beatLevel=level;onBeat=cb;
 if(level<=.05){if(beatTimer){clearTimeout(beatTimer);beatTimer=null;}return;}
 if(!beatTimer)beat();
}
function beat(){
 if(beatLevel<=.05){beatTimer=null;return;}
 const bpm=62+beatLevel*88,vol=.035+beatLevel*.12;
 pulse(58,.13,vol);pulse(48,.12,vol*.6,.16);if(onBeat)onBeat(beatLevel);
 beatTimer=setTimeout(beat,60000/bpm);
}
export function buzz(pattern){try{if(!muted&&navigator.vibrate)navigator.vibrate(pattern);}catch(_){}}
document.addEventListener('visibilitychange',()=>{if(!ctx)return;if(document.hidden){for(const source of active){try{source.stop();}catch(_){}}ctx.suspend().catch(()=>{});}else ctx.resume().catch(()=>{});});
