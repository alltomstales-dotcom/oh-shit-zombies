// Local serve_recovery fatal-wound fixture; all UI/death/respawn/transfers are real.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8030';
assert(new URL(base).hostname==='127.0.0.1','fatal-wound fixture acceptance is local only');
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const c=await browser.newContext({...devices['Pixel 7'],permissions:['geolocation'],geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage(),errors=[];
 p.on('pageerror',e=>errors.push(e.message));await p.goto(base+'/?auto=desk&name=RecoveryCheck');
 await p.waitForFunction(()=>__osz.G.dead,null,{timeout:90000});
 console.log('stage: died');const card=await p.evaluate(()=>__osz.G.card);assert(card.corpse&&card.recover_until);
 assert((await p.locator('#deathStats').textContent()).includes('72 hours'));
 await p.locator('#bAgain').tap();console.log('stage: new requested');await p.waitForFunction(()=>!__osz.G.dead&&__osz.G.body&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
 console.log('stage: new located');await p.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id&&b.own),card.corpse,{timeout:20000}).catch(async e=>{console.log(await p.evaluate(()=>({errors:[],bodies:__osz.G.corpses,inside:__osz.G.inside,lat:__osz.G.you.lat,lng:__osz.G.you.lng})));throw e;});
 const body=await p.evaluate(id=>__osz.G.corpses.find(b=>b.id===id),card.corpse);
 assert(body.kind==='survivor'&&body.can_loot);
 await p.locator('#bBody').tap();await p.waitForFunction(id=>__osz.G.selection?.id===id,card.corpse);
 if(!body.reachable){await p.getByRole('button',{name:'Approach',exact:true}).tap();await p.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id&&b.reachable),card.corpse,{timeout:25000});await p.locator('#bStop').click({force:true});await p.locator('#bBody').tap();}
 await p.getByRole('button',{name:'Recover gear',exact:true}).tap();await p.waitForFunction(()=>__osz.G.drawer?.mode==='bodyloot');
 const row=p.locator('#drawerContent [data-item="knife"]');await row.getByRole('button',{name:'Take 1',exact:true}).tap();
 await p.waitForFunction(()=>__osz.G.body.items.some(i=>i.code==='knife'&&i.cond===2));
 assert(await p.locator('#panel').isHidden());await p.locator('#drawerClose').tap();await p.locator('#bArea').tap();
 await p.waitForFunction(()=>!document.getElementById('areaBar').hidden);
 await p.screenshot({path:'/tmp/osz-recovery-phone.png'});await p.reload();
 await p.waitForFunction(()=>__osz.G.body?.items.some(i=>i.code==='knife'&&i.cond===2),null,{timeout:30000}).catch(async e=>{console.log(await p.evaluate(()=>({dead:__osz.G.dead,launchPending:__osz.G.launchPending,located:__osz.G.located,locationBusy:__osz.G.locationBusy,notice:document.getElementById('locationMessage').textContent,body:!!__osz.G.body,mapping:__osz.G.mapping,hp:__osz.G.you?.hp,lat:__osz.G.you?.lat,pending:[...__osz.G.pending.values()].map(x=>({a:x.a,why:x.result?.why}))})));throw e;});
 await p.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id&&b.searched),card.corpse);
 assert(!await p.evaluate(id=>__osz.G.corpses.find(b=>b.id===id).items.some(i=>i.code==='knife'),card.corpse));
 assert.deepEqual(errors,[]);console.log(JSON.stringify({fixtureFatalBleeding:true,actualDeath:true,newLife:true,ownerPack:true,compactRecovery:true,damagedGearExact:true,reloadStockConserved:true,errors}));
}finally{await browser.close();}
