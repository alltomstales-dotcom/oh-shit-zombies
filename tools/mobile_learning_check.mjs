// Normal map fixtures, GPS placement and scene card/drawer. No injected media.
const {chromium,devices}=await import(process.env.OSZ_PLAYWRIGHT_MODULE||'playwright');
import assert from 'node:assert/strict';
const base=process.argv[2]||'http://127.0.0.1:8038';
const browser=await chromium.launch({headless:false,args:['--no-sandbox']});
try{
 const phone={...devices['Pixel 7'],permissions:['geolocation']};
 const scout=await browser.newContext({...phone,geolocation:{latitude:44.9778,longitude:-93.265,accuracy:8}}),s=await scout.newPage();
 await s.goto(base+'/?auto=desk&name=LearningScout');await s.waitForFunction(()=>__osz.G.buildings.some(b=>b.stairs&&b.rooms.length<=2),null,{timeout:90000});
 console.log('stage: map loaded');const at=await s.evaluate(()=>__osz.G.buildings.find(b=>b.stairs&&b.rooms.length<=2).stairs);await scout.setGeolocation({latitude:at[0],longitude:at[1],accuracy:8});await s.reload();
 await s.waitForFunction(()=>__osz.G.body?.survival.objects.some(o=>o.kind==='television')&&!__osz.G.mapping&&!__osz.G.launchPending,null,{timeout:90000});
 console.log('stage: inside with tv');const tv=await s.evaluate(()=>__osz.G.body.survival.objects.find(o=>o.kind==='television'));await scout.close();
 const location={latitude:tv.lat,longitude:tv.lng,accuracy:8},c=await browser.newContext({...phone,geolocation:location}),p=await c.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/?auto=desk&name=LearningCheck');await p.waitForFunction(id=>__osz.G.body?.survival.objects.some(o=>o.id===id&&o.reachable)&&!__osz.G.launchPending&&!__osz.G.mapping,tv.id,{timeout:90000});
 console.log('stage: reachable tv');const before=await p.evaluate(()=>__osz.G.body.items);
 const lesson=p.locator('#drawerContent .work-row').filter({hasText:'Woodworking basics'});
 const skill=()=>p.evaluate(()=>__osz.G.body.progression.skills.find(s=>s.id==='carpentry').xp);
 const xp=await skill();
 await p.locator('#bInteract').tap();await p.locator('[data-nearby="object"][data-entity="'+tv.id+'"]').tap();await p.getByRole('button',{name:'Watch / learn',exact:true}).tap();
 await lesson.getByRole('button',{name:'Watch',exact:true}).tap();await p.waitForFunction(()=>__osz.G.body.study?.reading);
 await p.waitForTimeout(5000);await p.getByRole('button',{name:'Stop',exact:true}).tap();await p.waitForFunction(()=>__osz.G.body.study&&!__osz.G.body.study.reading);
 const left=await p.evaluate(()=>__osz.G.body.study.left_s);assert(left>0&&left<45);await p.waitForTimeout(1000);assert.equal(await skill(),xp);
 await p.getByRole('button',{name:'Resume',exact:true}).tap();await p.waitForFunction(()=>__osz.G.body.study?.reading);
 await p.waitForFunction(()=>__osz.G.body.lessons.find(l=>l.id==='tv_carpentry').learned,null,{timeout:65000});
 assert.equal(await skill(),xp+20);assert(await lesson.getByRole('button',{name:'Learned',exact:true}).isDisabled());
 assert.deepEqual(await p.evaluate(()=>__osz.G.body.items),before);await p.screenshot({path:'/tmp/osz-learning-phone.png'});
 await c.setGeolocation(location);await p.reload();await p.waitForFunction(()=>__osz.G.body&&!__osz.G.launchPending&&!__osz.G.mapping,null,{timeout:90000});
 assert(await p.evaluate(()=>__osz.G.body.lessons.find(l=>l.id==='tv_carpentry').learned));assert.equal(await skill(),xp+20);
 assert.deepEqual(errors,[]);console.log(JSON.stringify({normalTelevision:true,sceneWatch:true,pauseResume:true,exactOnceXp:true,mapVisible:true,reload:true,errors}));await c.close();
}finally{await browser.close();}
