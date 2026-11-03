// Attachment points measured against each existing standing illustration (frame fractions).
// Right/left refer to the survivor. These are procedural poses, not extra authored sprites.
const poses=[
 {head:[.50,.20],neck:[.53,.39],torso:[.48,.52],hand:[.14,.52],other:[.63,.59],shoulder:[.30,.42],elbow:[.23,.56],otherShoulder:[.68,.43],otherElbow:[.69,.56],thigh:[.32,.70],otherThigh:[.62,.73],shin:[.27,.83],otherShin:[.66,.89],helmet:[.48,.09],bag:[.82,.48]},
 {head:[.50,.11],neck:[.52,.42],torso:[.46,.53],hand:[.17,.47],other:[.90,.39],shoulder:[.30,.46],elbow:[.24,.54],otherShoulder:[.69,.45],otherElbow:[.79,.47],thigh:[.36,.70],otherThigh:[.66,.68],shin:[.33,.83],otherShin:[.74,.80],helmet:[.47,.085],bag:[.17,.44]},
 {head:[.48,.18],neck:[.49,.35],torso:[.48,.47],hand:[.19,.41],other:[.86,.36],shoulder:[.28,.37],elbow:[.17,.46],otherShoulder:[.65,.38],otherElbow:[.74,.44],thigh:[.34,.68],otherThigh:[.56,.66],shin:[.31,.82],otherShin:[.61,.82],helmet:[.47,.06],bag:[.12,.57]},
 {head:[.52,.18],neck:[.53,.35],torso:[.47,.51],hand:[.37,.47],other:[.91,.44],shoulder:[.32,.40],elbow:[.24,.51],otherShoulder:[.66,.42],otherElbow:[.73,.51],thigh:[.34,.74],otherThigh:[.57,.74],shin:[.28,.86],otherShin:[.60,.85],helmet:[.51,.06],bag:[.13,.43]},
 {head:[.55,.20],neck:[.57,.36],torso:[.46,.49],hand:[.54,.43],other:[.84,.45],shoulder:[.35,.39],elbow:[.33,.51],otherShoulder:[.64,.44],otherElbow:[.70,.54],thigh:[.35,.70],otherThigh:[.60,.70],shin:[.29,.85],otherShin:[.66,.85],helmet:[.54,.06],bag:[.12,.48]},
 {head:[.56,.20],neck:[.57,.35],torso:[.47,.47],hand:[.44,.47],other:[.88,.41],shoulder:[.35,.38],elbow:[.27,.49],otherShoulder:[.68,.37],otherElbow:[.72,.46],thigh:[.42,.70],otherThigh:[.65,.68],shin:[.32,.87],otherShin:[.68,.83],helmet:[.55,.065],bag:[.14,.56]},
 {head:[.56,.22],neck:[.57,.37],torso:[.48,.49],hand:[.33,.49],other:[.88,.46],shoulder:[.34,.41],elbow:[.24,.54],otherShoulder:[.68,.41],otherElbow:[.72,.54],thigh:[.38,.71],otherThigh:[.59,.69],shin:[.30,.83],otherShin:[.58,.83],helmet:[.55,.07],bag:[.14,.49]},
 {head:[.61,.18],neck:[.62,.32],torso:[.55,.44],hand:[.42,.37],other:[.91,.47],shoulder:[.35,.31],elbow:[.26,.44],otherShoulder:[.75,.36],otherElbow:[.79,.45],thigh:[.40,.64],otherThigh:[.65,.65],shin:[.35,.80],otherShin:[.72,.78],helmet:[.61,.06],bag:[.16,.38]},
];
export const characterPose=n=>poses[Math.max(0,Math.min(7,Number(n)||0))];
export function characterParts(n){
 const p=characterPose(n),part=(key,length,tilt=0)=>[...p[key],length,tilt];
 return {head:part('head',.46,-.10),neck:part('neck',.20),torso:part('torso',.34,.05),
  'right upper arm':part('shoulder',.15,.9),'right forearm':part('elbow',.14,.9),'right hand':part('hand',.15,.2),
  'left upper arm':part('otherShoulder',.15,-.9),'left forearm':part('otherElbow',.14,-1.2),'left hand':part('other',.15,-.2),
  'right thigh':part('thigh',.24,.15),'left thigh':part('otherThigh',.24,-.15),'right shin':part('shin',.20),'left shin':part('otherShin',.20,.1)};
}
