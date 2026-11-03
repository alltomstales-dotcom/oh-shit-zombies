// Actual unmodified server + normal combat and search buttons. May take2min.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';import fs from 'node:fs';
const base=process.argv[2]||'http://127.0.0.1:8018',prefix=process.argv[3]||'/tmp/osz-body';const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const c=await browser.newContext({...devices['Pixel 7'],permissions:['geolocation'],geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=AftermathCheck');await p.waitForFunction(()=>__osz.G.you&&__osz.G.located&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
 const initial=await p.evaluate(()=>({kills:__osz.G.you.kills,bodies:__osz.G.corpses.map(b=>b.id)}));
 // Use normal buttons to finish a zombie; an existing communal body is not proof of a kill.
 for(let n=0;n<150;n++){
  const s=await p.evaluate(initialIds=>{const G=__osz.G;return {dead:G.dead,kills:G.you.kills,bodies:G.corpses.filter(b=>!initialIds.includes(b.id)).length,hp:G.you.hp,near:[...G.zeds.values()].some(z=>Math.hypot((z.p.b[0]-G.you.lat)*111320,(z.p.b[1]-G.you.lng)*111320*Math.cos(G.you.lat*Math.PI/180))<3.4),inside:G.inside};},initial.bodies);
  if(s.dead)throw Error('Test survivor died before first search');if(s.kills>initial.kills&&s.bodies)break;
  if(s.near)await p.locator('#bSwing').tap();
  await p.waitForTimeout(800);
 }
 await p.waitForFunction(initial=>__osz.G.you.kills>initial.kills&&__osz.G.corpses.some(b=>!initial.bodies.includes(b.id)),initial,{timeout:10000});
 const body=await p.evaluate(ids=>__osz.G.corpses.find(b=>!ids.includes(b.id)),initial.bodies);
 console.log(JSON.stringify({realFightBody:true,look:body.variant,kind:body.kind}));
 async function tapBody(){const xy=await p.evaluate(({lat,lng})=>{const G=__osz.G,[x,y]=__osz.project(lat,lng),c=G.corpses.find(c=>c.lat===lat&&c.lng===lng),h=G.inside?Math.max(22,Math.min(72,2*G.cam.ppm)):Math.max(48,Math.min(120,4.6*G.cam.ppm)),a=c?.variant%2?-1.5:1.5;return [x+Math.sin(a)*h*.6,y-Math.cos(a)*h*.6];},body);await p.touchscreen.tap(...xy);}
 await tapBody();await p.waitForFunction(id=>__osz.G.selection?.kind==='corpse'&&__osz.G.selection.id===id,body.id);
 if(!body.reachable){await p.getByRole('button',{name:'Approach',exact:true}).tap();await p.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id&&b.reachable),body.id,{timeout:20000});await p.locator('#bStop').click({force:true});await tapBody();}
 await p.getByRole('button',{name:'Search body',exact:true}).tap();
 await p.waitForFunction(()=>__osz.G.drawer?.mode==='bodyloot'&&!document.getElementById('sceneDrawer').hidden,null,{timeout:18000}).catch(async err=>{console.log('searchFailure',await p.evaluate(()=>({hp:__osz.G.you.hp,dead:__osz.G.dead,channel:__osz.G.channel,selection:__osz.G.selection,drawer:__osz.G.drawer,bodies:__osz.G.corpses.map(b=>({id:b.id,searched:b.searched,reachable:b.reachable})),toasts:[...document.querySelectorAll('.toast')].map(t=>t.textContent),z:__osz.state().zeds.slice(0,3)})));throw err;});
 const searched=await p.evaluate(id=>__osz.G.corpses.find(b=>b.id===id),body.id);assert(searched.searched);
 await p.screenshot({path:'/tmp/osz-body-phone.png'});
 await c.storageState({path:prefix+'-storage.json'});fs.chmodSync(prefix+'-storage.json',0o600);
 fs.writeFileSync(prefix+'-evidence.json',JSON.stringify({base,body:searched,kills:initial.kills+1}));fs.chmodSync(prefix+'-evidence.json',0o600);
 await p.reload();await p.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id&&b.searched),body.id,{timeout:65000});
 assert.deepEqual(await p.evaluate(id=>__osz.G.corpses.find(b=>b.id===id)?.items,body.id),searched.items);
 assert(await p.evaluate(n=>__osz.G.you.kills>n,initial.kills),'own kill must survive reload');
 assert.deepEqual(errors,[]);console.log(JSON.stringify({realFightBody:true,tapSelectBody:true,searchOpensCompactDrawer:true,reloadBodyAndStock:true,items:searched.items.map(i=>i.code),errors}));
}finally{await browser.close();}
