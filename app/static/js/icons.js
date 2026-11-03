// Original small line icons; no platform emoji/font dependency.
const paths={
 weapon:'M4 20 18 6M15 4l5 5M8 15l2 2',
 gun:'M3 8h17v6H9l-1 6H4l1-7H3z',
 clothing:'m7 3 5 2 5-2 5 5-4 3v10H6V11L2 8z',
 bag:'M7 7V5a5 5 0 0 1 10 0v2M5 7h14v15H5zM8 13h8v5H8z',
 drink:'M9 2h6v5l3 4v10H6V11l3-4zM8 15h8',
 food:'M5 5h14v16H5zM5 8h14M5 18h14M8 12h8',
 medical:'M4 4h16v16H4zM12 8v8M8 12h8',
 material:'m2 9 16-5 4 11-16 5zM6 11l13-4M8 15l13-4',
 tool:'m4 21 10-10M14 11a6 6 0 0 0 7-7l-4 4-3-3 4-4a6 6 0 0 0-7 7M3 20l2 2',
 ammo:'M7 21V8l2-5 2 5v13zM15 21V8l2-5 2 5v13z',
 personal:'M4 4h7a4 4 0 0 1 4 2h5v15h-5a4 4 0 0 0-4-2H4zM15 6v15M7 8h4M7 12h4',
};
paths.book=paths.personal;   // the open-book outline
// How long until something finishes, in the units a person would say it in.
export function waitText(seconds){
 if(seconds<=0)return 'now';if(seconds<90)return 'a minute';if(seconds<5400)return Math.round(seconds/60)+' min';
 return Math.round(seconds/3600)+' h';
}
export function itemIcon(kind){
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');
 const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',paths[kind]||paths.bag);
 path.setAttribute('fill','none');path.setAttribute('stroke','currentColor');path.setAttribute('stroke-width','1.7');path.setAttribute('stroke-linecap','round');path.setAttribute('stroke-linejoin','round');svg.append(path);return svg;
}
