import {worldPoint,screenWorld} from './projection.js';
import {clear,buildingAt} from './buildings.js';
import {waitText} from './icons.js';
// Shelter work, resource gathering and construction. Server recipes are authoritative.
let api,lastKey='';
const $=id=>document.getElementById(id),make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const distance=(G,o)=>Math.hypot((o.lat-G.you.lat)*111320,(o.lng-G.you.lng)*111320*Math.cos(G.you.lat*Math.PI/180));
function button(name,fn,disabled=false){const b=make('button',name);b.onclick=fn;b.disabled=disabled;return b;}
function placeValid(G,ll){const kind=G.body.survival.recipes[G.placement?.args.recipe]?.object;if(['fence','gate','stone_wall','metal_fence'].includes(kind)&&ll&&buildingAt(G.buildings,ll))return false;return ll&&distance(G,{lat:ll[0],lng:ll[1]})<=8&&clear(G.buildings,ll,ll)&&clear(G.buildings,[G.you.lat,G.you.lng],ll)&&!G.body.survival.objects.some(o=>Math.hypot((o.lat-ll[0])*111320,(o.lng-ll[1])*111320*Math.cos(ll[0]*Math.PI/180))<1.2);}
export function setupWork(actions){api=actions;$('confirmPlacement').onclick=()=>{const G=api.G,p=G.placement;if(!p?.ll||!placeValid(G,p.ll))return;G.placement=null;$('placementNotice').hidden=true;work({...p.args,lat:p.ll[0],lng:p.ll[1],rotation:p.rotation});};$('cancelPlacement').onclick=()=>{api.G.placement=null;$('placementNotice').hidden=true;};$('rotatePlacement').onclick=()=>{if(api.G.placement)api.G.placement.rotation=(api.G.placement.rotation+90)%180;};}
export function beginPlacement(args,label){const G=api.G;api.stop();G.placement={args,label,rotation:0};$('confirmPlacement').disabled=true;api.close();$('placementNotice').hidden=false;$('placementLabel').textContent='Place '+label+' within 8m; keep exits clear. Tap the map to preview, then Build here.';}
function work(args){if(api.G.body?.base?.can_build===false){api.toast('This base grants storage access. Ask the owner for Builder access to work here.');return;}api.stop();api.fire('work',args);}
export function renderWork(){
 if(!api)return;const G=api.G,s=G.body?.survival;if(!s)return;
 const b=$('workContent');
 const needs=s.needs;$('needsSummary').textContent='Hunger '+Math.round(needs.hunger)+'% · Thirst '+Math.round(needs.thirst)+'% · Sleep debt '+Math.round(needs.sleep)+'% · '+(s.powered?'Shelter power on':'No shelter power');
 const key=JSON.stringify([G.body.base?.owner,G.body.base?.role,G.body.home?.revision,G.body.items.map(i=>[i.id,i.qty,Math.floor((i.cond||0)/(G.items[i.code]?.perishable?10:1))]),s.objects.map(o=>[o.id,o.reachable,Math.round(o.hp),o.remaining,o.open,Math.floor((o.fuel||0)/5),o.water,o.powered,o.ready&&Math.ceil((o.ready-G.serverNow)/60),o.job&&Math.ceil((o.job.ready-G.serverNow)/60)]),s.resources.map(o=>[o.id,o.remaining,Math.round(distance(G,o))]),s.defenses,G.inside,G.workAll,G.you.lantern]);
 if(key===lastKey)return;lastKey=key;b.replaceChildren();
 const jump=make('div',undefined,'work-jump');for(const [label,id] of [['Nearby','workNearby'],['Recipes','workRecipes'],['Repairs','workRepairs']])jump.append(button(label,()=>$(id).scrollIntoView({block:'start'})));b.append(jump);
 b.append(make('h3','Next shelter goal'),make('p',s.objective));
 b.append(make('p','Choose a home first. Keep materials in your pack while working; stored supplies must be retrieved. Generated trees and deposits are game resources.','fine'));
 const nearby=[...s.objects,...s.resources].sort((a,b)=>distance(G,a)-distance(G,b));
 const heading=make('h3','Nearby furniture and resources');heading.id='workNearby';b.append(heading);if(nearby.length>8)b.append(button(G.workAll?'Show closest targets':'Show all nearby targets',()=>{G.workAll=!G.workAll;renderWork();}));
 for(const o of (G.workAll?nearby:nearby.slice(0,8))){
  const d=distance(G,o),row=make('div',undefined,'work-row');row.dataset.object=o.id;
  const status=o.remaining!==undefined?o.remaining+' gathers left':(o.hp!==undefined?Math.round(o.hp)+' durability':'');
  row.append(make('b',o.name+' · '+Math.round(d)+'m'),make('p',status+(['garden','plot'].includes(o.kind)?(o.ready<=G.serverNow?' · ready to harvest':' · ready in '+waitText(o.ready-G.serverNow)):'')+(o.job?' · '+o.job.name.split(' (')[0]+(o.job.ready<=G.serverNow?': ready to collect':': '+waitText(o.job.ready-G.serverNow)+' left'):'')+(o.kind==='generator'?' · '+Math.round(o.fuel||0)+'s fuel':'')+(o.kind==='rainbarrel'?' · '+(o.water||0)+' water':'')+(o.kind==='fridge'?' · '+(o.powered?'Cooling · food lasts 10× longer':'No power · ordinary storage'):''),'fine'));
  const actions=make('div',undefined,'item-actions');row.append(actions);
  actions.append(button('Walk here',()=>{api.close();api.walk([o.lat,o.lng]);}));
  const ops={tree:[['Chop','chop']],rock:[['Mine stone','mine']],ore:[['Mine ore','mine']],rubble:[['Scavenge materials','forage']],forage:[['Forage','forage']],pond:[['Fish','fish']],bed:[['Rest','rest'],['Dismantle','salvage']],wardrobe:[['Dismantle','salvage']],counter:[['Dismantle','salvage']],chair:[['Dismantle','salvage']],crate:[['Dismantle','salvage']],workbench:[['Dismantle','salvage']],rainbarrel:[['Collect water','collect']],garden:[['Harvest','harvest']],plot:[['Harvest','harvest'],['Dismantle','salvage']],generator:[['Fuel','fuel'],['Power '+(o.on?'off':'on'),'toggle']],gate:[['Gate '+(o.open?'close':'open'),'open_gate'],['Dismantle','salvage']],fence:[['Dismantle','salvage']],stone_wall:[['Dismantle','salvage']],metal_fence:[['Dismantle','salvage']]}[o.kind]||[];
  for(const [label,op] of ops)actions.append(button(label,()=>work({op,object:o.id}),d>2.7||o.remaining===0||(o.hp===0&&op!=='salvage')||(op==='harvest'&&o.ready>G.serverNow)));
  if(o.job)actions.append(button('Collect',()=>work({op:'take',object:o.id}),d>2.7||o.job.ready>G.serverNow));
  if(o.hp!==undefined){actions.append(button('Repair',()=>work({op:'repair',object:o.id}),d>2.7));if(!['fence','gate','stone_wall','metal_fence'].includes(o.kind))actions.append(button('Move',()=>beginPlacement({op:'move',object:o.id},o.name),d>2.7));}
  b.append(row);
 }
 const inside=G.buildings.find(b=>b.id===G.inside);
 if(inside){b.append(make('h3','Door and window defenses'));for(const o of inside.openings){
  const row=make('div',undefined,'work-row'),hp=s.defenses?.[o.id]?.hp||0;row.append(make('b',o.label+' · barricade '+Math.round(hp)+'/80'));const a=make('div',undefined,'item-actions');row.append(a);
  for(const [label,op] of [['Barricade','barricade'],['Repair defense','repair_opening'],['Remove barricade','remove_barricade']])a.append(button(label,()=>work({op,opening:o.id})));b.append(row);
 }}
 const recipesHeading=make('h3','Recipes');recipesHeading.id='workRecipes';b.append(recipesHeading);
 for(const [id,r] of Object.entries(s.recipes)){
  const row=make('div',undefined,'work-row');row.dataset.recipe=id;if(r.locked)row.append(make('p','Learn from '+r.learn_from,'fine'));
  const parts=Object.entries(r.need).map(([c,n])=>n+' '+(G.items[c]?.name||c));let missing=false;for(const [c,n] of Object.entries(r.need))if(G.body.items.filter(i=>i.code===c&&(!G.items[c]?.perishable||(i.cond||0)>0)).reduce((n,i)=>n+i.qty,0)<n)missing=true;
  const missingTool=r.tool&&!G.body.items.some(i=>i.code===r.tool&&(i.cond||0)>0),missingBench=r.bench&&!s.objects.some(o=>o.kind===r.bench&&o.reachable&&o.hp>0);const output=r.out?Object.entries(r.out).map(([c,n])=>n+' '+(G.items[c]?.name||c)).join(', '):'new structure';
  row.append(make('b',r.name),make('p',parts.join(' + ')+' → '+output+(r.tool?' · tool: '+G.items[r.tool].name:'')+(r.bench?' · beside '+r.bench:'')+' · '+r.seconds+'s'+(missingTool?' · Missing tool':'')+(missingBench?' · Approach the workstation':''),'fine'));
  row.append(button(r.object?'Place / build':'Craft',()=>r.object?beginPlacement({op:'craft',recipe:id},r.name):work({op:'craft',recipe:id}),r.locked||missing||missingTool||missingBench||!G.body.home));b.append(row);
 }
 // Slow jobs a station does alone on the real clock; started here, collected at the station.
 for(const [id,r] of Object.entries(s.slow||{})){
  const row=make('div',undefined,'work-row');row.dataset.slow=id;
  const station=s.objects.find(o=>o.kind===r.bench&&o.reachable&&o.hp>0&&!o.job),busy=s.objects.some(o=>o.kind===r.bench&&o.reachable&&o.job);
  let missing=false;for(const [c,n] of Object.entries(r.need))if(G.body.items.filter(i=>i.code===c&&(!G.items[c]?.perishable||(i.cond||0)>0)).reduce((n,i)=>n+i.qty,0)<n)missing=true;
  row.append(make('b',r.name),make('p',Object.entries(r.need).map(([c,n])=>n+' '+(G.items[c]?.name||c)).join(' + ')+' → '+Object.entries(r.out).map(([c,n])=>n+' '+(G.items[c]?.name||c)).join(', ')+' · beside '+r.bench+' · takes '+waitText(r.seconds)+', also while the game is closed'+(busy&&!station?' · Collect what is on it first':!station?' · Approach the workstation':''),'fine'));
  row.append(button('Start',()=>work({op:'slow',recipe:id,object:station.id}),missing||!station||!G.body.home));b.append(row);
 }
 const repairsHeading=make('h3','Equipment repairs');repairsHeading.id='workRepairs';b.append(repairsHeading);
 for(const i of G.body.items.filter(i=>['clothing','bag','tool','weapon','gun'].includes(G.items[i.code]?.kind)&&i.cond!=null&&i.cond<(G.items[i.code]?.cond||10))){b.append(button('Repair '+G.items[i.code].name,()=>work({op:'repair_gear',item:i.id})));}
 if(G.body.items.some(i=>i.code==='lantern'))b.append(button('Lantern '+(G.you.lantern?'off':'on'),()=>api.fire('light')));
}
export function drawWork(ctx,P,ppm,objects=null,placement=true){
 const G=api?.G,s=G?.body?.survival;if(!s)return;
 for(const o of objects||[...s.resources,...s.objects]){
  if(distance(G,o)>160)continue;const [x,y]=P(o.lat,o.lng),size=Math.max(15,Math.min(36,ppm*1.3));ctx.save();ctx.globalAlpha=o.remaining===0||o.hp===0?.35:1;
  const symbol=o.symbol||{tree:'♣',rock:'◆',ore:'◆',rubble:'▧',forage:'❀',pond:'≈'}[o.kind]||'▣';
  ctx.translate(x,y-12);ctx.shadowColor='#050a08aa';ctx.shadowBlur=5;
  if(o.kind==='tree'){
   ctx.fillStyle='#6c4b32';ctx.fillRect(-size*.1,-size*.1,size*.2,size*.8);
   for(const [dx,dy,r,color] of [[0,-.6,.57,'#294c34'],[-.3,-.45,.4,'#3a6940'],[.25,-.55,.4,'#52804a'],[-.05,-.8,.3,'#6b9656']]){ctx.fillStyle=color;ctx.beginPath();ctx.arc(dx*size,dy*size,r*size,0,Math.PI*2);ctx.fill();}
  }else if(['rock','ore','rubble'].includes(o.kind)){
   ctx.fillStyle=o.kind==='ore'?'#8d7965':'#858b83';ctx.beginPath();ctx.moveTo(-size*.6,size*.15);ctx.lineTo(-size*.35,-size*.5);ctx.lineTo(size*.15,-size*.65);ctx.lineTo(size*.6,-size*.25);ctx.lineTo(size*.45,size*.25);ctx.closePath();ctx.fill();
   ctx.fillStyle=o.kind==='ore'?'#d39661':'#b9bcaa';ctx.fillRect(-size*.12,-size*.35,size*.2,size*.13);ctx.fillRect(size*.24,-size*.1,size*.14,size*.12);
  }else if(o.kind==='bed'){
   ctx.fillStyle='#745737';ctx.fillRect(-size*.45,-size*.65,size*.9,size*1.3);ctx.fillStyle='#bac6ba';ctx.fillRect(-size*.35,-size*.55,size*.7,size*1.05);ctx.fillStyle='#dddccd';ctx.fillRect(-size*.3,-size*.5,size*.6,size*.28);ctx.fillStyle='#547b79';ctx.fillRect(-size*.35,-size*.05,size*.7,size*.58);
  }else if(o.kind==='pond'){
   ctx.fillStyle='#375d69';ctx.beginPath();ctx.ellipse(0,0,size*.8,size*.45,0,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#7cb4bc';ctx.beginPath();ctx.ellipse(0,0,size*.5,size*.2,0,0,Math.PI*2);ctx.stroke();
  }else if(o.kind==='plot'){
   // the day-long plot: a wider bed in two rows, bare soil until it is ready
   const grown=o.ready<=G.serverNow;ctx.fillStyle='#5d4630';ctx.fillRect(-size*.8,-size*.5,size*1.6,size);ctx.strokeStyle='#3d2e20';ctx.lineWidth=1.5;ctx.strokeRect(-size*.8,-size*.5,size*1.6,size);
   for(const ry of [-.22,.22])for(let i=-2;i<=2;i++){ctx.fillStyle=grown?'#7fbf5a':'#4d6b3c';ctx.beginPath();ctx.ellipse(i*size*.3,ry*size,size*(grown?.13:.06),size*(grown?.2:.09),-.3,0,Math.PI*2);ctx.fill();}
  }else if(o.kind==='forage'||o.kind==='garden'){
   ctx.fillStyle='#695037';ctx.fillRect(-size*.6,-size*.35,size*1.2,size*.7);for(let i=-1;i<=1;i++){ctx.fillStyle='#6ea653';ctx.beginPath();ctx.ellipse(i*size*.32,-size*.12,size*.17,size*.3,-.3,0,Math.PI*2);ctx.fill();}
  }else{
   ctx.fillStyle=['generator','fridge','furnace'].includes(o.kind)?'#747c74':'#997b53';ctx.fillRect(-size*.45,-size*.5,size*.9,size*.8);ctx.strokeStyle='#3d3327';ctx.lineWidth=2;ctx.strokeRect(-size*.45,-size*.5,size*.9,size*.8);ctx.fillStyle='#e2ce9d';ctx.font='900 '+size*.65+'px system-ui';ctx.textAlign='center';ctx.fillText(symbol,0,size*.05);
  }
  ctx.shadowBlur=0;ctx.setTransform(1,0,0,1,0,0);ctx.restore();ctx.save();
  if(G.selection?.id===o.id){ctx.font='700 10px system-ui';ctx.textAlign='center';ctx.fillStyle='#e8e9db';ctx.fillText(o.name,x,y+18);}ctx.restore();
 }
 if(placement&&G.placement){const ll=G.placement.ll||G.desk,[x,y]=P(...ll);ctx.save();ctx.strokeStyle=G.placement.ll&&placeValid(G,ll)?'#8cdfab':'#e47768';ctx.setLineDash([4,3]);ctx.lineWidth=3;ctx.translate(x,y);ctx.rotate(-(G.placement.rotation||0)*Math.PI/180);const kind=s.recipes[G.placement.args.recipe]?.object;if(['fence','gate','stone_wall','metal_fence'].includes(kind)){ctx.beginPath();ctx.moveTo(-1.3*ppm,0);ctx.lineTo(1.3*ppm,0);ctx.stroke();}else ctx.strokeRect(-.6*ppm,-.6*ppm,1.2*ppm,1.2*ppm);ctx.restore();}
}
export function tapWork(x,y){
 const G=api?.G,s=G?.body?.survival;if(!s)return false;
 const origin=G.screenOrigin||[innerWidth/2,innerHeight*.46],ll=G.screenLL||G.desk;
 if(G.placement){const [lat,lng]=screenWorld(G,x,y);const h=G.body.home,mx=111320*Math.cos(h.lat*Math.PI/180);G.placement.ll=[h.lat+Math.floor((lat-h.lat)*111320+.5)/111320,h.lng+Math.floor((lng-h.lng)*mx+.5)/mx];$('confirmPlacement').disabled=!placeValid(G,G.placement.ll);return true;}
 const hit=hitWork(x,y);
 if(hit){api.select({kind:'object',id:hit.id});return true;}return false;
}
export function hitWork(x,y){
 const G=api?.G,s=G?.body?.survival;if(!s||!G.desk)return null;
 const origin=G.screenOrigin||[innerWidth/2,innerHeight*.46],ll=G.screenLL||G.desk;
 return [...s.objects,...s.resources].map(o=>{const p=worldPoint(G,o.lat,o.lng);return {...o,hit:Math.hypot(x-p[0],y-p[1]+15)};}).filter(o=>o.hit<23).sort((a,b)=>a.hit-b.hit)[0]||null;
}
