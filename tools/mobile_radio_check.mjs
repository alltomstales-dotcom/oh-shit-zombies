// Normal map fixtures, GPS placement and scene card/drawer. No injected radios.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8037';
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const phone={...devices['Pixel 7'],permissions:['geolocation']};
 const scout=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),s=await scout.newPage();
 await s.goto(base+'/?auto=desk&name=RadioScout');await s.waitForFunction(()=>__osz.G.buildings.some(b=>b.stairs&&b.rooms.length<=2),null,{timeout:90000});
 console.log('stage: map loaded');const at=await s.evaluate(()=>__osz.G.buildings.find(b=>b.stairs&&b.rooms.length<=2).stairs);await scout.setGeolocation({latitude:at[0],longitude:at[1],accuracy:8});await s.reload();
 await s.waitForFunction(()=>__osz.G.body?.survival.objects.some(o=>o.kind==='radio')&&!__osz.G.mapping&&!__osz.G.launchPending,null,{timeout:90000});
 console.log('stage: inside with radio');const radio=await s.evaluate(()=>__osz.G.body.survival.objects.find(o=>o.kind==='radio'));await scout.close();
 const location={latitude:radio.lat,longitude:radio.lng,accuracy:8},c=await browser.newContext({...phone,geolocation:location}),p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=RadioCheck');await p.waitForFunction(id=>__osz.G.body?.survival.objects.some(o=>o.id===id&&o.reachable)&&!__osz.G.launchPending&&!__osz.G.mapping,radio.id,{timeout:90000});
 console.log('stage: reachable radio');const before=await p.evaluate(()=>__osz.G.body.items);
 async function listen(){await p.locator('#bInteract').tap();await p.locator('[data-nearby="object"][data-entity="'+radio.id+'"]').tap();await p.getByRole('button',{name:'Listen',exact:true}).tap();await p.waitForFunction(()=>__osz.G.drawer?.mode==='radio'&&__osz.G.broadcast?.lines.length>1);}
 await listen();assert(await p.locator('#drawerContent').innerText().then(s=>s.includes('world keeps moving')));assert(await p.locator('#world').count()||await p.locator('canvas').count());
 assert.deepEqual(await p.evaluate(()=>__osz.G.body.items),before);await p.screenshot({path:'/tmp/osz-radio-phone.png'});
 await c.setGeolocation(location);await p.reload();await p.waitForFunction(()=>__osz.G.body&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});await listen();
 assert.deepEqual(errors,[]);console.log(JSON.stringify({normalFixtureRadio:true,sceneListen:true,mapVisible:true,quietNoItemsConsumed:true,reload:true,errors}));await c.close();
}finally{await browser.close();}
