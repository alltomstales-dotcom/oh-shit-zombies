// All world targets compete by distance, so a nearby doorway cannot steal a shelf tap.
export function nearestTarget(candidates){
 return candidates.filter(Boolean).sort((a,b)=>a.hit-b.hit)[0]||null;
}
