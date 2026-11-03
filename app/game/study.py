"""Banked per-life reading and nearby training playback on the real clock."""
from __future__ import annotations
import math
from app.game.content import ITEMS,TUNE
from app.game.progression import SKILLS,award

LESSONS={
 'tv_carpentry':dict(name='Woodworking basics',skill='carpentry',xp=20,seconds=45),
 'tv_first_aid':dict(name='Emergency first aid',skill='first_aid',xp=15,seconds=40),
 'tape_workshop':dict(name='Workshop repairs',skill='metalworking',xp=25,seconds=90,item='tape_workshop'),
 'tape_cooking':dict(name='Safe kitchen survival',skill='cooking',xp=20,seconds=60,item='tape_cooking'),
}

def at_home(world,a):
 b=world.buildings.containing((a.lat,a.lng))
 return bool(a.home and b is not None and b.id==a.home.get('building') and a.floor_level==a.home.get('floor_level',0))

def progress(world,a):
 s=a.study
 if not s:return 0.
 running=world.now-s['since'] if s.get('since') is not None else 0.
 return min(s['need_s'],s['done_s']+max(0.,running))

def _grabbed(world,a):return any(z.alive and z.target==a.id and z.state=='engaged' for z in world.zeds.values())

def television(world,a,oid):
 from app.game import survival
 if a.vehicle_id:return None
 return next((o for o in survival.objects(world,a) if o['id']==oid and o['kind']=='television' and o['hp']>0 and
              survival.in_range(world,a,o)),None)

def can_continue(world,a,s):
 if s.get('kind')=='media':return a.floor_level==s.get('floor',0) and television(world,a,s.get('object')) is not None
 return at_home(world,a)

def name(s):return s.get('name') or ITEMS[s['code']]['name']

def pause(world,a):
 s=a.study
 if s and s.get('since') is not None:
  s['done_s'],s['since'],s['at']=progress(world,a),None,None;a.dirty=True

def update(world,a):
 s=a.study
 if not s or a.dead:return None
 kind=s.get('kind','book');title=name(s)
 if s.get('since') is not None:
  moved=math.hypot((a.lat-s['at'][0])*111320,(a.lng-s['at'][1])*111320*math.cos(math.radians(a.lat)))
  # New media/recipes validate place before granting anything; old manuals retain their prior finish semantics.
  invalid=moved>TUNE['study_leave_m'] or _grabbed(world,a) or (kind!='book' and not can_continue(world,a,s))
  if invalid and (kind!='book' or progress(world,a)<s['need_s']):
   pause(world,a);return f'You put the {title} down. It keeps your place.' if kind=='book' else f'Paused {title}. Your place is kept.'
 if kind!='book' and s.get('since') is None:return None
 if progress(world,a)>=s['need_s']:
  if kind=='media':
   lesson=s['lesson'];spec=LESSONS[lesson]
   if lesson not in a.learned_media:
    a.learned_media.append(lesson);award(a,spec['skill'],spec['xp'])
   message=f'Finished {title}. This survivor has learned this lesson; replay gives no more XP.'
  elif kind=='recipe':
   if s['knowledge'] not in a.knowledge:a.knowledge.append(s['knowledge'])
   message=f'Finished {title}. New recipes are available at your workbench.'
  else:
   if s['skill'] not in a.studied:a.studied.append(s['skill'])
   message=f"You finished the {title}. {SKILLS[s['skill']][0]} now grows twice as fast for this survivor."
  a.study=None;a.dirty=True;return message
 return None

def action(world,a,op='read',item=None,object=None,lesson=None,**_):
 if a.dead:return {'ok':False,'why':'dead'}
 if op=='stop':
  if not a.study or a.study.get('since') is None:return {'ok':False,'why':'you are not studying'}
  pause(world,a);return {'ok':True,'message':'Paused. Your place is kept.'}
 if op not in ('read','watch','resume'):return {'ok':False,'why':'unknown learning action'}
 if a.channel or a.pending_work:return {'ok':False,'why':'finish or cancel your work first'}
 if a.vehicle_id:return {'ok':False,'why':'exit the vehicle before studying'}
 if _grabbed(world,a):return {'ok':False,'why':'escape the zombies first'}
 s=a.study
 if op=='watch':
  spec=LESSONS.get(lesson)
  if spec is None:return {'ok':False,'why':'choose a training lesson'}
  if lesson in a.learned_media:return {'ok':False,'why':'this survivor already learned this lesson'}
  if not television(world,a,object):return {'ok':False,'why':'approach a working television on this floor'}
  if spec.get('item') and not a.count(spec['item']):return {'ok':False,'why':'find the matching training tape'}
  if s and (s.get('lesson')!=lesson or s.get('object')!=object):return {'ok':False,'why':'finish your current reading or lesson first'}
  if not s:
   s=a.study=dict(kind='media',code=spec.get('item','radio'),name=spec['name'],lesson=lesson,skill=spec['skill'],object=object,
                  floor=a.floor_level,need_s=spec['seconds'],done_s=0.,since=None,at=None)
 else:
  if s and item==s.get('item'):item=None # identical start retry; the magazine/manual is already open
  if item is not None:
   row=a.item(item);spec=ITEMS.get(row['code'],{}) if row else {};skill=spec.get('teaches');knowledge=spec.get('knowledge')
   if not skill and not knowledge:return {'ok':False,'why':'that is not something to study'}
   if (skill and skill in a.studied) or (knowledge and knowledge in a.knowledge):return {'ok':False,'why':'this survivor already learned it'}
   if s and s['code']!=row['code']:return {'ok':False,'why':'finish your current reading or lesson first'}
   if not at_home(world,a):return {'ok':False,'why':'read at home, inside your own building'}
   if not s:
    code=row['code'];assert a.take(code,1)
    s=a.study=dict(kind='recipe' if knowledge else 'book',code=code,item=item,skill=skill,knowledge=knowledge,
                   need_s=spec.get('study_s',TUNE['study_s']),done_s=0.,since=None,at=None)
  if not s:return {'ok':False,'why':'choose a manual or magazine from your pack, or a nearby television'}
 if not can_continue(world,a,s):return {'ok':False,'why':'return to the television' if s.get('kind')=='media' else 'read at home, inside your own building'}
 if s.get('since') is None:s['since'],s['at']=world.now,[a.lat,a.lng]
 a.sprinting=False;a.dirty=True
 left=s['need_s']-progress(world,a)
 return {'ok':True,'message':f'{name(s)}: {max(1,round(left))}s remaining. Move or Stop to pause; your place is kept.'}

def view(world,a):
 s=a.study
 if not s:return None
 reading=s.get('since') is not None;left=s['need_s']-progress(world,a)
 return dict(kind=s.get('kind','book'),skill=s['skill'],code=s['code'],name=name(s),reading=reading,
             ready=round(world.now+left) if reading else None,left_s=None if reading else round(left),
             can_read=can_continue(world,a,s),object=s.get('object'))

def catalog(a):
 return [{**spec,'id':lid,'learned':lid in a.learned_media,'available':not spec.get('item') or bool(a.count(spec['item']))} for lid,spec in LESSONS.items()]
