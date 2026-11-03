import copy
import pytest
from app.game import study,survival,store,bases
from app.game.sim import World,Actor,Zed
from tests.test_equipment_home import shelter


def tv_setup():
 w,a,b=shelter();tv=next(o for o in survival.objects(w,a) if o['kind']=='television');a.lat,a.lng=tv['lat'],tv['lng'];a.raw=None
 return w,a,b,tv


def test_magazine_unlocks_new_recipe_once_and_existing_recipes_stay_available():
 w,a,b=shelter();book=a.add('mag_repair');before=a.xp
 assert w.act(a.id,'study',item=book['id'])['ok'];assert w.act(a.id,'study',item=book['id'])['ok']
 assert not a.count('mag_repair');w.now+=45;assert study.update(w,a)
 assert a.knowledge==['vehicle_kits'] and a.xp==before
 again=a.add('mag_repair');assert not w.act(a.id,'study',item=again['id'])['ok'] and a.count('mag_repair')==1
 recipes=survival.view(w,a)['recipes'];assert not recipes['repair_kit']['locked'] and recipes['reinforced_vest']['locked']
 assert all(not r['locked'] for key,r in recipes.items() if key not in ('repair_kit','reinforced_vest'))
 # Knowledge is checked by server at both start and finish.
 a.add('scrap',2);a.add('cloth',1);a.add('hammer');assert not w.act(a.id,'work',op='craft',recipe='reinforced_vest')['ok']


def test_training_is_once_per_life_and_sampling_does_not_multiply_xp():
 w,a,b,tv=tv_setup();start=w.now
 args={'op':'watch','object':tv['id'],'lesson':'tv_carpentry'}
 assert w.act(a.id,'study',**args)['ok'];assert w.act(a.id,'study',**args)['ok']
 for i in range(10):assert study.view(w,a)['ready']==start+45
 w.now=start+45;assert study.update(w,a);xp=a.xp
 assert xp==20 and a.learned_media==['tv_carpentry']
 assert not w.act(a.id,'study',**args)['ok'];assert study.update(w,a) is None and a.xp==xp
 fresh=Actor(id=2,lat=a.lat,lng=a.lng);w.actors[fresh.id]=fresh
 assert w.act(fresh.id,'study',**args)['ok'] # each survivor learns independently


def test_media_pauses_for_movement_floor_and_destroyed_fixture_and_keeps_progress():
 w,a,b,tv=tv_setup();t=w.now;args={'op':'watch','object':tv['id'],'lesson':'tv_first_aid'}
 assert w.act(a.id,'study',**args)['ok'];w.now=t+8;a.lat+=.001
 assert study.update(w,a) and a.study['since'] is None and a.study['done_s']==8
 a.lat,a.lng=tv['lat'],tv['lng'];assert w.act(a.id,'study',op='resume')['ok']
 w.now=t+15;a.floor_level=1;assert study.update(w,a) and not a.learned_media
 a.floor_level=0;assert w.act(a.id,'study',op='resume')['ok']
 a.home['mutations'][tv['id']]={**tv,'hp':0};w.now=t+60
 assert study.update(w,a) and not a.learned_media and a.study['since'] is None
 assert not w.act(a.id,'study',op='resume')['ok']
 assert study.update(w,a) is None and not a.learned_media


def test_tapes_require_real_item_are_reusable_but_cannot_repeat_reward():
 w,a,b,tv=tv_setup();args={'op':'watch','object':tv['id'],'lesson':'tape_workshop'}
 assert not w.act(a.id,'study',**args)['ok'];a.add('tape_workshop')
 assert w.act(a.id,'study',**args)['ok'];w.now+=90;study.update(w,a)
 assert a.count('tape_workshop')==1 and a.skill_xp['metalworking']==25
 assert not w.act(a.id,'study',**args)['ok']

@pytest.mark.asyncio
async def test_atomic_learning_start_failure_retry_reload_and_completion(maker,monkeypatch):
 from tests.test_vehicles import setup_hub
 h,p,c,a,v=await setup_hub(maker)
 # Use a normal building geometry fixture; the transactional failure is confined to this DB.
 w,template,b,tv=tv_setup();h.world.buildings=w.buildings
 a.lat,a.lng=tv['lat'],tv['lng'];a.home=copy.deepcopy(template.home);a.raw=None;bases.publish(h.world,a)
 book=a.add('mag_repair');original=store.save
 async def fail(*args,**kwargs):raise RuntimeError('learning save fixture')
 monkeypatch.setattr(store,'save',fail)
 assert not (await h.act(c,'study',{'item':book['id']}))['ok'];assert a.count('mag_repair')==1 and a.study is None
 monkeypatch.setattr(store,'save',original)
 assert (await h.act(c,'study',{'item':book['id']}))['ok']
 assert (await h.act(c,'study',{'item':book['id']}))['ok']
 async with maker() as s:
  loaded,_,_=await store.load_or_create(s,p,100);await bases.bind(s,h.world,loaded)
  assert loaded.study and loaded.count('mag_repair')==0 and not loaded.knowledge
  w.now=145;told=study.update(w,loaded);assert loaded.knowledge==['vehicle_kits'],(told,loaded.study,loaded.lat,loaded.lng,loaded.home);await store.save(s,loaded,c.survivor_id,145)
 async with maker() as s:
  again,_,_=await store.load_or_create(s,p,150);assert again.knowledge==['vehicle_kits'] and again.study is None

@pytest.mark.asyncio
async def test_pending_media_reward_is_saved_before_publication_and_cold_retry_is_once(maker,monkeypatch):
 from tests.test_vehicles import setup_hub
 h,p,c,a,v=await setup_hub(maker);w,template,b,tv=tv_setup();h.world.buildings=w.buildings
 a.lat,a.lng=tv['lat'],tv['lng'];a.raw=None;bases.publish(h.world,a)
 assert (await h.act(c,'study',{'op':'watch','object':tv['id'],'lesson':'tv_carpentry'}))['ok']
 a=h.world.actors[p.id];h.world.step(145)
 assert a.pending_learning and not a.learned_media and a.skill_xp.get('carpentry',0)==0
 original=store.save
 async def fail(*args,**kwargs):raise RuntimeError('reward save fixture')
 monkeypatch.setattr(store,'save',fail)
 assert await h._commit_learning(c,a,145) is a and not a.learned_media
 monkeypatch.setattr(store,'save',original)
 a=await h._commit_learning(c,a,145);assert a.learned_media==['tv_carpentry'] and a.skill_xp['carpentry']==20
 async with maker() as s:
  loaded,_,_=await store.load_or_create(s,p,150)
  assert loaded.study is None and loaded.learned_media==['tv_carpentry'] and loaded.skill_xp['carpentry']==20
  assert study.update(w,loaded) is None


def test_recipe_knowledge_checked_again_at_finish_and_materials_conserved():
 from tests.test_survival_work import complete
 w,a,b=shelter();b.type='garage';bench=next(o for o in survival.objects(w,a) if o['kind']=='workbench')
 a.lat,a.lng=bench['lat'],bench['lng'];a.raw=None;a.add('scrap',4);a.add('cloth',2);a.add('hammer');a.knowledge=['vehicle_kits']
 assert w.act(a.id,'work',op='craft',recipe='repair_kit')['ok'];channel=copy.deepcopy(a.channel);a.channel=None;a.knowledge=[];w.now=channel['ends'];survival.finish(w,a,channel)
 assert a.count('repair_kit')==0 and a.count('scrap')==4 and a.count('cloth')==2
 a.knowledge=['vehicle_kits'];complete(w,a,op='craft',recipe='repair_kit')
 assert a.count('repair_kit')==1 and a.count('scrap')==2 and a.count('cloth')==1


def test_boarding_vehicle_pauses_learning_instead_of_discarding_progress():
 from app.game import vehicles
 from tests.test_vehicles import setup_world
 w,a,v=setup_world();a.study=dict(kind='recipe',code='mag_repair',skill=None,knowledge='vehicle_kits',need_s=45,done_s=0.,since=92.,at=[a.lat,a.lng])
 assert vehicles.action(w,a,v,{'op':'enter_driver'},100)['ok']
 assert a.study['since'] is None and a.study['done_s']==8
 assert not study.action(w,a,op='resume')['ok']
