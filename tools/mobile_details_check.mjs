// Character choice/reload on a normal server, explicit map start to isolate this from GPS launch/hunt policy; injected corpse positions only test
// drawing and touch selection, not a kill, server search or persistence.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8023';
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const c=await browser.newContext({...devices['Pixel 7'],permissions:['geolocation'],geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),p=await c.newPage(),errors=[];
 p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=DetailsCheck&at=44.9778,-93.265');
 const ready=()=>p.waitForFunction(()=>__osz.G.you&&__osz.G.body&&__osz.G.located&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
 await ready();await p.locator('#bPack').tap();await p.locator('[data-pack-tab="equipment"]').tap();
 assert.equal(await p.locator('[data-character]').count(),8);
 for(const i of [4,7,0,1,6]){
  await p.locator(`[data-character="${i}"]`).tap();assert.equal(await p.evaluate(()=>__osz.state().look.character),i);
  await p.waitForFunction(i=>[...document.images].some(im=>im.src.endsWith('/surv_p'+i+'.webp')&&im.complete&&im.naturalWidth>0),i);
 }
 await p.locator('#panelClose').tap();await p.reload();await ready();
 assert.equal(await p.evaluate(()=>__osz.state().look.character),6,'choice survives reload');
 await p.evaluate(()=>{const G=__osz.G;window.__fixtureMessage=G.ws.onmessage;G.ws.onmessage=null;G.zeds.clear();G.stashes=[];G.buildings=[];G.body.home=null;G.body.survival.objects=[];G.body.survival.resources=[];});
 // Place a render fixture in clear screen space and tap near the fallen head.
 for(const variant of [0,1]){
  await p.evaluate(variant=>{const G=__osz.G;const lat=G.you.lat,lng=G.you.lng+3/(111320*Math.cos(G.you.lat*Math.PI/180));G.corpses=[{id:'render-fixture',lat,lng,kind:'shambler',variant,searched:false,items:null,reachable:true}];G.selection=null;window.__fixtureMessage({data:JSON.stringify({t:'s',you:G.you,sight:G.sight,now:G.serverNow,z:[],stashes:[],drops:[],corpses:G.corpses,buildings:[],inside:null,room:null})});},variant);
  await p.waitForTimeout(700);
  const xy=await p.evaluate(variant=>{const G=__osz.G,c=G.corpses[0],[x,y]=__osz.project(c.lat,c.lng),ppm=G.cam.ppm,h=G.inside?Math.max(22,Math.min(72,2*ppm)):Math.max(48,Math.min(120,4.6*ppm)),a=variant%2?-1.5:1.5;return [x+Math.sin(a)*h*.8,y-Math.cos(a)*h*.8];},variant);
  await p.touchscreen.tap(...xy);
  await p.waitForFunction(()=>__osz.G.selection?.id==='render-fixture');
  assert(await p.getByRole('button',{name:'Search body',exact:true}).isEnabled());
  await p.locator('#worldClose').tap();await p.locator('#bBody').tap();
  await p.waitForFunction(()=>__osz.G.selection?.kind==='corpse');
 }
 await p.screenshot({path:'/tmp/osz-details-phone.png'});
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({characterChoices:8,changedAndReloaded:true,fallenHeadBothOrientations:true,nearbyBodyButton:true,serverSearchNotExercised:true,errors}));
}finally{await browser.close();}
