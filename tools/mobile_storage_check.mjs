// Normal server: create a home, deposit/withdraw via compact controls, then use
// a real household container and prove its stock survives reload.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8023',browser=await chromium.launch({headless:false,args:['--no-sandbox']});
const phone={...devices['Pixel 7'],viewport:{width:393,height:851},permissions:['geolocation']};
try{
 let c=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage();
 await p.goto(base+'/?auto=desk&name=StorageScout');await p.waitForFunction(()=>__osz.G.buildings.some(b=>b.rooms.length),null,{timeout:90000});
 const b=await p.evaluate(()=>__osz.G.buildings.find(b=>b.rooms.length));await c.close();
 c=await browser.newContext({...phone,geolocation:{latitude:b.rooms[0].pos[0],longitude:b.rooms[0].pos[1],accuracy:8}});p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=StorageCheck');await p.waitForFunction(id=>__osz.G.inside===id&&__osz.G.body&&!__osz.G.launchPending,b.id,{timeout:90000});
 const water=()=>p.evaluate(()=>__osz.G.body.items.filter(i=>i.code==='water').reduce((n,i)=>n+i.qty,0));
 const before=await water();assert(before>=1);
 await p.locator('#bPack').tap();await p.locator('[data-pack-tab="home"]').tap();await p.locator('#setHome').tap();await p.waitForFunction(()=>__osz.G.body.home);await p.locator('#panelClose').tap();
 await p.locator('#qStore').tap();assert.equal(await p.locator('#storageDeposit').getAttribute('aria-pressed'),'true');
 await p.locator('#drawerContent [data-item="water"]').getByRole('button',{name:'Store 1',exact:true}).tap();
 await p.waitForFunction(n=>__osz.G.body.items.filter(i=>i.code==='water').reduce((n,i)=>n+i.qty,0)===n,before-1);
 assert.equal(await p.locator('#drawerContent [data-item="schoolbag"]').getByRole('button',{name:'Store 1',exact:true}).isDisabled(),true);
 await p.locator('#storageWithdraw').tap();await p.locator('#drawerContent [data-item="water"]').getByRole('button',{name:'Take 1',exact:true}).tap();
 await p.waitForFunction(n=>__osz.G.body.items.filter(i=>i.code==='water').reduce((n,i)=>n+i.qty,0)===n,before);
 await p.locator('#drawerClose').tap();
 // Wheel and two-finger pinch use the same world projection as subsequent container taps.
 const oldPpm=await p.evaluate(()=>__osz.G.cam.ppm);
 await p.mouse.move(190,380);await p.mouse.wheel(0,-200);await p.waitForTimeout(1200);
 assert(await p.evaluate(()=>__osz.G.cam.ppm)>oldPpm*1.2,'wheel enlarges the interior');
 await p.locator('#bZoomReset').tap();await p.waitForTimeout(1500);
 const cd=await c.newCDPSession(p),touch=(type,pts)=>cd.send('Input.dispatchTouchEvent',{type,touchPoints:pts.map(([x,y,id])=>({x,y,id,radiusX:5,radiusY:5})),modifiers:0});
 const initial=await p.evaluate(()=>({position:[...__osz.G.desk],zoom:__osz.G.indoorZoom}));
 await touch('touchStart',[[130,390,1]]);await touch('touchStart',[[130,390,1],[260,390,2]]);
 await touch('touchMove',[[80,390,1],[310,390,2]]);await touch('touchEnd',[]);await p.waitForTimeout(1500);
 assert(await p.evaluate(()=>__osz.G.indoorZoom)>initial.zoom*1.5,'pinch enlarges the interior');
 assert.equal(await p.evaluate(()=>__osz.G.stick),null);assert.equal(await p.evaluate(()=>__osz.G.goal),null,'pinch release must not walk');
 const moved=await p.evaluate(pos=>Math.hypot((__osz.G.desk[0]-pos[0])*111320,(__osz.G.desk[1]-pos[1])*111320*Math.cos(pos[0]*Math.PI/180)),initial.position);assert(moved<.1);
 await p.locator('#bZoomReset').tap();await p.waitForTimeout(1500);
 const container=await p.evaluate(()=>__osz.G.body.home.containers.find(c=>c.capacity>0&&(!c.building||c.building===__osz.G.inside)));
 assert(container,'house has an actual reusable container');
 await p.evaluate(o=>__osz.walkTo([o.lat,o.lng]),container);
 await p.waitForFunction(id=>__osz.G.body.home.containers.some(c=>c.id===id&&c.reachable),container.id,{timeout:30000});
 await p.locator('#bStop').click({force:true});
 const xy=await p.evaluate(o=>{const [x,y]=__osz.project(o.lat,o.lng);return [x,y-12];},container);
 await p.touchscreen.tap(...xy);await p.waitForFunction(id=>__osz.G.selection?.id===id,container.id);
 await p.getByRole('button',{name:'Storage',exact:true}).tap();
 await p.locator('#drawerContent [data-item="water"]').getByRole('button',{name:'Store 1',exact:true}).tap();
 await p.waitForFunction(id=>__osz.G.body.home.containers.find(c=>c.id===id)?.items.some(i=>i.code==='water'),container.id);
 await p.locator('#storageWithdraw').tap();await p.screenshot({path:'/tmp/osz-storage-phone.png'});
 await p.reload();await p.waitForFunction(id=>__osz.G.body?.home?.containers.find(c=>c.id===id)?.items.some(i=>i.code==='water'),container.id,{timeout:65000});
 assert.equal(await water(),before-1);assert.deepEqual(errors,[]);
 console.log(JSON.stringify({cupboardDepositWithdraw:true,houseContainer:container.kind,containerDepositReload:true,wornBlocked:true,wheelAndPinch:true,pinchDidNotWalk:true,errors}));
}finally{await browser.close();}
