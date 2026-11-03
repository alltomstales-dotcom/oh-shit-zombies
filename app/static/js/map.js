// A small slippy-map ground layer: no library, one canvas, any fractional zoom.
export const D2R = Math.PI / 180;
const R = 6378137, CIRC = 2 * Math.PI * R;
export const M_PER_DEG = D2R * R;
const KEEP = 280;
// Standard OpenStreetMap tiles, greyed and darkened once per tile as they arrive.
let SRC = { url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', max_z: 19, dark: true };
export function setTiles(cfg) { if (cfg && cfg.url) { SRC = { ...SRC, ...cfg }; cache.clear(); } }
const tileUrl = (z, x, y) => SRC.url.replace('{s}', 'abc'[(x + y) % 3]).replace('{z}', z).replace('{x}', x).replace('{y}', y).replace('{r}', '');

function night(img) {
  const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  const g = c.getContext('2d');
  g.drawImage(img, 0, 0);
  g.globalCompositeOperation = 'saturation'; g.fillStyle = '#808080'; g.fillRect(0, 0, c.width, c.height);
  g.globalCompositeOperation = 'multiply';
  g.drawImage(c, 0, 0); g.drawImage(c, 0, 0);            // twice over itself: pale streets, dark blocks
  g.fillStyle = '#7d8c82'; g.fillRect(0, 0, c.width, c.height);
  return c;
}

const cache = new Map();
export const tileStats = { loaded: 0, failed: 0 };

function merc(lat, lng, z) {
  const s = 256 * 2 ** z, sin = Math.sin(lat * D2R);
  return [(lng + 180) / 360 * s, (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * s];
}

function tile(z, x, y, now) {
  const n = 2 ** z;
  if (y < 0 || y >= n) return null;
  x = ((x % n) + n) % n;
  const k = z + '/' + x + '/' + y;
  let t = cache.get(k);
  if (!t) {
    const img = new Image();
    t = { img, ok: false, bad: 0, used: now };
    img.onload = () => { t.pic = SRC.dark ? night(img) : img; t.size = img.naturalWidth; t.ok = true; tileStats.loaded++; };
    img.onerror = () => { t.bad = performance.now(); tileStats.failed++; };
    img.src = tileUrl(z, x, y);
    cache.set(k, t);
    if (cache.size > KEEP) prune();
  } else if (t.bad && now - t.bad > 6000) {
    cache.delete(k);                       // try again on a later frame
  }
  t.used = now;
  return t;
}

function prune() {
  const rows = [...cache.entries()].sort((a, b) => a[1].used - b[1].used);
  for (let i = 0; i < rows.length - KEEP * 0.75; i++) cache.delete(rows[i][0]);
}

// cam = {lat, lng, ppm}: pixels per metre on the ground at the camera. (cx, cy) is where the
// camera point sits on the canvas, in CSS pixels.
export function drawTiles(ctx, cam, w, h, cx, cy, now, bounds=[0,0,w,h]) {
  const zf = Math.log2(cam.ppm * CIRC * Math.cos(cam.lat * D2R) / 256);
  const z = Math.max(3, Math.min(SRC.max_z, Math.round(zf)));
  const scale = 2 ** (zf - z), ts = 256 * scale;
  const [mx, my] = merc(cam.lat, cam.lng, z);
  const x0 = Math.floor((mx + (bounds[0]-cx) / scale) / 256), x1 = Math.floor((mx + (bounds[2] - cx) / scale) / 256);
  const y0 = Math.floor((my + (bounds[1]-cy) / scale) / 256), y1 = Math.floor((my + (bounds[3] - cy) / scale) / 256);
  for (let ty = y0; ty <= y1; ty++) {
    for (let tx = x0; tx <= x1; tx++) {
      const sx = Math.floor(cx + (tx * 256 - mx) * scale), sy = Math.floor(cy + (ty * 256 - my) * scale);
      const size = Math.ceil(ts) + 1;
      const t = tile(z, tx, ty, now);
      if (t && t.ok) { ctx.drawImage(t.pic, sx, sy, size, size); continue; }
      for (let k = 1; k <= 5 && z - k >= 3; k++) {          // stand in with a loaded ancestor
        const n = 2 ** (z - k), px = (((tx >> k) % n) + n) % n;
        const p = cache.get((z - k) + '/' + px + '/' + (ty >> k));
        if (p && p.ok) {
          const div = 2 ** k, src = p.size / div;
          ctx.drawImage(p.pic, (tx & (div - 1)) * src, (ty & (div - 1)) * src, src, src, sx, sy, size, size);
          break;
        }
      }
    }
  }
  // closer than the tiles go, street names turn into giant smears: fade to plain ground
  const over = Math.max(0, Math.min(0.8, (zf - SRC.max_z - 0.2) / 1.6));
  if (over > 0) { ctx.fillStyle = `rgba(52,60,55,${over})`; ctx.fillRect(bounds[0],bounds[1],bounds[2]-bounds[0],bounds[3]-bounds[1]); }
}

// metres east and north from one point to another (fine over the few hundred metres we draw)
export function deltaM(lat0, lng0, lat, lng) {
  return [(lng - lng0) * M_PER_DEG * Math.cos(lat0 * D2R), (lat - lat0) * M_PER_DEG];
}
export function shiftLL(lat, lng, dx, dy) {
  return [lat + dy / M_PER_DEG, lng + dx / (M_PER_DEG * Math.cos(lat * D2R))];
}
