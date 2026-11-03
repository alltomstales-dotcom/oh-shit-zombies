// Device preferences apply only when the server says this is an unplaced new life.
let catalog=null,storage;
const $=id=>document.getElementById(id);
const defaults={occupation:'generalist',trait:'balanced'};
export function normalizeBackground(choice,data){
 return {occupation:data?.occupations.some(o=>o.id===choice?.occupation)?choice.occupation:defaults.occupation,
         trait:data?.traits.some(t=>t.id===choice?.trait)?choice.trait:defaults.trait};
}
function preference(){return {occupation:storage.get('occupation',defaults.occupation),trait:storage.get('trait',defaults.trait)};}
function describe(occupation,trait){
 const job=catalog?.occupations.find(o=>o.id===occupation),t=catalog?.traits.find(t=>t.id===trait);
 return (job?.description||'')+' '+(t?.description||'');
}
function refresh(){
 const choice=normalizeBackground(preference(),catalog);
 for(const prefix of ['background','deathBackground']){
  const jobs=$(prefix+'Occupation'),traits=$(prefix+'Trait');if(!jobs||!traits)continue;
  for(const [select,rows,key] of [[jobs,catalog.occupations,'occupation'],[traits,catalog.traits,'trait']]){
   select.replaceChildren();for(const row of rows){const o=document.createElement('option');o.value=row.id;o.textContent=row.name;select.append(o);}select.value=choice[key];select.disabled=false;
   select.onchange=()=>{storage.set(key,select.value);refresh();};
  }
  $(prefix+'Description').textContent=describe(choice.occupation,choice.trait);
 }
}
export function setBackgroundCatalog(data){if(!data?.occupations?.length||!data?.traits?.length)return;catalog=data;if(storage)refresh();}
export function setupBackgrounds(ls){storage=ls;fetch('/api/backgrounds').then(r=>{if(!r.ok)throw Error('catalog');return r.json();}).then(setBackgroundCatalog).catch(()=>{});}
export function backgroundChoice(data=catalog){return normalizeBackground(preference(),data);}
