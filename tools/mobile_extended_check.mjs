// Sustained normal-server exploration with real canvas taps; optional duration is milliseconds.
// No injected world state. A scripted outing is browser acceptance, not a human phone review.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8025',duration=Number(process.argv[3]||600000);
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const c=await browser.newContext({...devices['Pixel 7'],viewport:{width:393,height:851},permissions:['geolocation'],geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage(),errors=[];
 p.on('pageerror',e=>errors.push(e.message));await p.goto(base+'/?auto=desk&name=ExtendedExplorer');
 await p.waitForFunction(()=>__osz.G.you&&__osz.G.body&&__osz.G.located&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
 const start=Date.now(),stats={legs:0,metres:0,minimumHp:100,minimumFps:60,overviewChecks:0,chooserChecks:0};let previous=await p.evaluate(()=>[__osz.G.you.lat,__osz.G.you.lng]),angle=0,lastReport=0,lastOverview=0;
 while(Date.now()-start<duration){
  const s=await p.evaluate(()=>({dead:__osz.G.dead,hp:__osz.G.you.hp,fps:__osz.G.fps,at:[__osz.G.you.lat,__osz.G.you.lng],chasing:__osz.G.chasing,engaged:__osz.G.engaged,inside:__osz.G.inside}));assert(!s.dead,'explorer remains alive');
  stats.minimumHp=Math.min(stats.minimumHp,s.hp);stats.minimumFps=Math.min(stats.minimumFps,s.fps);stats.metres+=Math.hypot((s.at[0]-previous[0])*111320,(s.at[1]-previous[1])*111320*Math.cos(s.at[0]*Math.PI/180));previous=s.at;
  if(s.engaged){await p.locator('#bShove').tap();if(await p.locator('#bBack').isVisible())await p.locator('#bBack').tap();}
  if(s.inside){await p.getByRole('button',{name:'EXIT BUILDING',exact:true}).tap();await p.waitForTimeout(1500);continue;}
  if(Date.now()-lastOverview>90000&&!s.chasing&&!s.engaged){
   await p.locator('#bArea').tap();await p.waitForFunction(()=>__osz.area.on&&__osz.area.data,null,{timeout:10000});
   assert(await p.evaluate(()=>__osz.area.data.known>0));stats.overviewChecks++;
   await p.screenshot({path:'/tmp/osz-extended-overview.png'});await p.locator('#areaBack').tap();lastOverview=Date.now();
   if(await p.locator('#bInteract').isVisible()){await p.locator('#bInteract').tap();assert(await p.locator('#sceneDrawer').isVisible());stats.chooserChecks++;await p.locator('#drawerClose').tap();}
  }
  if(await p.locator('#worldClose').isVisible())await p.locator('#worldClose').tap();
  const target=await p.evaluate(async angle=>{
   const {clear}=await import('/js/buildings.js'),{shiftLL,deltaM}=await import('/js/map.js'),{hitOpening}=await import('/js/world-ui.js'),{hitWork}=await import('/js/work.js'),{corpseHit}=await import('/js/body-hit.js'),G=__osz.G;
   const top=document.getElementById('navigation').getBoundingClientRect().bottom+12;
   const near=[...G.zeds.values()].map(z=>({ll:z.p.b,d:Math.hypot(...deltaM(...G.desk,...z.p.b))})).filter(z=>z.d<16).sort((a,b)=>a.d-b.d)[0];
   if(near){const [dx,dy]=deltaM(...G.desk,...near.ll);angle=Math.atan2(-dy,-dx);}
   for(const radius of [7,12,18])for(let i=0;i<16;i++){
    const a=angle+(i%2?-1:1)*Math.ceil(i/2)*Math.PI/8,ll=shiftLL(...G.desk,Math.cos(a)*radius,Math.sin(a)*radius),[x,y]=__osz.project(...ll);
    if(x<50||x>343||y<Math.max(220,top)||y>490||hitOpening(x,y)||hitWork(x,y)||!clear(G.buildings,G.desk,ll)||G.buildings.some(b=>b.outline.length&&b.rooms.length&&b.outline.some(p=>Math.hypot(...deltaM(...ll,...p))<.5)))continue;
    if(G.stashes.some(s=>{const [sx,sy]=__osz.project(s[1],s[2]);return Math.hypot(x-sx,y-sy+18)<34;}))continue;
    if(G.corpses.some(b=>{const [bx,by]=__osz.project(b.lat,b.lng);return corpseHit(x,y,bx,by,Math.max(48,Math.min(120,4.6*G.cam.ppm)),1,b.variant)!==null;}))continue;
    const occupied=[...G.stashes.map(s=>({lat:s[1],lng:s[2]})),...G.corpses,...G.body.survival.objects,...G.body.survival.resources];
    if(occupied.some(o=>Math.hypot(...deltaM(...ll,o.lat,o.lng))<2))continue;
    return {xy:[x,y],angle:a};
   }
  },angle);
  if(target){await p.touchscreen.tap(...target.xy);angle=target.angle;const accepted=await p.evaluate(()=>!!__osz.G.goal||!!__osz.G.routePending);if(accepted)stats.legs++;else angle+=Math.PI/3;}else angle+=Math.PI/3;
  await p.waitForTimeout(1300);
  if(Date.now()-start-lastReport>60000){lastReport=Date.now()-start;console.log(JSON.stringify({seconds:Math.round(lastReport/1000),...stats,metres:Math.round(stats.metres),navigation:await p.evaluate(()=>({selection:__osz.G.selection?.kind,goal:!!__osz.G.goal,navBottom:Math.round(document.getElementById('navigation').getBoundingClientRect().bottom)}))}));}
 }
 if(await p.locator('#bStop').isEnabled())await p.locator('#bStop').tap();assert(stats.legs>10&&stats.metres>50);assert.deepEqual(errors,[]);
 await p.screenshot({path:'/tmp/osz-extended-world.png'});console.log(JSON.stringify({seconds:Math.round((Date.now()-start)/1000),...stats,metres:Math.round(stats.metres),errors}));
}finally{await browser.close();}
