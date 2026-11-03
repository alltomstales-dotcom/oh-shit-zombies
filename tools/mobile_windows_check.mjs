// Local two-cloth fixture; real map/windows, channels, materials and persistence.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';const base=process.argv[2]||'http://127.0.0.1:8031';
const fixture=new URL(base).hostname==='127.0.0.1'&&process.argv[3]!=='earned';
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const phone={...devices['Pixel 7'],permissions:['geolocation']};let c=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage();
 await p.goto(base+'/?auto=desk&name=WindowScout');await p.waitForFunction(()=>__osz.G.buildings.some(b=>b.openings.some(o=>o.kind==='window')),null,{timeout:90000});
 const chosen=await p.evaluate(()=>{
  function inside(poly,point){let yes=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const [y,x]=poly[i],[y1,x1]=poly[j];if((y>point[0])!==(y1>point[0])&&point[1]<(x1-x)*(point[0]-y)/(y1-y)+x)yes=!yes;}return yes;}
  const buildings=__osz.G.buildings.filter(b=>b.rooms.length<=2);
  for(const b of buildings)for(const o of b.openings.filter(o=>o.kind==='window'&&!o.broken&&!o.curtain)){
   const lat=(o.a[0]+o.b[0])/2,lng=(o.a[1]+o.b[1])/2;
   for(const [east,north] of [[0,1],[0,-1],[1,0],[-1,0]]){
    const at=[lat+north/111320,lng+east/(111320*Math.cos(lat*Math.PI/180))];if(inside(b.outline,at))return {building:b.id,opening:o.id,at};
   }
  }
 });assert(chosen);await c.close();
 c=await browser.newContext({...phone,geolocation:{latitude:chosen.at[0],longitude:chosen.at[1],accuracy:8}});p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=WindowCheck');await p.waitForFunction(id=>__osz.G.inside===id&&__osz.G.body&&!__osz.G.mapping&&!__osz.G.launchPending,chosen.building,{timeout:90000});
 const find=()=>p.evaluate(id=>__osz.G.buildings.flatMap(b=>b.openings).find(o=>o.id===id),chosen.opening);
 async function select(){await p.locator('#bInteract').tap();await p.locator('[data-nearby="opening"][data-entity="'+chosen.opening+'"]').tap();}
 const cloth=()=>p.evaluate(()=>__osz.G.body.items.filter(i=>i.code==='cloth').reduce((n,i)=>n+i.qty,0));
 if(!fixture){
  await p.locator('#bPack').tap();await p.locator('[data-pack-tab="home"]').tap();await p.locator('#setHome').tap();await p.waitForFunction(()=>__osz.G.body.home);await p.locator('#panelClose').tap();
  const furniture=await p.evaluate(()=>__osz.G.body.survival.objects.filter(o=>o.generated&&o.building===__osz.G.inside).sort((a,b)=>Math.hypot((a.lat-__osz.G.you.lat)*111320,(a.lng-__osz.G.you.lng)*111320*Math.cos(a.lat*Math.PI/180))-Math.hypot((b.lat-__osz.G.you.lat)*111320,(b.lng-__osz.G.you.lng)*111320*Math.cos(b.lat*Math.PI/180)))[0]);assert(furniture,'generated furniture to salvage');
  await p.evaluate(o=>__osz.walkTo([o.lat,o.lng]),furniture);await p.waitForFunction(id=>__osz.G.body.survival.objects.some(o=>o.id===id&&o.reachable),furniture.id,{timeout:30000});await p.locator('#bStop').click({force:true});
  await p.locator('#bInteract').tap();await p.locator('[data-nearby="object"][data-entity="'+furniture.id+'"]').tap();await p.getByRole('button',{name:'More',exact:true}).tap();await p.getByRole('button',{name:'Dismantle',exact:true}).tap();
  await p.waitForFunction(()=>__osz.G.body.items.some(i=>i.code==='cloth'&&i.qty>=2)&&!__osz.G.channel,null,{timeout:30000});await p.locator('#drawerClose').tap();
  await p.evaluate(at=>__osz.walkTo(at),chosen.at);await p.waitForFunction(at=>Math.hypot((__osz.G.you.lat-at[0])*111320,(__osz.G.you.lng-at[1])*111320*Math.cos(at[0]*Math.PI/180))<.9,chosen.at,{timeout:30000});await p.locator('#bStop').click({force:true});
  console.log('stage: cloth earned from furniture');
 }
 await p.waitForFunction(()=>__osz.G.body.items.some(i=>i.code==='cloth'&&i.qty>=2),null,{timeout:20000});const before=await cloth();await select();await p.getByRole('button',{name:'More',exact:true}).tap();
 await p.getByRole('button',{name:'Hang curtain (2 cloth)',exact:true}).tap();await p.waitForFunction(id=>__osz.G.buildings.flatMap(b=>b.openings).some(o=>o.id===id&&o.curtain_closed),chosen.opening,{timeout:15000});
 assert.equal(await cloth(),before-2);console.log('stage: curtain hung');await p.reload();
 await p.waitForFunction(id=>__osz.G.buildings.flatMap(b=>b.openings).some(o=>o.id===id&&o.curtain_closed),chosen.opening,{timeout:90000});assert.equal(await cloth(),before-2);await select();await p.getByRole('button',{name:'More',exact:true}).tap();
 await p.getByRole('button',{name:'Open curtain',exact:true}).tap();await p.waitForFunction(id=>__osz.G.buildings.flatMap(b=>b.openings).some(o=>o.id===id&&!o.curtain_closed),chosen.opening);
 await p.getByRole('button',{name:'Close curtain',exact:true}).tap();await p.waitForFunction(id=>__osz.G.buildings.flatMap(b=>b.openings).some(o=>o.id===id&&o.curtain_closed),chosen.opening);
 await p.getByRole('button',{name:'Remove curtain',exact:true}).tap();await p.waitForFunction(id=>__osz.G.buildings.flatMap(b=>b.openings).some(o=>o.id===id&&!o.curtain),chosen.opening);assert.equal(await cloth(),before);
 console.log('stage: curtain returned');await p.getByRole('button',{name:'Smash window',exact:true}).tap();await p.waitForFunction(id=>__osz.G.buildings.flatMap(b=>b.openings).some(o=>o.id===id&&o.broken),chosen.opening);await p.waitForTimeout(1000);
 await p.getByRole('button',{name:'Clear glass',exact:true}).tap();await p.waitForFunction(id=>__osz.G.buildings.flatMap(b=>b.openings).some(o=>o.id===id&&o.glass_cleared),chosen.opening,{timeout:15000});
 await p.screenshot({path:'/tmp/osz-window-phone.png'});await p.getByRole('button',{name:'Climb through',exact:true}).tap();await p.waitForFunction(()=>!__osz.G.inside&&!__osz.G.channel,null,{timeout:20000});await p.waitForTimeout(1800);assert(!await p.evaluate(()=>__osz.G.inside),'client must not pull the player back through the window');
 assert(await p.locator('#panel').isHidden());assert.deepEqual(errors,[]);console.log(JSON.stringify({clothFixture:fixture,earnedCloth:!fixture,hangOpenCloseRemove:true,curtainReload:true,materialsConserved:true,clearGlass:true,climbOutside:true,noPositionPullback:true,errors}));
}finally{await browser.close();}
