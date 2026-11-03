// Ordinary map discovery, actual GPS start and touch controls; no world injections.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8036';
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const phone={...devices['Pixel 7'],permissions:['geolocation']};
 let c=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage(),car;
 for(const [e,n] of [[0,0],[40,0],[-40,0],[0,40],[0,-40],[60,60],[-60,-60],[60,-60],[-60,60]]){
  await c.setGeolocation({latitude:44.9778+n/111320,longitude:-93.265+e/(111320*Math.cos(44.9778*Math.PI/180)),accuracy:8});
  await p.goto(base+'/?auto=desk&name=VehicleScout');await p.waitForFunction(()=>__osz.G.body&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
  car=await p.evaluate(()=>__osz.G.vehicles.find(v=>v.allowed&&v.occupied.every(x=>!x)));if(car)break;
 }
 assert(car,'a car discovered through the normal scene');await c.close();
 const location={latitude:car.lat,longitude:car.lng,accuracy:8};c=await browser.newContext({...phone,geolocation:location});p=await c.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=VehicleCheck');await p.waitForFunction(id=>__osz.G.vehicles?.some(v=>v.id===id&&v.reachable)&&!__osz.G.mapping&&!__osz.G.launchPending,car.id,{timeout:90000});
 const snapshot=()=>p.evaluate(id=>__osz.G.vehicles.find(v=>v.id===id),car.id);
 await p.locator('#bInteract').tap();await p.locator('[data-nearby="vehicle"][data-entity="'+car.id+'"]').tap();
 await p.getByRole('button',{name:'Drive',exact:true}).tap();await p.waitForFunction(id=>__osz.G.you.vehicle===id,car.id);
 assert(await p.locator('#vehicleBar').isVisible());assert(await p.locator('#bar').isHidden());
 await p.locator('#vehicleCargo').tap();await p.locator('#storageWithdraw').tap();
 const fuelRow=p.locator('#drawerContent [data-item="fuel"]');
 // itemRow uses data-item when supplied by inventory, so the compact drawer is selected by text here.
 await p.locator('#drawerContent .loot-row').filter({hasText:'Generator Fuel'}).getByRole('button',{name:'Take 1',exact:true}).tap();
 await p.waitForFunction(()=>__osz.G.body.items.some(i=>i.code==='fuel'));await p.locator('#drawerClose').tap();
 const stored=await snapshot();await c.setGeolocation(location);await p.reload();
 await p.waitForFunction(()=>__osz.G.body&&!__osz.G.launchPending&&!__osz.G.mapping&&!__osz.G.you.vehicle,null,{timeout:90000});
 assert.equal((await snapshot()).items.filter(i=>i.code==='fuel').reduce((n,i)=>n+i.qty,0),0,'reload does not refill cargo');
 assert.equal((await snapshot()).fuel,stored.fuel);
 await p.locator('#bInteract').tap();await p.locator('[data-nearby="vehicle"][data-entity="'+car.id+'"]').tap();await p.getByRole('button',{name:'Drive',exact:true}).tap();await p.waitForFunction(id=>__osz.G.you.vehicle===id,car.id);
 const before=await snapshot();await p.locator('#vehicleEngine').tap();await p.waitForFunction(id=>__osz.G.vehicles.find(v=>v.id===id)?.engine,car.id);
 let driven,meters=0;
 // Parked vehicles can face a wall; steer through several actual stick directions to find a clear exit.
 for(const [x,y] of [[118,490],[12,490],[62,452],[62,568]]){
  await p.mouse.move(62,510);await p.mouse.down();await p.mouse.move(x,y,{steps:10});await p.waitForTimeout(2200);await p.mouse.up();
  await p.locator('#vehicleBrake').tap();await p.waitForFunction(id=>Math.abs(__osz.G.vehicles.find(v=>v.id===id).speed)<.2,car.id,{timeout:10000});
  driven=await snapshot();meters=Math.hypot((driven.lat-before.lat)*111320,(driven.lng-before.lng)*111320*Math.cos(before.lat*Math.PI/180));
  if(meters>1)break;
 }
 assert(meters>1,'actual stick drive changes world coordinates');assert(driven.fuel<before.fuel);
 await p.locator('#vehicleEngine').tap();await p.waitForFunction(id=>!__osz.G.vehicles.find(v=>v.id===id)?.engine,car.id);
 await p.locator('#vehicleExit').tap();await p.waitForFunction(()=>!__osz.G.you.vehicle);
 await p.locator('#bInteract').tap();await p.locator('[data-nearby="vehicle"][data-entity="'+car.id+'"]').tap();await p.getByRole('button',{name:'More',exact:true}).tap();await p.getByRole('button',{name:'Refuel (1 can)',exact:true}).tap();
 await p.waitForFunction(id=>__osz.G.vehicles.find(v=>v.id===id).fuel>20,car.id);await p.locator('#drawerClose').tap();
 await p.screenshot({path:'/tmp/osz-vehicle-phone.png'});assert.deepEqual(errors,[]);
 console.log(JSON.stringify({normalDiscovery:true,touchBoard:true,cargoTake:true,reloadParksWithoutRefill:true,stickDriveMeters:+meters.toFixed(2),fuelConsumed:true,brake:true,exit:true,refuel:true,errors}));
 await c.close();
}finally{await browser.close();}
