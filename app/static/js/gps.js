// A GPS start uses a fresh fix; stored anchors never count as current location.
export function freshFix(p, now = Date.now()) {
  const c = p?.coords, timestamp = p?.timestamp;
  if (!c || ![c.latitude,c.longitude,c.accuracy,timestamp].every(Number.isFinite) ||
      Math.abs(c.latitude) >= 90 || Math.abs(c.longitude) > 180 ||
      c.accuracy <= 0 || c.accuracy > 80 || now-timestamp > 15000 || timestamp-now > 5000) return null;
  return [c.latitude,c.longitude,c.accuracy,timestamp];
}

export function acknowledgedPlacement(you, pending, minimumEpoch, generation) {
  if ((you.placement_epoch || 0) <= minimumEpoch) return null;
  const p = pending.filter(p=>p.a==='place'&&p.args.generation===generation).at(-1);
  if (!p) return null;
  return {result:{lat:you.lat,lng:you.lng,placement_epoch:you.placement_epoch,
    anchor:p.args.source==='gps'?[p.args.lat,p.args.lng]:null},args:p.args};
}
