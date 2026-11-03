// The Area overview: the camera pulled out over what this player remembers.
// It is a way of looking, never a way of moving. Nothing here walks, teleports or shows what is
// happening out of sight: dim ground was seen before, and every mark carries the time it was seen.
// A tap on empty ground offers a pin: the player's own note, kept with their memory of the map.
import { drawTiles, deltaM, shiftLL } from './map.js';

const $ = (id) => document.getElementById(id);
const ZOOMS = [1.1, 0.6, 0.3];          // pixels per metre: about 350 m, 650 m and 1.3 km across a phone
const PAN_LIMIT_M = 3000, REFETCH_M = 500, PICK_PX = 26;
const COMPASS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
const PINS = { supplies: ['Supplies', '#e0a030', 'S'], danger: ['Danger', '#e24638', '!'], shelter: ['Shelter', '#9fe0b4', 'H'], note: ['Come back', '#e8e6df', '?'] };
const SPENT = { tree: 'Felled trees', rubble: 'Picked-over rubble', rock: 'Quarried-out rock', ore: 'Worked-out ore', forage: 'Stripped foraging patch', pond: 'Fished-out pond' };
let api = null, fog = null;

export const area = { on: false, ppm: 1, zoom: 1, pan: [0, 0], data: null, asked: null, asking: false, drag: null, picked: null, spot: null };

const ago = (s) => s < 90 ? 'just now' : s < 5400 ? Math.round(s / 60) + ' min ago' : s < 129600 ? Math.round(s / 3600) + ' h ago' : Math.round(s / 86400) + ' days ago';
function whereFrom(ll, lat, lng) {
  const [dx, dy] = deltaM(ll[0], ll[1], lat, lng), d = Math.hypot(dx, dy);
  if (d < 8) return 'right here';
  return Math.round(d / 10) * 10 + ' m ' + COMPASS[Math.round(((Math.atan2(dx, dy) * 180 / Math.PI + 360) % 360) / 45) % 8];
}

export function setupArea(a) {
  api = a;
  $('bArea').addEventListener('click', () => (area.on ? closeArea() : openArea()));
  $('areaBack').addEventListener('click', () => closeArea());
  $('areaOut').addEventListener('click', () => { area.zoom = Math.min(ZOOMS.length - 1, area.zoom + 1); });
  $('areaIn').addEventListener('click', () => { area.zoom = Math.max(0, area.zoom - 1); });
  $('areaInfo').addEventListener('click', (ev) => {
    const b = ev.target.closest('button'); if (!b || !area.on) return;
    if (b.dataset.pin && area.spot) api.fire('pin', { op: 'add', kind: b.dataset.pin, lat: area.spot[0], lng: area.spot[1] });
    else if (b.dataset.unpin) api.fire('pin', { op: 'remove', pin: b.dataset.unpin });
    area.picked = area.spot = null; $('areaInfo').hidden = true;
  });
}
export function areaPinned(m) {              // the server's answer to a pin put down or taken off
  if (m.pins && area.data) area.data.pins = m.pins;
  if (!m.ok && m.why) api.toast(m.why, 'bad');
}

function ask() {
  const G = api.G; if (area.asking || !G.you) return;
  const c = shiftLL(G.you.lat, G.you.lng, area.pan[0], area.pan[1]);
  area.asking = true; area.asked = c;
  api.fire('memory', { lat: c[0], lng: c[1] });
}
export function areaResult(m) {
  area.asking = false;
  if (m.ok) area.data = m; else if (area.on) $('areaNote').textContent = 'Your map could not be loaded. Try again.';
}

export function openArea() {
  const G = api.G;
  if (!G.you || !G.located || G.dead || G.pickStart || G.placement) return;
  api.stop();                                            // looking at the map is not a way to keep walking
  if (G.channel) api.fire('cancel');
  api.collapse();
  Object.assign(area, { on: true, ppm: G.cam.ppm, zoom: 1, pan: [0, 0], drag: null, picked: null, spot: null, data: null, asking: false });
  document.body.classList.add('area');
  $('areaBar').hidden = false; $('areaInfo').hidden = true;
  $('areaNote').textContent = 'Loading what you remember…';
  ask();
}
export function closeArea(why) {
  if (!area.on) return;
  area.on = false; area.drag = null;
  document.body.classList.remove('area');
  $('areaBar').hidden = true; $('areaInfo').hidden = true;
  if (why === 'attack') api.toast('Back to the street: something is close.', 'bad');
}

// ---- touch: drag pans the camera, a tap inspects the nearest mark. Neither moves the survivor.
export function areaPointer(type, ev) {
  if (type === 'down') { area.drag = { id: ev.pointerId, x: ev.clientX, y: ev.clientY, pan: [...area.pan], moved: false }; return; }
  const d = area.drag; if (!d || ev.pointerId !== d.id) return;
  const dx = ev.clientX - d.x, dy = ev.clientY - d.y;
  if (type === 'move') {
    if (Math.hypot(dx, dy) > 10) d.moved = true;
    if (d.moved) area.pan = [d.pan[0] - dx / area.ppm, d.pan[1] + dy / area.ppm].map((v) => Math.max(-PAN_LIMIT_M, Math.min(PAN_LIMIT_M, v)));
    return;
  }
  area.drag = null;
  if (type !== 'up') return;
  if (!d.moved) { pick(ev.clientX, ev.clientY); return; }
  const G = api.G, c = shiftLL(G.you.lat, G.you.lng, area.pan[0], area.pan[1]);
  if (!area.asked || Math.hypot(...deltaM(area.asked[0], area.asked[1], c[0], c[1])) > REFETCH_M) ask();
}

function marks() {
  const G = api.G, out = [], home = G.body && G.body.home, d = area.data;
  if (home) out.push({ kind: 'home', lat: home.lat, lng: home.lng, name: home.name || 'Home', line: 'Your home. Supplies stored there outlive you.' });
  if (d && d.death) out.push({ kind: 'death', lat: d.death.lat, lng: d.death.lng, name: 'Where your last survivor fell', line: ago(d.death.age_s) });
  for(const r of d?.recoveries||[])out.push({kind:'recovery',lat:r.lat,lng:r.lng,name:r.empty?'Recovered pack':'Your recovery pack',line:(r.floor_level?'Floor '+(r.floor_level+1)+' · ':'Ground floor · ')+(r.empty?'Already emptied':Math.ceil(r.remaining_s/3600)+'h left to recover your gear')});
  for(const v of d?.vehicles||[])out.push({kind:'vehicle',lat:v.lat,lng:v.lng,name:v.kind==='van'?'Hauling van':'Abandoned car',line:'Last seen '+ago(v.age_s)+'. It may have moved.'});
  for (const m of (d ? d.marks : [])) {
    out.push({ kind: m.left > 0 ? 'stock' : 'empty', lat: m.lat, lng: m.lng, name: api.containerName(m.kind),
      line: (m.left > 0 ? m.left + ' item' + (m.left === 1 ? '' : 's') + ' left' : 'Emptied') + ' when you last looked, ' + ago(m.age_s) + '. It may have changed.' });
  }
  for (const m of (d && d.spent ? d.spent : [])) out.push({ kind: 'spent', lat: m.lat, lng: m.lng, name: SPENT[m.kind] || 'Used-up spot', line: 'You used this up. Look elsewhere.' });
  for (const m of (d && d.pins ? d.pins : [])) out.push({ kind: 'pin', pin: m.kind, id: m.id, lat: m.lat, lng: m.lng, name: 'Your pin: ' + (PINS[m.kind] || PINS.note)[0], line: 'You put it here ' + ago(m.age_s) + '.' });
  return out;
}
function pick(x, y) {
  const G = api.G, here = [G.you.lat, G.you.lng], box = $('areaInfo');
  let best = null, bestD = PICK_PX;
  for (const m of marks()) { const [px, py] = area.P(m.lat, m.lng), d = Math.hypot(px - x, py - y); if (d < bestD) { best = m; bestD = d; } }
  area.picked = best; area.spot = best || !area.at ? null : area.at(x, y);
  box.hidden = false; box.textContent = '';
  const say = (text) => { const t = document.createElement('span'); t.textContent = text; box.appendChild(t); };
  const button = (label, key, value) => { const b = document.createElement('button'); b.textContent = label; b.dataset[key] = value; box.appendChild(b); };
  if (best) {
    say(`${best.name} · ${whereFrom(here, best.lat, best.lng)}. ${best.line}`);
    if (best.kind === 'pin') button('Remove pin', 'unpin', best.id);
  } else if (area.spot) {
    say(`Pin this spot, ${whereFrom(here, area.spot[0], area.spot[1])}:`);
    for (const [kind, [label]] of Object.entries(PINS)) button(label, 'pin', kind);
  } else box.hidden = true;
}

export function drawArea(ctx, W, H, now, dt, ylat, ylng) {
  const G = api.G;
  area.ppm += (ZOOMS[area.zoom] - area.ppm) * (1 - Math.exp(-dt * 5));
  const ppm = area.ppm, c = shiftLL(ylat, ylng, area.pan[0], area.pan[1]), cx = W / 2, cy = H / 2;
  drawTiles(ctx, { lat: c[0], lng: c[1], ppm }, W, H, cx, cy, now);
  const P = area.P = (lat, lng) => { const [dx, dy] = deltaM(c[0], c[1], lat, lng); return [cx + dx * ppm, cy - dy * ppm]; };
  area.at = (x, y) => shiftLL(c[0], c[1], (x - cx) / ppm, (cy - y) / ppm);
  const [yx, yy] = P(ylat, ylng), sightPx = (G.sight || 55) * ppm;

  // ---- fog: dark where you have never been, dim where you have, clear where you are looking now
  if (!fog) fog = document.createElement('canvas');
  if (fog.width !== W || fog.height !== H) { fog.width = W; fog.height = H; }
  const f = fog.getContext('2d');
  f.globalCompositeOperation = 'source-over'; f.clearRect(0, 0, W, H);
  f.fillStyle = 'rgba(5,8,7,0.9)'; f.fillRect(0, 0, W, H);
  f.globalCompositeOperation = 'destination-out';
  const d = area.data;
  if (d) {
    const hM = d.span[0] * 111320, wM = d.span[1] * 111320 * Math.cos(c[0] * Math.PI / 180), w = wM * ppm + 0.6, h = hM * ppm + 0.6;
    for (const cell of d.cells) {
      const [px, py] = P(cell[0], cell[1]);
      if (px > W || py < 0 || px + w < 0 || py - h > H) continue;
      f.fillStyle = cell[2] < 1 ? 'rgba(0,0,0,0.58)' : cell[2] < 7 ? 'rgba(0,0,0,0.46)' : 'rgba(0,0,0,0.34)';
      f.fillRect(px, py - h, w, h);
    }
  }
  const g = f.createRadialGradient(yx, yy, sightPx * 0.55, yx, yy, sightPx);
  g.addColorStop(0, 'rgba(0,0,0,1)'); g.addColorStop(1, 'rgba(0,0,0,0)');
  f.fillStyle = g; f.beginPath(); f.arc(yx, yy, sightPx, 0, 6.3); f.fill();
  ctx.drawImage(fog, 0, 0, W, H);

  // ---- what is in sight right now, and only that
  ctx.fillStyle = 'rgba(226,70,56,0.95)';
  for (const z of G.zeds.values()) { const [px, py] = P(z.p.b[0], z.p.b[1]); ctx.beginPath(); ctx.arc(px, py, 3.2, 0, 6.3); ctx.fill(); }
  for (const h of G.herds.values()) {              // a herd in sight: the whole column, and what it is
    const L = 1.9 * Math.sqrt(h.count), Wd = 0.55 * Math.sqrt(h.count), fc = Math.cos(h.to), fs = Math.sin(h.to), ph = h.seed * Math.PI / 180;
    for (let i = 0; i < h.count; i++) {
      const r = Math.sqrt((i + 0.5) / h.count), t = i * 2.399963229728653 + ph, u = L * r * Math.cos(t), v = Wd * r * Math.sin(t);
      const at = shiftLL(h.p.b[0], h.p.b[1], u * fc - v * fs, u * fs + v * fc), [px, py] = P(at[0], at[1]);
      ctx.beginPath(); ctx.arc(px, py, 2.2, 0, 6.3); ctx.fill();
    }
    const [hx, hy] = P(h.p.b[0], h.p.b[1]);
    ctx.font = '700 11px system-ui'; ctx.textAlign = 'center'; ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(0,0,0,0.85)';
    ctx.strokeText('HERD · ' + h.count, hx, hy - L * ppm - 8); ctx.fillStyle = '#f0c267'; ctx.fillText('HERD · ' + h.count, hx, hy - L * ppm - 8);
    ctx.fillStyle = 'rgba(226,70,56,0.95)';
  }

  // ---- remembered marks
  ctx.lineWidth = 2; ctx.font = '700 11px system-ui'; ctx.textAlign = 'center';
  for (const m of marks()) {
    const [px, py] = P(m.lat, m.lng); if (px < -20 || py < -20 || px > W + 20 || py > H + 20) continue;
    if (m.kind === 'home') {
      ctx.fillStyle = '#9fe0b4'; ctx.strokeStyle = '#0b1410';
      ctx.beginPath(); ctx.moveTo(px, py - 11); ctx.lineTo(px + 10, py - 2); ctx.lineTo(px + 7, py - 2); ctx.lineTo(px + 7, py + 8); ctx.lineTo(px - 7, py + 8); ctx.lineTo(px - 7, py - 2); ctx.lineTo(px - 10, py - 2); ctx.closePath(); ctx.fill(); ctx.stroke();
    } else if (m.kind === 'vehicle') {
      ctx.fillStyle='#94bdd2';ctx.strokeStyle='#11202a';ctx.fillRect(px-9,py-5,18,10);ctx.strokeRect(px-9,py-5,18,10);ctx.fillStyle='#11202a';ctx.fillText('V',px,py+4);
    } else if (m.kind === 'recovery') {
      ctx.fillStyle='#77dba4';ctx.strokeStyle='#11281c';ctx.fillRect(px-7,py-8,14,16);ctx.strokeRect(px-7,py-8,14,16);ctx.fillStyle='#11281c';ctx.fillText('R',px,py+4);
    } else if (m.kind === 'death') {
      ctx.strokeStyle = '#e8d9c8'; ctx.beginPath(); ctx.moveTo(px - 6, py - 6); ctx.lineTo(px + 6, py + 6); ctx.moveTo(px + 6, py - 6); ctx.lineTo(px - 6, py + 6); ctx.stroke();
    } else if (m.kind === 'pin') {            // a teardrop standing on the spot, with its letter
      const [, colour, letter] = PINS[m.pin] || PINS.note;
      ctx.fillStyle = colour; ctx.strokeStyle = '#0b1410';
      ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(px - 6, py - 12); ctx.arc(px, py - 15, 7, Math.PI * 0.87, Math.PI * 0.13); ctx.lineTo(px, py); ctx.closePath(); ctx.fill(); ctx.stroke();
      ctx.fillStyle = '#0b1410'; ctx.fillText(letter, px, py - 11);
    } else if (m.kind === 'spent') {
      ctx.strokeStyle = '#8a938c'; ctx.beginPath(); ctx.arc(px, py, 5, 0, 6.3); ctx.moveTo(px - 4, py + 4); ctx.lineTo(px + 4, py - 4); ctx.stroke();
    } else {
      ctx.fillStyle = m.kind === 'stock' ? '#e0a030' : '#6f7a73'; ctx.strokeStyle = '#0b1410';
      ctx.fillRect(px - 5, py - 5, 10, 10); ctx.strokeRect(px - 5, py - 5, 10, 10);
    }
    if (area.picked && area.picked.lat === m.lat && area.picked.lng === m.lng && area.picked.kind === m.kind) {
      ctx.strokeStyle = '#d5ecb5'; ctx.setLineDash([5, 3]); ctx.strokeRect(px - 14, py - (m.kind === 'pin' ? 27 : 16), 28, m.kind === 'pin' ? 32 : 30); ctx.setLineDash([]);
    }
  }
  if (area.spot) {                            // the empty ground just tapped
    const [px, py] = P(area.spot[0], area.spot[1]);
    ctx.strokeStyle = '#d5ecb5'; ctx.beginPath(); ctx.arc(px, py, 7, 0, 6.3); ctx.moveTo(px - 11, py); ctx.lineTo(px + 11, py); ctx.moveTo(px, py - 11); ctx.lineTo(px, py + 11); ctx.stroke();
  }
  // ---- you
  ctx.strokeStyle = '#f4f7ee'; ctx.fillStyle = '#3a78c2'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.arc(yx, yy, 6, 0, 6.3); ctx.fill(); ctx.stroke();
  ctx.fillStyle = '#f4f7ee'; ctx.fillText('YOU', yx, yy - 11);
  ctx.textAlign = 'left';

  const home = G.body && G.body.home;
  if (d) {
    $('areaNote').textContent = (d.known ? 'Bright: in sight now. Dim: seen before. Dark: not visited. Marks may be out of date. Tap empty ground to pin it.' : 'Nothing remembered yet. Walk, and the ground you pass stays lit.')
      + (home ? ' Home is ' + whereFrom([ylat, ylng], home.lat, home.lng) + '.' : '');
  }
}
