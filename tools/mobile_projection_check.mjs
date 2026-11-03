// Real canvas taps and touch stick in the isometric world, no injected game state.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8023',browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const c=await browser.newContext({...devices['Pixel 7'],viewport:{width:393,height:851},permissions:['geolocation'],geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=ProjectionCheck');await p.waitForFunction(()=>__osz.G.you&&__osz.G.located&&__osz.G.body&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
 assert(await p.evaluate(()=>__osz.G.cam.iso));
 const choose=()=>p.evaluate(async()=>{
  const {clear}=await import('/js/buildings.js'),{shiftLL,deltaM}=await import('/js/map.js'),G=__osz.G;
  const obstacles=[...(G.body?.survival.objects||[]),...(G.body?.survival.resources||[]),...G.corpses,...G.stashes.map(s=>({lat:s[1],lng:s[2]}))];
  for(let i=0;i<32;i++){
   const a=i*Math.PI/16,ll=shiftLL(...G.desk,Math.cos(a)*4,Math.sin(a)*4),px=__osz.project(...ll);
   if(!clear(G.buildings,G.desk,ll)||px[0]<40||px[0]>350||px[1]<245||px[1]>510||obstacles.some(o=>Math.hypot(...deltaM(...ll,o.lat,o.lng))<2))continue;
   return {ll,px,start:[...G.desk]};
  }
 });
 let target=await choose();assert(target,'find a clear tap target in real terrain');
 await p.touchscreen.tap(...target.px);
 await p.waitForFunction(ll=>Math.hypot((__osz.G.desk[0]-ll[0])*111320,(__osz.G.desk[1]-ll[1])*111320*Math.cos(ll[0]*Math.PI/180))<.5,target.ll,{timeout:20000});
 target=await choose();assert(target);
 const vector=await p.evaluate(({ll,start})=>__osz.screenVector((ll[1]-start[1])*111320*Math.cos(start[0]*Math.PI/180),(ll[0]-start[0])*111320),target);
 const cd=await c.newCDPSession(p),touch=(type,pts)=>cd.send('Input.dispatchTouchEvent',{type,touchPoints:pts.map(([x,y,id])=>({x,y,id,radiusX:5,radiusY:5}))});
 await touch('touchStart',[[105,625,1]]);await touch('touchMove',[[105+vector[0]*65,625+vector[1]*65,1]]);await p.waitForTimeout(400);await touch('touchEnd',[]);
 const alignment=await p.evaluate(({ll,start})=>{const G=__osz.G,mx=111320*Math.cos(start[0]*Math.PI/180),a=[(ll[1]-start[1])*mx,(ll[0]-start[0])*111320],b=[(G.desk[1]-start[1])*mx,(G.desk[0]-start[0])*111320];return {distance:Math.hypot(...b),cosine:(a[0]*b[0]+a[1]*b[1])/(Math.hypot(...a)*Math.hypot(...b))};},target);
 assert(alignment.distance>.2&&alignment.cosine>.98,'thumb direction agrees with the projected tap direction');
 await p.screenshot({path:'/tmp/osz-isometric-world.png'});assert.deepEqual(errors,[]);
 console.log(JSON.stringify({isometric:true,realTapWalk:true,realThumbAligned:alignment,errors}));
}finally{await browser.close();}
