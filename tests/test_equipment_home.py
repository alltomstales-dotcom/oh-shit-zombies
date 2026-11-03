import copy
import random
import pytest
from app.game import equipment, home, store
from app.game.hub import Hub
from app.game.sim import Actor, World
from app.models import Player, Survivor, PlayerHome
from tests.test_building_world import setup


def shelter():
    w,a,b=setup();a.lat,a.lng=b.ll(b.rooms[0]['pos'])
    assert home.action(w,a,'home',{'name':'Test shelter'})['ok']
    return w,a,b


def request(a,item,op='deposit',qty=1,key='transfer-001'):
    return dict(item=item,op=op,qty=qty,revision=a.home['revision'],request=key)


def test_bag_counts_mass_and_only_one_back_slot_applies():
    a=Actor(id=1);w=World();first=a.add('schoolbag');second=a.add('rucksack')
    base=w.carry_capacity(a)
    assert equipment.wear(a,first['id'])['ok']
    assert w.carry_capacity(a)==base+6
    equipment.wear(a,second['id'])
    assert w.carry_capacity(a)==base+12 and a.weight()==1.9
    assert not w.act(1,'drop',item=second['id'])['ok']


def test_protection_is_covered_condition_dependent_and_wears():
    a=Actor(id=1);j=a.add('fire_jacket');equipment.wear(a,j['id'])
    class Hit:
        def random(self):return 0
    assert equipment.intercept(a,'torso','bite',Hit()) is j
    assert j['cond']==9
    assert equipment.intercept(a,'left thigh','bite',Hit()) is None
    j['cond']=0
    assert equipment.intercept(a,'torso','bite',Hit()) is None


def test_old_save_defaults_and_new_gear_roundtrip():
    a=store.from_state(Survivor(player_id=1,born=100,state={'items':[]}), 'Old')
    assert a.worn=={} and a.home is None
    a=store.starter(1,'New',100);s=store.to_state(a)
    restored=store.from_state(Survivor(player_id=1,born=100,state=s),'New')
    assert restored.worn==a.worn and 'home' not in s


def test_partial_storage_transfer_preserves_condition_and_retries():
    w,a,b=shelter();row=a.add('bandage',5)
    args=request(a,row['id'],qty=2)
    assert home.action(w,a,'transfer',args)['ok']
    assert a.count('bandage')==3 and a.home['items'][0]['qty']==2
    assert home.action(w,a,'transfer',args)['ok']
    assert a.count('bandage')==3
    assert not home.action(w,a,'transfer',{**args,'qty':1})['ok']
    item=a.home['items'][0]
    assert home.action(w,a,'transfer',request(a,item['id'],'withdraw',1,'withdraw-001'))['ok']
    assert a.count('bandage')==4 and item['qty']==1


def test_storage_rejects_stale_revision_range_capacity_and_worn():
    w,a,b=shelter();row=a.add('water',100)
    assert not home.action(w,a,'transfer',request(a,row['id'],qty=100))['ok']
    shirt=a.add('shirt');equipment.wear(a,shirt['id'])
    assert not home.action(w,a,'transfer',request(a,shirt['id']))['ok']
    stale=request(a,row['id']);stale['revision']-=1
    assert not home.action(w,a,'transfer',stale)['ok']
    a.lat,a.lng=b.ll((-5,-5))
    assert not home.action(w,a,'transfer',request(a,row['id']))['ok']


@pytest.mark.asyncio
async def test_database_atomic_storage_and_new_life_ownership(maker):
    w,a,b=shelter();a.add('water',2)
    async with maker() as s:
        p=Player(id=1,device_token='home-test',name='Tester');s.add(p)
        row=Survivor(player_id=1,born=100,state=store.to_state(a),last_seen=100);s.add(row);await s.commit();sid=row.id
        assert home.action(w,a,'transfer',request(a,a.items[0]['id']))['ok']
        await store.save(s,a,sid,100)
    async with maker() as s:
        row=await s.get(Survivor,sid);h=await s.get(PlayerHome,1)
        restored=store.from_state(row,'Tester')
        assert restored.count('water')==1 and h.state['items'][0]['qty']==1
        row.alive=False;await s.commit()
        fresh,_,_=await store.load_or_create(s,await s.get(Player,1),101)
        assert fresh.count('water')==2
        assert (await s.get(PlayerHome,1)).state['items'][0]['qty']==1


@pytest.mark.asyncio
async def test_failed_commit_never_publishes_inventory_change(maker,monkeypatch):
    h=Hub();w,a,b=shelter();h.world=w
    async with maker() as s:
        p=Player(id=1,device_token='rollback',name='Tester');s.add(p)
        r=Survivor(player_id=1,born=100,state=store.to_state(a));s.add(r);await s.commit();sid=r.id
    from app.game.hub import Conn
    async def send(m):pass
    c=Conn(1,sid,send);h.conns[1]=c;h.clock=lambda:100
    row=a.add('water',2);before=copy.deepcopy(a.home)
    async def failed(*args,**kwargs):raise RuntimeError('simulated DB outage')
    monkeypatch.setattr(store,'save',failed)
    result=await h.act(c,'transfer',request(a,row['id']))
    assert not result['ok'] and w.actors[1].count('water')==2 and w.actors[1].home==before
