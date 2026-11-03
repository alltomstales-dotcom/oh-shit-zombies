// Requires Playwright + Chromium; optional OSZ_PLAYWRIGHT_MODULE override.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8017', browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 let c=await browser.newContext({...devices['Pixel 7'],permissions:['geolocation'],geolocation:{latitude:44.965,longitude:-93.282,accuracy:8}}),p=await c.newPage();
 await p.goto(base+'/?auto=desk&name=RoomScout');
 await p.waitForFunction(()=>__osz.G.buildings.some(b=>b.rooms.some(r=>['Kitchen','Bathroom','Bedroom'].includes(r.name))),null,{timeout:90000});
 const room=await p.evaluate(()=>{const b=__osz.G.buildings.find(b=>b.rooms.some(r=>['Kitchen','Bathroom','Bedroom'].includes(r.name)));return {building:b.id,...b.rooms.find(r=>['Kitchen','Bathroom','Bedroom'].includes(r.name))};});
 await c.close();c=await browser.newContext({...devices['Pixel 7'],permissions:['geolocation'],geolocation:{latitude:room.pos[0],longitude:room.pos[1],accuracy:8}});p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=RoomShelfCheck');
 await p.waitForFunction(({building,id})=>__osz.G.inside===building&&__osz.G.stashes.some(s=>s[0]==='room:'+id&&s[7])&&!__osz.G.launchPending,room,{timeout:90000});
 await p.getByRole('button',{name:/^SEARCH (?!BUILDING)/}).first().tap();
 await p.waitForFunction(()=>!document.getElementById('sceneDrawer').hidden&&__osz.G.lootShelves.some(s=>s.items.length),null,{timeout:20000});
 const data=await p.evaluate(()=>{const G=__osz.G,s=G.lootShelves.find(s=>s.id===G.drawer.id);return {room:s.room,kind:s.kind,items:s.items.map(i=>i.code),beans:G.items.beans,personal:G.items.soap,text:document.getElementById('drawerContent').textContent,personalIcon:G.items.soap.kind};});
 assert.equal(data.kind,room.name.toLowerCase());assert.equal(data.beans.hunger,25);assert(data.personal.description);assert.equal(data.personalIcon,'personal');
 if(data.kind==='kitchen')assert.match(data.text,/Hunger −25|Thirst −45/);
 await p.screenshot({path:'/tmp/osz-themed-shelf-phone.png'});assert.deepEqual(errors,[]);
 console.log(JSON.stringify({themedShelf:data.kind,items:data.items,foodStatsExposed:true,personalDescriptionExposed:true,errors}));
}finally{await browser.close();}
