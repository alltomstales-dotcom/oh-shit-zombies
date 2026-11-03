// Phone inventory and owner storage. All item changes are judged by the server.
import {floorName,homeApproach} from './home-navigation.js';
import {renderWork} from './work.js';
import {itemIcon,waitText} from './icons.js';
const $=id=>document.getElementById(id);
let api;
export function setupInventory(actions){
 api=actions;
 for(const b of document.querySelectorAll('[data-pack-tab]'))b.onclick=()=>{api.G.packTab=b.dataset.packTab;renderInventory();};
 $('inventoryFilter').onchange=renderInventory;
 $('storageContainer').onchange=()=>{api.G.storageContainer=$('storageContainer').value;renderInventory();};
 $('homeName').oninput=()=>{api.G.homeDraft=$('homeName').value;};
 $('setHome').onclick=()=>{api.stop();api.fire('home',{name:$('homeName').value});};
 $('renameHome').onclick=()=>api.fire('home',{op:'rename',name:$('homeName').value});
 $('baseInvite').onclick=()=>api.fire('base',{op:'invite',role:$('baseInviteRole').value});
 $('baseCopy').onclick=async()=>{try{await navigator.clipboard.writeText($('baseCode').value);api.toast('Invitation copied.');}catch(_){api.toast('Long press the code to copy it.');}};
 $('baseCloseInvites').onclick=()=>api.fire('base',{op:'close_invites'});
 $('baseJoin').onclick=()=>api.fire('base',{op:'join',invite:$('baseJoinCode').value});
 $('baseLeave').onclick=()=>api.fire('base',{op:'leave'});
 $('baseChoice').onchange=()=>api.fire('base',{op:'select',owner:Number($('baseChoice').value)});
 $('returnHome').onclick=()=>{const h=api.G.body?.home;if(!h)return;api.close();const plan=homeApproach(api.G,h);if(plan.mode==='stairs')api.select({kind:'stairs',id:plan.building});else if(plan.mode==='exit'){api.leave();api.toast('Head outside, then choose Walk home.');}else api.walk(plan.goal);};
}
const el=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
function button(label,fn,disabled=false){const b=el('button','',label);b.onclick=fn;b.disabled=disabled;return b;}
function selectedStorage(G){return G.body.home?.containers?.find(c=>c.id===G.storageContainer)||G.body.home;}
function transfer(op,row){const G=api.G,qty=Math.min(row.qty,Math.max(1,Math.floor(Number($('transferQty').value)||1)));api.fire('transfer',{op,item:row.id,qty,container:G.storageContainer||undefined,revision:G.body.home.revision,request:crypto.randomUUID()});}
function row(item,storage=false){
 const G=api.G,spec=G.items[item.code]||{name:item.code,kind:'material'},r=el('div','inventory-row');r.dataset.item=item.code;
 const text=el('div','item-description'),worn=Object.entries(G.body.worn||{}).find(([slot,id])=>id===item.id);
 const symbol=itemIcon(spec.kind);symbol.classList.add('item-symbol');r.append(symbol,text);
 text.append(el('b','',spec.name+(item.qty>1?' × '+item.qty:'')));
 if(spec.hunger||spec.thirst)text.append(el('div','s',[spec.hunger?'Hunger −'+spec.hunger:'',spec.thirst?'Thirst −'+spec.thirst:''].filter(Boolean).join(' · ')));
 if(spec.description)text.append(el('div','s',spec.description));
 if((spec.teaches&&G.body.studied?.includes(spec.teaches))||(spec.knowledge&&G.body.knowledge?.includes(spec.knowledge)))text.append(el('div','s','This survivor has already learned it.'));
 const notes=[(spec.w*item.qty).toFixed(1)+'kg'];
 if(item.cond!=null)notes.push(spec.perishable?(item.cond<=0?'SPOILED':'freshness '+Math.round(item.cond)+'%'):'condition '+Math.round(item.cond)+'/'+(spec.cond||10));
 if(!storage&&G.body.hands===item.id)notes.push('held');if(!storage&&worn)notes.push('worn: '+worn[0]);
 if(spec.capacity)notes.push('+'+spec.capacity+'kg capacity');
 if(spec.covers)notes.push('bite '+Math.round((spec.bite||0)*100*item.cond/(spec.cond||10))+'% · scratch '+Math.round((spec.scratch||0)*100*item.cond/(spec.cond||10))+'%');
 if(spec.pace)notes.push('pace '+Math.round(spec.pace*100)+'%');
 text.append(el('div','s',notes.join(' · ')));
 if(spec.covers)text.append(el('div','s','Covers: '+spec.covers.join(', ')));
 const actions=el('div','item-actions');r.append(actions);
 if(storage)actions.append(button('Retrieve',()=>transfer('withdraw',item),!selectedStorage(G)?.reachable));
 else {
  if(spec.slot)actions.append(button(worn?'Take off':'Wear',()=>api.fire('wear',worn?{op:'remove',slot:worn[0]}:{item:item.id,op:'wear'}),!worn&&item.cond<=0));
  if(['weapon','gun'].includes(spec.kind)&&G.body.hands!==item.id)actions.append(button('Hold',()=>api.fire('equip',{item:item.id})));
  if(item.code==='radio')actions.append(button('Listen',()=>api.fire('radio',{item:item.id})));
  if(spec.teaches||spec.knowledge)actions.append(button('Read at home',()=>api.fire('study',{item:item.id}),(spec.teaches?!!G.body.studied?.includes(spec.teaches):!!G.body.knowledge?.includes(spec.knowledge))||(!!G.body.study&&G.body.study.code!==item.code)));
  if(spec.kind==='food'||spec.kind==='drink')actions.append(button(spec.kind==='food'?'Eat':'Drink',()=>api.fire('use',{code:item.code}),!!spec.perishable&&item.cond<=0));
  if(G.packTab==='home'&&G.body.home)actions.append(button('Store',()=>transfer('deposit',item),!selectedStorage(G)?.reachable||!!worn));
  else actions.append(button(item.qty>1?'Drop 1':'Drop',()=>api.fire('drop',{item:item.id}),!!worn));
 }
 return r;
}
// What is running at home and when it finishes. Times are absolute on the server, so this only
// changes when a minute does.
function renderJobs(G,h){
 const box=$('homeJobs'),jobs=h?.jobs||[],study=G.body.study;box.replaceChildren();
 if(!h)return;
 box.append(el('h3','','Running at home'));
 if(!jobs.length){box.append(el('p','fine','Nothing yet. A vegetable plot takes a day, smoked rations an hour at a cooking fire, and a manual an hour of reading here. They carry on while the game is closed.'));return;}
 for(const j of jobs){
  const r=el('div','job-row'),left=j.ready!=null?j.ready-G.serverNow:j.left_s,done=j.kind!=='study'&&left<=0;r.dataset.job=j.kind;
  const state=j.kind==='study'?(study?.reading?waitText(left)+' left':'paused · '+waitText(left)+' left'):done?(j.kind==='crop'?'READY to harvest':'READY to collect'):'ready in '+waitText(left);
  r.append(el('b','',j.name),el('span',done?'job-ready':'fine',state));
  if(j.kind==='study')r.append(button(study?.reading?'Stop':'Keep reading',()=>api.fire('study',study?.reading?{op:'stop'}:{}),!study?.reading&&!study?.can_read));
  else r.append(button('Walk there',()=>{api.close();api.walk([j.lat,j.lng]);}));
  box.append(r);
 }
}
export function renderInventory(){
 if(!api)return;const G=api.G,b=G.body;if(!b)return;const tab=G.packTab||'pack';
 for(const e of document.querySelectorAll('[data-pack-tab]')){e.setAttribute('aria-selected',String(e.dataset.packTab===tab));}
 $('packSection').hidden=tab!=='pack';$('equipmentSection').hidden=tab!=='equipment';$('homeSection').hidden=tab!=='home';$('statusSection').hidden=tab!=='status';$('workSection').hidden=tab!=='work';
 if(tab==='work')renderWork();
 $('weight').textContent=b.weight.toFixed(1)+' / '+b.carry_max.toFixed(1)+'kg · '+Math.max(0,b.carry_max-b.weight).toFixed(1)+'kg free';
 const list=$('items');list.replaceChildren();const filter=$('inventoryFilter').value;
 for(const i of b.items)if(filter==='all'||filter==='gear'&&['weapon','gun','clothing','bag','tool'].includes(G.items[i.code]?.kind)||filter===G.items[i.code]?.kind)list.append(row(i));
 const eq=$('equipment');eq.replaceChildren();
 for(const slot of ['head','torso','legs','hands','feet','back']){
  const i=b.items.find(i=>i.id===b.worn?.[slot]);eq.append(el('h3','',slot));eq.append(i?row(i):el('p','fine','Nothing worn'));
 }
 const h=b.home;$('homeName').value=G.homeDraft??h?.name??'My shelter';$('setHome').textContent=h?'Move empty home here':'SET HOME HERE';$('setHome').disabled=!G.inside||!!h?.items.length;
 const base=b.base||{role:'owner',members:[],choices:[]};
 $('setHome').disabled||=base.role!=='owner'||!!base.members.length;
 $('renameHome').hidden=!h||base.role!=='owner';
 $('baseStatus').textContent=base.role==='owner'?'Your personal base. You control membership.':'Shared base · '+(base.role==='builder'?'Builder: storage and work.':'Storage access: supplies only.');
 $('baseOwnerControls').hidden=base.role!=='owner'||!h;
 $('baseLeave').hidden=base.role==='owner';
 const choices=$('baseChoice');choices.replaceChildren();for(const choice of base.choices||[]){const o=el('option','',choice.name);o.value=choice.owner;choices.append(o);}choices.value=String(base.owner);
 $('baseMembers').replaceChildren();for(const member of base.members||[]){const r=el('div','row');r.append(el('span','',member.name+' · '+member.role),button('Revoke',()=>api.fire('base',{op:'revoke',member:member.id})));$('baseMembers').append(r);}
 $('renameHome').disabled=!h?.reachable;$('returnHome').hidden=!h;
 $('homeStatus').textContent=h?(base.role!=='owner'?'Shared base · ':'')+h.name+' · '+floorName(h.floor_level)+' · '+Math.round(h.distance)+'m away · '+h.weight+' / '+h.capacity+'kg stored · '+h.food+' food · '+h.water+' drinking water · '+h.defenses+' defenses · '+h.objective+(h.reachable?' · In reach':' · Walk to the cupboard to transfer'):'Choose a room inside a building. Its cupboard will hold supplies between trips and survivor lives.';
 renderJobs(G,h);
 $('homeItems').replaceChildren();$('homePack').replaceChildren();
 const select=$('storageContainer');select.replaceChildren();const main=el('option','', 'Home cupboard');main.value='';select.append(main);
 if(h){for(const c of h.containers||[]){const o=el('option','',c.name+' · '+c.weight+'/'+c.capacity+'kg'+(c.reachable?' · in reach':''));o.value=c.id;select.append(o);}select.value=G.storageContainer||'';if(select.selectedIndex<0){G.storageContainer='';select.value='';}
 const storage=selectedStorage(G);for(const i of storage.items)$('homeItems').append(row(i,true));for(const i of b.items)$('homePack').append(row(i));if(!storage.items.length)$('homeItems').append(el('p','fine','Container empty. Store supplies from your pack below.'));}
}
