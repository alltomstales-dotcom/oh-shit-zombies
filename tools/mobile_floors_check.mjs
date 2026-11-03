// Real map, real stairs actions and authoritative floor state. No injected game objects.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8024',browser=await chromium.launch({headless:false,args:['--no-sandbox']});
const phone={...devices['Pixel 7'],viewport:{width:393,height:851},permissions:['geolocation']};
try{
 let c=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage();
 await p.goto(base+'/?auto=desk&name=FloorScout');await p.waitForFunction(()=>__osz.G.buildings.some(b=>b.stairs),null,{timeout:90000});
 const b=await p.evaluate(()=>__osz.G.buildings.find(b=>b.stairs&&b.rooms.length<=2));assert(b);console.log(JSON.stringify({stage:'chosen',building:b.id,rooms:b.rooms.length}));await c.close();
 c=await browser.newContext({...phone,geolocation:{latitude:b.stairs[0],longitude:b.stairs[1],accuracy:8}});p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=FloorCheck');
 await p.waitForFunction(id=>__osz.G.inside===id&&__osz.G.body&&!__osz.G.mapping,b.id,{timeout:90000});
 console.log('stage: inside');await p.locator('#bFloor').tap();await p.getByRole('button',{name:'Upstairs',exact:true}).tap();
 await p.waitForFunction(()=>__osz.G.you.floor===1,null,{timeout:20000});
 console.log('stage: upstairs');assert(await p.evaluate(()=>__osz.G.buildings.every(b=>b.floor===1||b.construction)));
 await p.waitForFunction(()=>__osz.G.stashes.length>0,null,{timeout:15000});
 const up=await p.evaluate(()=>({epoch:__osz.G.you.floor_epoch,stairs:__osz.G.buildings.find(b=>b.id===__osz.G.inside).stairs,stashes:__osz.G.stashes.map(s=>s[0])}));
 assert(up.stashes.length&&up.stashes.every(id=>id.includes(':f1:')),'upper room loot uses independent container ids');
 await p.locator('#bPack').tap();await p.locator('[data-pack-tab="home"]').tap();await p.locator('#setHome').tap();
 await p.waitForFunction(()=>__osz.G.body.home?.floor_level===1);await p.locator('#panelClose').tap();
 await p.locator('#qStore').tap();await p.locator('#drawerContent [data-item="water"]').getByRole('button',{name:'Store 1',exact:true}).tap();
 await p.waitForFunction(()=>__osz.G.body.home.items.some(i=>i.code==='water'));await p.locator('#drawerClose').tap();
 await p.screenshot({path:'/tmp/osz-upstairs-phone.png'});
 console.log('stage: stored');await p.reload();await p.waitForFunction(()=>__osz.G.you?.floor===0&&__osz.G.body&&!__osz.G.mapping&&!__osz.G.launchPending,null,{timeout:90000});
 assert(await p.evaluate(epoch=>__osz.G.you.floor_epoch>epoch,up.epoch),'new phone launch returns to current GPS on ground');
 assert(await p.evaluate(()=>__osz.G.body.home.items.some(i=>i.code==='water')),'upstairs cupboard stock survives reload');
 await p.locator('#bPack').tap();await p.locator('[data-pack-tab="home"]').tap();assert((await p.locator('#homeStatus').textContent()).includes('Floor 2'));await p.locator('#returnHome').tap();await p.waitForFunction(()=>__osz.G.selection?.kind==='stairs');
 await p.getByRole('button',{name:'Upstairs',exact:true}).tap();await p.waitForFunction(()=>__osz.G.you.floor===1);
 // Exit includes approaching the stairs and descending before opening a ground-floor exit.
 await p.getByRole('button',{name:'EXIT BUILDING',exact:true}).tap();
 await p.waitForFunction(()=>__osz.G.you.floor===0&&!__osz.G.inside&&!__osz.G.exitIntent,null,{timeout:60000});
 assert.deepEqual(errors,[]);console.log(JSON.stringify({stairsUp:true,distinctFloorLoot:true,phoneReloadAtCurrentGPS:true,upperHomeDepositReload:true,floorAwareHomeNavigation:true,automaticDescendAndExit:true,errors}));
}finally{await browser.close();}
