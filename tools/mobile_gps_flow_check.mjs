// Geolocation API emulation: fresh launch, virtual walking, GPS drift and 0.5-mile travel.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8025',browser=await chromium.launch({headless:false,args:['--no-sandbox']});
const phone={...devices['Pixel 7'],viewport:{width:393,height:851},permissions:['geolocation']};
const metres=(a,b)=>Math.hypot((a[0]-b[0])*111320,(a[1]-b[1])*111320*Math.cos(a[0]*Math.PI/180));
try{
 let c=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage();
 await p.goto(base+'/?auto=desk&name=GPSScout');await p.waitForFunction(()=>__osz.G.buildings.some(b=>b.stairs),null,{timeout:90000});
 const b=await p.evaluate(()=>__osz.G.buildings.find(b=>b.stairs&&b.rooms.length<=2));await c.close();
 const gps=b.stairs;c=await browser.newContext({...phone,geolocation:{latitude:gps[0],longitude:gps[1],accuracy:8}});p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=GPSFlowCheck');
 const ready=()=>p.waitForFunction(()=>__osz.G.located&&__osz.G.gpsCenter&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});await ready();
 assert(metres(await p.evaluate(()=>__osz.G.gpsCenter),gps)<.2);
 const direction=await p.evaluate(async()=>{const {shiftLL,deltaM}=await import('/js/map.js'),{clear}=await import('/js/buildings.js'),G=__osz.G;for(let i=0;i<16;i++){const a=i*Math.PI/8,ll=shiftLL(...G.desk,Math.cos(a)*3,Math.sin(a)*3);if(clear(G.buildings,G.desk,ll))return __osz.screenVector(Math.cos(a),Math.sin(a));}});assert(direction);
 const cd=await c.newCDPSession(p),touch=(type,pts)=>cd.send('Input.dispatchTouchEvent',{type,touchPoints:pts.map(([x,y,id])=>({x,y,id,radiusX:5,radiusY:5}))});
 await touch('touchStart',[[105,625,1]]);await touch('touchMove',[[105+65*direction[0],625+65*direction[1],1]]);await p.waitForTimeout(450);await touch('touchEnd',[]);if(await p.locator('#bStop').isEnabled())await p.locator('#bStop').tap();await p.waitForTimeout(1600);
 const virtual=await p.evaluate(()=>[__osz.G.you.lat,__osz.G.you.lng]);assert(metres(virtual,gps)>.7,'thumb walking changes the virtual position');
 for(let i=0;i<3;i++){await c.setGeolocation({latitude:gps[0]+(12+i)/111320,longitude:gps[1],accuracy:8});await p.waitForTimeout(900);}
 assert(metres(await p.evaluate(()=>[__osz.G.you.lat,__osz.G.you.lng]),virtual)<.6,'watch drift must not undo touch movement');
 assert(metres(await p.evaluate(()=>__osz.G.gpsCenter),gps)<.2);
 const travel=[gps[0]+1050/111320,gps[1]];
 for(let i=0;i<4;i++){await c.setGeolocation({latitude:travel[0]+i*.1/111320,longitude:travel[1],accuracy:8});await p.waitForTimeout(3100);}
 await p.waitForFunction(ll=>__osz.G.gpsCenter&&Math.abs(__osz.G.gpsCenter[0]-ll[0])*111320<2,travel,{timeout:20000});
 const anchor=await p.evaluate(()=>__osz.G.gpsCenter);assert(metres(anchor,travel)<2);
 // A new app opening must use current GPS, not the previous anchor.
 const relaunch=[gps[0]+500/111320,gps[1]];await c.setGeolocation({latitude:relaunch[0],longitude:relaunch[1],accuracy:8});await p.reload();await ready();
 assert(metres(await p.evaluate(()=>__osz.G.gpsCenter),relaunch)<.2);
 assert.deepEqual(errors,[]);console.log(JSON.stringify({newPlayerGPS:true,touchWalkSurvivesDrift:true,recenterAfterConsistent1050mTravel:true,freshLaunchUsesCurrentGPS:true,errors}));
}finally{await browser.close();}
