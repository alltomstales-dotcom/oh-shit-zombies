// Two independent browser players: ordinary GPS/map/home/stock, no injected world objects.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8035';
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const phone={...devices['Pixel 7'],permissions:['geolocation']};
 let scout=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),s=await scout.newPage();
 await s.goto(base+'/?auto=desk&name=BaseScout');await s.waitForFunction(()=>__osz.G.buildings.some(b=>b.stairs&&b.rooms.length<=2),null,{timeout:90000});
 const at=await s.evaluate(()=>__osz.G.buildings.find(b=>b.stairs&&b.rooms.length<=2).stairs);await scout.close();
 const location={latitude:at[0],longitude:at[1],accuracy:8},errors=[];
 const owner=await browser.newContext({...phone,geolocation:location}),member=await browser.newContext({...phone,geolocation:location});
 async function launch(c,name){const p=await c.newPage();p.on('pageerror',e=>errors.push(e.message));await p.goto(base+'/?auto=desk&name='+name);await p.waitForFunction(()=>__osz.G.inside&&__osz.G.body&&!__osz.G.mapping&&!__osz.G.launchPending,null,{timeout:90000});return p;}
 async function home(p){await p.locator('#bPack').tap();await p.locator('[data-pack-tab="home"]').tap();}
 async function makeHome(p,name){await home(p);await p.locator('#homeName').fill(name);await p.locator('#setHome').tap();await p.waitForFunction(name=>__osz.G.body.home?.name===name,name);}
 const stock=p=>p.evaluate(()=>__osz.G.body.home?.items.filter(i=>i.code==='water').reduce((n,i)=>n+i.qty,0)||0);
 const carried=p=>p.evaluate(()=>__osz.G.body.items.filter(i=>i.code==='water').reduce((n,i)=>n+i.qty,0));
 async function deposit(p){const before=await stock(p);await p.locator('#homePack [data-item="water"]').getByRole('button',{name:'Store',exact:true}).tap();await p.waitForFunction(n=>__osz.G.body.home.items.filter(i=>i.code==='water').reduce((sum,i)=>sum+i.qty,0)===n,before+1);}
 let a=await launch(owner,'BaseOwner'),b=await launch(member,'BaseMember');
 await makeHome(a,'Team shelter');await makeHome(b,'Private shelter');await deposit(b);
 await a.locator('#baseSharing summary').tap();await a.locator('#baseInvite').tap();await a.waitForFunction(()=>document.getElementById('baseCode').value.length>=16);
 const code=await a.locator('#baseCode').inputValue();await deposit(a);console.log('stage: owner invite and private stocks');
 await b.locator('#baseSharing summary').tap();await b.locator('#baseJoinCode').fill(code);await b.locator('#baseJoin').tap();
 await b.waitForFunction(()=>__osz.G.body.base.role==='builder'&&__osz.G.body.home.name==='Team shelter');
 await b.waitForFunction(()=>__osz.G.allies?.size===1);
 await b.locator('#panelClose').tap();
 const furniture=await b.evaluate(()=>__osz.G.body.survival.objects.filter(o=>o.generated&&o.building===__osz.G.inside).sort((a,b)=>Math.hypot((a.lat-__osz.G.you.lat)*111320,(a.lng-__osz.G.you.lng)*111320*Math.cos(a.lat*Math.PI/180))-Math.hypot((b.lat-__osz.G.you.lat)*111320,(b.lng-__osz.G.you.lng)*111320*Math.cos(b.lat*Math.PI/180)))[0]);assert(furniture);
 await b.evaluate(o=>__osz.walkTo([o.lat,o.lng]),furniture);await b.waitForFunction(id=>__osz.G.body.survival.objects.some(o=>o.id===id&&o.reachable),furniture.id,{timeout:30000});await b.locator('#bStop').click({force:true});
 await b.locator('#bInteract').tap();await b.locator('[data-nearby="object"][data-entity="'+furniture.id+'"]').tap();await b.getByRole('button',{name:'More',exact:true}).tap();await b.getByRole('button',{name:'Dismantle',exact:true}).tap();
 await b.waitForFunction(id=>!__osz.G.body.survival.objects.some(o=>o.id===id)&&!__osz.G.channel,furniture.id,{timeout:30000});
 await a.waitForFunction(id=>!__osz.G.body.survival.objects.some(o=>o.id===id),furniture.id,{timeout:20000});
 await b.locator('#drawerClose').tap();await b.evaluate(at=>__osz.walkTo(at),at);await b.waitForFunction(()=>__osz.G.body.home.reachable,null,{timeout:30000});await b.locator('#bStop').click({force:true});await home(b);
 console.log('stage: member work changes canonical shared furniture');
 assert.equal(await stock(b),1);const before=await carried(b);
 await b.locator('#homeItems [data-item="water"]').getByRole('button',{name:'Retrieve',exact:true}).tap();
 await b.waitForFunction(n=>__osz.G.body.items.filter(i=>i.code==='water').reduce((sum,i)=>sum+i.qty,0)===n,before+1);
 await a.waitForFunction(()=>__osz.G.body.home.items.every(i=>i.code!=='water'));
 await a.close();await deposit(b);console.log('stage: conserved shared transfer while owner absent');
 // Chromium's static geolocation emulation can retain the old timestamp; deliver a fresh fix.
 await member.setGeolocation(location);await b.goto(base+'/?auto=desk&name=BaseMember');
 try{await b.waitForFunction(()=>__osz.G.body?.base.role==='builder'&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});}
 catch(e){console.log(await b.evaluate(()=>({dead:__osz.G.dead,role:__osz.G.body?.base?.role,launch:__osz.G.launchPending,mapping:__osz.G.mapping,hello:__osz.G.gotHello,life:__osz.G.lifeId,notice:document.getElementById('locationMessage').textContent})));throw e;}
 assert.equal(await stock(b),1);
 await home(b);await b.locator('#baseSharing summary').tap();await b.locator('#baseChoice').selectOption({label:'Personal home'});
 await b.waitForFunction(()=>__osz.G.body.home.name==='Private shelter');assert.equal(await stock(b),1);
 await b.locator('#baseChoice').selectOption({label:'Team shelter'});await b.waitForFunction(()=>__osz.G.body.home.name==='Team shelter');
 await owner.setGeolocation(location);a=await launch(owner,'BaseOwner');await home(a);await a.locator('#baseSharing summary').tap();
 await a.locator('#baseMembers').getByRole('button',{name:'Revoke',exact:true}).tap();
 await b.waitForFunction(()=>__osz.G.body.base.role==='owner'&&__osz.G.body.home.name==='Private shelter');assert.equal(await stock(b),1);
 await b.waitForFunction(()=>__osz.G.allies?.size===0);
 assert.equal(await b.locator('#baseChoice option').count(),1);
 await b.locator('#baseJoinCode').fill(code);await b.locator('#baseJoin').tap();await b.waitForTimeout(1200);assert.equal(await b.evaluate(()=>__osz.G.body.base.role),'owner');
 await b.screenshot({path:'/tmp/osz-base-phone.png'});assert.deepEqual(errors,[]);
 console.log(JSON.stringify({twoIndependentPlayers:true,inviteJoin:true,visibleTeammate:true,sharedWork:true,sharedStockConserved:true,ownerAbsentTransfer:true,reloadMembership:true,personalHomePreserved:true,ownerRevoke:true,oldCodeClosed:true,errors}));
 await owner.close();await member.close();
}finally{await browser.close();}
