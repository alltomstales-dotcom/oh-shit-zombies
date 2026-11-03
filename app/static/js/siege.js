// Siege: survive 30 minutes (server: app/game/siege.py). The street is drawn by main.js as usual;
// this adds the timer and score, the boss warning and health bar, the choice of three, chests and
// the end card. Every frame carries a `siege` block; events arrive as siege_* in the event list.
const $ = (id) => document.getElementById(id);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const COMPASS = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west'];
const compass = (b) => COMPASS[Math.round(((b % 360) + 360) % 360 / 45) % 8];

export const mmss = (s) => { s = Math.max(0, Math.floor(s)); return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };

let S = null, ctl = null, shownChoice = '', ended = false;

export function setupSiege(c) {
  // c: {fire, toast, sfx, buzz, onAgain, onExit}
  ctl = c;
  for (let i = 0; i < 3; i++) $('siegePick' + i).addEventListener('click', () => pick(i));
  $('siegeAgain').addEventListener('click', () => { hideEnd(); ctl.onAgain(); });
  $('siegeExit').addEventListener('click', () => { hideEnd(); ctl.onExit(); });
  window.addEventListener('keydown', (e) => {
    if (!S || !S.choice || $('siegeChoice').hidden) return;
    const i = ['1', '2', '3'].indexOf(e.key);
    if (i >= 0 && i < S.choice.length) { e.preventDefault(); pick(i); }
  });
}

function pick(i) {
  if (!S || !S.choice || !S.choice[i]) return;
  ctl.fire('siege_pick', { pick: i });
  $('siegeChoice').hidden = true; shownChoice = 'picked:' + S.level;
}

export function siegeReset() {
  S = null; shownChoice = ''; ended = false;
  for (const id of ['siegeBar', 'siegeBanner', 'siegeBoss', 'siegeChoice', 'siegeEnd']) $(id).hidden = true;
}

export function siegeState(info) {
  S = info;
  $('siegeBar').hidden = false;
  const t = info.t, over = info.over;
  $('siegeTime').textContent = mmss(over ? over.t : t);
  $('siegeTime').classList.toggle('dead', !!over && over.result !== 'extracted');
  $('siegeScore').textContent = (over ? over.score : info.score).toLocaleString();
  $('siegeLevel').textContent = 'Lv ' + info.level;
  $('siegeKills').textContent = info.kills + ' down';
  $('siegeXp').style.width = (100 * clamp(info.xp / Math.max(1, info.xp_next), 0, 1)) + '%';
  const next = info.boss_in != null && info.boss_in > 0 && !info.boss ? 'Boss in ' + mmss(info.boss_in) : '';
  $('siegeNext').textContent = info.evac_in != null ? 'Helicopter in ' + mmss(info.evac_in) : next;
  // the warning, then the health bar
  const ban = $('siegeBanner');
  if (info.boss_warn) {
    ban.hidden = false; ban.className = 'warn';
    ban.textContent = `Something big is coming — from the ${compass(info.boss_warn.b)}. ${info.boss_warn.name}, in ${Math.max(0, Math.ceil(info.boss_warn.at - t))} s.`;
  } else if (info.evac_in != null && !over) {
    ban.hidden = false; ban.className = 'evac'; ban.textContent = `Helicopter inbound: hold on ${Math.ceil(info.evac_in)} s.`;
  } else ban.hidden = true;
  if (info.boss) {
    $('siegeBoss').hidden = false; $('siegeBossName').textContent = info.boss.name;
    $('siegeBossHp').style.width = (100 * clamp(info.boss.hp / Math.max(1, info.boss.hp_max), 0, 1)) + '%';
  } else $('siegeBoss').hidden = true;
  // the choice of three: the run waits for it
  if (info.choice && !over) {
    const key = info.level + ':' + info.choice.map((c) => c.id).join(',');
    if (key !== shownChoice) {
      shownChoice = key; $('siegeChoice').hidden = false;
      $('siegeChoiceTitle').textContent = `Level ${info.level}. Choose one.`;
      for (let i = 0; i < 3; i++) {
        const b = $('siegePick' + i), c = info.choice[i];
        b.hidden = !c; if (!c) continue;
        b.innerHTML = `<b>${i + 1}. ${c.name}</b><small>${c.text}</small>`;
      }
      ctl.sfx.found(); ctl.buzz(30);
    }
    $('siegeChoiceLeft').textContent = info.choice_left != null ? `The fight waits. First one in ${Math.ceil(info.choice_left)} s.` : 'The fight waits.';
  } else $('siegeChoice').hidden = true;
  if (over && !ended) showEnd(info);
}

function showEnd(info) {
  ended = true;
  const o = info.over;
  $('siegeChoice').hidden = true; $('siegeBanner').hidden = true;
  $('siegeEndTitle').textContent = o.result === 'extracted' ? 'EXTRACTED' : o.result === 'left' ? 'You left the siege' : 'Siege over';
  $('siegeEndTime').textContent = mmss(o.t);
  $('siegeEndTime').className = o.result === 'extracted' ? 'win' : 'dead';
  const ul = $('siegeEndStats'); ul.textContent = '';
  const add = (t) => { const li = document.createElement('li'); li.textContent = t; ul.appendChild(li); };
  add(`Score ${o.score.toLocaleString()}`);
  add(`${o.kills} put down, level ${o.level}, ${o.bosses} boss${o.bosses === 1 ? '' : 'es'}`);
  if (o.cause) add(o.cause === 'bled out' ? 'Bled out' : 'Pulled down');
  const d = info.delivered, name = (c) => (ctl.items?.[c]?.name || c);
  if (!o.haul.length) add('No chests opened: nothing to take home.');
  else if (d && d.items && d.items.length) add('Taken home to ' + d.home + ': ' + d.items.map((r) => r.qty + ' × ' + name(r.code)).join(', ') + (d.left.length ? '. No room for the rest.' : '.'));
  else if (d && d.home === null) add('No home set in survival, so the haul stayed in Chicago: ' + o.haul.map((r) => r.qty + ' × ' + name(r.code)).join(', ') + '.');
  else add('Haul: ' + o.haul.map((r) => r.qty + ' × ' + name(r.code)).join(', ') + '.');
  setTimeout(() => { $('siegeEnd').hidden = false; }, o.result === 'dead' ? 1200 : 300);
  if (o.result === 'extracted') ctl.sfx.heli(0.12); else ctl.sfx.death();
}
function hideEnd() { $('siegeEnd').hidden = true; }

export function siegeEvent(e) {
  switch (e.e) {
    case 'siege_boss_warn': ctl.sfx.groan(0, 0.4, true); ctl.buzz([80, 60, 80]); break;
    case 'siege_boss': ctl.toast(`${e.name} is here.`, 'bad'); break;
    case 'siege_boss_down': ctl.toast('Boss down. It dropped a chest.', 'good'); ctl.sfx.found(); break;
    case 'siege_chest': if (e.kind === 'arena') ctl.toast('A chest appeared in the plaza.', 'tip'); break;
    case 'siege_chest_open': ctl.sfx.found(); ctl.toast(`Chest: ${e.upgrade_name ? e.upgrade_name + ', and ' : ''}${e.qty} × ${e.find_name} for home.`, 'good'); break;
    case 'siege_picked': ctl.toast(e.name + '.', 'good'); break;
    case 'siege_extracted': ctl.toast('The helicopter is down. GO.', 'good'); break;
  }
}

export function siegeInfo() { return S; }
export function siegeBossId() { return S && S.boss ? S.boss.id : null; }

// Under everyone: the arena's edge, chests, and where the boss will walk in.
export function siegeDrawGround(ctx, P, ppm, now, sprite, groundCircle, iso) {
  if (!S) return;
  const a = S.arena, [ax, ay] = P(a.lat, a.lng);
  ctx.save();
  ctx.strokeStyle = 'rgba(224,160,48,0.35)'; ctx.lineWidth = 2; ctx.setLineDash([10, 8]);
  ctx.beginPath(); groundCircle(ctx, ax, ay, a.r * ppm, iso); ctx.stroke(); ctx.setLineDash([]);
  const pulse = 0.5 + 0.5 * Math.sin(now / 220);
  for (const [id, lat, lng, kind] of S.chests || []) {
    const [x, y] = P(lat, lng), sz = clamp(3 * ppm, 30, 64), sp = sprite('item_crate');
    ctx.fillStyle = `rgba(255,214,90,${0.18 + 0.2 * pulse})`; ctx.beginPath(); ctx.ellipse(x, y, sz * 0.7, sz * 0.28, 0, 0, 6.3); ctx.fill();
    if (sp.ok) { const w = sz * sp.img.naturalWidth / sp.img.naturalHeight; ctx.drawImage(sp.img, x - w / 2, y - sz * 0.85, w, sz); }
    else { ctx.fillStyle = '#c8962e'; ctx.fillRect(x - 10, y - 18, 20, 16); }
    ctx.font = '800 11px system-ui'; ctx.textAlign = 'center'; ctx.fillStyle = '#ffe08a';
    ctx.fillText(kind === 'boss' ? 'BOSS CHEST' : 'CHEST', x, y + 15);
  }
  if (S.boss_warn) {
    const [x, y] = P(S.boss_warn.lat, S.boss_warn.lng), r = (4 + 2 * pulse) * ppm;
    ctx.strokeStyle = `rgba(230,50,40,${0.5 + 0.4 * pulse})`; ctx.lineWidth = 4;
    ctx.beginPath(); groundCircle(ctx, x, y, r, iso); ctx.stroke();
    ctx.font = '900 14px system-ui'; ctx.textAlign = 'center'; ctx.fillStyle = '#ff6a5c';
    ctx.fillText('!', x, y - 6); ctx.font = '800 11px system-ui'; ctx.fillText(S.boss_warn.name.toUpperCase(), x, y + r * 0.4 + 14);
    // and an arrow at the screen's edge pointing to it
    const W = ctx.canvas.clientWidth || ctx.canvas.width, H = ctx.canvas.clientHeight || ctx.canvas.height;
    if (x < 0 || y < 0 || x > W || y > H) {
      const cx = W / 2, cy = H / 2, ang = Math.atan2(y - cy, x - cx), ex = cx + Math.cos(ang) * (Math.min(W, H) / 2 - 40), ey = cy + Math.sin(ang) * (Math.min(W, H) / 2 - 40);
      ctx.translate(ex, ey); ctx.rotate(ang); ctx.fillStyle = `rgba(230,50,40,${0.6 + 0.4 * pulse})`;
      ctx.beginPath(); ctx.moveTo(18, 0); ctx.lineTo(-10, -12); ctx.lineTo(-10, 12); ctx.closePath(); ctx.fill();
    }
  }
  ctx.restore();
}

// Over a boss: its name and health, drawn with the zombie.
export function siegeDrawBoss(ctx, z, x, y, h) {
  if (!S || !S.boss || S.boss.id !== z.id) return;
  const w = Math.max(50, h * 0.7), f = clamp(S.boss.hp / Math.max(1, S.boss.hp_max), 0, 1);
  ctx.fillStyle = 'rgba(0,0,0,0.6)'; ctx.fillRect(x - w / 2, y - h - 16, w, 7);
  ctx.fillStyle = '#d9483b'; ctx.fillRect(x - w / 2, y - h - 16, w * f, 7);
  ctx.font = '800 11px system-ui'; ctx.textAlign = 'center'; ctx.fillStyle = '#ffb39e'; ctx.fillText(S.boss.name, x, y - h - 20);
}
