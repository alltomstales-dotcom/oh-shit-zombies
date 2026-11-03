// World selection and small drawers: the street and combat controls stay usable.
import {floorName,homeApproach} from './home-navigation.js';
import {deltaM,shiftLL} from './map.js';
import {worldPoint} from './projection.js';
import {clear,buildingFaces} from './buildings.js';
import {openingHit,isWindowOpening} from './opening-hit.js';
import {itemIcon,waitText} from './icons.js';

let api,cardKey='',drawerKey='';
export const HOME_MARKER_OFFSET_X=-38; // Home and a room shelf can occupy the same world point.
const $=id=>document.getElementById(id);
const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
const distance=o=>Math.hypot(...deltaM(api.G.you.lat,api.G.you.lng,o.lat,o.lng));
function button(label,fn,disabled=false){const e=make('button',label);e.onclick=fn;e.disabled=disabled;return e;}
function work(args){if(api.G.body?.base?.can_build===false){api.toast('This base grants storage access. Ask the owner for Builder access to work here.');return;}api.stop();api.fire('work',args);}

export function setupWorldUI(actions){
 api=actions;
 $('worldClose').onclick=()=>selectWorld(null);
 $('drawerClose').onclick=()=>{$('sceneDrawer').hidden=true;api.G.drawer=null;renderWorldUI();};
 $('drawerExpand').onclick=()=>{$('sceneDrawer').classList.toggle('expanded');$('drawerExpand').textContent=$('sceneDrawer').classList.contains('expanded')?'Collapse':'Expand';};
 $('panelExpand').onclick=()=>{$('panel').classList.toggle('expanded');$('panelExpand').textContent=$('panel').classList.contains('expanded')?'Collapse':'Expand';};
 $('bInteract').onclick=()=>{api.stop();openSceneDrawer('nearby','');};
 $('qStore').onclick=()=>{
  const G=api.G,h=G.body?.home;if(!h)return;
  const candidates=[{...h,id:'',kind:'home'},...(h.containers||[]).filter(c=>!c.building||c.building===h.building)];
  const target=candidates.sort((a,b)=>Number(b.reachable)-Number(a.reachable)||distance(a)-distance(b))[0];
  api.stop();selectWorld({kind:target.id?'object':'home',id:target.id||'home'});openSceneDrawer('storage',target.id);
 };
 for(const [id,pane] of [['storageDeposit','deposit'],['storageWithdraw','withdraw']])$(id).onclick=()=>{api.G.storagePane=pane;drawerKey='';renderWorldUI();};
 $('drawerQty').oninput=()=>{drawerKey='';renderWorldUI();};
 $('channelCancel').onclick=()=>api.fire('cancel');
 $('qWater').onclick=()=>quickUse('drink');$('qFood').onclick=()=>quickUse('food');
 $('qBandage').onclick=()=>{const w=api.G.body?.wounds.find(w=>w.bleeding&&!w.bandaged);if(w)api.press('bandage');else{api.G.packTab='status';api.openPack();}};
 $('qWeapon').onclick=()=>{api.G.packTab='pack';api.openPack();$('inventoryFilter').value='gear';api.renderPack();};
 $('qBuild').onclick=()=>{api.G.workFocus=null;api.G.packTab='work';api.openPack();};
 for(const [id,kind] of [['qWeapon','weapon'],['qWater','drink'],['qFood','food'],['qBandage','medical'],['qBuild','tool']])$(id).replaceChildren(itemIcon(kind),make('span',''));
}
function quickUse(kind){
 const G=api.G,items=G.body?.items.filter(i=>G.items[i.code]?.kind===kind&&(!G.items[i.code].perishable||i.cond>0))||[];
 if(items.length===1)api.press('use',null,{code:items[0].code});
 else if(items.length){openSceneDrawer('quick',kind);}else api.toast(kind==='drink'?'Find drinking water.':'Find food.');
}
export function selectWorld(selection){
 const G=api.G;G.selection=selection;cardKey='';
 if(selection){$('sceneDrawer').hidden=true;$('panel').hidden=true;G.drawer=null;}
 for(const tip of document.querySelectorAll('.toast.tip'))tip.remove();
 if(selection?.kind==='stash')G.selectedStash=selection.id;
 else G.selectedStash=null;
 renderWorldUI();
}
export function openSceneDrawer(mode,id){
 const G=api.G;G.drawer={mode,id};if(mode==='storage')G.storagePane='deposit';drawerKey='';$('panel').hidden=true;
 for(const tip of document.querySelectorAll('.toast.tip'))tip.remove();
 $('sceneDrawer').classList.remove('expanded');$('drawerExpand').textContent='Expand';
 $('sceneDrawer').hidden=false;renderWorldUI();
}
export function collapseWorldUI(reason){
 if(!api)return;
 for(const id of ['panel','sceneDrawer']){$(id).hidden=true;$(id).classList.remove('expanded');}
 api.G.drawer=null;
 if(reason==='movement'){api.G.selection=null;$('worldCard').hidden=true;cardKey='';}
 if(reason==='attack')api.toast('Under attack — move or shove!', 'bad');
}
function selected(){
 const G=api.G,s=G.selection;if(!s)return null;
 if(s.kind==='vehicle'){const v=G.vehicles?.find(v=>v.id===s.id);return v?{...v,vehicleKind:v.kind,kind:'vehicle'}:null;}
 if(s.kind==='stash'){
  const st=G.stashes.find(x=>x[0]===s.id);if(!st)return null;
  return {id:st[0],lat:st[1],lng:st[2],name:api.containerName(st),kind:'stash',searched:st[4],reachable:st[7],room:st[6],shelf:G.lootShelves?.find(x=>x.id===s.id)};
 }
 if(s.kind==='opening'){
  const o=G.buildings.flatMap(b=>b.openings).find(o=>o.id===s.id);
  return o?{...o,lat:(o.a[0]+o.b[0])/2,lng:(o.a[1]+o.b[1])/2,name:o.label,openingKind:o.kind,kind:'opening'}:null;
 }
 if(s.kind==='stairs'){
  const b=G.buildings.find(b=>b.id===s.id);return b?.stairs?{id:b.id,kind:'stairs',name:'Stairs · '+(G.you.floor?'Floor '+(G.you.floor+1):'Ground floor'),lat:b.stairs[0],lng:b.stairs[1],floors:b.floors}:null;
 }
 if(s.kind==='home'){const h=G.body?.home;return h?{...h,id:'home',name:h.name+' · '+floorName(h.floor_level),kind:'home'}:null;}
 if(s.kind==='corpse'){
  const b=G.corpses.find(b=>b.id===s.id);if(!b)return null;
  const look=b.kind==='shambler'?{1:'Medical worker',2:'Construction worker',4:'Chef',14:'Firefighter'}[b.variant%16]:null;
  return {...b,name:b.kind==='survivor'?(b.own?'Your recovery pack':(b.name||'Survivor')+' recovery pack'):(look||'Zombie')+' body',kind:'corpse'};
 }
 return [...(G.body?.survival.objects||[]),...(G.body?.survival.resources||[])].find(o=>o.id===s.id);
}
function approach(o){
 const G=api.G;collapseWorldUI('movement');
 if(o.kind==='stash'){api.approachContainer(G.stashes.find(s=>s[0]===o.id));return;}
 let goal=[o.lat,o.lng];
 if(o.kind==='home'){const plan=homeApproach(G,o);if(plan.mode==='stairs'){selectWorld({kind:'stairs',id:plan.building});api.toast('Home is on '+floorName(o.floor_level)+'. Take the stairs.');return;}if(plan.mode==='exit'){api.toast('Exit this building first, then approach home.');return;}goal=plan.goal;}
 if(o.kind==='opening'){
  const [dx,dy]=deltaM(...o.a,...o.b),n=Math.hypot(dx,dy)||1;
  const options=[1,-1].map(sign=>shiftLL(o.lat,o.lng,-dy/n*sign,dx/n*sign));
  goal=options.sort((a,b)=>Math.hypot(...deltaM(...G.desk,...a))-Math.hypot(...deltaM(...G.desk,...b))).find(ll=>clear(G.buildings,ll,ll))||goal;
 }
 api.walk(goal);api.toast('Approaching '+o.name+'. Start the action when you arrive.');
}
function objectActions(o){
 const G=api.G,d=distance(o);
 let reachable=o.reachable??(d<=2.7&&clear(G.buildings,[G.you.lat,G.you.lng],[o.lat,o.lng]));
 if(o.kind==='opening'){
  const [ax,ay]=deltaM(G.you.lat,G.you.lng,...o.a),[bx,by]=deltaM(G.you.lat,G.you.lng,...o.b),dx=bx-ax,dy=by-ay;
  const t=Math.max(0,Math.min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy||1)));
  reachable=Math.hypot(ax+dx*t,ay+dy*t)<=2.7;
 }
 const out=[];
 if(!reachable)out.push([o.kind==='home'&&(o.floor_level||0)!==(G.you.floor||0)&&G.inside===o.building?'Find stairs':'Approach',()=>approach(o)]);
 if(o.kind==='vehicle'){
  out.push(['Drive',()=>api.fire('vehicle',{vehicle:o.id,op:'enter_driver'}),!reachable||!o.can_drive]);
  out.push(['Cargo',()=>openSceneDrawer('cargo',o.id),!o.allowed]);
  out.push(['More',()=>openSceneDrawer('vehicle',o.id)]);
  return [...out.filter(x=>x[0]!=='More').slice(0,2),out.find(x=>x[0]==='More')];
 }else if(o.kind==='television'){
  out.push(['Watch / learn',()=>openSceneDrawer('media',o.id),!reachable]);out.push(['More',()=>openSceneDrawer('object',o.id)]);
 }else if(o.kind==='radio'){
  out.push(['Listen',()=>api.fire('radio',{object:o.id}),!reachable]);out.push(['More',()=>openSceneDrawer('object',o.id)]);
 }else if(o.kind==='stash'){
  if(!o.searched)out.push(['Search',()=>{api.stop();api.fire('search',{stash:o.id});},!reachable||!!G.channel]);
  else out.push(['Look inside',()=>openSceneDrawer('loot',o.id)]);
 }else if(o.kind==='corpse'){
  if(!o.searched&&o.can_loot!==false)out.push([o.own?'Recover gear':'Search body',()=>{api.stop();api.fire('search_body',{corpse:o.id});},!reachable||!!G.channel]);
  else out.push(['Look inside',()=>openSceneDrawer('bodyloot',o.id)]);
 }else if(o.kind==='opening'){
  if(isWindowOpening(o)&&o.broken&&!o.barricaded){
   if(!o.glass_cleared)out.push(['Clear glass',()=>{api.stop();api.fire('window',{opening:o.id,op:'clear'});},!reachable||!!G.channel]);
   if(!G.you.floor&&!o.curtain_closed)out.push(['Climb through',()=>{api.stop();api.fire('window',{opening:o.id,op:'vault'});},!reachable||!!G.channel]);
  }
  if(!o.broken&&!o.barricaded)out.push([o.open?'Close':'Open',()=>api.fire('opening',{opening:o.id,op:o.open?'close':'open'}),!reachable]);
  // Knock before opening: what is inside answers by sound only.
  if(reachable&&!o.open&&!o.broken)out.push(['Knock',()=>api.fire('opening',{opening:o.id,op:'knock'})]);
  if(o.broken&&!isWindowOpening(o))out.push(['Broken open',()=>{},true]);
  out.push(['More',()=>openSceneDrawer('opening',o.id)]);
 }else if(o.kind==='stairs'){
  if(G.you.floor>0)out.push(['Downstairs',()=>{api.stop();api.fire('stairs',{op:'down'});},!reachable]);
  if((G.you.floor||0)<o.floors-1)out.push(['Upstairs',()=>{api.stop();api.fire('stairs',{op:'up'});},!reachable]);
 }else if(o.kind==='home'){
  out.push(['Open cupboard',()=>openSceneDrawer('storage','')]);
  out.push(['Sharing',()=>{G.packTab='home';api.openPack();$('baseSharing').open=true;$('baseSharing').scrollIntoView({block:'nearest'});}]);
 }
 else {
  const ops={tree:[['Chop','chop']],rock:[['Mine stone','mine']],ore:[['Mine ore','mine']],rubble:[['Scavenge','forage']],forage:[['Forage','forage']],pond:[['Fish','fish']],bed:[['Rest','rest']],rainbarrel:[['Collect water','collect']],garden:[['Harvest','harvest']],plot:[['Harvest','harvest']],generator:[['Fuel','fuel'],[o.on?'Power off':'Power on','toggle']],gate:[[o.open?'Close gate':'Open gate','open_gate']]}[o.kind]||[];
  for(const [label,op] of ops)out.push([label,()=>work({op,object:o.id}),!reachable||o.remaining===0||o.hp===0||(op==='harvest'&&o.ready>G.serverNow)]);
  // something left on a station by itself: collected once, when its time is up
  if(o.job)out.push(['Collect',()=>work({op:'take',object:o.id}),!reachable||o.hp===0||o.job.ready>G.serverNow]);
  if(o.capacity>0&&G.body.home?.containers.some(c=>c.id===o.id))out.push(['Storage',()=>openSceneDrawer('storage',o.id)]);
  if(['workbench','campfire','furnace'].includes(o.kind))out.push([o.kind==='campfire'?'Cook':'Make',()=>openSceneDrawer('recipes',o.id)]);
  out.push(['More',()=>openSceneDrawer('object',o.id)]);
 }
 // Keep window options reachable even when Approach consumes a primary slot.
 if(o.kind==='opening')return [...out.filter(x=>x[0]!=='More').slice(0,2),out.find(x=>x[0]==='More')].filter(Boolean);
 // Three stable actions; secondary jobs live in the focused drawer.
 return out.slice(0,3);
}
function itemRow(item,actions){
 const G=api.G,spec=G.items[item.code]||{name:item.code,w:0},r=make('div',undefined,'loot-row');r.dataset.item=item.code;
 const name=make('div',undefined,'loot-description'),symbol=itemIcon(spec.kind);symbol.classList.add('loot-icon');r.append(symbol,name);
 name.append(make('b',spec.name+(item.qty>1?' × '+item.qty:'')));
 if(spec.hunger||spec.thirst)name.append(make('small',[spec.hunger?'Hunger −'+spec.hunger:'',spec.thirst?'Thirst −'+spec.thirst:''].filter(Boolean).join(' · ')));
 if(spec.description)name.append(make('small',spec.description));
 name.append(make('small',(spec.w*item.qty).toFixed(1)+'kg'+(item.cond!=null?' · '+(spec.perishable?(item.cond>0?'fresh':'spoiled'):'condition '+Math.round(item.cond)+'/'+(spec.cond||10)):'')+(spec.capacity?' · +'+spec.capacity+'kg carry':'')+(spec.bite?' · bite '+Math.round(spec.bite*100*item.cond/(spec.cond||10))+'%':'')));
 const box=make('div',undefined,'loot-actions');for(const action of actions)box.append(button(...action));r.append(box);return r;
}
function amount(item){return Math.min(item.qty,Math.max(1,Math.floor(Number($('drawerQty').value)||1)));}
function nearbyObjects(){
 const G=api.G,inside=G.buildings.find(b=>b.id===G.inside),h=G.body.home;
 const entries=[...G.corpses.map(c=>({...c,kind:'corpse',name:c.kind==='survivor'?(c.own?'Your recovery pack':'Survivor recovery pack'):c.searched?'Body loot':'Search body'})),
  ...(G.vehicles||[]).map(v=>({...v,kind:'vehicle'})),
  ...G.stashes.filter(s=>!s[5]||s[5]===G.inside&&s[8]!==false).map(s=>({id:s[0],lat:s[1],lng:s[2],kind:'stash',name:api.containerName(s),room:s[6]})),
  ...G.body.survival.objects.map(o=>({...o,kind:'object'})),
  ...(inside?.openings||[]).map(o=>({...o,lat:(o.a[0]+o.b[0])/2,lng:(o.a[1]+o.b[1])/2,kind:'opening',name:o.label+(o.broken?' · broken':o.open?' · open':' · closed')})),
  ...(inside?.stairs?[{id:inside.id,lat:inside.stairs[0],lng:inside.stairs[1],kind:'stairs',name:'Stairs'}]:[]),
  ...(h&&(h.floor_level||0)===(G.you.floor||0)?[{...h,id:'home',kind:'home',name:'Home cupboard'}]:[])];
 return entries.map(o=>({...o,d:distance(o)})).filter(o=>o.d<=12).sort((a,b)=>a.d-b.d);
}
function renderDrawer(o){
 const G=api.G,drawer=G.drawer;if(!drawer||$('sceneDrawer').hidden)return;
 const {mode,id}=drawer,nearby=mode==='nearby'?nearbyObjects():[],shelf=mode==='bodyloot'?G.corpses.find(c=>c.id===id):G.lootShelves?.find(s=>s.id===id),storage=id?G.body.home?.containers.find(c=>c.id===id):G.body.home;
 const car=G.vehicles?.find(v=>v.id===id);
 const key=JSON.stringify([drawer,nearby.map(o=>[o.id,o.name,Math.round(o.d)]),G.body.items.map(i=>[i.id,i.code,i.qty,Math.floor(i.cond)]),G.broadcast,G.body.lessons,G.body.study,G.body.study?.reading&&Math.ceil((G.body.study.ready-G.serverNow)),G.body.base?.owner,G.body.base?.role,G.body.home?.revision,shelf,storage?.reachable,o?.reachable,o?.hp===0,o?.kind,o?.open,o?.broken,o?.barricaded,o?.curtain,o?.curtain_closed,o?.glass_cleared,G.inside,!!G.channel,G.storagePane,o?.job&&Math.ceil((o.job.ready-G.serverNow)/60)]);
 const fullKey=key+JSON.stringify([car?.revision,car?.items,car?.reachable,car?.seat,car?.allowed,car?.engine,car?.speed]);
 if(fullKey===drawerKey)return;drawerKey=fullKey;
 $('storageTabs').hidden=!['storage','cargo'].includes(mode);
 const box=$('drawerContent');box.replaceChildren();$('drawerQtyWrap').hidden=!['loot','bodyloot','storage','cargo'].includes(mode);
 $('drawerWeight').textContent=G.body.weight.toFixed(1)+' / '+G.body.carry_max.toFixed(1)+'kg';
 if(['media','learning'].includes(mode)){
  $('drawerTitle').textContent=mode==='media'?'Training television':'Learning';$('drawerHint').textContent='Stay nearby. The world keeps moving; move or Stop to pause.';
  const current=G.body.study;
  if(current){const left=current.reading?current.ready-G.serverNow:current.left_s;box.append(make('b',current.name),make('p',(current.reading?Math.max(0,Math.ceil(left))+'s remaining':'Paused · '+Math.ceil(left)+'s remaining'),'fine'));box.append(button(current.reading?'Stop':'Resume',()=>api.fire('study',{op:current.reading?'stop':'resume'}),!current.reading&&!current.can_read));}
  if(mode==='media')for(const lesson of G.body.lessons||[]){const row=make('div',undefined,'work-row');row.append(make('b',lesson.name),make('p',lesson.learned?'Learned by this survivor':lesson.available?lesson.seconds+'s · '+lesson.xp+' skill XP · once per survivor':'Find the matching training tape','fine'));row.append(button(lesson.learned?'Learned':'Watch',()=>{api.stop();api.fire('study',{op:'watch',object:id,lesson:lesson.id});},lesson.learned||!lesson.available||!!current||!G.body.survival.objects.some(o=>o.id===id&&o.reachable)));box.append(row);}
 }else if(mode==='radio'){
  $('drawerTitle').textContent='Local emergency broadcast';$('drawerHint').textContent='Received '+new Date((G.broadcast?.at||0)*1000).toLocaleTimeString()+'. Reports may become outdated.';
  for(const line of G.broadcast?.lines||[])box.append(make('p',line));
 }else if(mode==='vehicle'){
  $('drawerTitle').textContent=car?.name||'Vehicle';$('drawerHint').textContent=car?'Fuel '+car.fuel.toFixed(1)+'/'+car.tank+' · Hull '+Math.round(car.hull)+'% · Engine '+Math.round(car.motor)+'% · Cargo '+car.capacity+'kg':'Vehicle is out of sight.';
  if(car)for(const [label,op] of [['Driver seat','enter_driver'],['Passenger seat','enter_passenger'],['Refuel (1 can)','fuel'],[car.engine?'Stop engine':'Start engine','engine'],['Exit vehicle','exit']])box.append(button(label,()=>api.fire('vehicle',{vehicle:id,op}),!car.allowed));
 }else if(mode==='cargo'){
  $('drawerTitle').textContent=car?.name+' · cargo';$('drawerHint').textContent=car?(car.allowed?(car.capacity-(car.weight||0)).toFixed(1)+'kg free · stop beside the vehicle to transfer.':'Select the owning base to use this cargo.'):'Vehicle out of sight.';
  const pane=G.storagePane||'deposit',usable=car?.allowed&&(car.reachable||car.seat!=null)&&Math.abs(car.speed)<.8;
  for(const [key,value] of [['storageDeposit','deposit'],['storageWithdraw','withdraw']])$(key).setAttribute('aria-pressed',String(value===pane));
  const rows=pane==='withdraw'?car?.items||[]:G.body.items;
  for(const item of rows){const blocked=!usable||pane==='deposit'&&Object.values(G.body.worn||{}).includes(item.id),op=pane==='withdraw'?'withdraw':'deposit';box.append(itemRow(item,[[pane==='withdraw'?'Take 1':'Store 1',()=>take(op,item,1),blocked],[pane==='withdraw'?'Take qty':'Store qty',()=>take(op,item,amount(item)),blocked]]));}
  if(!rows.length)box.append(make('p','Empty.','fine'));
  function take(op,item,qty){api.fire('vehicle',{vehicle:id,op,item:item.id,qty,revision:car.revision,request:crypto.randomUUID()});}
 }else if(mode==='nearby'){
  $('drawerTitle').textContent='Nearby';$('drawerHint').textContent='Choose an object. Approach it, then search or use it. The world keeps moving.';
  for(const target of nearby){const row=button(target.name+' · '+Math.round(target.d)+'m',()=>selectWorld({kind:target.kind,id:target.id}));row.dataset.nearby=target.kind;row.dataset.entity=target.id;box.append(row);}
  if(!nearby.length)box.append(make('p','Nothing close enough. Walk toward a room, shelf or body.','fine'));
 }else if(mode==='loot'||mode==='bodyloot'){
  $('drawerTitle').textContent=(shelf?.room?shelf.room+' · ':'')+(o?.name||'Container');
  $('drawerHint').textContent=mode==='bodyloot'?(shelf?(shelf.reachable?(shelf.own?'Your carried gear. Take what you can carry; wear recovered equipment from the belt or Pack.':shelf.can_loot===false?'This recovery pack belongs to another survivor.':'Shared body — supplies can be taken by anyone nearby.'):'Approach the body to take items.'):'This body is no longer here.'):(shelf?(shelf.reachable?'Take what you need. Leave the rest for later.':'Out of reach — approach the container to take items.'):'Empty. Previously claimed loot stays depleted.');
  for(const item of shelf?.items||[])box.append(itemRow(item,[['Take 1',()=>take(item,1),!shelf.reachable||!!G.channel],['Take qty',()=>take(item,amount(item)),!shelf.reachable||!!G.channel]]));
  if(shelf&&!shelf.items?.length)box.append(make('p',mode==='bodyloot'?'Nothing useful left on this body.':'Nothing left in this container.','fine'));
  function take(item,qty){api.fire(mode==='bodyloot'?'body_loot':'loot',{[mode==='bodyloot'?'corpse':'stash']:id,item:item.id,qty,revision:shelf.revision,request:crypto.randomUUID()});}
 }else if(mode==='storage'){
  const free=storage?Math.max(0,storage.capacity-storage.weight):0,pane=G.storagePane||'deposit';
  $('drawerTitle').textContent=storage?.name||'Storage';$('drawerHint').textContent=storage?(storage.reachable?free.toFixed(1)+'kg free · '+storage.weight+'/'+storage.capacity+'kg stored':(storage.floor_level||0)!==(G.you.floor||0)?'This storage is on '+floorName(storage.floor_level)+'. Use the building stairs.':'Out of reach — close and Approach this storage first.'):'Set Home in this building to store supplies.';
  for(const [key,value] of [['storageDeposit','deposit'],['storageWithdraw','withdraw']])$(key).setAttribute('aria-pressed',String(value===pane));
  if(pane==='withdraw'){
   for(const item of storage?.items||[])box.append(itemRow(item,[['Take 1',()=>transfer('withdraw',item,1),!storage?.reachable||!!G.channel],['Take qty',()=>transfer('withdraw',item),!storage?.reachable||!!G.channel]]));
   if(!storage?.items.length)box.append(make('p','Empty. Tap Store from pack to put supplies here.','fine'));
  }else{
   for(const item of G.body.items){
    const worn=Object.values(G.body.worn||{}).includes(item.id),weight=G.items[item.code]?.w||0,blocked=!storage?.reachable||worn||!!G.channel;
    const row=itemRow(item,[['Store 1',()=>transfer('deposit',item,1),blocked||weight>free+.001],['Store qty',()=>transfer('deposit',item),blocked||weight*amount(item)>free+.001]]);
    if(worn)row.querySelector('.loot-description').append(make('small','Take off before storing.'));
    else if(weight>free+.001)row.querySelector('.loot-description').append(make('small','Not enough space in this container.'));
    box.append(row);
   }
   if(!G.body.items.length)box.append(make('p','Your pack is empty.','fine'));
  }
  function transfer(op,item,qty=amount(item)){api.fire('transfer',{op,item:item.id,qty,container:id||undefined,revision:G.body.home.revision,request:crypto.randomUUID()});}
 }else if(mode==='quick'){
  $('drawerTitle').textContent=id==='drink'?'Drinking water':'Food';$('drawerHint').textContent='Use one serving. Keep an eye on the street.';
  for(const item of G.body.items.filter(i=>G.items[i.code]?.kind===id))box.append(itemRow(item,[[id==='drink'?'Drink':'Eat',()=>api.press('use',null,{code:item.code}),!!G.items[item.code].perishable&&item.cond<=0]]));
 }else if(mode==='recipes'){
  const station=[...G.body.survival.objects].find(x=>x.id===id);$('drawerTitle').textContent=station?.name||'Workstation';$('drawerHint').textContent='Materials and tools must be in your pack.';
  // what is already on the station comes first, so Collect is never below the fold
  const slowRows=()=>{
  // Slow jobs: the station does them alone, on the real clock, also while the game is closed.
   for(const [recipe,r] of Object.entries(G.body.survival.slow||{}).filter(([,r])=>r.bench===station?.kind)){
    const job=station.job,missing=Object.entries(r.need).filter(([c,n])=>G.body.items.filter(i=>i.code===c&&(!G.items[c].perishable||i.cond>0)).reduce((n,i)=>n+i.qty,0)<n),row=make('div',undefined,'work-row');row.dataset.slow=recipe;
    const gives=Object.entries(r.out).map(([c,n])=>n+' '+G.items[c].name).join(', ');
    if(job){
     const ready=job.ready<=G.serverNow;
     row.append(make('b',job.name.split(' (')[0]+(ready?' · ready':' · '+waitText(job.ready-G.serverNow)+' left')),make('p',ready?'Collect it once. It will not spoil while it waits.':'It carries on while you are out, or while the game is closed.','fine'));
     row.append(button('Collect',()=>work({op:'take',object:id}),!ready||!station.reachable||!!G.channel));
    }else{
     row.append(make('b',r.name),make('p',Object.entries(r.need).map(([c,n])=>n+' '+G.items[c].name).join(' + ')+' → '+gives+' · takes '+waitText(r.seconds)+'; you need not wait'+(missing.length?' · Missing supplies':''),'fine'));
     row.append(button('Start',()=>work({op:'slow',recipe,object:id}),!!missing.length||!station.reachable||!!G.channel||!G.body.home));
    }
    box.append(row);
   }
  };
  if(station?.job)slowRows();
  for(const [recipe,r] of Object.entries(G.body.survival.recipes).filter(([,r])=>r.bench===station?.kind)){
   const missing=Object.entries(r.need).filter(([c,n])=>G.body.items.filter(i=>i.code===c&&(!G.items[c].perishable||i.cond>0)).reduce((n,i)=>n+i.qty,0)<n);
   const tool=r.tool&&!G.body.items.some(i=>i.code===r.tool&&i.cond>0),row=make('div',undefined,'work-row');row.dataset.recipe=recipe;
   row.append(make('b',r.name),make('p',Object.entries(r.need).map(([c,n])=>n+' '+G.items[c].name).join(' + ')+' · '+r.seconds+'s'+(tool?' · Need '+G.items[r.tool].name:'')+(missing.length?' · Missing supplies':'')+(r.locked?' · Learn from '+r.learn_from:''),'fine'));
   row.append(button(r.object?'Build':'Make',()=>r.object?api.place({op:'craft',recipe},r.name):work({op:'craft',recipe}),r.locked||!!missing.length||!!tool||!station?.reachable||!!G.channel||!G.body.home));box.append(row);
  }
  if(!station?.job)slowRows();
 }else{
  $('drawerTitle').textContent=o?.name||'Object';$('drawerHint').textContent='Approach before working. Noisy work can attract zombies.';
  if(!o)return;
  if(mode==='opening'){
   if(isWindowOpening(o)){
    const windowAction=op=>{api.stop();api.fire('window',{opening:id,op});},blocked=distance(o)>2.7||!!G.channel;
    if(G.inside){
     if(!o.curtain)box.append(button('Hang curtain (2 cloth)',()=>windowAction('hang'),blocked));
     else {box.append(button(o.curtain_closed?'Open curtain':'Close curtain',()=>windowAction(o.curtain_closed?'curtain_open':'curtain_close'),blocked));box.append(button('Remove curtain',()=>windowAction('remove'),blocked));}
    }
    if(o.broken&&!o.glass_cleared)box.append(button('Clear glass',()=>windowAction('clear'),blocked));
    if(!G.you.floor&&(o.open||o.broken)&&!o.barricaded&&!o.curtain_closed)box.append(button('Climb through',()=>windowAction('vault'),blocked));
    box.append(make('p',(o.curtain_closed?'Curtain blocks sight; sound still carries. ':'')+(o.broken&&!o.glass_cleared?'Loose glass can cut you. Clear it with a usable weapon/tool, or wear gloves.':'Climbing costs stamina.'),'fine'));
   }
   for(const [label,op] of [['Barricade','barricade'],['Repair boards','repair_opening'],['Remove boards','remove_barricade']])box.append(button(label,()=>work({op,opening:id})));
   if(o.kind==='opening'&&!o.broken&&isWindowOpening(o))box.append(button('Smash window',()=>api.fire('opening',{opening:id,op:'smash'})));
  }else{
   if(o.hp!==undefined){
    for(const [label,op] of [['Repair','repair'],['Dismantle','salvage']])box.append(button(label,()=>work({op,object:id}),!o.reachable));
    box.append(button('Move',()=>api.place({op:'move',object:id},o.name),!o.reachable));
   }else box.append(make('p',(o.remaining||0)+' gathers left'+({tree:' · Needs an axe',rock:' · Needs a pickaxe',ore:' · Needs a pickaxe',pond:' · Needs a fishing rod'}[o.kind]||'')+'. Generated game resource.','fine'));
   if(!G.body.home&&G.inside)box.append(button('Make this room home',()=>api.fire('home',{name:'My shelter'})));
  }
 }
}
export function renderWorldUI(){
 if(!api?.G.you||!api.G.body)return;
 const G=api.G,o=selected(),card=$('worldCard');
 card.hidden=!o||!$('sceneDrawer').hidden||!$('panel').hidden||G.dead;
 if(o){
  const d=distance(o),buttons=objectActions(o),key=JSON.stringify([G.selection,buttons.map(a=>[a[0],!!a[2]])]);
  $('worldName').textContent=o.name;$('worldDetail').textContent=Math.round(d)+'m'+(o.room?' · '+o.room:'')+(o.remaining!==undefined?' · '+o.remaining+' yields left':'')+(o.hp!==undefined?' · '+Math.round(o.hp)+' durability':'')+(o.kind==='generator'?' · '+Math.round(o.fuel||0)+'s fuel':'')+(o.barricaded?' · boarded':'')+(o.kind==='corpse'?(o.reachable?' · in reach':' · approach to search'):'')+(['garden','plot'].includes(o.kind)&&o.ready!==undefined?(o.ready<=G.serverNow?' · ready to harvest':' · ready in '+waitText(o.ready-G.serverNow)):'')+(o.job?' · '+o.job.name.split(' (')[0]+(o.job.ready<=G.serverNow?': ready':': '+waitText(o.job.ready-G.serverNow)+' left'):'');
  if(key!==cardKey){cardKey=key;
   const actions=$('worldActions');actions.replaceChildren();for(const action of buttons)actions.append(button(...action));
  }
 }
 renderDrawer(o);
 if(!$('sceneDrawer').hidden||!$('panel').hidden)$('bLoot').hidden=true;
 const available=kind=>G.body.items.filter(i=>G.items[i.code]?.kind===kind&&(!G.items[i.code].perishable||i.cond>0)).reduce((n,i)=>n+i.qty,0);
 $('bInteract').hidden=G.dead||(!G.inside&&!nearbyObjects().length);
 $('qStore').hidden=!G.body.home;
 $('qWeapon').lastChild.textContent='Gear';$('qBuild').lastChild.textContent='Build';
 $('qWater').lastChild.textContent=' '+available('drink');$('qFood').lastChild.textContent=' '+available('food');
 const bleeding=G.body.wounds.some(w=>w.bleeding&&!w.bandaged);
 $('qBandage').lastChild.textContent=bleeding?'Bleed!':'Health';$('qBandage').classList.toggle('urgent',bleeding);
 $('beltWeight').textContent=G.body.weight.toFixed(1)+'/'+G.body.carry_max.toFixed(0)+'kg';
 let imminent=false;
 for(const z of G.zeds.values())if(z.mine&&['chase','alert','engaged'].includes(z.state)){
  const ll=z.p.b,d=Math.hypot(...deltaM(G.you.lat,G.you.lng,...ll));if(d<=6)imminent=true;
 }
 const hint=imminent?'Zombie close — move or shove!':'';
 $('threatWarning').hidden=!imminent;$('threatWarning').textContent=hint;
 if(imminent){$('panel').classList.remove('expanded');$('sceneDrawer').classList.remove('expanded');$('panelExpand').textContent='Expand';$('drawerExpand').textContent='Expand';}
}
export function tapOpening(x,y){
 const hit=hitOpening(x,y);if(!hit)return false;selectWorld({kind:'opening',id:hit.o.id});return true;
}
export function hitOpening(x,y){
 const G=api.G,origin=G.screenOrigin,ll=G.screenLL;if(!origin||!ll)return false;
 const visible=G.buildings.filter(b=>!G.inside||b.id===G.inside),P=(lat,lng)=>worldPoint(G,lat,lng);
 const faces=G.cam.iso?new Map(buildingFaces(visible,G.inside,P,G.cam.ppm,P(...(G.desk||[G.you.lat,G.you.lng]))).filter(f=>f.edge.id).map(f=>[f.edge.id,f.h])):new Map();
 const hits=visible.flatMap(b=>b.openings).map(o=>({o,d:openingHit(x,y,P(...o.a),P(...o.b),faces.get(o.id)||0)})).filter(o=>o.d!==null).sort((a,b)=>a.d-b.d);
 return hits[0]||null;
}
export function drawSelection(ctx,P){
 const o=selected();if(!o)return;const [worldX,y]=P(o.lat,o.lng),x=worldX+(o.kind==='home'?HOME_MARKER_OFFSET_X:0);
 ctx.save();ctx.strokeStyle='#d5ecb5';ctx.lineWidth=2;ctx.setLineDash([5,3]);ctx.strokeRect(x-23,y-35,46,48);ctx.restore();
}
