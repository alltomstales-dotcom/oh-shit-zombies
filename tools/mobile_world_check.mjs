// Requires Playwright + Chromium. Use OSZ_PLAYWRIGHT_MODULE for an existing installation.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base=process.argv[2]||'http://127.0.0.1:8016',phone={...devices['Pixel 7'],viewport:{width:393,height:851}};
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 let c=await browser.newContext({...phone,permissions:['geolocation'],geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage();
 await p.goto(base+'/?auto=desk&name=WorldUiScout');await p.waitForFunction(()=>__osz.G.buildings.some(b=>b.rooms.length>1),null,{timeout:65000});
 const b=await p.evaluate(()=>__osz.G.buildings.find(b=>b.rooms.length>1));await c.close();
 c=await browser.newContext({...phone,permissions:['geolocation'],geolocation:{latitude:b.rooms[0].pos[0],longitude:b.rooms[0].pos[1],accuracy:8}});p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=WorldDrawerCheck');await p.waitForFunction(id=>__osz.G.inside===id&&!__osz.G.launchPending,b.id,{timeout:65000});
 const before=await p.evaluate(()=>__osz.G.body.items);
 const search=p.getByRole('button',{name:/^SEARCH (?!BUILDING)/}).first();await search.tap();
 await p.waitForFunction(()=>!document.getElementById('sceneDrawer').hidden&&__osz.G.lootShelves.some(s=>s.items.length),null,{timeout:20000});
 assert.deepEqual(await p.evaluate(()=>__osz.G.body.items),before,'search must not auto take');
 const shelf=await p.evaluate(()=>__osz.G.lootShelves.find(s=>s.id===__osz.G.drawer.id));
 await p.screenshot({path:'/tmp/osz-world-drawer-phone.png'});
 const layout=await p.evaluate(()=>{const d=document.getElementById('sceneDrawer').getBoundingClientRect(),s=document.getElementById('bSwing').getBoundingClientRect();return {height:d.height,viewport:innerHeight,drawerBottom:d.bottom,swingTop:s.top,overflow:document.documentElement.scrollWidth>innerWidth,origin:__osz.G.screenOrigin};});
 assert(layout.height/layout.viewport<=.4);assert(layout.drawerBottom<layout.swingTop);assert(!layout.overflow);
 const row=shelf.items[0],previous=before.filter(i=>i.code===row.code).reduce((n,i)=>n+i.qty,0);
 await p.locator('#drawerContent .loot-row').first().getByRole('button',{name:'Take 1',exact:true}).tap();
 await p.waitForFunction(({code,n})=>__osz.G.body.items.filter(i=>i.code===code).reduce((n,i)=>n+i.qty,0)===n,{code:row.code,n:previous+1});
 const remainder=await p.evaluate(id=>__osz.G.lootShelves.find(s=>s.id===id),shelf.id);
 assert.equal(remainder.items.find(i=>i.id===row.id)?.qty||0,row.qty-1);
 // Existing pack remains compact; expanding is optional. Combat closes it immediately.
 await p.locator('#drawerClose').tap();await p.locator('#bPack').tap();assert(await p.locator('#panel').isVisible());
 const packHeight=await p.locator('#panel .sheet').evaluate(e=>e.getBoundingClientRect().height);assert(packHeight/851<=.4);
 await p.locator('#panelExpand').tap();await p.locator('#bShove').tap();await p.waitForFunction(()=>document.getElementById('panel').hidden);
 // Escape uses actual UI, through the real generated layout.
 await p.getByRole('button',{name:'EXIT BUILDING',exact:true}).tap();await p.waitForFunction(id=>__osz.G.inside!==id,b.id,{timeout:120000});
 await p.screenshot({path:'/tmp/osz-world-outside-phone.png'});
 assert.deepEqual(errors,[]);
 await c.storageState({path:'/tmp/osz-world-ui-storage.json'});fs.chmodSync('/tmp/osz-world-ui-storage.json',0o600);
 fs.writeFileSync('/tmp/osz-world-ui-evidence.json',JSON.stringify({base,shelf:remainder,building:b.id,start:b.rooms[0].pos}));
 console.log(JSON.stringify({searchLeavesLoot:true,oneItemTaken:true,remainder:true,compactDrawer:true,combatUsable:true,physicallyExited:true,errors,layout}));
}finally{await browser.close();}
