import {entranceApproach} from './buildings.js';
export const floorName=n=>Number(n)?'Floor '+(Number(n)+1):'Ground floor';
export function homeApproach(G,h){
 const b=G.buildings.find(b=>b.id===h.building),level=G.you.floor||0,target=h.floor_level||0;
 if(G.inside===h.building&&level!==target&&b?.stairs)return {mode:'stairs',building:b.id,goal:b.stairs};
 if(level&&G.inside!==h.building)return {mode:'exit'};
 if(b&&G.inside!==h.building)return {mode:'entrance',goal:entranceApproach(b,G.desk)||[h.lat,h.lng]};
 return {mode:'cupboard',goal:[h.lat,h.lng]};
}
