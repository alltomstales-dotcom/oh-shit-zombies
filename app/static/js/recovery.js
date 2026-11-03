// Nearby shortcut must never choose a stranger's private recovery pack.
export function nearbyBody(corpses,distance){
 return corpses.filter(c=>c.can_loot!==false&&(!c.searched||c.items?.length))
  .map(c=>({c,d:distance(c)})).filter(o=>o.d<=12)
  .sort((a,b)=>Number(b.c.reachable)-Number(a.c.reachable)||Number(!!b.c.own)-Number(!!a.c.own)||a.d-b.d||(b.c.recover_until||0)-(a.c.recover_until||0))[0];
}
