// Check a saved test profile and shared body after actual server replacement.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';import fs from 'node:fs';
const prefix=process.argv[2]||'/tmp/osz-body',e=JSON.parse(fs.readFileSync(prefix+'-evidence.json'));
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const c=await browser.newContext({...devices['Pixel 7'],storageState:prefix+'-storage.json',permissions:['geolocation'],geolocation:{latitude:e.body.lat,longitude:e.body.lng,accuracy:8}}),p=await c.newPage();const errors=[];let sessions=0;
 p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(new URL(r.url()).pathname==='/api/session')sessions++;});
 await p.goto(e.base+'/?auto=desk');
 await p.waitForFunction(id=>__osz.G.corpses.some(b=>b.id===id)&&!__osz.G.launchPending,e.body.id,{timeout:65000});
 const b=await p.evaluate(id=>__osz.G.corpses.find(b=>b.id===id),e.body.id);
 assert.deepEqual(b.items,e.body.items);assert.equal(b.revision,e.body.revision);assert.equal(b.searched,e.body.searched);
 assert.equal(b.variant,e.body.variant);assert.equal(b.kind,e.body.kind);assert.equal(sessions,0);assert.deepEqual(errors,[]);
 if(e.kills!=null)assert(await p.evaluate(n=>__osz.G.you.kills>=n,e.kills),'test profile must have completed its own fight');
 console.log(JSON.stringify({bodySurvivesProcessReplacement:true,exactStockAndRevision:true,sameLook:true,noNewSession:true,errors}));
}finally{await browser.close();}
