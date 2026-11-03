// Run after a local restart or app replacement with the first harness's private test evidence.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
import fs from 'node:fs';
const e=JSON.parse(fs.readFileSync(process.argv[2]||'/tmp/osz-world-ui-evidence.json')),base=e.base;
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const c=await browser.newContext({...devices['Pixel 7'],viewport:{width:393,height:851},storageState:process.argv[3]||'/tmp/osz-world-ui-storage.json',permissions:['geolocation'],geolocation:{latitude:e.start[0],longitude:e.start[1],accuracy:8}}),p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));let newSessions=0;p.on('request',r=>{if(new URL(r.url()).pathname==='/api/session')newSessions++;});
 await p.goto(base+'/?auto=desk');await p.waitForFunction(id=>__osz.G.lootShelves?.some(s=>s.id===id)&&!__osz.G.launchPending,e.shelf.id,{timeout:65000});
 const shelf=await p.evaluate(id=>__osz.G.lootShelves.find(s=>s.id===id),e.shelf.id);assert.deepEqual(shelf.items,e.shelf.items);assert.equal(shelf.revision,e.shelf.revision);
 console.log('beforeInteriorReady',await p.evaluate(()=>({mapping:__osz.G.mapping,inside:__osz.G.inside,shelfVisible:__osz.G.stashes.some(s=>s[4]&&s[8]!==false)})));await p.waitForFunction(({id,b})=>__osz.G.inside===b&&__osz.G.stashes.some(s=>s[0]===id&&s[8]!==false),{id:e.shelf.id,b:e.building},{timeout:65000});await p.waitForTimeout(1200);
 async function tapAt(lat,lng,offset=18){const xy=await p.evaluate(({lat,lng,offset})=>{const G=__osz.G,ll=G.screenLL,o=G.screenOrigin;return [o[0]+(lng-ll[1])*111320*Math.cos(ll[0]*Math.PI/180)*G.cam.ppm,o[1]-(lat-ll[0])*111320*G.cam.ppm-offset];},{lat,lng,offset});await p.touchscreen.tap(...xy);}
 await tapAt(shelf.lat,shelf.lng);await p.waitForFunction(id=>__osz.G.selection?.kind==='stash'&&__osz.G.selection.id===id,e.shelf.id);await p.getByRole('button',{name:'Look inside',exact:true}).tap();assert(await p.locator('#sceneDrawer').isVisible());
 await p.locator('#drawerClose').tap();
 // Pick a visible furniture icon; it opens its own card, not the Work catalogue.
 const bed=await p.evaluate(()=>__osz.G.body.survival.objects.find(o=>o.kind==='bed'&&o.building===__osz.G.inside));assert(bed);await tapAt(bed.lat,bed.lng,15);await p.waitForFunction(id=>__osz.G.selection?.id===id,bed.id);assert(await p.locator('#worldCard').isVisible());assert(await p.locator('#panel').isHidden());
 const buttonIdentity=await p.locator('#worldActions button').first().evaluate(e=>{window.__stableWorldButton=e;return e.textContent;});await p.waitForTimeout(1800);assert(await p.locator('#worldActions button').first().evaluate(e=>e===window.__stableWorldButton),'world action target must stay stable during snapshots');
 await p.screenshot({path:'/tmp/osz-world-object-card.png'});
 await p.locator('#bPack').tap();await p.locator('#panelExpand').tap();await p.keyboard.press('ArrowLeft');await p.waitForFunction(()=>document.getElementById('panel').hidden);
 await p.setViewportSize({width:851,height:393});await p.locator('#bPack').tap();assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth),851);await p.screenshot({path:'/tmp/osz-world-landscape.png'});await p.locator('#bPack').tap();
 assert.equal(newSessions,0);if(process.env.OSZ_EXPECT_HOME==='1')assert.equal(await p.evaluate(()=>__osz.G.body.home?.building),e.building);assert.deepEqual(errors,[]);console.log(JSON.stringify({remainderSurvivedServerRestart:true,tapSelectsCorrectContainer:true,furnitureCard:true,stableActions:true,movementClosesExpandedPack:true,landscapeNoOverflow:true,errors}));
}finally{await browser.close();}
