const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8025',browser=await chromium.launch({headless:false,args:['--no-sandbox']});
const phone={...devices['Pixel 7'],viewport:{width:393,height:851},permissions:['geolocation']};
try{
 let c=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage();
 await p.goto(base+'/?auto=desk&name=InteractScout');await p.waitForFunction(()=>__osz.G.buildings.some(b=>b.stairs),null,{timeout:90000});
 const b=await p.evaluate(()=>__osz.G.buildings.find(b=>b.stairs&&b.rooms.length<=2));await c.close();
 c=await browser.newContext({...phone,geolocation:{latitude:b.stairs[0],longitude:b.stairs[1],accuracy:8}});p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=InteractCheck');await p.waitForFunction(id=>__osz.G.inside===id&&__osz.G.stashes.length&&!__osz.G.launchPending,b.id,{timeout:90000});
 await p.locator('#bInteract').tap();await p.locator('[data-nearby="stairs"]').tap();
 assert.equal(await p.evaluate(()=>__osz.G.selection.kind),'stairs');assert(await p.locator('#sceneDrawer').isHidden());
 await p.getByRole('button',{name:'Upstairs',exact:true}).tap();await p.waitForFunction(()=>__osz.G.you.floor===1);
 await p.locator('#bInteract').tap();await p.waitForFunction(()=>document.querySelector('[data-nearby="stash"]'));
 const shelves=await p.locator('[data-nearby="stash"]').count();await p.locator('[data-nearby="stash"]').first().tap();
 assert.equal(await p.evaluate(()=>__osz.G.selection.kind),'stash');assert(await p.locator('#worldCard').isVisible());
 assert(await p.locator('#panel').isHidden());assert(await p.locator('#bar').isVisible());assert(!await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth));
 await p.locator('#bInteract').tap();
 const windowChoice=p.locator('[data-nearby="opening"]',{hasText:/window/i}).first();
 let extraWindowSmash=false;
 if(await windowChoice.count()){await windowChoice.tap();await p.getByRole('button',{name:'More',exact:true}).tap();extraWindowSmash=await p.getByRole('button',{name:'Smash window',exact:true}).isVisible();assert(extraWindowSmash);}
 await p.screenshot({path:'/tmp/osz-interact-phone.png'});assert.deepEqual(errors,[]);
 console.log(JSON.stringify({nearbyStairs:true,normalStairAction:true,chooseUpperShelf:true,shelves,compact:true,combatVisible:true,extraWindowSmash,errors}));
}finally{await browser.close();}
