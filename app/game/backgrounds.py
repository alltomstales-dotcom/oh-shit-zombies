"""A durable, bounded new-life background; never a living-character respec."""
from app.game.content import ITEMS
from app.game.progression import threshold

OCCUPATIONS={
 'survivor':dict(name='Survivor',skills={},gear=[],description='No starting specialism; learn everything through use.'),
 'generalist':dict(name='Generalist',skills={'fitness':1,'cooking':1},gear=[('snack',1)],description='Fitness and Cooking start at level 1. Extra snack.'),
 'medic':dict(name='Medic',skills={'first_aid':1,'cooking':1},gear=[('disinfectant',1)],description='First aid and Cooking start at level 1. Disinfectant.'),
 'carpenter':dict(name='Carpenter',skills={'carpentry':1,'scavenging':1},gear=[('nails',6)],description='Carpentry and Scavenging start at level 1. Six nails.'),
 'mechanic':dict(name='Mechanic',skills={'metalworking':1,'mining':1},gear=[('scrap',2)],description='Metalworking and Mining start at level 1. Two scrap.'),
 'scout':dict(name='Scout',skills={'foraging':1,'scavenging':1},gear=[('water',1)],description='Foraging and Scavenging start at level 1. Extra water.'),
 'firefighter':dict(name='Firefighter',skills={'fitness':1,'melee':1},gear=[('gloves',1)],description='Fitness and Melee start at level 1. Leather gloves (wear them from Pack).'),
}
TRAITS={
 'balanced':dict(name='Balanced',description='No bonuses or penalties.'),
 'nimble':dict(name='Nimble',description='Move 8% faster; carry 1kg less.',pace=1.08,carry=-1.),
 'sturdy':dict(name='Sturdy',description='Carry 1.5kg more; footsteps carry 15% further.',carry=1.5,noise=1.15),
 'steady':dict(name='Steady',description='Panic rises 20% slower; passive stamina recovery is 10% slower.',panic=.8,regen=.9),
}

def catalog():
 return {'occupations':[{'id':k,'name':v['name'],'description':v['description']} for k,v in OCCUPATIONS.items()],
         'traits':[{'id':k,'name':v['name'],'description':v['description']} for k,v in TRAITS.items()]}

def factor(a,key,default=1.):
 return TRAITS.get((a.background or {}).get('trait'),{}).get(key,default)

def choose(a,occupation='generalist',trait='balanced',now=0):
 if a.dead:return {'ok':False,'why':'choose a background for your new survivor'}
 if occupation not in OCCUPATIONS or trait not in TRAITS:return {'ok':False,'why':'choose a listed occupation and trait'}
 if a.background is not None:
  same=a.background.get('occupation')==occupation and a.background.get('trait')==trait
  return {'ok':True,'replay':True,'background':view(a)} if same else {'ok':False,'why':'this survivor already has a background; choose again for a new life'}
 if a.placed_at or a.lat or a.lng or a.xp or a.walked_m or a.kills:
  return {'ok':False,'why':'choose your background before this survivor starts'}
 spec=OCCUPATIONS[occupation]
 for skill,rank in spec['skills'].items():a.skill_xp[skill]=max(a.skill_xp.get(skill,0),threshold(rank))
 for code,qty in spec['gear']:a.add(code,qty,6 if 'cond' in ITEMS[code] else None)
 a.background={'occupation':occupation,'trait':trait,'chosen_at':now,'rule':1};a.dirty=True
 return {'ok':True,'background':view(a)}

def view(a):
 if a.background is None:return None
 job=OCCUPATIONS.get(a.background.get('occupation'),OCCUPATIONS['survivor']);trait=TRAITS.get(a.background.get('trait'),TRAITS['balanced'])
 return {'occupation':a.background.get('occupation'),'trait':a.background.get('trait'),'name':job['name'],
         'description':job['description'],'trait_name':trait['name'],'trait_description':trait['description']}
