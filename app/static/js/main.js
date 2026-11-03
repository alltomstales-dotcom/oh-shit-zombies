import {setupVehicles,vehicleFrame,renderVehicles,drawVehicle,vehicleHit} from './vehicles.js';
import {setupBackgrounds,setBackgroundCatalog,backgroundChoice} from './backgrounds.js';
import {characterPose,characterParts} from './character-pose.js';
import {freshFix,acknowledgedPlacement} from './gps.js';
import {setupWork,drawWork,tapWork,hitWork,beginPlacement} from "./work.js";
import {setupWorldUI,selectWorld,openSceneDrawer,renderWorldUI,collapseWorldUI,hitOpening,drawSelection,HOME_MARKER_OFFSET_X} from './world-ui.js';
import {nearestTarget} from './selection.js';
import {corpseHit} from './body-hit.js';
import {nearbyBody} from './recovery.js';
import {installIndoorZoom,zoomFactor} from './indoor-zoom.js';
import {projectM,unprojectM,worldPoint,screenWorld,screenDirection,groundBounds,groundCircle} from './projection.js';
import {setupArea,area,openArea,closeArea,areaResult,areaPinned,areaPointer,drawArea} from './area.js';
import { setupInventory, renderInventory } from './inventory.js';
import { waitText } from './icons.js';
import {setupTrailer,stopTrailer} from './trailer.js';
import {setupSiege,siegeState,siegeEvent,siegeReset,siegeDrawGround,siegeDrawBoss,siegeBossId,siegeInfo} from './siege.js';
// Oh shit, Zombies. The whole client: one canvas for the street, plain DOM for the buttons.
import { initAudio, sfx, setHeart, buzz, setMuted, isMuted } from './audio.js';
import { drawTiles, deltaM, shiftLL, tileStats, setTiles } from './map.js';
import { buildingAt, clear as pathClear, move as buildingMove, slide as buildingSlide, entranceApproach, drawBuildings,buildingFaces,drawBuildingFace } from './buildings.js';

const $ = (id) => document.getElementById(id);
const T = () => performance.now();
const Q = new URLSearchParams(location.search);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const LS = {
  get(k, d = '') { try { const v = localStorage.getItem('osz.' + k); return v === null ? d : v; } catch (_) { return d; } },
  set(k, v) { try { localStorage.setItem('osz.' + k, v); } catch (_) {} },
};
const pct = (xs, p) => { if (!xs.length) return 0; const s = [...xs].sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.floor(s.length * p))]; };
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// What this server allows. Until it answers, assume the private choice: no GPS, no typed text.
const CFG = { real_gps: false, free_text: false, starts: [] };
const cfgReady = fetch('/api/config').then((r) => r.ok ? r.json() : null).then((c) => { if (c) Object.assign(CFG, c); }).catch(() => {}).then(() => {
  if (!CFG.real_gps) G.phoneGps = false;
  document.body.classList.toggle('real-gps', CFG.real_gps);
  document.body.classList.toggle('free-text', CFG.free_text);
  if (CFG.real_gps) $('goWalk').textContent = 'Play near me';
});

const DESK_SPEED = 2.0, FALLBACK_START = [41.8807, -87.6278];
const CHANNEL_WORD = {window_work:'Window work… Stay still.',work: "WORKING… Stay still.",  back: 'Breaking free', bandage: 'Bandaging', disinfect: 'Cleaning', search: 'Searching', search_body:'Searching body', search_building: 'Searching building' };
const MOOD_HELP = {hungry: "Eat something. Hunger gradually reduces pace.", thirsty: "Drink clean water. Thirst gradually reduces pace.", sleepy: "Rest in a bed. Sleep debt is different from endurance.",
  bleeding: 'Bleeding. Bandage it or you will keep losing blood.',
  hurt: 'Hurt. Health only comes back while you are away from the game.',
  panic: 'Panic. Your swings miss more, and severe panic can make you scream and attract more zombies. Get clear of them, or eat something.',
  winded: 'Winded. Swings are slower and weaker. Stop fighting, or drink.',
  heavy: 'Carrying too much. You tire faster.',
  queasy: 'Queasy. You do not feel right.',
  fever: 'Fever.',
};

// ------------------------------------------------------------------ art
const sprites = new Map();
function sprite(name) {
  let s = sprites.get(name);
  if (!s) {
    const img = new Image();
    s = { img, ok: false };
    img.onload = () => { s.ok = true; };
    img.src = `/assets/${name}.webp`;
    sprites.set(name, s);
  }
  return s;
}
const ZED_ART = { shambler: ['s', 16], lurcher: ['l', 3], crawler: ['c', 2] };
const zedSprite = (kind, v) => { const [p, n] = ZED_ART[kind] || ZED_ART.shambler; return sprite(`zed_${p}${v % n}`); };

// ------------------------------------------------------------------ state
const G = {
  mode: '', ws: null, token: LS.get('token'), name: LS.get('name'), gotHello: false, retry: 0,
  tune: {}, items: {}, you: null, body: null, sight: 55, located: false,
  zeds: new Map(), herds: new Map(), herdMoanAt: 0, gone: [], corpses: [], stashes: [], drops: [], buildings: [], inside: null, room: null, route: [], routePending: false, nav: 0, lastReplan: 0, replans: 0, exitIntent: false, autoOpening: null, autoStairs:false,
  pos: null, desk: null, goal: null, moving: false, heading: 0, keys: new Set(), lastPos: null, lastPosSent: 0,
  indoorZoom:zoomFactor(Number(LS.get('indoorZoom','1'))),cam: { lat: 0, lng: 0, ppm: 4,iso:LS.get('worldView','iso')!=='map' }, shake: 0, hurtAt: 0, swingAt: 0, actionKind: '', aimAng: 0,
  fx: [], floaters: [], blips: [],
  busyUntil: 0, busySpan: 600, backReadyAt: 0, channel: null, lastFire: 0, bufTimer: 0,
  seq: 0, pending: new Map(), lastSnapAt: 0, snapGap: 200, snaps: 0,
  rec: { swing: 0.75, shove: 0.55, shoot: 0.9 },
  lat: { frame: [], server: [], ping: [] }, taps: [], fps: 60, dev: LS.get('dev') === '1' || Q.has('dev'),
  dead: false, card: null, lastSting: 0, hints: {}, ctxKey: '', moodKey: '', edgeBeat: 0,
  gpsDeniedToast: false, gpsFixToast: false,
  phoneGps: !Q.has("at") && (navigator.maxTouchPoints > 0 || /Android|iPhone|iPad/.test(navigator.userAgent)),
  backgroundBusy:false,launchPending: false, locationBusy: false, locationGeneration: 0, minimumEpoch: 0,
  stick: null, stickTouch: null, quietHeld: false, quietSent: 0,
};

const lerpNew = (lat, lng) => ({ a: [lat, lng], b: [lat, lng], t0: 0, dur: 1 });
function lerpAt(p, now) {
  const k = clamp((now - p.t0) / p.dur, 0, 1);
  return [p.a[0] + (p.b[0] - p.a[0]) * k, p.a[1] + (p.b[1] - p.a[1]) * k];
}
function lerpTo(p, lat, lng, now, dur) { p.a = lerpAt(p, now); p.b = [lat, lng]; p.t0 = now; p.dur = dur; }

function youLL(now) {
  const srv = G.pos ? lerpAt(G.pos, now) : [0, 0];
  if(G.you?.vehicle)return srv;
  if (G.mode === 'desk' && G.desk) {
    const [dx, dy] = deltaM(srv[0], srv[1], G.desk[0], G.desk[1]);
    if (Math.hypot(dx, dy) < 6) return G.desk;       // show the step the moment the key goes down
  }
  return srv;
}

// ------------------------------------------------------------------ network
function send(m) { if (G.ws && G.ws.readyState === 1) G.ws.send(JSON.stringify(m)); }

async function ensureSession(name) {
  if (G.token && (G.name === name || !CFG.free_text)) return;
  let dev = LS.get('device');
  if (!dev) {
    dev = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + String(Math.random()).slice(2))
      + '-' + Date.now().toString(36);
    LS.set('device', dev);
  }
  const r = await fetch('/api/session', { method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ device_id: dev, name }) });
  if (!r.ok) throw new Error('Could not start a session (' + r.status + ')');
  const j = await r.json();
  G.token = j.token; G.name = j.player.name;
  LS.set('token', G.token); LS.set('name', G.name);
}

function connect() {
  if (G.full) return;
  const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${G.siege ? '/ws/siege' : '/ws'}?token=${encodeURIComponent(G.token)}`);
  G.ws = ws; G.gotHello = false;
  ws.onmessage = (e) => {if(G.ws===ws)onMsg(JSON.parse(e.data));};
  ws.onclose = async () => {
    stickEnd(false);
    if (G.ws !== ws) return;
    G.ws = null;
    if (G.full) { $('hud').hidden = true; if (G.full === 'Your data is deleted.') { $('title').hidden = false; titleStatus(G.full); } else showFull(); return; }
    if (!G.gotHello && G.retry === 1) {            // the saved token is no good: start over once
      G.token = ''; LS.set('token', '');
      try { await ensureSession(G.name || 'Survivor'); } catch (_) {}
    }
    if (G.retry > 0) toast('Lost the connection. Retrying.', 'bad');
    setTimeout(connect, Math.min(5000, 400 * 2 ** G.retry++));
  };
}

// Server full: a screen of its own, which tries again by itself. The survivor is kept meanwhile.
function showFull() {
  $('title').hidden = true; $('full').hidden = false;
  $('fullLine').textContent = G.full;
  clearInterval(G.fullTimer); let left = G.fullRetry || 30;
  const tick = () => { $('fullCount').textContent = 'Trying again in ' + left + ' s.'; if (left-- <= 0) retryFull(); };
  tick(); G.fullTimer = setInterval(tick, 1000);
}
function retryFull() {
  clearInterval(G.fullTimer); G.fullTimer = 0;
  if (G.full === 'Your data is deleted.') return;
  G.full = null; G.retry = 0; $('fullCount').textContent = 'Trying now…';
  connect();
}

function onMsg(m) {
  if (m.t === 's') return onState(m);
  if (m.t === 'r') return onResult(m);
  if (m.t === 'pong') { G.lat.ping.push(T() - m.c); if (G.lat.ping.length > 40) G.lat.ping.shift(); return; }
  if (m.t === 'hello') return onHello(m);
  if (m.t === 'full') { G.full = m.why; G.fullRetry = m.retry_s || 30; return; }
  if (m.t === 'err') console.warn('server:', m.why);
}

function onHello(m) {
  if (!$('full').hidden) { $('full').hidden = true; clearInterval(G.fullTimer); }
  const firstHello = !G.hasHello;
  G.hasHello = true;
  G.placementTicket = m.placement_ticket;
  G.lifeId=m.life_id;G.backgroundBusy=false;
  G.locationBusy = false;
  G.minimumEpoch = m.placement_epoch || 0;
  G.gotHello = true; G.retry = 0;
  G.tune = m.tune; G.items = m.items; G.name = m.name;
  if (m.tiles && !G.tilesSet) { G.tilesSet = true; setTiles(m.tiles); $('attrib').textContent = m.tiles.credit || ''; }
  G.dead = false; G.card = null;
  stopTrailer(); $('title').hidden = true; $('death').hidden = true; $('hud').hidden = false;
  if (m.fresh) {
    G.zeds.clear(); G.corpses = []; G.body = null; G.calmTold = false;
    G.goal=null;G.route=[];G.routePending=false;G.nav++;G.exitIntent=false;G.autoOpening=null;
    G.desk=null;G.pos=null;G.lastPos=null;G.located=false;G.gpsCenter=null;
    toast(m.siege?'Siege: survive 30 minutes. Chests heal and arm you; a boss comes every five minutes.':G.phoneGps?'Finding GPS for your new survivor.':'Choose where your new survivor starts.', 'good');
  }
  if (m.dead) { showDeath(m.card); return; }
  // A mobile reconnect must not wait forever for a route reply from the old socket.
  G.pending.clear();
  setBackgroundCatalog(m.backgrounds);
  if(m.unplaced&&!m.dead){
    submitBackground(backgroundChoice(m.backgrounds));
  }
  if(G.exitIntent)leaveBuilding();
  else if(G.routePending&&G.goal){G.routePending=false;walkTo(G.goal);}
  else G.routePending=false;
  const aw = m.away;
  if (aw && aw.away_s > 600) {
    const bits = [];
    if (aw.healed > 0) bits.push(`+${Math.round(aw.healed)} health`);
    if (aw.closed) bits.push(`${aw.closed} wound${aw.closed > 1 ? 's' : ''} healed`);
    if (aw.bled > 0) bits.push(`lost ${Math.round(aw.bled)} to bleeding`);
    if (bits.length) toast(`While you were away: ${bits.join(', ')}.`);
  }
  // what finished at home meanwhile: the reason to come back
  if (aw && aw.home && aw.home.length) setTimeout(() => toast(aw.home.join(' '), 'tip'), 1200);
  if(!CFG.real_gps){
    // Public server: an unplaced survivor picks a named start. Nothing asks where the player is.
    G.launchPending=!!m.unplaced&&!m.dead;
    if(G.launchPending){G.locationGeneration++;showStarts();}
  }else if(G.phoneGps&&(firstHello||m.fresh||G.launchPending)){
    G.launchPending=true;G.locationGeneration++;G.gpsCenter=null;
    locationMessage('Finding your current street…');startGps();requestLocation();
  }else if(m.fresh)startDesk();
  if (G.lastPos && !G.launchPending) sendPos(true);
}

function onState(m) {
  const now = T();
  if (G.lastSnapAt) G.snapGap = clamp(now - G.lastSnapAt, 90, 450);
  G.lastSnapAt = now; G.snaps++;
  const y = m.you;
  if(G.lifeId&&y.life_id&&G.lifeId!==y.life_id)return;
  if((y.placement_epoch||0)<G.minimumEpoch)return;
  const acknowledged=acknowledgedPlacement(y,[...G.pending.values()],G.minimumEpoch,G.locationGeneration);
  if(acknowledged)completePlacement(acknowledged.result,acknowledged.args);
  const awaitingAnchor=G.gpsRelocateUntil>now&&G.gpsCenter&&Math.hypot(...deltaM(...G.gpsCenter,y.lat,y.lng))>10;
  if(!awaitingAnchor)G.gpsRelocateUntil=0;
  if(G.you&&(y.floor_epoch||0)!==(G.you.floor_epoch||0)){
    G.desk=[y.lat,y.lng];G.lastPos=[y.lat,y.lng,1];G.pos=lerpNew(y.lat,y.lng);
    G.goal=null;G.route=[];G.routePending=false;G.nav++;G.keys.clear();G.stick=null;
    G.exitIntent=false;G.autoOpening=null;G.autoStairs=false;G.zeds.clear();G.herds.clear();G.gone=[];
    G.buildings=[];G.selection=null;G.drawer=null;collapseWorldUI('movement');
  }
  if((G.you?.vehicle||null)!==(y.vehicle||null)){G.desk=[y.lat,y.lng];G.goal=null;G.vehicleGoal=null;G.stick=null;G.keys.clear();G.vehicleReverse=false;G.lastPos=[y.lat,y.lng,1];}
  G.vehicles=m.vehicles||[];
  G.you = y; G.sight = m.sight; G.serverNow=m.now;
  if (m.siege) siegeState(m.siege);
  const placed = Math.abs(y.lat) + Math.abs(y.lng) > 1e-6;
  if (placed) {
    if (!G.pos || !G.located) G.pos = lerpNew(y.lat, y.lng);
    else {
      const [dx, dy] = deltaM(G.pos.b[0], G.pos.b[1], y.lat, y.lng);
      if (Math.hypot(dx, dy) > 50) G.pos = lerpNew(y.lat, y.lng); else lerpTo(G.pos, y.lat, y.lng, now, G.snapGap);
    }
    G.located = true;
  }
  if (G.mode === 'desk' && !G.desk && (!G.launchPending||G.launchHunted)) startDesk(placed ? [y.lat, y.lng] : null);

  const seen = new Set();
  G.allies||=new Map();const allySeen=new Set();
  for(const row of m.allies||[]){let ally=G.allies.get(row.id);if(!ally){ally={p:lerpNew(row.lat,row.lng)};G.allies.set(row.id,ally);}lerpTo(ally.p,row.lat,row.lng,now,G.snapGap);Object.assign(ally,row);allySeen.add(row.id);}
  for(const id of G.allies.keys())if(!allySeen.has(id))G.allies.delete(id);
  // Other players in sight (public servers only): [id, lat, lng, name, state, heading].
  G.others||=new Map();const otherSeen=new Set();
  for(const [id,lat,lng,name,state,heading] of m.others||[]){let o=G.others.get(id);if(!o){o={id,p:lerpNew(lat,lng),look:parseInt(id.slice(0,4),16)%8};G.others.set(id,o);}lerpTo(o.p,lat,lng,now,G.snapGap);Object.assign(o,{name,state,heading});otherSeen.add(id);}
  for(const id of G.others.keys())if(!otherSeen.has(id))G.others.delete(id);
  for (const [id, lat, lng, state, kind, variant, mine, atk, hp] of m.z) {
    let z = G.zeds.get(id);
    if (!z) {
      z = { id, kind, variant, p: lerpNew(lat, lng), born: now, flash: 0, spot: 0, ph: Math.random() * 6.28, hp: 1 };
      G.zeds.set(id, z);
    }
    lerpTo(z.p, lat, lng, now, G.snapGap);
    if (hp < z.hp - 0.001) z.flash = now;
    if (state === 'alert' && z.state !== 'alert') z.spot = now;
    z.state = state; z.mine = mine; z.hp = hp; z.atkAt = atk >= 0 ? now + atk * 1000 : 0;
    seen.add(id);
  }
  for (const [id, z] of G.zeds) if (!seen.has(id)) { G.zeds.delete(id); z.goneAt = now; G.gone.push(z); }
  // A herd arrives as one row: where its middle is, how many, and the numbers its crowd is drawn from.
  const herdSeen = new Set();
  for (const [id, lat, lng, count, seed, facing] of m.herds || []) {
    let h = G.herds.get(id);
    if (!h) { h = { id, p: lerpNew(lat, lng), born: now, facing, hid: null, hidAt: 0 }; G.herds.set(id, h); }
    lerpTo(h.p, lat, lng, now, G.snapGap);
    h.count = count; h.seed = seed; h.to = facing; herdSeen.add(id);
  }
  for (const id of [...G.herds.keys()]) if (!herdSeen.has(id)) G.herds.delete(id);
  if (G.herds.size && now - G.herdMoanAt > 2400) {             // a crowd is never quiet
    G.herdMoanAt = now + Math.random() * 900;
    const h = G.herds.values().next().value, [dx, dy] = deltaM(y.lat, y.lng, h.p.b[0], h.p.b[1]);
    sfx.groan(clamp(dx / 40, -0.9, 0.9), clamp(0.34 - Math.hypot(dx, dy) / 400, 0.08, 0.3), false);
  }
  if(m.stashes)G.stashes = m.stashes; G.drops = m.drops;G.lootShelves=m.loot||[];
  if(m.corpses)G.corpses=m.corpses;
  if(m.buildings){G.buildings=m.buildings;if(G.goal&&!G.exitIntent)walkTo(G.goal);}
  G.inside=awaitingAnchor?null:m.inside;
  if(!awaitingAnchor&&m.room&&m.room!==G.room)toast(m.room+' · search carefully.');
  G.room=awaitingAnchor?null:m.room;
  if(!awaitingAnchor&&G.desk&&G.buildings.length&&!pathClear(G.buildings,[y.lat,y.lng],G.desk)){
    G.desk=[y.lat,y.lng];G.lastPos=[...G.desk,1];
    if(G.goal&&!G.routePending&&now-G.lastReplan>800){G.lastReplan=now;G.replans++;if(G.exitIntent)leaveBuilding();else walkTo(G.goal);}
  }

  if (y.busy > 0 || now - G.lastFire > 350) setBusy(now + y.busy * 1000, now);
  G.backReadyAt = now + y.back * 1000;
  if (y.channel) {
    if (y.channel.kind === 'search') G.selectedStash = y.channel.stash;
    if (!G.channel || G.channel.kind !== y.channel.kind) {
      const total = y.channel.total || { back: 0.8, bandage: G.tune.bandage_s, disinfect: 2.0, search: G.tune.search_s }[y.channel.kind] || 2;
      G.channel = { kind: y.channel.kind, total: total * 1000 };
    }
    G.channel.end = now + y.channel.left * 1000;
  } else G.channel = null;

  if (m.body) { G.body = m.body; if (!$('panel').hidden) renderPanel(); }
  if (m.body || !!m.mapping !== G.mapping) { G.mapping = !!m.mapping; updateNavigation(); }
  if (placed && !G.mapping) firstSteps();
  if (y.arriving && m.z.length && !G.calmTold) { G.calmTold = true; toast('They have not noticed you yet. Walk away before they do.', 'tip'); }
  if (m.ev) for (const e of m.ev) onEvent(e, now);
  if (y.dead && !G.dead) { if (G.siege) { G.dead = true; collapseWorldUI('death'); stickEnd(false); setHeart(0); } else showDeath(G.card); }
  updateHud(now);renderVehicles();
}

function setBusy(until, now, fresh) {
  if (fresh || until - now > G.busySpan) G.busySpan = Math.max(200, until - now);
  G.busyUntil = until;
}

// ------------------------------------------------------------------ events from the world
const COMPASS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
const compass = (b) => COMPASS[Math.round(((b % 360) + 360) % 360 / 45) % 8];
const NOISE_LINE = { glass: 'Glass breaks', alarm: 'A car alarm starts up', crash: 'Something heavy falls', dog: 'A dog is barking' };
const WOUND_LINE = { scratch: 'Scratched', laceration: 'Cut open', bite: 'BITTEN' };

function onEvent(e, now) {
  if (e.e && e.e.startsWith('siege_')) { siegeEvent(e); return; }
  if (G.siege && e.e === 'died') return;                 // the siege has its own end card
  const z = e.z ? G.zeds.get(e.z) : null;
  switch (e.e) {
    case 'body_found':
      sfx.found();selectWorld({kind:'corpse',id:e.corpse});openSceneDrawer('bodyloot',e.corpse);
      toast('Body searched. Take only what you need.');break;
    case 'groan': {
      const pan = Math.sin(e.b * Math.PI / 180) * 0.9;
      const vol = clamp(0.5 - e.d / 260, 0.06, 0.5) * (e.loud ? 1.3 : 1);
      sfx.groan(pan, vol, e.loud);
      if (!e.seen) G.blips.push({ b: e.b, kind: 'groan', t0: now, loud: e.loud });
      if (G.knock && !e.seen && e.d < 20) G.knock.answered = true;
      if (z) z.groanAt = now;
      if (e.you && z) {
        z.spot = now;
        if (now - G.lastSting > 7000) { G.lastSting = now; sfx.sting(); buzz(30); hint('spot', 'It has seen you. Walking away works. For a while.'); }
      }
      break;
    }
    case 'building_searched':
      if(e.found){sfx.found();G.selectedStash=e.stash;toast('Found a hidden container in '+e.room+'. Tap it to collect the loot.');}
      else toast('No hidden loot this time. '+e.left+' building search attempt'+(e.left===1?'':'s')+' left.');
      break;
    case 'broadcast_sound':toast((e.kind==='gunshot'?'Distant gunfire':'A distant scream')+' to the '+compass(e.b)+'. Zombies may follow the sound.','tip');break;
    case 'armor': sfx.thwack();toast((G.items[e.code]?.name||e.code)+" stopped a "+e.part+" wound. Condition "+e.cond+".");break;
    case 'work': sfx.found();toast(e.message);break;
    case 'vaulted':
      G.goal=null;G.route=[];G.routePending=false;G.nav++;G.exitIntent=false;G.autoOpening=null;G.stick=null;G.keys.clear();
      G.desk=[e.lat,e.lng];G.pos=lerpNew(e.lat,e.lng);G.lastPos=[e.lat,e.lng,1];sendPos(true);break;
    case 'opening':
      if (e.op === 'knock') { sfx.click(); setTimeout(() => sfx.click(), 170); listenAfterKnock(e.name); break; }
      toast(e.name+' '+(e.op==='broken'?'BREAKS!':e.op==='close'?'closed.':e.op==='smash'?'smashed.':'opened.'),e.op==='broken'?'bad':'');
      if(e.op==='smash'||e.op==='broken'){if(/window/i.test(e.name))sfx.glass();else sfx.broke();}else sfx.door(e.op==='open');
      break;
    case 'xp':
      if (e.level_up || e.skill_up) sfx.ok();
      toast(e.level_up ? 'SURVIVOR LEVEL ' + e.level + ' · ' + e.skill + ' +' + e.amount + ' XP' : e.skill_up ? e.skill + ' level ' + e.skill_level + ' · +' + e.amount + ' XP' : '+' + e.amount + ' XP · ' + e.skill, 'good');
      break;
    case 'scream':
      sfx.scream(); buzz(e.involuntary ? [35, 25, 60] : 25);
      G.screamAt = now; G.screamRadius = e.radius;
      toast(e.involuntary ? 'Panic makes you scream. They heard you.' : 'You scream. They are coming to look.', e.involuntary ? 'bad' : '');
      break;
    case 'alarm': sfx.alarm(0);toast('Building alarm! Nearby zombies heard it.','bad');break;
    case 'herd':   // one walking thing until it notices someone: see herds.py
      if (e.op === 'heard') {
        sfx.groan(Math.sin(e.b * Math.PI / 180) * 0.9, 0.2, false); G.blips.push({ b: e.b, kind: 'groan', t0: now, loud: true });
        toast(`Many feet and a low moan to the ${compass(e.b)}. A herd is passing. Keep well away from it.`, 'tip');
      } else if (e.op === 'seen') {
        buzz(40); toast(`A herd: ${e.n} of them, walking as one. It has not noticed you. Go round it, keep low and make no noise.`, 'tip');
      } else if (e.op === 'woke') {
        sfx.sting(); sfx.groan(0, 0.5, true); buzz(e.mine ? [70, 40, 70] : 40);
        toast(e.mine ? 'The herd has seen you. Do not fight it. Run, and put walls between you and them.' : 'The herd has turned on someone near you.', 'bad');
      }
      break;
    case 'heli':   // the same one for everyone in this area
      if (e.phase === 'coming') { sfx.heli(.07); toast('A helicopter, far off and coming this way. When it is overhead, everything nearby walks toward anyone in the open. Get indoors.', 'tip'); }
      else if (e.phase === 'overhead') { sfx.heli(.16); buzz(60); toast(G.inside ? 'The helicopter is overhead. Stay inside until it has gone.' : 'The helicopter is overhead. They are coming to look. Get indoors.', 'bad'); }
      else toast('The helicopter has moved on.');
      break;
    case 'map': toast(e.message);break;
    case 'pried': toast('Forced the lock with a tool. That made noise.');break;
    case 'noise': {
      const pan = Math.sin(e.b * Math.PI / 180) * 0.9;
      (sfx[e.kind] || sfx.crash)(pan);
      G.blips.push({ b: e.b, kind: 'noise', t0: now, loud: true });
      toast(`${NOISE_LINE[e.kind] || 'A noise'} to the ${compass(e.b)}.`);
      break;
    }
    case 'grabbed':
      sfx.grab(); buzz([50, 30, 50]); G.shake = Math.max(G.shake, 9);
      if (z) { z.spot = now; z.attackAt = now; }
      hint('grab', 'It has hold of you. SHOVE it off, then FINISH it on the ground.', 3);
      break;
    case 'miss_you':
      if (z) { z.attackAt = now; floatAt(z, 'missed', '#9fb3a6'); }
      break;
    case 'hit_you':
      collapseWorldUI('attack');
      (e.wound === 'bite' ? sfx.bite : sfx.hurt)(); buzz(e.wound === 'bite' ? [120, 40, 160] : 90);
      G.shake = Math.max(G.shake, e.wound === 'bite' ? 22 : 13); G.hurtAt = now; flashEdge(1);
      if (z) z.attackAt = now;
      toast(`${WOUND_LINE[e.wound] || 'Hurt'}: ${e.part}`, e.wound === 'bite' ? 'bad big' : 'bad');
      break;
    case 'interrupted':
      if (e.what !== 'back') toast(`${CHANNEL_WORD[e.what] || 'That'} was interrupted.`, 'bad');
      break;
    case 'dropped':
      sfx.broke(); buzz(80);
      toast(e.deliberate ? `Dropped: ${itemName(e.code)}` : `You dropped the ${itemName(e.code)}!`, e.deliberate ? '' : 'bad big');
      break;
    case 'broke':
      sfx.broke(); toast(`Your ${itemName(e.code)} broke.`, 'bad');
      break;
    case 'broke_free':
      sfx.free(); toast('You tear free. Move.', 'good');
      break;
    case 'bandaged': sfx.ok(); toast(`Bandaged: ${e.part}`, 'good'); break;
    case 'cleaned': sfx.ok(); toast(`Cleaned: ${e.part}`, 'good'); break;
    case 'found':
      sfx.found();
      G.selection={kind:'stash',id:e.stash};G.selectedStash=e.stash;
      openSceneDrawer('loot',e.stash);
      toast(e.items.length ? 'Search complete. Choose what to take.' : 'Nothing useful in it.', 'good');
      break;
    case 'died':
      G.card = e.card; showDeath(e.card);
      break;
  }
}
const itemName = (code) => (G.items[code] && G.items[code].name) || code;

function listenAfterKnock(opening) {
  // What is inside answers in its own time. Silence is a hint, not a promise.
  const since = T();
  G.knock = { opening, since };
  toast('You knock, and listen.');
  setTimeout(() => {
    if (!G.knock || G.knock.since !== since) return;
    toast(G.knock.answered ? 'Something inside is moving toward the door.' : 'No answer. That is not a promise.', G.knock.answered ? 'bad' : '');
    G.knock = null;
  }, 3200);
}

function submitBackground(choice){
  if(!G.ws||G.dead)return;
  G.backgroundBusy=true;const id=++G.seq,args={...choice,life_id:G.lifeId};
  G.pending.set(id,{a:'background',args,sent:T()});send({t:'act',id,a:'background',...args});
}
function onResult(m) {
  const p = G.pending.get(m.id), now = T();
  if (!p) return;
  G.pending.delete(m.id);
  if(p.a==='study'&&m.ok&&p.args.op!=='stop'){const tv=p.args.object||G.body?.study?.object||(G.drawer?.mode==='media'?G.drawer.id:null);openSceneDrawer(tv?'media':'learning',tv||null);}
  if(p.a==='radio'&&m.ok){G.broadcast=m.broadcast;openSceneDrawer('radio',null);}
  if(p.a==='base'&&m.ok){
    G.storageContainer='';G.homeDraft=null;
    if(p.args.op==='join')$('baseJoinCode').value='';
    if(m.code){$('baseCode').value=m.code;$('baseCodeLabel').hidden=false;}
    else if(['revoke','close_invites'].includes(p.args.op)){$('baseCode').value='';$('baseCodeLabel').hidden=true;}
  }
  if(p.a==='background'){
    if(p.args.life_id!==G.lifeId)return;
    if(m.ok){G.backgroundBusy=false;if(G.phoneGps&&G.launchPending)requestLocation();else if(!G.desk)startDesk();}
    else if(m.retry){locationMessage('Saving your background…');setTimeout(()=>{if(G.backgroundBusy&&p.args.life_id===G.lifeId)submitBackground(p.args);},2500);}
    else {G.backgroundBusy=false;toast(m.why||'Background unavailable.');if(G.phoneGps&&G.launchPending)requestLocation();else if(!G.desk)startDesk();}
    return;
  }
  if(p.a==='place'){
    if(p.args.generation!==G.locationGeneration)return;
    G.locationBusy=false;
    if(m.ok){
      completePlacement(m,p.args);
      if(m.adjusted&&CFG.real_gps)toast('Started beside the wall at your GPS location.');
      else if(p.args.reason==='travel')toast('Your play area followed your GPS travel.');
    }else{
      G.launchHunted=!!m.hunted;locationMessage(m.why||'Location could not be saved. Retry GPS.');
      if(m.hunted&&G.you)startDesk([G.you.lat,G.you.lng]);
      if(m.retry&&G.launchPending)setTimeout(requestLocation,m.hunted?5000:2500);
    }
    return;
  }
  if (p.a === 'memory') { areaResult(m); return; }
  if (p.a === 'pin') { areaPinned(m); return; }
  const took = now - p.sent;
  G.lat.server.push(took); if (G.lat.server.length > 60) G.lat.server.shift();
  if(p.a==='exit_route'){
    if(!G.exitIntent)return;
    G.routePending=false;
    if(m.ok){G.route=m.route;G.goal=m.route[m.route.length-1];G.autoOpening=m.opening;G.autoStairs=!!m.stairs;}
    else{G.exitIntent=false;G.autoOpening=null;G.goal=null;G.route=[];}
  }
  if(p.a==='stairs'&&p.args?.exit&&m.ok)leaveBuilding();
  if(p.a==='opening'&&p.args?.exit){
    if(m.ok&&G.exitIntent)leaveBuilding();
    else if(!m.ok&&m.why!=='busy'){G.exitIntent=false;G.autoOpening=null;}
  }
  if(p.a==='route'){
    if(p.args.nav!==G.nav)return;
    G.routePending=false;
    if(m.ok){G.route=m.route;G.goal=m.route[m.route.length-1];}else{G.goal=null;G.route=[];}
  }
  if (!m.ok) {
    if (m.why === 'busy' && m.ready_in <= 0.4 && !p.retry) {
      setTimeout(() => fire(p.a, p.args, true), m.ready_in * 1000 + 10);
      return;
    }
    if (m.why === 'busy') return;
    sfx.click();
    if (m.why && m.why !== 'dead' && m.why !== 'unknown') toast(m.why[0].toUpperCase() + m.why.slice(1) + '.');
    if (p.a === 'swing' || p.a === 'shove' || p.a === 'shoot') setBusy(now, now);
    return;
  }
  if (m.message) toast(m.message);
  if (m.rec) { G.rec[p.a] = m.rec; setBusy(p.sent + took / 2 + m.rec * 1000, now); }
  if (p.a === 'swing' || p.a === 'shoot') {
    const z = m.z ? (G.zeds.get(m.z) || G.gone.find((g) => g.id === m.z)) : null;
    if (m.whiff) { if (p.a === 'swing') sfx.whiff(); return; }
    if (!m.hit) { if (z) floatAt(z, 'miss', '#c9cdc6'); return; }
    if (m.finish) sfx.finish(); else if (p.a === 'swing') sfx.thwack();
    buzz(m.kill ? 45 : 18); G.shake = Math.max(G.shake, m.finish ? 7 : 4);
    if (z) {
      z.flash = now; spark(z, now);
      floatAt(z, m.kill ? 'DEAD' : m.down ? 'DOWN' : String(Math.round(m.dmg)), m.kill ? '#ff6a5c' : m.down ? '#e0a030' : '#fff');
      if (m.kill) { sfx.kill(); z.killed = true; }
    }
    if (m.down) hint('down', 'It is down. FINISH it before it gets up.', 3);
  } else if (p.a === 'shove') {
    for (const h of m.hit) {
      const z = G.zeds.get(h.z);
      if (z) { z.flash = now; floatAt(z, h.down ? 'DOWN' : 'shoved', h.down ? '#e0a030' : '#c9cdc6'); }
    }
    if (m.hit.some((h) => h.down)) hint('down', 'It is down. FINISH it before it gets up.', 3);
  }
}

// ------------------------------------------------------------------ doing things
const CONTAINER_NAME = { bag: 'Bag', car: 'Car boot', crate: 'Crate', chest: 'Chest', medical: 'Medical case', toolbox: 'Toolbox', fire_station: 'Fire station locker', police_station: 'Police locker', kitchen:'Kitchen cupboard',bathroom:'Bathroom cabinet',bedroom:'Bedroom wardrobe',garage:'Garage shelves' };
const CONTAINER_ART = { chest: 'crate', medical: 'bandage', toolbox: 'crate',fire_station:'crate',police_station:'crate',kitchen:'crate',bathroom:'crate',bedroom:'crate',garage:'crate' };
const containerName = (s) => CONTAINER_NAME[s[3]] || s[3];
function approachContainer(s) {
  if (!s || s[4] || !G.desk || G.dead) return;
  G.selectedStash = s[0];
  const building=s[5]&&G.buildings.find(b=>b.id===s[5]);
  if(G.you.vehicle){G.vehicleGoal=target;collapseWorldUI('movement');return;}
  if(building&&G.inside!==building.id){walkTo(entranceApproach(building,G.desk));toast('Approach the door, open it, then tap inside.');return;}
  walkTo([s[1],s[2]]);
  toast('Walking to the ' + containerName(s).toLowerCase() + '. Search when you get close.');
}
function leaveBuilding(){
  if(!G.inside)return;
  G.exitIntent=true;G.autoOpening=null;G.autoStairs=false;G.route=[];G.goal=null;G.nav++;G.routePending=true;
  fire('exit_route');
  toast('Heading outside. Closed doors will open as you reach them.');
}
function walkTo(ll){
  if(!ll||!G.desk)return;
  collapseWorldUI('movement');
  G.nav++;G.route=[];G.goal=ll;
  if(pathClear(G.buildings,G.desk,ll)){G.routePending=false;return;}
  G.routePending=true;fire('route',{lat:ll[0],lng:ll[1],nav:G.nav});
}
const BTN = { scream: 'bScream', swing: 'bSwing', shove: 'bShove', shoot: 'bShoot', back: 'bBack' };

function aim(now, forDisplay, action='swing') {
  // what a swing would reach: one on the ground first, then the nearest standing
  if (!G.you || !G.pos) return null;
  const [la, ln] = lerpAt(G.pos, now);
  if(G.you.combat){
    const id=G.you.combat[['shoot','shove'].includes(action)?action:'swing'],z=G.zeds.get(id);
    if(!z)return null;const ll=lerpAt(z.p,now),[dx,dy]=deltaM(la,ln,...ll);
    return {z,d:Math.hypot(dx,dy),dx,dy,down:['down','rising'].includes(z.state)};
  }
  let best = null, bestD = 1e9, bestDown = null, bestDownD = 1e9;
  for (const z of G.zeds.values()) {
    const ll = lerpAt(z.p, now), [dx, dy] = deltaM(la, ln, ll[0], ll[1]), d = Math.hypot(dx, dy);
    if(!pathClear(G.buildings,[la,ln],ll)&&G.items[G.you.hands?.code]?.kind!=='gun')continue;
    const down = z.state === 'down' || z.state === 'rising';
    if (down && d <= (G.tune.finish_reach_m || 5.2) && d < bestDownD) { bestDown = { z, d, dx, dy, down }; bestDownD = d; }
    if (!down && d <= (G.tune.swing_reach_m || 3.4) + (forDisplay ? 0 : 1.5) && d < bestD) { best = { z, d, dx, dy, down }; bestD = d; }
  }
  return bestDown || best;
}

function press(a, ev, args) {
  if(['swing','shove','shoot','back'].includes(a)){collapseWorldUI('combat');closeArea();}
  const tapT = (ev && ev.timeStamp) || T();
  initAudio();
  if (!G.you || G.dead) return;
  if(a==='leave'){leaveBuilding();return;}
  if(['search_building','search','bandage','disinfect'].includes(a)){$('bStop').click();}
  G.taps.push({ t: tapT, drawn: false });
  const el = $(BTN[a]);
  if (el) { el.classList.add('hit'); setTimeout(() => el.classList.remove('hit'), 90); }
  const now = T();
  if (a === 'swing' || a === 'shove' || a === 'shoot') {
    const wait = G.busyUntil - now;
    if (wait > 450) { sfx.click(); return; }
    if (wait > 12) {                                   // pressed a touch early: hold it and fire on time
      clearTimeout(G.bufTimer);
      G.bufTimer = setTimeout(() => fire(a, args), wait + 4);
      return;
    }
  }
  if (a === 'back' && (G.backReadyAt > now + 150)) { sfx.click(); return; }
  if(a==='search'||a==='search_building')sfx.search();
  fire(a, args);
}

function fire(a, args, retry) {
  const now = T();
  if (!G.you || G.dead) return;
  const id = ++G.seq;
  G.pending.set(id, { a, args, sent: now, retry });
  send({ t: 'act', id, a, ...(args || {}) });
  G.lastFire = now;
  if (retry) return;
  // show it now; the server's verdict lands a moment later
  if (a === 'swing' || a === 'shove' || a === 'shoot') {
    const t = aim(now,false,a);
    if(t){const d=projectM(t.dx,t.dy,G.cam.iso);G.aimAng=Math.atan2(d[1],d[0]);}
    G.swingAt = now; G.actionKind = a;
    G.fx.push({ kind: a, ang: G.aimAng, t0: now, reach: t ? t.d : 0 });
    setBusy(now + (G.rec[a] || 0.7) * 1000, now, true);
    if (a === 'swing') sfx.swing(); else if (a === 'shove') sfx.shove(); else sfx.shot();
  } else if (a === 'back') {
    sfx.free(); G.backReadyAt = now + 6000;
  }
}

// ------------------------------------------------------------------ the heads-up display
function toast(text, cls = '') {
  const box = $('toasts'), d = document.createElement('div');
  // under whatever heads the screen just now: the goal and the nearby-loot line make that bar taller
  const bar = (document.body.classList.contains('area') ? $('areaBar') : $('navigation')).getBoundingClientRect();
  if (bar.height) box.style.top = Math.round(bar.bottom + 6) + 'px';
  d.className = 'toast ' + cls; d.textContent = text;
  box.appendChild(d);
  while (box.children.length > 2) box.firstChild.remove();
  setTimeout(() => d.remove(), cls === 'tip' ? 6500 : 2700);   // a tip is a full sentence: leave time to read it
}
function hint(key, text, times = 2) {
  const n = +(LS.get('hint.' + key, '0'));
  if (n >= times || G.hints[key]) return;
  G.hints[key] = 1; setTimeout(() => { delete G.hints[key]; }, 20000);
  LS.set('hint.' + key, String(n + 1));
  toast(text);
}
// A newcomer's first minute: three spaced tips, each shown once per device.
function firstSteps() {
  if (G.firstSteps || +(LS.get('hint.first', '0')) >= 1) return;
  G.firstSteps = true; LS.set('hint.first', '1');
  const tips = ['Tap the street to walk, or drag the lower left of the screen to steer. Tap a glowing bag or crate, then SEARCH it.',
    'Fast feet are loud: a gentle push on the stick, or QUIET, creeps past. SHOVE one that grabs you, then SWING.',
    'Go into a building and choose Home in your pack: supplies stored there outlive you.'];
  tips.forEach((text, i) => setTimeout(() => { if (!G.dead) toast(text, 'tip'); }, 1500 + i * 9000));
}
function flashEdge(v) { const e = $('edge'); e.style.opacity = String(v); setTimeout(() => { e.style.opacity = String(G.edgeBase || 0); }, 160); }
function floatAt(z, text, color) { const ll = lerpAt(z.p, T()); G.floaters.push({ lat: ll[0], lng: ll[1], text, color, t0: T() }); }
function spark(z, now) { const ll = lerpAt(z.p, now); G.fx.push({ kind: 'spark', lat: ll[0], lng: ll[1], t0: now }); }

function updateHud(now) {
  const y = G.you; if (!y) return;
  let engaged = 0, chasing = 0;
  for (const z of G.zeds.values()) if (z.mine) { if (z.state === 'engaged') engaged++; else if (z.state === 'chase' || z.state === 'alert') chasing++; }
  G.engaged = engaged; G.chasing = chasing;
  if (area.on) {                                       // the world does not wait while you read the map
    let close = engaged > 0;
    for (const z of G.zeds.values()) if (z.mine && z.state !== 'down' && Math.hypot(...deltaM(y.lat, y.lng, z.p.b[0], z.p.b[1])) < 8) close = true;
    if (close) closeArea('attack');
  }

  // status badges: only there when something is wrong
  const mk = y.moodles.map((m) => m.join(':')).join(',');
  if (mk !== G.moodKey) {
    const had = new Set(G.moodKey.split(',').map((s) => s.split(':')[0]));
    G.moodKey = mk;
    const box = $('moodles'); box.textContent = '';
    for (const [code, lvl] of y.moodles) {
      const d = document.createElement('div'); d.className = `mood tap l${lvl}`;
      const img = new Image(); img.alt = code; img.src = `/assets/mood_${code}.webp`;
      img.onerror = () => { const f = document.createElement('div'); f.className = 'fb'; f.textContent = code; img.replaceWith(f); };
      const pips = document.createElement('div'); pips.className = 'pips';
      for (let i = 1; i <= 4; i++) { const s = document.createElement('s'); if (i <= lvl) s.className = 'on'; pips.appendChild(s); }
      d.append(img, pips);
      d.addEventListener('pointerdown', () => toast(MOOD_HELP[code] || code));
      box.appendChild(d);
      if (!had.has(code)) hint('mood.' + code, MOOD_HELP[code], 1);
    }
  }
  $('kills').textContent = y.kills ? `${y.kills} put down` : '';
  $('bScream').disabled = y.scream > 0;
  $('bScream').textContent = y.scream > 0 ? 'SCREAM ' + Math.ceil(y.scream) + 's' : 'SCREAM';

  const ew = $('endwrap'), eb = $('endbar');
  ew.classList.toggle('on', engaged > 0 || chasing > 0 || y.end < 99);
  eb.style.width = y.end + '%';
  eb.style.background = y.end < 25 ? 'var(--red)' : y.end < 50 ? 'var(--amber)' : 'var(--green)';

  const gun = y.hands && G.items[y.hands.code] && G.items[y.hands.code].kind === 'gun';
  $('bBack').hidden = engaged === 0;
  $('bBack').classList.toggle('no', y.end < (G.tune.back_cost || 15));
  $('bShoot').hidden = !gun;
  $('ammo').textContent = gun ? String(y.ammo) : '';
  $('bShoot').classList.toggle('no', gun && y.ammo <= 0);
  const t = aim(now, true), armed = y.hands && !gun;
  const fin = !!(t && t.down);
  $('swingLabel').textContent = fin ? (armed ? 'FINISH' : 'STOMP') : (armed ? 'SWING' : 'PUNCH');
  $('bSwing').classList.toggle('finish', fin);
  const nearest=[...G.zeds.values()].map(z=>({z,d:Math.hypot(...deltaM(y.lat,y.lng,...z.p.b))})).filter(z=>z.d<8).sort((a,b)=>a.d-b.d)[0];
  $('combatHint').hidden=!nearest&&!t;
  $('combatHint').textContent=t?(fin?'Finish':'In reach')+' · '+t.d.toFixed(1)+'m':nearest?(pathClear(G.buildings,[y.lat,y.lng],nearest.z.p.b)?'Approach':'Blocked')+' · '+nearest.d.toFixed(1)+'m':'';
  $('bSwing').setAttribute('aria-label',(fin?(armed?'Finish zombie':'Stomp zombie'):(armed?'Swing weapon':'Punch'))+(t?' · in reach':' · no target in reach'));
  if(t&&!G.moving){const direction=projectM(t.dx,t.dy,G.cam.iso);G.faceLeft=direction[0]<0;}

  const hi = $('handImg'), hc = y.hands ? y.hands.code : 'fist';
  if (hi.dataset.code !== hc) { hi.dataset.code = hc; hi.style.visibility = y.hands ? 'visible' : 'hidden'; if (y.hands) hi.src = `/assets/item_${hc}.webp`; }
  $('handCond').style.setProperty('--c', (y.hands ? y.hands.cond * 10 : 0) + '%');

  const floorBuilding=G.buildings.find(b=>b.id===G.inside);
  $('bFloor').hidden=!floorBuilding?.stairs;
  $('bFloor').textContent=(G.you.floor?'Floor '+(G.you.floor+1):'Ground floor')+' · stairs';
  $('bZoomReset').hidden=!G.inside;
  $('bZoomReset').textContent='Zoom '+Math.round(G.indoorZoom*100)+'% · reset';
  $('bSprint').firstElementChild.textContent = y.sprinting ? 'STOP' : 'SPRINT';
  $('bSprint').disabled = !y.sprinting && y.end < 10;
  $('bSprint').setAttribute('aria-pressed', String(!!y.sprinting));
  $('bQuiet').setAttribute('aria-pressed', String(!!y.quiet));
  // how far the survivor's feet carry right now: the dial the pace buttons turn
  const heard = y.heard_m || 0, chip = $('noiseChip');
  const study = G.body && G.body.study;
  chip.textContent = study && study.reading && y.speed < 0.4 ? 'Reading · ' + waitText(study.ready - G.serverNow) + ' left'
    : (y.quiet && y.speed > 0.4 ? 'Creeping · ' : y.sprinting && y.speed > 0.4 ? 'Sprinting · ' : '') + 'heard ' + heard + ' m';
  chip.className = heard <= 5 ? 'soft' : heard <= 11 ? '' : heard <= 20 ? 'loud' : 'roar';
  // the calendar of this life, and what the whole area shares: rain and the helicopter
  const sky = (G.body && G.body.weather) || {}, heli = sky.heli, heliEl = $('heliChip');
  $('dayChip').textContent = 'Day ' + ((G.body && G.body.day) || 1) + (sky.rain ? ' · Rain' : '');
  $('dayChip').className = sky.rain ? 'rain' : '';
  $('dayChip').title = sky.rain ? 'Rain: barrels fill faster and work is harder to hear.' : '';
  heliEl.hidden = !heli;
  if (heli) {
    const over = heli.phase === 'overhead', mins = Math.max(1, Math.ceil(((over ? heli.ends : heli.overhead) - G.serverNow) / 60));
    heliEl.textContent = !over ? 'HELICOPTER coming · get indoors' : G.inside ? 'Helicopter overhead · ' + mins + ' min · stay inside' : 'HELICOPTER overhead · ' + mins + ' min · get indoors';
    heliEl.className = over && !G.inside ? 'roar' : over ? 'soft' : 'loud';
    const nowMs = performance.now();
    if (nowMs - (G.heliAt || 0) > 2700) { G.heliAt = nowMs; sfx.heli(over ? (G.inside ? .08 : .15) : .06); }
  }
  const leads = (G.stashes || []).filter(s => !s[4]).map(s => ({s, d: Math.hypot(...deltaM(y.lat, y.lng, s[1], s[2]))})).sort((a,b) => a.d-b.d);
  const lead = leads.find(x => x.s[0] === G.selectedStash) || leads[0];
  G.bodyLead=nearbyBody(G.corpses||[],c=>Math.hypot(...deltaM(y.lat,y.lng,c.lat,c.lng)));
  $('bBody').hidden=!G.bodyLead;
  if(G.bodyLead)$('bBody').textContent=(G.bodyLead.c.own?'Recover gear':G.bodyLead.c.searched?'Body loot':'Search body')+' · '+Math.round(G.bodyLead.d)+'m';
  G.lootLead = lead?.s || null;
  $('bLoot').hidden = !lead;
  if (lead) $('bLoot').textContent = (lead.d <= (G.tune.stash_reach_m || 14) ? 'Nearby: ' : 'Explore: ') + containerName(lead.s) + ' · ' + Math.round(lead.d) + 'm';

  // one-tap things that only make sense right now
  const list = [], b = G.body, have = (code) => b && b.items.some((i) => i.code === code && i.qty > 0);
  const open = b ? b.wounds.filter((w) => w.bleeding && !w.bandaged) : [];
  if (open.length && have('bandage') && !(G.channel && G.channel.kind === 'bandage')) list.push({ k: 'bandage', label: 'BANDAGE', cls: 'red', a: 'bandage' });
  if (G.pos) {
    const [la, ln] = lerpAt(G.pos, now);
    let near = null, nd = G.tune.stash_reach_m || 14;
  for (const s of G.stashes) {
      if(s[5]&&(s[5]!==G.inside||s[8]===false))continue;
      if (s[4]) continue;
      const d = Math.hypot(...deltaM(la, ln, s[1], s[2]));
      if (d <= nd && s[7]!==false) { nd = d; near = s; }
    }
    if (near && engaged === 0 && !(G.channel && G.channel.kind === 'search')) list.push({ k: 'search:' + near[0], label: 'SEARCH ' + containerName(near).toUpperCase(), a: 'search', args: { stash: near[0] } });
    for (const d of G.drops) {
      const [dx, dy] = deltaM(la, ln, d[1], d[2]);
      if (Math.hypot(dx, dy) <= (G.tune.pickup_m || 5)) { list.push({ k: 'pick:' + d[0], label: 'PICK UP ' + itemName(d[3]).toUpperCase(), a: 'pickup', args: { drop: d[0] } }); break; }
    }
  }
  if(G.you){
    const nearby=G.buildings.filter(b=>!G.inside||b.id===G.inside).flatMap(b=>b.openings.map(o=>({o,d:Math.hypot(...deltaM(G.you.lat,G.you.lng,(o.a[0]+o.b[0])/2,(o.a[1]+o.b[1])/2))}))).filter(x=>x.d<=2.7&&!x.o.broken&&!x.o.barricaded).sort((a,b)=>a.d-b.d);   // a boarded one cannot be opened: its card says so
    for(const {o} of nearby.slice(0,2))list.push({k:o.id+':'+o.open,label:(o.open?'CLOSE ':'OPEN ')+o.label.toUpperCase(),a:'opening',args:{opening:o.id,op:o.open?'close':'open'}});
  }
  const interior=G.buildings.find(b=>b.id===G.inside);
  if(interior){
    if(interior.stairs&&Math.hypot(...deltaM(y.lat,y.lng,...interior.stairs))<=2.7){
      if(y.floor>0)list.push({k:'stairs:down:'+y.floor,label:'DOWNSTAIRS',a:'stairs',args:{op:'down'}});
      if((y.floor||0)<interior.floors-1)list.push({k:'stairs:up:'+y.floor,label:'UPSTAIRS',a:'stairs',args:{op:'up'}});
    }
    if(y.building_search_left>0&&G.channel?.kind!=='search_building'&&engaged===0)list.push({k:'building-search:'+interior.id+':'+y.building_search_left,label:'SEARCH BUILDING · '+y.building_search_left+' LEFT',a:'search_building'});
    list.push({k:'leave:'+interior.id,label:'EXIT BUILDING',a:'leave'});
  }
  const lvl = (code) => { const m = y.moodles.find((x) => x[0] === code); return m ? m[1] : 0; };
  if (lvl('winded') >= 2 && have('water')) list.push({ k: 'water', label: 'DRINK', a: 'use', args: { code: 'water' } });
  if (lvl('panic') >= 3 && have('snack') && engaged === 0) list.push({ k: 'snack', label: 'EAT', a: 'use', args: { code: 'snack' } });
  const key = list.map((x) => x.k).join('|');
  if (key !== G.ctxKey) {
    G.ctxKey = key; G.ctx = list;
    const box = $('ctx'); box.textContent = '';
    for (const it of list) {
      const btn = document.createElement('button'); btn.className = 'ctxb ' + (it.cls || ''); btn.textContent = it.label;
      btn.addEventListener('pointerdown', (ev) => { ev.preventDefault(); press(it.a, ev, it.args); });
      box.appendChild(btn);
    }
  }

  // heartbeat and the red edge follow panic and blood
  const level = clamp(Math.max(y.panic / 100, (60 - y.hp) / 60, engaged ? 0.45 : 0), 0, 1);
  G.edgeBase = clamp((50 - y.hp) / 100, 0, 0.45);
  setHeart(level, (lv) => flashEdge(Math.max(G.edgeBase, lv * 0.4)));
  if (level <= 0.05) $('edge').style.opacity = String(G.edgeBase);
  renderWorldUI();
}

function healthWord(hp) { return hp >= 80 ? 'Fine' : hp >= 60 ? 'Hurt' : hp >= 40 ? 'Badly hurt' : hp >= 20 ? 'In a very bad way' : 'Dying'; }

function renderPanel() {
  const b = G.body, y = G.you; if (!b || !y) return;
  $('health').textContent = `${G.name}: ${healthWord(y.hp)}`;
  $('backgroundStatus').textContent=b.background?b.background.name+' · '+b.background.trait_name+' — '+b.background.description+' '+b.background.trait_description:'Survivor · Balanced — this existing life has no starting background bonuses.';
  const progress = b.progression;
  const pb = $('progression'); pb.textContent = '';
  if (progress) {
    const summary = document.createElement('p');
    summary.className = 'fine'; summary.textContent = 'Survivor level ' + progress.level + ' · ' + progress.xp + ' XP' + (progress.next ? ' / ' + progress.next + ' for the next level' : ' · maximum level');
    pb.appendChild(summary);
    for (const skill of progress.skills) {
      const row = document.createElement('div'); row.className = 'rowi';
      row.innerHTML = '<div class="n"><b>' + esc(skill.name) + ' · ' + skill.level + '/5</b><div class="s">' + skill.xp + ' XP' + (skill.next ? ' / ' + skill.next : ' · mastered') + '</div><div class="s">' + esc(skill.effect) + '</div></div>';
      pb.appendChild(row);
    }
  }
  const wb = $('wounds'); wb.textContent = '';
  const has = (code) => b.items.some((i) => i.code === code && i.qty > 0);
  if (!b.wounds.length) wb.innerHTML = '<div class="rowi"><span class="s">None.</span></div>';
  for (const w of b.wounds) {
    const row = document.createElement('div'); row.className = 'rowi';
    const state = [w.bleeding ? '<span class="bad">bleeding</span>' : '', w.bandaged ? 'bandaged' : '', w.clean ? 'clean' : ''].filter(Boolean).join(', ');
    row.innerHTML = `<div class="n">${esc(w.kind === 'laceration' ? 'Deep cut' : w.kind[0].toUpperCase() + w.kind.slice(1))}, ${esc(w.part)}<div class="s">${state || 'open'}</div></div>`;
    if (!w.bandaged && has('bandage')) row.appendChild(panelBtn('Bandage', 'bandage', { wound: w.id }, true));
    if (!w.clean && has('disinfectant')) row.appendChild(panelBtn('Disinfect', 'disinfect', { wound: w.id }));
    wb.appendChild(row);
  }
  renderInventory();
  $('bWorldView').textContent=G.cam.iso?'View: 3D':'View: flat map';
  $('bMute').textContent = 'Sound: ' + (isMuted() ? 'off' : 'on');
  $('bDev').textContent = 'Stopwatch: ' + (G.dev ? 'on' : 'off');

}
function panelBtn(label, a, args, pri) {
  const btn = document.createElement('button'); btn.textContent = label; if (pri) btn.className = 'pri';
  btn.addEventListener('click', (ev) => { press(a, ev, args); if (a === 'bandage' || a === 'disinfect') $('panel').hidden = true; });
  return btn;
}

function fmtDur(s) { s = Math.max(0, Math.round(s)); const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60); return h ? `${h} h ${m} min` : m ? `${m} min ${s % 60} s` : `${s} s`; }
function showDeath(card) {
  collapseWorldUI('death'); stickEnd(false); closeArea(); G.quietHeld = false;
  if (G.dead) return;
  G.dead = true; G.card = card || G.card || {};
  const c = G.card;
  sfx.death(); buzz([200, 80, 300]); setHeart(0);
  $('panel').hidden = true;
  const line = c.cause === 'turned' ? `The fever won. ${G.name} got back up, but not as ${G.name}.`
    : c.cause === 'bled out' ? `${G.name} bled out${c.part ? ' from the ' + c.part : ''}.`
    : `${G.name} was pulled down${c.by > 1 ? ' by ' + c.by + ' of them' : ''}.`;
  $('deathLine').textContent = line;
  const ul = $('deathStats'); ul.textContent = '';
  const add = (t) => { const li = document.createElement('li'); li.textContent = t; ul.appendChild(li); };
  if (c.lived_s !== undefined) add(`Lasted ${fmtDur(c.lived_s)}, day ${Math.floor(c.lived_s / 86400) + 1}`);
  if (c.walked_m !== undefined) add(`Walked ${c.walked_m >= 1000 ? (c.walked_m / 1000).toFixed(1) + ' km' : c.walked_m + ' m'}`);
  if (c.kills !== undefined) add(`Put down ${c.kills}`);
  if (c.infected && c.cause !== 'turned') add('Was already infected');
  if(c.corpse)add('Your carried gear stays here for 72 hours. Find your recovery pack in Area'+(c.floor_level?' on Floor '+(c.floor_level+1):'')+'. Home supplies are safe.');
  setTimeout(() => { $('death').hidden = false; $('hud').hidden = true; }, c.t ? 900 : 0);
}

// ------------------------------------------------------------------ where you are
function sendPos(force) {
  if (!G.lastPos || G.launchPending&&!G.launchHunted) return;
  const now = T();
  if (!force && now - G.lastPosSent < 110) return;
  G.lastPosSent = now;
  send({ t: 'pos', lat: G.lastPos[0], lng: G.lastPos[1], acc: G.lastPos[2], mode: G.mode, placement_epoch:G.minimumEpoch, floor_epoch:G.you?.floor_epoch||0 });
}

async function startDesk(serverLL) {
  if (!CFG.real_gps && !serverLL) return;          // a public survivor starts by choosing, never by locating
  if (G.backgroundBusy || G.deskStarting || G.phoneGps&&G.launchPending&&!G.launchHunted) return;
  G.deskStarting = true;
  let ll = null;
  const at = CFG.real_gps ? (Q.get('at') || '').split(',').map(Number) : [];
  if (at.length === 2 && isFinite(at[0]) && isFinite(at[1]) && Q.get('at')) ll = at;
  if (!ll && serverLL) ll = serverLL;
  if (!ll && navigator.geolocation) {
    toast('Finding your street.');
    ll = await new Promise((res) => {
      const t = setTimeout(() => res(null), 6000);
      navigator.geolocation.getCurrentPosition((p) => { clearTimeout(t); res([p.coords.latitude, p.coords.longitude]); },
        () => { clearTimeout(t); res(null); }, { enableHighAccuracy: false, timeout: 5500, maximumAge: 600000 });
    });
  }
  if (G.gpsCenter && G.desk) ll = G.desk; // a GPS callback may finish while awaiting location
  if (!ll) { ll = FALLBACK_START; toast('No location, so you start in Chicago.'); }
  G.desk = ll; G.lastPos = [ll[0], ll[1], 1];
  sendPos(true);
  if (CFG.real_gps && !Q.has('at')) startGps();
  if (!('ontouchstart' in window)) hint('desk', 'Arrow keys or WASD to walk, or tap the street.', 2);   // phones get the first-steps tips
}

const GPS_CENTER_RADIUS_M = 804.672;

function updateNavigation() {
  // One line of guidance: what the server is doing, else the next shelter goal, else how to move.
  const goal = G.body && G.body.survival && G.body.survival.objective;
  $('movementLabel').textContent = G.mapping ? 'Mapping nearby buildings…'
    : G.siege ? 'Hold the plaza. Tap to move; chests open when you reach them.'
    : goal ? 'Goal: ' + goal
    : G.gpsCenter ? 'Tap to walk · GPS centered' : 'Tap the map to walk';
}

function completePlacement(m,args){
  // A committed snapshot is also an acknowledgement if the action reply is lost.
  if(m.placement_epoch<=G.minimumEpoch&&!G.launchPending)return;
  G.minimumEpoch=m.placement_epoch;G.launchPending=false;G.launchHunted=false;G.pickStart=false;
  G.locationBusy=false;G.gpsCenter=m.anchor;G.desk=[m.lat,m.lng];G.pos=lerpNew(m.lat,m.lng);G.located=true;
  G.lastPos=[m.lat,m.lng,1];G.goal=null;G.route=[];G.keys.clear();G.nav++;G.exitIntent=false;G.autoOpening=null;
  if(m.anchor)LS.set('gpsCenter',JSON.stringify(m.anchor));
  $('locationNotice').hidden=true;$('locationStart').hidden=true;$('startChooser').hidden=true;sendPos(true);updateNavigation();
}

function showStarts(){
  const list=$('startList');list.replaceChildren();
  for(const s of CFG.starts){
    const b=document.createElement('button'),name=document.createElement('b'),blurb=document.createElement('small');
    b.type='button';b.className='go';b.dataset.start=s.id;name.textContent=s.label;blurb.textContent=s.blurb;
    b.append(name,blurb);b.onclick=()=>chooseStart(s.id);list.append(b);
  }
  $('startChooser').hidden=false;
}
function chooseStart(id){
  if(G.backgroundBusy||G.locationBusy){setTimeout(()=>chooseStart(id),200);return;}
  placeLocation([0,0,1,Date.now()],'launch','manual',id);
}
function titleStatus(text){const e=$('titleStatus');e.textContent=text;e.hidden=false;}

function locationMessage(message){$('locationMessage').textContent=message;$('locationNotice').hidden=false;}
function requestLocation(){
  if(!CFG.real_gps||!G.launchPending||G.locationBusy||G.dead||G.pickStart)return;
  if(!navigator.geolocation){locationMessage('GPS is unavailable. Choose a map start.');return;}
  const generation=G.locationGeneration;
  navigator.geolocation.getCurrentPosition(p=>{
    if(generation!==G.locationGeneration||!G.launchPending)return;
    G.lastGPSFix=[p.coords.latitude,p.coords.longitude,p.coords.accuracy,p.timestamp];
    const fix=freshFix(p);
    if(fix)placeLocation(fix,'launch');
    else locationMessage('Waiting for a fresh GPS fix within 80m accuracy. Retry or choose on map.');
  },()=>{if(generation===G.locationGeneration&&G.launchPending)locationMessage('GPS is unavailable right now. Retry or choose a map start.');},
  {enableHighAccuracy:true,maximumAge:0,timeout:15000});
  // A current watch fix is useful while stationary; never reuse a stored anchor.
  const last=G.lastGPSFix;
  const current=last&&freshFix({coords:{latitude:last[0],longitude:last[1],accuracy:last[2]},timestamp:last[3]});
  if(current&&!G.locationBusy)placeLocation(current,'launch');
}
function placeLocation(fix,reason,source='gps',start=null){
  if(G.backgroundBusy||G.locationBusy||!G.gotHello||G.dead)return;
  G.locationBusy=true;
  const id=++G.seq,args={lat:fix[0],lng:fix[1],accuracy:fix[2],timestamp:fix[3],source,reason,
    ticket:G.placementTicket,request:crypto.randomUUID(),generation:G.locationGeneration};
  if(start)args.start=start;
  G.pending.set(id,{a:'place',args,sent:T()});send({t:'act',id,a:'place',...args});
  if(reason==='launch')locationMessage(source==='gps'?'Starting at your current GPS location…':'Starting at your selected map location…');
}

function gpsCenterHere(fix, announce = false) {
  if(G.phoneGps){placeLocation(fix,'travel');return;}
  const ll = fix.slice(0, 2);
  G.gpsCenter = ll; LS.set('gpsCenter', JSON.stringify(ll));
  G.gpsRelocateUntil=T()+3000;G.inside=null;G.room=null;
  G.mode = 'desk'; G.desk = ll; G.goal = null; G.keys.clear();
  G.route=[];G.routePending=false;G.nav++;G.exitIntent=false;G.autoOpening=null;G.gpsTravelCandidate=null;
  G.lastPos = [ll[0], ll[1], 1]; sendPos(true);
  updateNavigation();
  if (announce) toast('Your play area moved to your new GPS location.');
}

function startGps() {
  if (!CFG.real_gps || !navigator.geolocation || G.watch != null) return;
  G.watch = navigator.geolocation.watchPosition((p) => {
    const fix = [p.coords.latitude, p.coords.longitude, p.coords.accuracy || 15,p.timestamp];
    G.fixAt = T(); G.lastGPSFix = fix;
    // A coarse network fix must not replace a useful GPS center.
    if (fix[2] > 80) return;
    if(G.phoneGps){
      if(!freshFix(p)||G.pickStart)return;
      if(G.launchPending){placeLocation(fix,'launch');return;}
      if(!G.gpsCenter)return; // explicit manual start never silently relocates
    }
    if (!G.gpsCenter) {
      let saved = null;
      try { saved = JSON.parse(LS.get('gpsCenter', 'null')); } catch (_) {}
      const valid = Array.isArray(saved) && saved.length === 2 && saved.every(Number.isFinite);
      const away = valid ? Math.hypot(...deltaM(saved[0], saved[1], fix[0], fix[1])) : Infinity;
      if ((away < GPS_CENTER_RADIUS_M || !valid && G.you && Math.hypot(...deltaM(G.you.lat,G.you.lng,fix[0],fix[1]))<GPS_CENTER_RADIUS_M) && G.located && G.you) {
        // Reopening in the same area preserves the survivor's virtual position.
        G.gpsCenter = valid?saved:fix.slice(0,2); LS.set('gpsCenter',JSON.stringify(G.gpsCenter));G.mode = 'desk';
        // Establish the anchor without undoing a tap walk already in progress.
        if(!G.desk){G.desk = [G.you.lat, G.you.lng]; G.lastPos = [...G.desk, 1]; sendPos(true);}
        updateNavigation();
      } else gpsCenterHere(fix);
      return;
    }
    const d = Math.hypot(...deltaM(G.gpsCenter[0], G.gpsCenter[1], fix[0], fix[1]));
    // Require the fix's uncertainty circle to be outside the radius: ignore drift.
    if (d - fix[2] <= GPS_CENTER_RADIUS_M){G.gpsTravelCandidate=null;return;}
    const candidate=G.gpsTravelCandidate,now=T();
    if(!candidate||Math.hypot(...deltaM(...candidate.ll,fix[0],fix[1]))>50){
      G.gpsTravelCandidate={ll:fix.slice(0,2),firstAt:now,count:1};return;
    }
    candidate.count++;
    if(candidate.count>=3&&now-candidate.firstAt>=8000)gpsCenterHere(fix,true);
  }, (err) => {
    if (err.code === 1 && !G.gpsDeniedToast) { toast('Location is blocked. You can still tap to walk.', 'bad'); G.gpsDeniedToast = true; }
    else if (err.code !== 1 && !G.gpsCenter && !G.gpsFixToast) { toast('No GPS fix yet. You can still tap to walk.', 'bad'); G.gpsFixToast = true; }
    if (G.mode === 'gps') { G.mode = 'desk'; updateNavigation(); startDesk(); }
  }, { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 });
  if (navigator.wakeLock) navigator.wakeLock.request('screen').catch(() => {});
}

// ---- thumb steering -------------------------------------------------------------------
// A drag that starts in the lower left of the map becomes a stick; a tap there is still a tap.
// A gentle push creeps (slow, quiet, harder to spot); past half way is the normal pace.
const STICK = { dead: 10, max: 54, arm: 12, creep: 0.5 };
const stickZone = (x, y) => x <= W * 0.62 && y >= H * 0.42;
function stickPace(m, full) {
  if (m < STICK.creep && !G.you?.sprinting) return Math.min(full, G.tune.quiet_speed || 1.2) * Math.max(0.35, m / STICK.creep);
  return full * (0.6 + 0.4 * clamp((m - STICK.creep) / (1 - STICK.creep), 0, 1));
}
function wantQuiet(on) {
  // keep the server's creeping flag in step with the stick or the QUIET button, without flooding it
  const y = G.you, now = T();
  if (!y || G.dead || !!y.quiet === on || now - G.quietSent < 400) return;
  if ([...G.pending.values()].some((p) => p.a === 'quiet')) return;
  G.quietSent = now; fire('quiet', { op: on ? 'start' : 'stop' });
}
function stickMove(x, y) {
  const t = G.stickTouch; if (!t) return;
  const dx = x - t.x0, dy = y - t.y0, r = Math.hypot(dx, dy);
  if (!t.on) {
    if (r < STICK.arm) return;
    t.on = true; collapseWorldUI('movement'); $('stick').classList.remove('rest');
    $('stick').style.left = t.x0 + 'px'; $('stick').style.top = t.y0 + 'px';
  }
  const m = clamp((r - STICK.dead) / (STICK.max - STICK.dead), 0, 1), k = Math.min(r, STICK.max) / (r || 1);
  G.stick = { x: r ? dx / r : 0, y: r ? -dy / r : 0, m };
  $('stick').firstElementChild.style.transform = `translate(${dx * k}px,${dy * k}px)`;
  $('stick').classList.toggle('creep', m > 0 && m < STICK.creep && !G.you?.sprinting);
}
function stickEnd(tap) {
  const t = G.stickTouch; if (!t) return;
  G.stickTouch = null;
  try { cv.releasePointerCapture(t.id); } catch (_) {}
  const el = $('stick'); el.classList.add('rest'); el.classList.remove('creep'); el.style.left = el.style.top = ''; el.firstElementChild.style.transform = '';
  if (t.on) { G.stick = null; G.moving = false; sendPos(true); }
  else if (tap) tapWorld(t.x0, t.y0);
}

function stepDesk(dt, now) {
  if(G.you?.vehicle&&vehicleFrame(now))return;
  if (G.mode !== 'desk' || !G.desk || G.dead) return;
  let vx = 0, vy = 0, travel = Infinity;
  const k = G.keys;
  if (k.has('ArrowLeft') || k.has('KeyA')) vx -= 1;
  if (k.has('ArrowRight') || k.has('KeyD')) vx += 1;
  if (k.has('ArrowUp') || k.has('KeyW')) vy += 1;
  if (k.has('ArrowDown') || k.has('KeyS')) vy -= 1;
  let pace = G.you?.walk_speed || DESK_SPEED;
  const stick = G.stick;
  if (vx || vy) { G.exitIntent=false;G.autoOpening=null;G.goal = null; G.route=[];G.routePending=false;G.nav++; const n = Math.hypot(vx, vy); vx /= n; vy /= n; }
  else if (stick && stick.m > 0) {
    if (G.goal || G.route.length || G.routePending || G.exitIntent) { G.exitIntent = false; G.autoOpening = null; G.goal = null; G.route = []; G.routePending = false; G.nav++; }
    vx = stick.x; vy = stick.y;
    pace = stickPace(stick.m, pace);
  }
  else if (G.goal&&!G.routePending) {
    const waypoint=G.route[0]||G.goal;
    const [dx,dy]=deltaM(...G.desk,...waypoint),d=Math.hypot(dx,dy);
    if(d<.12){
      // Prediction reaches a door before the authoritative body. Wait before opening it.
      if((G.route.length>1||G.autoOpening||G.autoStairs)&&Math.hypot(...deltaM(G.you.lat,G.you.lng,...waypoint))>.35){sendPos(false);return;}
      if(G.route.length)G.route.shift();
      if(!G.route.length&&Math.hypot(...deltaM(...G.desk,...G.goal))<.5)G.goal=null;
    }
    else{vx=dx/d;vy=dy/d;travel=d;}
  }
  if(!G.goal&&(k.size||stick&&stick.m>0)&&G.cam?.iso){const d=unprojectM(vx,-vy,true),n=Math.hypot(...d)||1;vx=d[0]/n;vy=d[1]/n;}
  if(G.exitIntent&&!G.routePending&&!G.goal){
    if(G.autoOpening&&!([...G.pending.values()].some(p=>p.a==='opening'&&p.args?.exit))){
      const opening=G.autoOpening;G.autoOpening=null;fire('opening',{opening,op:'open',exit:true});
    }else if(G.autoStairs&&!([...G.pending.values()].some(p=>p.a==='stairs'))){
      G.autoStairs=false;fire('stairs',{op:'down',exit:true});
    }else if(!G.autoOpening&&!([...G.pending.values()].some(p=>['opening','stairs'].includes(p.a)&&p.args?.exit)))G.exitIntent=false;
  }
  G.moving = !!(vx || vy);
  if (G.you && !G.you.sprinting) wantQuiet(stick && stick.m > 0 ? stick.m < STICK.creep : G.quietHeld);
  $('bStop').disabled = !G.moving&&!G.routePending&&!G.exitIntent;
  if (G.moving) {
    const before=G.desk;
    // steering by thumb or keys slides along walls; a tapped walk keeps the plain rule, so that a blocked route is noticed and planned again
    G.desk = (G.goal ? buildingMove : buildingSlide)(G.buildings,G.desk,shiftLL(G.desk[0], G.desk[1], vx * Math.min(travel, pace * dt), vy * Math.min(travel, pace * dt)));
    if(dt>.005&&G.goal&&!G.routePending&&Math.hypot(...deltaM(...before,...G.desk))<.001&&now-G.lastReplan>800){
      const destination=G.goal;G.desk=[G.you.lat,G.you.lng];G.lastReplan=now;G.replans++;if(G.exitIntent)leaveBuilding();else walkTo(destination);
    }
    G.lastPos = [G.desk[0], G.desk[1], 1];
    const facing=projectM(vx,vy,!!G.cam?.iso)[0];if(Math.abs(facing)>.2)G.faceLeft=facing<0;
    sendPos(false);
  }
}

// ------------------------------------------------------------------ drawing
const cv = $('cv'), ctx = cv.getContext('2d', { alpha: false });
let W = 0, H = 0, DPR = 1, dprCap = 2, slowSince = 0, lastDrop = 0;
function resize() {
  DPR = Math.min(dprCap, window.devicePixelRatio || 1); W = window.innerWidth; H = window.innerHeight;
  cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR);
}
window.addEventListener('resize', resize); resize();

// A slow phone gets a softer picture rather than a slow one.
function watchSpeed(now) {
  if (G.fps >= 45 || document.hidden) { slowSince = 0; return; }
  if (!slowSince) slowSince = now;
  if (now - slowSince > 1500 && now - lastDrop > 3000 && dprCap > 1) {
    dprCap = Math.max(1, dprCap - 0.5); lastDrop = now; slowSince = 0; resize();
  }
}

const fogDisc = (() => {            // drawn once, stretched every frame
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const g = c.getContext('2d'), gr = g.createRadialGradient(128, 128, 128 * 0.485, 128, 128, 128);
  gr.addColorStop(0, 'rgba(4,6,5,0)'); gr.addColorStop(0.72, 'rgba(4,6,5,0.7)'); gr.addColorStop(1, 'rgba(4,6,5,0.97)');
  g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  return c;
})();

function blob(x, y, h, body, head) {            // stand-in until the clay loads
  ctx.fillStyle = body; ctx.beginPath(); ctx.ellipse(x, y - h * 0.32, h * 0.2, h * 0.32, 0, 0, 6.3); ctx.fill();
  ctx.fillStyle = head; ctx.beginPath(); ctx.arc(x, y - h * 0.76, h * 0.17, 0, 6.3); ctx.fill();
}

function drawSprite(s, x, y, h, flip, rot, alpha, flash, fbBody, fbHead) {
  ctx.save();
  ctx.translate(x, y); if (rot) ctx.rotate(rot);
  ctx.globalAlpha = alpha;
  if (s.ok) {
    const w = h * s.img.naturalWidth / s.img.naturalHeight;
    if (flip) ctx.scale(-1, 1);
    ctx.drawImage(s.img, -w / 2, -h, w, h);
    if (flash > 0) { ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = alpha * flash; ctx.drawImage(s.img, -w / 2, -h, w, h); }
  } else {
    blob(0, 0, h, fbBody, fbHead);
    if (flash > 0) { ctx.globalAlpha = alpha * flash * 0.7; blob(0, 0, h, '#fff', '#fff'); }
  }
  ctx.restore();
}

let lastFrame = 0, shownCam = false;
function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(0.1, (now - (lastFrame || now)) / 1000); lastFrame = now;
  if (dt > 0) G.fps += (1 / dt - G.fps) * 0.05;
  // a tap is "seen" once a frame that includes it has been handed to the screen
  for (const t of G.taps) {
    if (t.drawn) { G.lat.frame.push(now - t.t); if (G.lat.frame.length > 60) G.lat.frame.shift(); t.done = true; } else t.drawn = true;
  }
  if (G.taps.length) G.taps = G.taps.filter((t) => !t.done);
  stepDesk(dt, now);
  if(G.you&&!G.you.vehicle&&!G.dead&&G.you.speed>.35&&now-(G.lastFootstep||0)>(G.you.sprinting?230:Math.max(280,580-G.you.speed*35))){G.lastFootstep=now;sfx.step(!!G.inside,!!G.you.sprinting);}
  watchSpeed(now);

  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  ctx.fillStyle = '#0a0d0c'; ctx.fillRect(0, 0, W, H);
  if(G.pickStart){
    const ll=G.previewLL;drawTiles(ctx,{lat:ll[0],lng:ll[1],ppm:1},W,H,W/2,H*.46,now);
    ctx.strokeStyle='#e0a030';ctx.lineWidth=3;ctx.beginPath();ctx.arc(W/2,H*.46,14,0,Math.PI*2);ctx.stroke();return;
  }
  if (!G.you || !G.located) return;

  const [ylat, ylng] = youLL(now), cam = G.cam;
  cam.lat = ylat; cam.lng = ylng;
  if (area.on) { drawArea(ctx, W, H, now, dt, ylat, ylng); return; }

  // how close to look: wide when the street is quiet, tight when something is on you
  let near = 1e9, engaged = 0;
  for (const z of G.zeds.values()) {
    if (!z.mine || z.state === 'idle' || z.state === 'investigate') continue;
    const ll = lerpAt(z.p, now), [dx, dy] = deltaM(ylat, ylng, ll[0], ll[1]);
    near = Math.min(near, Math.hypot(dx, dy)); if (z.state === 'engaged') engaged++;
  }
  const wide = G.sight * 0.96;
  const radius = engaged || near < 7 ? 12 : near < 1e8 ? clamp(near * 1.7, 13, wide) : wide;
  const combatZoom = engaged || near < 7 ? 1.5 : 1;
  const interior=G.buildings.find(b=>b.id===G.inside);
  let buildingCenter=null;
  let want = Math.min(W, H * 0.78) / 2 / radius * combatZoom;
  if(interior){
    const points=interior.outline.map(ll=>projectM(...deltaM(ylat,ylng,...ll),cam.iso));
    const x0=Math.min(...points.map(p=>p[0])),x1=Math.max(...points.map(p=>p[0])),y0=Math.min(...points.map(p=>p[1])),y1=Math.max(...points.map(p=>p[1]));
    want=Math.min(W*.88/Math.max(6,x1-x0),H*.44/Math.max(6,y1-y0));
    want=Math.min(64,want*combatZoom*G.indoorZoom);
    buildingCenter=combatZoom>1||G.indoorZoom>1.05?null:[(x0+x1)/2,(y0+y1)/2];
  }
  if (!shownCam) { cam.ppm = want; shownCam = true; }
  cam.ppm += (want - cam.ppm) * (1 - Math.exp(-dt * (want > cam.ppm ? 3.2 : 1.4)));
  const ppm = cam.ppm;

  let cx = W / 2, cy = H * 0.46;
  const drawer=!$('sceneDrawer').hidden?$('sceneDrawer'):!$('panel').hidden?$('panel').firstElementChild:null;
  const obstruction=drawer||(!$('worldCard').hidden&&W>H?$('worldCard'):null);
  if(obstruction){
    const rect=obstruction.getBoundingClientRect();
    if(rect.width<W*.75)cx=Math.max(80,rect.left*.5);
    else cy=Math.max(100,Math.min(cy,(rect.top+150)/2));
  }
  if(buildingCenter&&!obstruction){cx-=buildingCenter[0]*ppm;cy-=buildingCenter[1]*ppm;}
  G.screenOrigin=[cx,cy];G.screenLL=[ylat,ylng];
  if (G.shake > 0.3) { cx += (Math.random() - 0.5) * G.shake; cy += (Math.random() - 0.5) * G.shake; G.shake *= Math.exp(-dt * 9); }
  const tileBounds=groundBounds(W,H,cx,cy,cam.iso);
  ctx.save();
  if(cam.iso){ctx.translate(cx,cy);ctx.transform(Math.sqrt(3)/2,.5,-Math.sqrt(3)/2,.5,0,0);ctx.translate(-cx,-cy);}
  drawTiles(ctx,cam,W,H,cx,cy,now,tileBounds);ctx.restore();
  const P=(lat,lng)=>worldPoint(G,lat,lng);
  drawBuildings(ctx,G.buildings,G.inside,P,ppm,cam.iso);
  for(const b of G.buildings.filter(b=>b.id===G.inside&&b.stairs)){
    const [x,y]=P(...b.stairs);ctx.save();ctx.translate(x,y);ctx.fillStyle='#313b40';ctx.strokeStyle='#e4d7a9';ctx.lineWidth=2;
    ctx.fillRect(-14,-16,28,22);for(let i=0;i<4;i++){ctx.beginPath();ctx.moveTo(-11,-12+i*5);ctx.lineTo(11,-12+i*5);ctx.stroke();}
    ctx.font='bold 11px sans-serif';ctx.textAlign='center';ctx.fillStyle='#fff0c9';ctx.fillText('STAIRS',0,-23);ctx.restore();
  }
  const SH = interior?clamp(2.0 * ppm,22,72):clamp(4.6 * ppm, 48, 120);

  if (G.screamAt && now - G.screamAt < 1100) {
    const k = clamp((now - G.screamAt) / 1100, 0, 1);
    ctx.strokeStyle = `rgba(255,190,85,${.7 * (1-k)})`; ctx.lineWidth = 2;
    ctx.beginPath(); groundCircle(ctx,cx,cy,G.screamRadius*ppm*k,cam.iso); ctx.stroke();
    ctx.fillStyle = `rgba(255,220,150,${1-k})`; ctx.font = '900 18px system-ui'; ctx.textAlign = 'center';
    ctx.fillText('AAAAH!', cx, cy - SH - 12 - k * 20);
  }
  // ---- things on the ground
  for (const c of G.corpses) {
    const [x, y] = P(c.lat, c.lng),flip=c.variant%2===1;
    const bl = sprite('item_blood' + c.variant%2);
    ctx.globalAlpha = 0.85;
    if (bl.ok) ctx.drawImage(bl.img, x - SH * 0.55, y - SH * 0.3, SH * 1.1, SH * 0.6);
    else { ctx.fillStyle = '#5a0f0b'; ctx.beginPath(); ctx.ellipse(x, y, SH * 0.45, SH * 0.2, 0, 0, 6.3); ctx.fill(); }
    ctx.globalAlpha = 1;
    drawSprite(c.kind==='survivor'?sprite('surv_p1'):zedSprite(c.kind, c.variant), x, y, SH * (c.kind === 'crawler' ? 0.6 : 1), flip, flip ? -1.5 : 1.5, 0.75, 0, '#3d4a3c', '#5d6b55');
    ctx.fillStyle=c.searched&&!c.items?.length?'#aaa':'#d2c2a6';ctx.font='700 10px system-ui';ctx.textAlign='center';
    if (!G.siege) ctx.fillText(c.kind==='survivor'?(c.own?(c.searched&&!c.items?.length?'PACK · EMPTY':'YOUR GEAR'):'SURVIVOR PACK'):c.searched?(c.items?.length?'BODY · LOOT':'BODY · EMPTY'):'BODY',x,y+16);   // siege bodies can't be searched
  }
  const pulse = 0.5 + 0.5 * Math.sin(now / 320);
  drawWork(ctx,P,ppm,[],true);
  const home=G.body?.home;
  if(home&&(home.floor_level||0)===(G.you.floor||0)&&(!G.inside||G.inside===home.building)){
    const [homeX,hy]=P(home.lat,home.lng),hx=homeX+HOME_MARKER_OFFSET_X;
    ctx.fillStyle='#64c995';ctx.strokeStyle='#0b2017';ctx.lineWidth=2;
    ctx.fillRect(hx-12,hy-24,24,20);ctx.strokeRect(hx-12,hy-24,24,20);
    ctx.fillStyle='#d8ffe8';ctx.font='800 11px system-ui';ctx.textAlign='center';ctx.fillText('HOME',hx,hy+12);
  }
  for (const s of G.stashes) {
      if(s[5]&&(s[5]!==G.inside||s[8]===false))continue;
    const [x, y] = P(s[1], s[2]), sz = s[5]?clamp(1.4 * ppm,18,42):clamp(4.2 * ppm, 34, 84), sp = sprite('item_' + (CONTAINER_ART[s[3]] || s[3]));
    if (Math.hypot(...deltaM(ylat, ylng, s[1], s[2])) > G.sight * 1.2) continue;
    const shelf=G.lootShelves?.find(x=>x.id===s[0]),stock=shelf?.items.length;
    ctx.globalAlpha = s[4]&&!stock ? .35 : 1;
    ctx.strokeStyle = `rgba(224,160,48,${0.35 + 0.4 * pulse})`; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.ellipse(x, y, sz * 0.55 + pulse * 3, sz * 0.24 + pulse * 1.5, 0, 0, 6.3); ctx.stroke();
    if (sp.ok) { const w = sz * sp.img.naturalWidth / sp.img.naturalHeight; ctx.drawImage(sp.img, x - w / 2, y - sz * 0.85, w, sz); }
    else { ctx.fillStyle = '#7a5a22'; ctx.fillRect(x - sz * 0.3, y - sz * 0.5, sz * 0.6, sz * 0.5); }
    ctx.fillStyle = s[4] ? '#aaa' : '#ffe2a8'; ctx.font = '700 11px system-ui'; ctx.textAlign = 'center';
    if(G.selection?.id===s[0]||G.selectedStash===s[0])ctx.fillText(s[4] ? stock?'LOOT · '+shelf.items.length:'EMPTY' : G.channel?.kind === 'search' && G.selectedStash === s[0] ? 'SEARCHING…' : containerName(s).toUpperCase(), x, y + 14);
    ctx.globalAlpha = 1;
  }
  for (const d of G.drops) {
    const [x, y] = P(d[1], d[2]), sz = clamp(2.6 * ppm, 26, 56), sp = sprite('item_' + d[3]);
    ctx.strokeStyle = `rgba(232,230,223,${0.3 + 0.4 * pulse})`; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.ellipse(x, y, sz * 0.5, sz * 0.22, 0, 0, 6.3); ctx.stroke();
    if (sp.ok) { const w = sz * sp.img.naturalWidth / sp.img.naturalHeight; ctx.drawImage(sp.img, x - w / 2, y - sz * 0.8, w, sz); }
    else { ctx.fillStyle = '#c9cdc6'; ctx.fillRect(x - 5, y - 10, 10, 10); }
  }
  if (G.siege) siegeDrawGround(ctx, P, ppm, now, sprite, groundCircle, cam.iso);
  if (G.goal) {
    const [x, y] = P(G.goal[0], G.goal[1]);
    ctx.strokeStyle = 'rgba(232,230,223,0.55)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x - 6, y - 6); ctx.lineTo(x + 6, y + 6); ctx.moveTo(x + 6, y - 6); ctx.lineTo(x - 6, y + 6); ctx.stroke();
  }
  if (near < 14) {
    ctx.strokeStyle = 'rgba(255,255,255,0.09)'; ctx.lineWidth = 1.5; ctx.setLineDash([5, 7]);
    ctx.beginPath(); groundCircle(ctx,cx,cy,(G.tune.swing_reach_m||3.4)*ppm,cam.iso); ctx.stroke(); ctx.setLineDash([]);
  }

  // ---- everyone standing, back to front
  G.gone = G.gone.filter((z) => now - z.goneAt < 450);
  const ents = [];
  for(const vehicle of G.vehicles||[]){const [x,y]=P(vehicle.lat,vehicle.lng);ents.push({vehicle,x,y});}
  for(const ally of G.allies?.values()||[]){const [x,y]=P(...lerpAt(ally.p,now));ents.push({ally,x,y});}
  for(const other of G.others?.values()||[]){const [x,y]=P(...lerpAt(other.p,now));ents.push({other,x,y});}
  for(const o of [...(G.body?.survival.resources||[]),...(G.body?.survival.objects||[])]){const [x,y]=P(o.lat,o.lng);ents.push({prop:o,x,y});}
  if(cam.iso)for(const f of buildingFaces(G.buildings,G.inside,P,ppm,[cx,cy]))ents.push({wall:f,x:f.x,y:f.y});
  for (const z of G.zeds.values()) { const ll = lerpAt(z.p, now), [x, y] = P(ll[0], ll[1]); ents.push({ z, x, y, a: clamp((now - z.born) / 250, 0, 1) }); }
  for (const z of G.gone) { if (z.killed) continue; const ll = lerpAt(z.p, now), [x, y] = P(ll[0], ll[1]); ents.push({ z, x, y, a: 1 - (now - z.goneAt) / 450 }); }
  for (const h of G.herds.values()) {                          // the server walks one thing; this draws its crowd
    const ll = lerpAt(h.p, now), L = 1.9 * Math.sqrt(h.count), W = 0.55 * Math.sqrt(h.count);
    h.facing += (((h.to - h.facing + Math.PI) % 6.2832 + 6.2832) % 6.2832 - Math.PI) * 0.15;
    const c = Math.cos(h.facing), s = Math.sin(h.facing), ph = h.seed * Math.PI / 180, a = clamp((now - h.born) / 600, 0, 1);
    const recheck = !h.hid || h.hid.length !== h.count || now - h.hidAt > 400;
    if (recheck) { h.hid = new Uint8Array(h.count); h.hidAt = now; }
    for (let i = 0; i < h.count; i++) {
      const r = Math.sqrt((i + 0.5) / h.count), t = i * 2.399963229728653 + ph, u = L * r * Math.cos(t), v = W * r * Math.sin(t);
      const at = shiftLL(ll[0], ll[1], u * c - v * s, u * s + v * c);
      if (recheck) h.hid[i] = buildingAt(G.buildings, at) ? 1 : 0;   // where the street narrows, nobody is drawn inside a wall
      if (h.hid[i]) continue;
      const [x, y] = P(at[0], at[1]);
      ents.push({ herd: h, i, x, y, a });
    }
  }
  ents.push({ you: true, x: cx, y: cy });
  ents.sort((a, b) => a.y - b.y);
  const aimed = G.dead ? null : aim(now, true);
  for (const e of ents) {
    if(e.prop){drawWork(ctx,P,ppm,[e.prop],false);continue;}
    if(e.wall){drawBuildingFace(ctx,e.wall);continue;}
    if (e.you) { drawYou(e.x, e.y, SH, now); continue; }
    if(e.vehicle){drawVehicle(ctx,G,e.vehicle);continue;}
    if(e.other){
      const o=e.other,moving=o.state!=='standing'&&o.state!=='searching'&&o.state!=='reading',sway=moving?Math.sin(now/120)*.06:0;
      ctx.fillStyle=o.state==='fighting'?'#d9604a55':'#d9c35b44';ctx.beginPath();ctx.ellipse(e.x,e.y,SH*.35,SH*.12,0,0,6.3);ctx.fill();
      drawSprite(sprite('surv_p'+o.look),e.x,e.y,SH,Math.cos(o.heading)<0,sway,1,0,'#6b6450','#d8cfa8');
      const label=o.name+' · '+o.state;
      ctx.textAlign='center';ctx.font='700 11px system-ui';ctx.strokeStyle='#1c1707';ctx.lineWidth=3;ctx.strokeText(label,e.x,e.y-SH-8);ctx.fillStyle=o.state==='fighting'?'#ffb39e':'#f0e3a8';ctx.fillText(label,e.x,e.y-SH-8);continue;
    }
    if(e.ally){
      const ally=e.ally,sway=ally.speed>.3?Math.sin(now/120)*.06:0;
      ctx.fillStyle='#5bc99a55';ctx.beginPath();ctx.ellipse(e.x,e.y,SH*.35,SH*.12,0,0,6.3);ctx.fill();
      drawSprite(sprite('surv_p1'),e.x,e.y,SH,Math.cos(ally.heading)<0,sway,1,0,'#56766c','#aed7a8');
      ctx.textAlign='center';ctx.font='700 11px system-ui';ctx.strokeStyle='#071c12';ctx.lineWidth=3;ctx.strokeText(ally.name+' · teammate',e.x,e.y-SH-8);ctx.fillStyle='#a8f0cf';ctx.fillText(ally.name+' · teammate',e.x,e.y-SH-8);continue;
    }
    if (e.herd) {
      const t = now / 1000 + e.i * 1.7, hh = SH * (0.94 + (e.i % 5) * 0.03);
      ctx.fillStyle = 'rgba(0,0,0,0.42)'; ctx.beginPath(); ctx.ellipse(e.x, e.y, hh * 0.27, hh * 0.085, 0, 0, 6.3); ctx.fill();
      drawSprite(zedSprite('shambler', (e.herd.seed + e.i) % 16), e.x, e.y - Math.abs(Math.sin(t * 2.4)) * 1.5, hh, Math.cos(e.herd.facing) < 0, Math.sin(t * 2.4) * 0.05, e.a, 0, '#4b5a48', '#77866c');
      continue;
    }
    const z = e.z, x = e.x, y = e.y, t = now / 1000 + z.ph, left = x < cx, side = left ? -1 : 1;
    let h = SH * (z.kind === 'crawler' ? 0.62 : 1), rot = 0, ox = 0, oy = 0, sc = 1;
    const isBoss = G.siege && z.id === siegeBossId();
    if (isBoss) h *= 1.7;
    const atk = z.atkAt ? z.atkAt - now : 1e9;
    if (z.state === 'idle' || z.state === 'investigate') rot = Math.sin(t * 1.3) * 0.04;
    else if (z.state === 'alert') ox = Math.sin(now / 26) * 2.2;
    else if (z.state === 'chase') { rot = Math.sin(t * 5.5) * 0.07 - side * 0.06; oy = -Math.abs(Math.sin(t * 5.5)) * 2.5; }
    else if (z.state === 'engaged') {
      rot = Math.sin(t * 9) * 0.05 - side * 0.08;
      const windup = atk >= 0 && atk < 850 ? 1 - atk / 850 : 0;
      const strike = z.attackAt && now - z.attackAt < 340 ? Math.sin((now - z.attackAt) / 340 * Math.PI) : 0;
      if (windup) { sc = 1 + 0.12 * windup; ox = -side * 4 * windup; rot -= side * 0.12 * windup; }
      if (strike) { sc = 1 + 0.18 * strike; ox = side * 12 * strike; rot += side * 0.25 * strike; }
    }
    else if (z.state === 'stagger') rot = side * 0.38;
    else if (z.state === 'down') rot = side * 1.48;
    else if (z.state === 'rising') rot = side * 0.8;
    // shadow and the ring that says "this one is yours"
    ctx.fillStyle = 'rgba(0,0,0,0.42)'; ctx.beginPath(); ctx.ellipse(x, y, h * 0.27, h * 0.085, 0, 0, 6.3); ctx.fill();
    if (z.mine && z.state !== 'down') {
      ctx.strokeStyle = z.state === 'engaged' ? 'rgba(220,60,48,0.85)' : 'rgba(220,60,48,0.4)'; ctx.lineWidth = z.state === 'engaged' ? 2.5 : 1.5;
      ctx.beginPath(); ctx.ellipse(x, y, h * 0.31, h * 0.11, 0, 0, 6.3); ctx.stroke();
      if (z.state === 'engaged' && atk < 1500) {       // the bite is coming: this arc closes as it winds up
        ctx.strokeStyle = atk < 420 ? '#fff' : '#ff9a8c'; ctx.lineWidth = 4;
        ctx.beginPath(); ctx.ellipse(x, y, h * 0.36, h * 0.14, 0, -1.57, -1.57 + 6.283 * clamp(1 - atk / 1500, 0, 1)); ctx.stroke();
      }
    }
    if (aimed && aimed.z === z) {                    // what SWING reaches right now
      ctx.strokeStyle = aimed.down ? 'rgba(255,120,100,0.95)' : 'rgba(245,245,235,0.9)'; ctx.lineWidth = 2; ctx.setLineDash([6, 5]);
      ctx.beginPath(); ctx.ellipse(x, y, h * 0.42, h * 0.16, 0, 0, 6.3); ctx.stroke(); ctx.setLineDash([]);
    }
    if (z.state === 'down') { ctx.strokeStyle = `rgba(224,160,48,${0.4 + 0.5 * pulse})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.ellipse(x + side * h * 0.4, y, h * 0.5, h * 0.16, 0, 0, 6.3); ctx.stroke(); }
    const fl = clamp(1 - (now - z.flash) / 140, 0, 1);
    const strikeAge = now - (z.attackAt || -1000);
    const attackArt = z.kind === 'shambler' && z.variant % 16 === 8 && strikeAge >= 0 && strikeAge < 340
      ? sprite('zed_attack' + Math.min(3, Math.floor(strikeAge / 85))) : null;
    drawSprite(attackArt?.ok ? attackArt : zedSprite(z.kind, z.variant), x + ox, y + oy, h * sc, !left, rot, e.a, fl, isBoss ? '#5a3b38' : '#4b5a48', isBoss ? '#8a5a52' : '#77866c');
    if (isBoss) siegeDrawBoss(ctx, z, x + ox, y + oy, h * sc);
    // Wounds remain visible as health falls, even when the zombie is no longer targeted.
    if (z.hp < 0.78 && z.state !== 'down') {
      const damage = clamp((0.78 - z.hp) / 0.78, 0, 1);
      ctx.save(); ctx.translate(x + ox, y + oy - h * 0.48); ctx.rotate(rot);
      ctx.globalAlpha = e.a * (0.35 + damage * 0.55); ctx.strokeStyle = '#762b26';
      ctx.lineWidth = Math.max(2, h * 0.045); ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(-h * 0.13, h * 0.08); ctx.lineTo(-h * 0.02, h * 0.21);
      if (damage > 0.35) { ctx.moveTo(h * 0.08, -h * 0.03); ctx.lineTo(h * 0.17, h * 0.1); }
      if (damage > 0.7) { ctx.moveTo(-h * 0.22, h * 0.25); ctx.lineTo(-h * 0.1, h * 0.36); }
      ctx.stroke(); ctx.restore();
    }
    const top = y - h * sc - 6;
    if ((z.state === 'alert' || now - z.spot < 1300) && z.state !== 'down') {
      const k = clamp((now - z.spot) / 160, 0, 1), fs = Math.round(22 + 10 * (1 - k));
      ctx.font = `900 ${fs}px system-ui, sans-serif`; ctx.textAlign = 'center';
      ctx.lineWidth = 4; ctx.strokeStyle = '#000'; ctx.strokeText('!', x, top); ctx.fillStyle = '#ff4a3a'; ctx.fillText('!', x, top);
    } else if (z.hp < 0.999 && z.mine) {
      ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(x - 15, top - 3, 30, 4);
      ctx.fillStyle = '#c8372d'; ctx.fillRect(x - 15, top - 3, 30 * z.hp, 4);
    }
  }

  drawSelection(ctx,P);
  // ---- effects
  G.fx = G.fx.filter((f) => now - f.t0 < 260);
  for (const f of G.fx) {
    const k = (now - f.t0) / (f.kind === 'shove' ? 220 : 160);
    if (k > 1) continue;
    if (f.kind === 'swing') {
      const r = Math.max(36, (G.tune.swing_reach_m || 3.4) * ppm * 0.82);
      ctx.strokeStyle = `rgba(255,255,240,${0.85 * (1 - k)})`; ctx.lineWidth = 3 + 9 * (1 - k); ctx.lineCap = 'round';
      ctx.beginPath(); ctx.arc(cx, cy - SH * 0.45, r, f.ang - 1.0, f.ang - 1.0 + 2.0 * Math.min(1, k * 1.6)); ctx.stroke();
    } else if (f.kind === 'shove') {
      const r = 22 + k * Math.max(30, 2.4 * ppm);
      ctx.strokeStyle = `rgba(232,230,223,${0.7 * (1 - k)})`; ctx.lineWidth = 6 * (1 - k) + 1;
      ctx.beginPath(); ctx.arc(cx, cy - SH * 0.4, r, f.ang - 1.2, f.ang + 1.2); ctx.stroke();
    } else if (f.kind === 'shoot') {
      const len = Math.max(60, (f.reach || 20) * ppm);
      ctx.strokeStyle = `rgba(255,230,150,${1 - k})`; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(cx, cy - SH * 0.5); ctx.lineTo(cx + Math.cos(f.ang) * len, cy - SH * 0.5 + Math.sin(f.ang) * len); ctx.stroke();
    } else if (f.kind === 'spark') {
      const [x, y] = P(f.lat, f.lng);
      ctx.strokeStyle = `rgba(255,120,100,${1 - k})`; ctx.lineWidth = 2.5;
      for (let i = 0; i < 7; i++) { const a = i * 0.9 + f.t0; ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * 6 * k * 3, y - SH * 0.5 + Math.sin(a) * 6 * k * 3); ctx.lineTo(x + Math.cos(a) * (10 + 26 * k), y - SH * 0.5 + Math.sin(a) * (10 + 26 * k)); ctx.stroke(); }
    }
  }
  G.floaters = G.floaters.filter((f) => now - f.t0 < 850);
  ctx.textAlign = 'center';
  for (const f of G.floaters) {
    const k = (now - f.t0) / 850, [x, y] = P(f.lat, f.lng);
    ctx.globalAlpha = 1 - k * k; ctx.font = '900 17px system-ui, sans-serif';
    ctx.lineWidth = 3.5; ctx.strokeStyle = '#000'; ctx.strokeText(f.text, x, y - SH - 10 - 30 * k); ctx.fillStyle = f.color; ctx.fillText(f.text, x, y - SH - 10 - 30 * k);
  }
  ctx.globalAlpha = 1;

  // ---- what you cannot see
  const rs=G.sight*ppm,fr=rs*1.03,fx=fr*(cam.iso?Math.sqrt(1.5):1),fy=fr*(cam.iso?Math.SQRT1_2:1);
  if(fx<W+H||fy<W+H){
    ctx.drawImage(fogDisc,cx-fx,cy-fy,fx*2,fy*2);ctx.fillStyle='rgba(4,6,5,0.97)';
    if(cy-fy>0)ctx.fillRect(0,0,W,cy-fy+1);
    if(cy+fy<H)ctx.fillRect(0,cy+fy-1,W,H-cy-fy+1);
    if(cx-fx>0)ctx.fillRect(0,cy-fy,cx-fx+1,fy*2);
    if(cx+fx<W)ctx.fillRect(cx+fx-1,cy-fy,W-cx-fx+1,fy*2);
  }
  const night = clamp((50 - G.sight) / 28, 0, 1);
  if (night > 0) { ctx.fillStyle = `rgba(6,10,34,${0.3 * night})`; ctx.fillRect(0, 0, W, H); }
  // ---- rain, when the area has it and there is no roof overhead
  if (G.body && G.body.weather && G.body.weather.rain && !G.inside) {
    ctx.strokeStyle = 'rgba(170,196,214,0.22)'; ctx.lineWidth = 1.2; ctx.beginPath();
    for (let i = 0; i < 70; i++) {
      const fall = (now * (0.55 + (i % 5) * 0.06) + i * 131) % (H + 60), x = ((i * 97) % (W + 80)) - 40 + fall * 0.18;
      ctx.moveTo(x, fall - 60); ctx.lineTo(x + 5, fall - 38);
    }
    ctx.stroke();
  }

  // ---- what you can only hear
  G.blips = G.blips.filter((b) => now - b.t0 < 2600);
  const rb = Math.min(rs * 0.93, Math.min(W, H * 0.78) / 2 - 22);
  for (const b of G.blips) {
    const k=(now-b.t0)/2600,bearing=b.b*Math.PI/180,direction=projectM(Math.sin(bearing),Math.cos(bearing),cam.iso),ang=Math.atan2(direction[1],direction[0]);
    const bx = cx + Math.cos(ang) * rb, by = cy + Math.sin(ang) * rb;
    ctx.strokeStyle = b.kind === 'noise' ? `rgba(224,160,48,${1 - k})` : `rgba(255,120,104,${1 - k})`;
    ctx.lineWidth = b.loud ? 3.5 : 2.5; ctx.lineCap = 'round';
    for (let i = 0; i < 3; i++) {
      const r = 7 + i * 8 + ((now - b.t0) / 90 % 8);
      ctx.beginPath(); ctx.arc(bx, by, r, ang - 0.6, ang + 0.6); ctx.stroke();
    }
  }
  // ---- a herd too far off to make out the figures: which way, and how far
  for (const h of G.herds.values()) {
    const ll = lerpAt(h.p, now), [dx, dy] = deltaM(ylat, ylng, ll[0], ll[1]), d = Math.hypot(dx, dy);
    if (d < G.sight * 0.9) continue;
    const projected=projectM(dx,dy,cam.iso),ang=Math.atan2(projected[1],projected[0]), bx = cx + Math.cos(ang) * rb, by = cy + Math.sin(ang) * rb, beat = 0.75 + 0.25 * Math.sin(now / 260);
    ctx.save(); ctx.translate(bx, by); ctx.rotate(ang);
    ctx.fillStyle = `rgba(224,160,48,${beat})`; ctx.strokeStyle = 'rgba(0,0,0,0.8)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(16, 0); ctx.lineTo(-6, -11); ctx.lineTo(-1, 0); ctx.lineTo(-6, 11); ctx.closePath(); ctx.stroke(); ctx.fill();
    ctx.restore();
    const label = `HERD · ${Math.round(d)} m`, lx = clamp(bx - Math.cos(ang) * 30, 62, W - 62), ly = clamp(by - Math.sin(ang) * 30 + 4, 20, H - 20);
    ctx.font = '700 12px system-ui'; ctx.textAlign = 'center';
    ctx.lineWidth = 3.5; ctx.strokeStyle = 'rgba(0,0,0,0.85)'; ctx.strokeText(label, lx, ly); ctx.fillStyle = '#f0c267'; ctx.fillText(label, lx, ly);
  }
  if (G.you.transit) { ctx.fillStyle = 'rgba(232,230,223,0.8)'; ctx.font = '600 14px system-ui'; ctx.textAlign = 'center'; ctx.fillText('Settling into this area…', W / 2, cy + SH); }

  // ---- buttons that are still recovering, and timed actions
  const left = clamp((G.busyUntil - now) / G.busySpan, 0, 1);
  for (const id of ['bSwing', 'bShove', 'bShoot']) $(id).lastElementChild.style.transform = `scaleY(${left})`;
  $('bBack').lastElementChild.style.transform = `scaleY(${clamp((G.backReadyAt - now) / 6000, 0, 1)})`;
  const ch = $('channel');
  if (G.channel && G.channel.kind !== 'back') {
    ch.hidden = false;
    $('channelBar').style.width = clamp(1 - (G.channel.end - now) / G.channel.total, 0, 1) * 100 + '%';
    $('channelLabel').textContent = CHANNEL_WORD[G.channel.kind] || '';
  } else ch.hidden = true;

  if (G.dev && (G.frameN = (G.frameN || 0) + 1) % 20 === 0) {
    const L = G.lat;
    $('dev').textContent = `fps ${G.fps.toFixed(0)}  ping ${pct(L.ping, 0.5).toFixed(0)} ms\n`
      + `tap>frame ${pct(L.frame, 0.5).toFixed(0)} / ${pct(L.frame, 0.95).toFixed(0)} ms\n`
      + `tap>server ${pct(L.server, 0.5).toFixed(0)} / ${pct(L.server, 0.95).toFixed(0)} ms\n`
      + `zeds ${G.zeds.size}  snap ${G.snapGap.toFixed(0)} ms  tiles ${tileStats.loaded}  x${DPR}`;
  }
}

// ---- C9: the one survivor sprite shows its state. Stains, wounds and bandages are painted on
// a copy of the frame and kept until the state changes; the bag, helmet and held weapon are small
// sprites placed at fixed points of the standing pose. Points are fractions of the frame, measured
// on surv_p1; the character's right hand is on the left of the picture.
const PART_AT=characterParts(1);
const STAINS = [[0.47, 0.55, 0.050], [0.60, 0.62, 0.038], [0.36, 0.70, 0.045], [0.55, 0.44, 0.035], [0.50, 0.26, 0.030], [0.68, 0.74, 0.042], [0.40, 0.60, 0.050]];
// longest side, turn, and where the middle of the picture sits from the grip (in picture widths and heights):
// each item was modelled lying its own way, so each is turned until its business end points up from the fist
const HELD = { bat: [0.46, 2.0, -0.40, 0.42], crowbar: [0.42, 0.68, -0.42, -0.35], axe: [0.36, 0.70, -0.43, -0.12], knife: [0.22, 1.99, -0.32, 0.32], pistol: [0.20, 0, -0.35, -0.18] };
const lookCache = new Map(), boxCache = new Map();
function frameBox(name, img) {                   // where the figure is inside its frame (action frames are padded)
  let b = boxCache.get(name);
  if (b) return b;
  const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  const g = c.getContext('2d', { willReadFrequently: true }); g.drawImage(img, 0, 0);
  let x0 = c.width, x1 = 0, y0 = c.height, y1 = 0;
  try {
    const d = g.getImageData(0, 0, c.width, c.height).data;
    for (let y = 0; y < c.height; y += 3) for (let x = 0; x < c.width; x += 3) if (d[(y * c.width + x) * 4 + 3] > 40) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  } catch (_) { x0 = 0; x1 = c.width; y0 = 0; y1 = c.height; }
  if (x1 <= x0) { x0 = 0; x1 = c.width; y0 = 0; y1 = c.height; }
  b = [x0, y0, x1 - x0, y1 - y0]; boxCache.set(name, b);
  return b;
}
function survivorState() {
  const y = G.you, b = G.body, hp = y ? y.hp : 100;
  return { hurt: hp < 25 ? 3 : hp < 50 ? 2 : hp < 75 ? 1 : 0,
    wounds: b ? b.wounds.filter((w) => PART_AT[w.part]).map((w) => [w.part, w.bandaged ? (w.clean ? 'c' : 'd') : w.bleeding ? 'b' : 'o']) : [] };
}
function dressed(name, sp, standing) {           // the frame with blood, wounds and bandages on it, or the frame itself
  if (!sp.ok) return sp;
  const st = survivorState(), wounds = standing ? st.wounds : [];
  if (!st.hurt && !wounds.length) return sp;
  const key = name + '|' + st.hurt + '|' + wounds.map((w) => w.join(':')).sort().join(',');
  let out = lookCache.get(key);
  if (out) return out;
  const img = sp.img, c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  g.globalCompositeOperation = 'source-atop';                  // paint only where the figure is
  const [bx, by, bw, bh] = frameBox(name, img);
  for (const [u, v, r] of STAINS.slice(0, [0, 2, 4, 7][st.hurt])) {
    g.fillStyle = 'rgba(112,18,14,0.6)';
    for (const [du, dv, k] of [[0, 0, 1], [0.7, 0.35, 0.62], [-0.55, 0.6, 0.5], [0.2, -0.8, 0.42]]) { g.beginPath(); g.arc(bx + (u + du * r) * bw, by + (v + dv * r) * bh, r * k * bh, 0, 6.3); g.fill(); }
  }
  for (const [part, how] of wounds) {
    const [u, v, len, tilt] = characterParts(Number(name.match(/^surv_p(\d)/)?.[1]||1))[part], px = u * c.width, py = v * c.height, L = len * c.width;
    g.save(); g.translate(px, py); g.rotate(tilt);
    if (how === 'c' || how === 'd') {                          // a bandage: a pale band with two wraps showing
      g.fillStyle = how === 'c' ? '#ece6d6' : '#b3a688'; g.strokeStyle = how === 'c' ? '#a59d88' : '#7d735c'; g.lineWidth = 2;
      g.beginPath(); g.rect(-L / 2, -c.height * 0.026, L, c.height * 0.052); g.fill(); g.stroke();
      g.beginPath(); g.moveTo(-L / 2, -c.height * 0.006); g.lineTo(L / 2, c.height * 0.012); g.stroke();
      if (how === 'd') { g.fillStyle = 'rgba(112,18,14,0.55)'; g.beginPath(); g.arc(0, 0, c.height * 0.016, 0, 6.3); g.fill(); }
    } else {                                                   // an open wound: dark, brighter while it bleeds
      g.fillStyle = how === 'b' ? '#a3170f' : '#6b1f1a';
      g.beginPath(); g.ellipse(0, 0, c.height * 0.030, c.height * 0.017, 0, 0, 6.3); g.fill();
      if (how === 'b') { g.beginPath(); g.ellipse(c.height * 0.006, c.height * 0.036, c.height * 0.008, c.height * 0.022, 0, 0, 6.3); g.fill(); }
    }
    g.restore();
  }
  c.naturalWidth = c.width; c.naturalHeight = c.height;
  out = { img: c, ok: true };
  if (lookCache.size > 40) lookCache.clear();
  lookCache.set(key, out);
  return out;
}
function wornCode(slot) { const id = G.body?.worn?.[slot]; return id ? G.body.items.find((i) => i.id === id)?.code : null; }
function gear(name, x, y, h, flip, rot, u, v, size, tilt, ox = 0, oy = 0) {    // a small sprite pinned to a point of the standing frame
  const g = sprite(name), base = sprite('surv_p'+Math.max(0,Math.min(7,Number(LS.get('character','1'))||0)));
  if (!g.ok || !base.ok) return;
  const w = h * base.img.naturalWidth / base.img.naturalHeight, k = size * h / Math.max(g.img.naturalWidth, g.img.naturalHeight), gw = g.img.naturalWidth * k, gh = g.img.naturalHeight * k;
  ctx.save(); ctx.translate(x, y); if (rot) ctx.rotate(rot); if (flip) ctx.scale(-1, 1);
  ctx.translate((u - 0.5) * w, (v - 1) * h); if (tilt) ctx.rotate(tilt);
  ctx.drawImage(g.img, -gw / 2 + ox * gw, -gh / 2 + oy * gh, gw, gh);
  ctx.restore();
}

function drawYou(x, y, SH, now) {
  const since = now - G.swingAt, phase = clamp(since / 420, 0, 1);
  const active = since >= 0 && since < 420 && ['swing', 'shove'].includes(G.actionKind);
  const arc = active ? Math.sin(phase * Math.PI) : 0;
  const reach = G.actionKind === 'shove' ? 13 : 8;
  const ox = Math.cos(G.aimAng) * reach * arc, oy = Math.sin(G.aimAng) * reach * arc;
  const pose = active ? (G.actionKind === 'shove' ? -0.28 * arc : 0.62 * arc) : 0;
  if (active) G.faceLeft = Math.cos(G.aimAng) < 0;
  const bob = G.moving || (G.you.speed > 0.3) ? -Math.abs(Math.sin(now / 130)) * 2.5 : 0;
  ctx.fillStyle = 'rgba(0,0,0,0.45)'; ctx.beginPath(); ctx.ellipse(x, y, SH * 0.27, SH * 0.085, 0, 0, 6.3); ctx.fill();
  const n = Math.max(0,Math.min(7,Number(LS.get('character','1'))||0));
  const actionArt = active ? sprite((G.actionKind === 'swing' ? 'surv_swing' : 'surv_push') + Math.min(3, Math.floor(phase * 4))) : null;
  const authored = n===1 && G.you.hands?.code==='bat' && actionArt?.ok;
  const frameName = authored ? (G.actionKind === 'swing' ? 'surv_swing' : 'surv_push') + Math.min(3, Math.floor(phase * 4)) : 'surv_p' + n;
  const pins=characterPose(n);
  const bx = x + ox, by = y + oy + bob, flip = !!G.faceLeft, bag = authored ? null : wornCode('back');
  if (bag) gear(sprite('item_' + bag).ok ? 'item_' + bag : 'item_bag', bx, by, SH, flip, pose, ...pins.bag, bag === 'rucksack' ? 0.46 : 0.34, -0.12);
  drawSprite(dressed(frameName, authored ? actionArt : sprite('surv_p' + n), !authored), bx, by,
    SH * (authored && G.actionKind === 'swing' ? 1.15 : 1), flip, authored ? 0 : pose, 1,
    clamp(1 - (now - G.hurtAt) / 180, 0, 1), '#3a5f8a', '#d9b99a');
  if (authored) return;                                         // the action frames carry their own bat; gear returns with the standing pose
  if (wornCode('head') === 'helmet') gear('item_helmet', bx, by, SH, flip, pose, ...pins.helmet, 0.28, -0.08);
  const held = G.you.hands && HELD[G.you.hands.code];
  if (held) gear('item_' + G.you.hands.code, bx, by, SH, flip, pose, ...pins.hand, held[0], held[1]+(active?(G.actionKind==='shove'?-.2:.8)*arc:0), held[2], held[3]);
}

// ------------------------------------------------------------------ input
function bindBtn(id, a) {
  const el = $(id);
  el.addEventListener('pointerdown', (ev) => { ev.preventDefault(); press(a, ev); });
  el.addEventListener('contextmenu', (ev) => ev.preventDefault());
}
bindBtn('bScream', 'scream'); bindBtn('bSwing', 'swing'); bindBtn('bShove', 'shove'); bindBtn('bShoot', 'shoot'); bindBtn('bBack', 'back');

const KEY_ACT = { KeyR: 'scream', KeyJ: 'swing', Space: 'swing', KeyK: 'shove', KeyL: 'back', KeyF: 'shoot' };
const WALK = new Set(['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'KeyW', 'KeyA', 'KeyS', 'KeyD']);
window.addEventListener('keydown', (ev) => {
  if (ev.target.closest?.('input,select,textarea') || !G.you) return;
  if (WALK.has(ev.code)) { collapseWorldUI('movement');closeArea();G.keys.add(ev.code); ev.preventDefault(); return; }
  if (ev.repeat) { if (KEY_ACT[ev.code]) ev.preventDefault(); return; }
  if (KEY_ACT[ev.code]) { ev.preventDefault(); press(KEY_ACT[ev.code], ev); }
  else if (ev.code === 'KeyB') { const c = (G.ctx || []).find((x) => x.a === 'bandage'); if (c) press('bandage', ev); }
  else if (ev.code === 'KeyE') { const c = (G.ctx || []).find((x) => x.a === 'search' || x.a === 'pickup'); if (c) press(c.a, ev, c.args); }
  else if (ev.code === 'KeyI' || ev.code === 'Tab') { ev.preventDefault(); togglePanel(); }
});
window.addEventListener('keyup', (ev) => G.keys.delete(ev.code));
window.addEventListener('blur', () => { G.keys.clear(); stickEnd(false); });
document.addEventListener('visibilitychange', () => { if (document.hidden) stickEnd(false); });

installIndoorZoom(cv,{
 enabled:()=>!!(G.inside&&G.you&&G.located&&!G.dead&&!area.on&&!G.placement),
 get:()=>G.indoorZoom,set:v=>{G.indoorZoom=v;LS.set('indoorZoom',String(v));$('bZoomReset').textContent='Zoom '+Math.round(v*100)+'% · reset';},
 start:ev=>{if(!G.desk||!stickZone(ev.clientX,ev.clientY))return false;initAudio();G.stickTouch={id:ev.pointerId,x0:ev.clientX,y0:ev.clientY,on:false};return true;},
 move:stickMove,end:stickEnd,tap:tapWorld,stop:()=>$('bStop').click()
});
$('bFloor').onclick=()=>{if(G.inside)selectWorld({kind:'stairs',id:G.inside});};
$('bZoomReset').onclick=()=>{G.indoorZoom=1;LS.set('indoorZoom','1');};
cv.addEventListener('pointerdown', (ev) => {
  initAudio();
  if (area.on) { try { cv.setPointerCapture(ev.pointerId); } catch (_) {} areaPointer('down', ev); return; }
  const playing = G.you && G.located && !G.dead && G.desk && !G.pickStart && !G.placement;
  if (playing && !G.stickTouch && stickZone(ev.clientX, ev.clientY)) {
    G.stickTouch = { id: ev.pointerId, x0: ev.clientX, y0: ev.clientY, on: false };
    try { cv.setPointerCapture(ev.pointerId); } catch (_) {}
    return;
  }
  tapWorld(ev.clientX, ev.clientY);
});
for (const [type, kind] of [['pointermove', 'move'], ['pointerup', 'up'], ['pointercancel', 'cancel']]) cv.addEventListener(type, (ev) => { if (area.on) areaPointer(kind, ev); });
cv.addEventListener('pointermove', (ev) => { if (G.stickTouch && ev.pointerId === G.stickTouch.id) stickMove(ev.clientX, ev.clientY); });
cv.addEventListener('pointerup', (ev) => { if (G.stickTouch && ev.pointerId === G.stickTouch.id) stickEnd(true); });
cv.addEventListener('pointercancel', (ev) => { if (G.stickTouch && ev.pointerId === G.stickTouch.id) stickEnd(false); });
cv.addEventListener('lostpointercapture', (ev) => { if (G.stickTouch && ev.pointerId === G.stickTouch.id) stickEnd(false); });

function tapWorld(clientX, clientY) {
  const ev = { clientX, clientY };
  if(G.pickStart){
    G.previewLL=shiftLL(...G.previewLL,ev.clientX-W/2,-(ev.clientY-H*.46));return;
  }
  if (!G.you || !G.located || G.dead) return;

  if (!G.desk) return;
  if(G.placement&&tapWork(ev.clientX,ev.clientY))return;
  const openingTarget=hitOpening(ev.clientX,ev.clientY);
  const home=G.body?.home;
  let homeTarget=null;
  if(home&&(home.floor_level||0)===(G.you.floor||0)){const [x,y]=worldPoint(G,home.lat,home.lng);
    const hit=Math.hypot(ev.clientX-(x+HOME_MARKER_OFFSET_X),ev.clientY-(y-14));
    if(hit<24)homeTarget={kind:'home',id:'home',hit};
  }
  const workTarget=hitWork(ev.clientX,ev.clientY);
  const bodyTarget=(G.corpses||[]).map(c=>{const [x,y]=worldPoint(G,c.lat,c.lng);
    const sp=c.kind==='survivor'?sprite('surv_p1'):zedSprite(c.kind,c.variant),interior=!!G.inside;
    const h=(interior?clamp(2*G.cam.ppm,22,72):clamp(4.6*G.cam.ppm,48,120))*(c.kind==='crawler'?.6:1);
    return {kind:'corpse',id:c.id,hit:corpseHit(ev.clientX,ev.clientY,x,y,h,sp.ok?sp.img.naturalWidth/sp.img.naturalHeight:.6,c.variant)};
  }).filter(c=>c.hit!==null).sort((a,b)=>a.hit-b.hit)[0];
  const tapped = (G.stashes || []).filter(s=>!s[5]||s[5]===G.inside&&s[8]!==false).map(s => {
    const [px,py]=worldPoint(G,s[1],s[2]);return {s,px,py};
  }).map(o=>({...o,hit:Math.hypot(ev.clientX-o.px,ev.clientY-(o.py-18))})).filter(o=>o.hit<30).sort((a,b)=>a.hit-b.hit)[0];
  const stairsTarget=G.buildings.filter(b=>b.id===G.inside&&b.stairs).map(b=>{const [x,y]=worldPoint(G,...b.stairs);return {kind:'stairs',id:b.id,hit:Math.hypot(ev.clientX-x,ev.clientY-(y-8))};}).find(b=>b.hit<22);
  const selected=nearestTarget([vehicleHit(G,ev.clientX,ev.clientY),stairsTarget,homeTarget,bodyTarget,tapped&&{kind:'stash',id:tapped.s[0],hit:tapped.hit},
    workTarget&&{kind:'object',id:workTarget.id,hit:workTarget.hit},openingTarget&&{kind:'opening',id:openingTarget.o.id,hit:openingTarget.d}]);
  if(selected){selectWorld({kind:selected.kind,id:selected.id});return;}
  G.exitIntent=false;G.autoOpening=null;
  G.selectedStash = null;
  const target=screenWorld(G,ev.clientX,ev.clientY),building=buildingAt(G.buildings,target);
  if(G.you.vehicle){G.vehicleGoal=target;collapseWorldUI('movement');return;}
  if(building&&G.inside!==building.id&&!building.openings.some(o=>o.label==='Entrance'&&(o.open||o.broken)))walkTo(entranceApproach(building,G.desk));
  else walkTo(target);
}
document.addEventListener('contextmenu', (ev) => { if (ev.target !== $('name')) ev.preventDefault(); });

function togglePanel() { const p = $('panel'); p.hidden = !p.hidden; p.classList.remove('expanded');$('panelExpand').textContent='Expand';$('sceneDrawer').hidden=true;G.drawer=null;if (!p.hidden) renderPanel();renderWorldUI(); }
setupWork({G,fire,walk:walkTo,select:selectWorld,close:()=>{$("panel").hidden=true;},open:()=>{$("panel").hidden=false;renderPanel();},stop:()=>{$("bStop").click();}});
setupArea({G,fire,toast,stop:()=>$('bStop').click(),collapse:()=>collapseWorldUI('movement'),containerName:(kind)=>CONTAINER_NAME[kind]||kind});
setupVehicles({G,fire,send,drawer:openSceneDrawer});
setupInventory({G,fire,walk:walkTo,select:selectWorld,leave:leaveBuilding,toast,close:()=>{$('panel').hidden=true;},stop:()=>{$('bStop').click();}});
setupWorldUI({G,fire,walk:walkTo,press,stop:()=>$('bStop').click(),toast,containerName,approachContainer,place:beginPlacement,
 openPack:()=>{$('sceneDrawer').hidden=true;G.drawer=null;$('panel').hidden=false;$('panel').classList.remove('expanded');$('panelExpand').textContent='Expand';renderPanel();renderWorldUI();},renderPack:renderPanel});
$('bPack').addEventListener('click', togglePanel);
$('bMenu').addEventListener('click', togglePanel);
$('panelClose').addEventListener('click', togglePanel);
$('panel').addEventListener('click', (ev) => { if (ev.target === $('panel')) togglePanel(); });
$('bMute').addEventListener('click', () => { setMuted(!isMuted()); LS.set('mute', isMuted() ? '1' : '0'); renderPanel(); });
$('bWorldView').onclick=()=>{G.cam.iso=!G.cam.iso;LS.set('worldView',G.cam.iso?'iso':'map');$('bWorldView').textContent=G.cam.iso?'View: 3D':'View: flat map';};
$('bDev').addEventListener('click', () => { G.dev = !G.dev; LS.set('dev', G.dev ? '1' : '0'); $('dev').hidden = !G.dev; renderPanel(); });
$('bBody').addEventListener('click',()=>{if(G.bodyLead)selectWorld({kind:'corpse',id:G.bodyLead.c.id});});
$('bLoot').addEventListener('click', () => {if(G.lootLead)selectWorld({kind:'stash',id:G.lootLead[0]});});
$('bSprint').addEventListener('pointerdown', (ev) => { ev.preventDefault(); if (!$('bSprint').disabled) { G.quietHeld = false; press('sprint', ev, { op: G.you?.sprinting ? 'stop' : 'start' }); } });
$('bQuiet').addEventListener('click', () => {
  if (!G.you || G.dead) return;
  G.quietHeld = !G.you.quiet; G.quietSent = 0;
  if (G.quietHeld && G.you.sprinting) fire('sprint', { op: 'stop' });
  wantQuiet(G.quietHeld);
  hint('quiet', 'Creeping is slow, but you are heard at 3 m instead of 20 and are harder to spot.', 1);
});
$('bStop').addEventListener('click', () => { if(G.you?.vehicle){G.vehicleGoal=null;$('vehicleBrake').click();} stickEnd(false); if(G.you?.sprinting)fire('sprint',{op:'stop'});G.exitIntent=false;G.autoOpening=null;G.route=[];G.routePending=false;G.nav++;G.goal = null; G.keys.clear(); G.moving = false; $('bStop').disabled = true; });
$('bAgain').addEventListener('click', () => { send({ t: 'new' }); });
$('bFullRetry').addEventListener('click', retryFull);
$('locationRetry').onclick=()=>{G.pickStart=false;$('locationStart').hidden=true;requestLocation();};
$('locationManual').onclick=()=>{
  if(G.locationBusy||!CFG.real_gps)return;
  G.pickStart=true;G.previewLL=G.lastGPSFix?.slice(0,2)||G.desk||FALLBACK_START.slice();
  $('locationStart').hidden=false;locationMessage('Manual map start: tap to choose a place, then Start here. This is not your GPS fix.');
};
$('locationStart').onclick=()=>placeLocation([...G.previewLL,1,Date.now()],'launch','manual');
$('bInvite').addEventListener('click', async () => {
  const text = `Oh shit, Zombies. Zombie survival on real street maps: ${location.origin}`;
  try { if (navigator.share) await navigator.share({ text }); else { await navigator.clipboard.writeText(text); toast('Link copied.'); } } catch (_) {}
});
$('bShare').addEventListener('click', async () => {
  const c = G.card || {};
  const text = `${G.name} lasted ${fmtDur(c.lived_s || 0)} and put down ${c.kills || 0}. Oh shit, Zombies. ${location.origin}`;
  try { if (navigator.share) await navigator.share({ text }); else { await navigator.clipboard.writeText(text); toast('Copied.'); } } catch (_) {}
});

$('bForget').addEventListener('click', async () => {
  if (!confirm('Delete your survivor, home and everything this server holds about you? This cannot be undone.')) return;
  try {
    const r = await fetch('/api/me', { method: 'DELETE', headers: { authorization: 'Bearer ' + G.token } });
    if (!r.ok) throw new Error(r.status);
    G.full = 'Your data is deleted.';
    for (const k of Object.keys(localStorage)) if (k.startsWith('osz.')) localStorage.removeItem(k);
    location.reload();
  } catch (_) { toast('Could not delete right now. Try again.', 'bad'); }
});

setInterval(() => {
  send({ t: 'ping', c: T() });
  if (G.lastPos && T() - G.lastPosSent > 1900) sendPos(true);          // keep-alive for a still survivor
}, 2000);
document.addEventListener('visibilitychange', () => { if (!document.hidden && G.mode && !G.ws) { G.retry = 0; } });

// ------------------------------------------------------------------ start
async function start(mode) {
  await cfgReady;
  initAudio();
  if (LS.get('mute') === '1') setMuted(true);
  G.mode = 'desk'; LS.set('mode', 'desk'); updateNavigation();
  $('dev').hidden = !G.dev;
  const name = ($('name').value || '').trim() || 'Survivor';
  try { await ensureSession(name); } catch (e) { titleStatus(e.message); return; }
  connect();
  if (CFG.real_gps&&mode === 'gps'&&!G.phoneGps) { startDesk(); startGps(); }
}
$('name').value = Q.get('name') || G.name || '';
$('goWalk').addEventListener('click', () => { stopTrailer(); G.siege = false; document.body.classList.remove('siege'); siegeReset(); start('desk'); });
$('goSiege').addEventListener('click', () => { stopTrailer(); G.siege = true; document.body.classList.add('siege'); siegeReset(); start('desk'); });
function leaveSiege() {
  const ws = G.ws; G.ws = null;
  if (ws) { try { ws.send(JSON.stringify({ t: 'leave' })); } catch (_) {} ws.close(); }
  G.you = null; G.located = false; G.dead = false; G.desk = null; G.pos = null; G.lastPos = null; G.goal = null; G.route = [];
  G.zeds.clear(); G.corpses = []; G.body = null; G.channel = null; G.hasHello = false;
  siegeReset();
}
setupSiege({ fire, toast, sfx, buzz, get items() { return G.items; },
  onAgain() { leaveSiege(); G.siege = true; G.retry = 0; connect(); },
  onExit() { leaveSiege(); G.siege = false; document.body.classList.remove('siege'); $('hud').hidden = true; $('title').hidden = false; } });
setupBackgrounds(LS);
setupTrailer();

for(let i=0;i<8;i++){
 const b=document.createElement('button');b.type='button';b.dataset.character=i;b.setAttribute('aria-label','Choose survivor '+(i+1));
 const img=document.createElement('img');img.src='/assets/surv_p'+i+'.webp';img.alt='Survivor '+(i+1);b.append(img);
 b.setAttribute('aria-pressed',String(i===Number(LS.get('character','1'))));
 b.onclick=()=>{LS.set('character',String(i));for(const e of document.querySelectorAll('[data-character]'))e.setAttribute('aria-pressed',String(Number(e.dataset.character)===i));sprite('surv_p'+i);};
 $('characterChoices').append(b);
}

for (const n of ['zed_s0', 'zed_s1', 'surv_p0', 'item_bat']) sprite(n);
requestAnimationFrame(frame);
if (Q.get('auto')) start(Q.get('auto') === 'gps' ? 'gps' : 'desk');

// for the test harness and for poking at it from the console
window.__osz = {
  G, press, fire, aim, area, siege: siegeInfo, lerpAt: (p, t) => lerpAt(p, t ?? T()), project:(lat,lng)=>worldPoint(G,lat,lng),screenVector:(east,north)=>screenDirection(east,north,G.cam.iso),
  state() {
    const now = T(), y = G.you, out = { you: y, sight: G.sight, engaged: G.engaged, chasing: G.chasing, dead: G.dead, zeds: [], ctx: (G.ctx || []).map((c) => c.k), ppm: G.cam.ppm, fps: G.fps };
    if (!y || !G.pos) return out;
    const [la, ln] = lerpAt(G.pos, now);
    for (const z of G.zeds.values()) { const ll = lerpAt(z.p, now), [dx, dy] = deltaM(la, ln, ll[0], ll[1]); out.zeds.push({ id: z.id, d: +Math.hypot(dx, dy).toFixed(1), dx: +dx.toFixed(1), dy: +dy.toFixed(1), state: z.state, mine: z.mine, kind: z.kind, hp: z.hp }); }
    out.zeds.sort((a, b) => a.d - b.d);
    out.look = { character:Number(LS.get('character','1')), ...survivorState(), bag: wornCode('back'), head: wornCode('head'), held: y.hands && y.hands.code, cached: lookCache.size };
    out.herds = [...G.herds.values()].map((h) => { const ll = lerpAt(h.p, now), [dx, dy] = deltaM(la, ln, ll[0], ll[1]); return { id: h.id, count: h.count, d: +Math.hypot(dx, dy).toFixed(1), dx: +dx.toFixed(1), dy: +dy.toFixed(1), drawn: h.hid ? h.count - h.hid.reduce((n, v) => n + v, 0) : 0, marker: Math.hypot(dx, dy) >= G.sight * 0.9 }; });
    return out;
  },
  latency() { const L = G.lat; return { frame: [pct(L.frame, 0.5), pct(L.frame, 0.95), L.frame.length], server: [pct(L.server, 0.5), pct(L.server, 0.95), L.server.length], ping: [pct(L.ping, 0.5), pct(L.ping, 0.95), L.ping.length] }; },
  walk(dx, dy) { if (G.desk) G.goal = shiftLL(G.desk[0], G.desk[1], dx, dy); },
  walkTo,
};

// Warm action frames before the first fight, preserving procedural fallback while loading.
for (const stem of ['surv_swing', 'surv_push', 'zed_attack']) for (let i = 0; i < 4; i++) sprite(stem + i);
