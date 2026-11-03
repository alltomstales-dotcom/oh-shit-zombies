// Real selectors, ordinary GPS placement, persisted roles and new-life UI.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8033',fatal=process.argv[3]==='fatal';
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const c=await browser.newContext({...devices['Pixel 7'],permissions:['geolocation'],geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}});
 const p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?name=BackgroundCheck');
 await p.waitForFunction(()=>!document.getElementById('backgroundOccupation').disabled);
 await p.locator('#backgroundOccupation').selectOption('medic');await p.locator('#backgroundTrait').selectOption('nimble');
 await p.screenshot({path:'/tmp/osz-background-title.png'});
 await p.locator('#goWalk').tap();
 await p.waitForFunction(()=>__osz.G.body?.background?.occupation==='medic'&&!__osz.G.backgroundBusy&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
 const profile=await p.evaluate(()=>({background:__osz.G.body.background,items:__osz.G.body.items,life:__osz.G.lifeId}));
 assert.equal(profile.background.trait,'nimble');assert.equal(profile.items.filter(i=>i.code==='disinfectant').reduce((n,i)=>n+i.qty,0),1);
 console.log('stage: saved medic/nimble at GPS');
 await p.locator('#bPack').tap();await p.locator('[data-pack-tab="status"]').tap();
 assert.match(await p.locator('#backgroundStatus').innerText(),/Medic.*Nimble/);
 await p.screenshot({path:'/tmp/osz-background-health.png'});await p.locator('#panelClose').tap();
 // Future-life preferences must not respec a currently living survivor.
 await p.evaluate(()=>{localStorage.setItem('osz.occupation','firefighter');localStorage.setItem('osz.trait','sturdy');});
 if(!fatal){await c.setGeolocation({latitude:44.9778,longitude:-93.265,accuracy:8});await p.goto(base+'/?auto=desk&name=BackgroundCheck');
 try{await p.waitForFunction(()=>__osz.G.body?.background&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});}
 catch(e){console.log(await p.evaluate(()=>({dead:__osz.G.dead,background:__osz.G.body?.background,busy:__osz.G.backgroundBusy,launch:__osz.G.launchPending,mapping:__osz.G.mapping,hello:__osz.G.gotHello,notice:document.getElementById('locationMessage').textContent})));throw e;}
 console.log('stage: existing life reloaded');
 assert.equal(await p.evaluate(()=>__osz.G.body.background.occupation),'medic');
 assert.equal(await p.evaluate(()=>__osz.G.body.items.filter(i=>i.code==='disinfectant').reduce((n,i)=>n+i.qty,0)),1);
 }
 if(fatal){
  assert.equal(new URL(base).hostname,'127.0.0.1','fatal fixture is local only');
  await p.waitForFunction(()=>__osz.G.dead,null,{timeout:30000});
  await p.locator('#deathBackgroundOccupation').selectOption('firefighter');await p.locator('#deathBackgroundTrait').selectOption('sturdy');
  await c.setGeolocation({latitude:44.9778,longitude:-93.265,accuracy:8});
  await p.locator('#bAgain').tap();
  await p.waitForFunction(()=>!__osz.G.dead&&__osz.G.body?.background?.occupation==='firefighter'&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
  assert.equal(await p.evaluate(()=>__osz.G.body.background.trait),'sturdy');
  assert.notEqual(await p.evaluate(()=>__osz.G.lifeId),profile.life);
  assert.equal(await p.evaluate(()=>__osz.G.body.items.filter(i=>i.code==='gloves').reduce((n,i)=>n+i.qty,0)),1);
  assert.equal(await p.evaluate(()=>__osz.G.body.items.filter(i=>i.code==='disinfectant').reduce((n,i)=>n+i.qty,0)),0);
 }
 assert.deepEqual(errors,[]);console.log(JSON.stringify({mobileSelectors:true,gpsAfterSavedChoice:true,roleReload:!fatal,noRepeatedGear:!fatal,futurePreferenceNotRespec:!fatal,deathNewRole:fatal,errors}));
 await c.close();
}finally{await browser.close();}
