// Use an existing real searched body with stock from mobile_body_check.mjs.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';import fs from 'node:fs';
const prefix=process.argv[2]||'/tmp/osz-body',e=JSON.parse(fs.readFileSync(prefix+'-evidence.json')),base=e.base,browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const phone={...devices['Pixel 7'],permissions:['geolocation'],geolocation:{latitude:e.body.lat,longitude:e.body.lng,accuracy:8}};
 const c=await browser.newContext({...phone,storageState:prefix+'-storage.json'}),p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk');await p.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id&&b.reachable)&&!__osz.G.launchPending,e.body.id,{timeout:65000}).catch(async err=>{console.log('transferReadiness',await p.evaluate(()=>({dead:__osz.G.dead,launchPending:__osz.G.launchPending,launchHunted:__osz.G.launchHunted,located:__osz.G.located,bodies:__osz.G.corpses.length})));throw err;});
 const shared=await p.evaluate(id=>__osz.G.corpses.find(b=>b.id===id),e.body.id);assert(shared.items.length,'use a real body with loot for transfer check');
 const c2=await browser.newContext(phone),p2=await c2.newPage();await p2.goto(base+'/?auto=desk&name=SharedBodyWitness');
 await p2.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id&&b.reachable)&&!__osz.G.launchPending,e.body.id,{timeout:65000});
 const seen=await p2.evaluate(id=>__osz.G.corpses.find(b=>b.id===id),e.body.id);assert.deepEqual(seen.items,shared.items);assert.equal(seen.revision,shared.revision);
 const before=await p.evaluate(code=>__osz.G.body.items.filter(i=>i.code===code).reduce((n,i)=>n+i.qty,0),shared.items[0].code);
 const xy=await p.evaluate(({lat,lng})=>{const G=__osz.G,o=G.screenOrigin,ll=G.screenLL;return [o[0]+(lng-ll[1])*111320*Math.cos(ll[0]*Math.PI/180)*G.cam.ppm,o[1]-(lat-ll[0])*111320*G.cam.ppm];},shared);
 await p.touchscreen.tap(...xy);await p.waitForFunction(id=>__osz.G.selection?.id===id,shared.id);await p.getByRole('button',{name:'Look inside',exact:true}).tap();
 await p.locator('#drawerContent .loot-row').first().getByRole('button',{name:'Take 1',exact:true}).tap();
 await p.waitForFunction(({code,n})=>__osz.G.body.items.filter(i=>i.code===code).reduce((n,i)=>n+i.qty,0)===n,{code:shared.items[0].code,n:before+1});
 const after=await p.evaluate(id=>__osz.G.corpses.find(b=>b.id===id),shared.id);
 await p2.waitForFunction(({id,revision})=>__osz.G.corpses.some(b=>b.id===id&&b.revision===revision),after);
 assert.deepEqual(await p2.evaluate(id=>__osz.G.corpses.find(b=>b.id===id).items,after.id),after.items);
 e.body=after;fs.writeFileSync(prefix+'-evidence.json',JSON.stringify(e));
 await p.reload();await p.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id&&b.reachable),after.id,{timeout:65000});assert.deepEqual(await p.evaluate(id=>__osz.G.corpses.find(b=>b.id===id).items,after.id),after.items);
 assert.deepEqual(errors,[]);console.log(JSON.stringify({sharedBodyTwoActualClients:true,takeOneAddsToPack:true,otherClientSeesDepletion:true,reloadPreservesDepletion:true,errors}));
}finally{await browser.close();}
