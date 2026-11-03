import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Exercise the actual frame handler with a predicted body already at a door.
const source=fs.readFileSync(new URL('../app/static/js/main.js',import.meta.url),'utf8');
const handler=source.slice(source.indexOf('function stepDesk('),source.indexOf('// ------------------------------------------------------------------ drawing'));
const G={mode:'desk',desk:[0,0],dead:false,keys:new Set(),goal:[0,0],route:[[0,0]],
  routePending:false,autoOpening:'door',exitIntent:true,pending:new Map(),you:{lat:5,lng:0}};
const calls=[];
const context=vm.createContext({G,Math,deltaM:(a,b,c,d)=>[c-a,d-b],
  sendPos:()=>calls.push('position'),fire:(a,args)=>{calls.push(a);G.pending.set(1,{a,args});},
  $:()=>({disabled:false}),DESK_SPEED:2,STICK:{creep:.5},wantQuiet:()=>{}});
vm.runInContext(handler,context);
context.stepDesk(.016,100);
assert.deepEqual(calls,['position']);
assert.equal(G.route.length,1);
assert.equal(G.autoOpening,'door');
assert.equal(G.exitIntent,true);
G.you.lat=.1;
context.stepDesk(.016,200);
assert.deepEqual(calls,['position','opening']);
assert.equal(G.route.length,0);
assert.equal(G.autoOpening,null);
assert.equal(G.exitIntent,true);
console.log('Exit waits for the authoritative body before opening a door.');
