"""Persistent parked cars, conserved cargo and bounded server driving."""
import copy
import math
from sqlalchemy import select,update
from app.models import WorldVehicle
from app.game import bases
from app.game.content import ITEMS
from app.game.survival import shift,dist
from app.geo import cell_of,_decode_bbox
from app.rng import seeded

class VehicleConflict(RuntimeError):
    pass

KINDS={'car':dict(name='Abandoned car',capacity=45.,seats=2,max_speed=14.,accel=3.5),
       'van':dict(name='Hauling van',capacity=100.,seats=4,max_speed=11.,accel=2.5)}

def stock(v):return {k:copy.deepcopy(x) for k,x in v.items() if not k.startswith('_')}
def permitted(a,v,drive=False):
    return v.get('owner') is None or v['owner']==a.id or (v['owner']==bases.owner(a) and (not drive or bases.can_build(a)))
def seated(a,v):return next((i for i,s in enumerate(v['seats']) if s and s['player']==a.id and s['life']==a.life_id),None)
def reachable(w,a,v):return not a.floor_level and dist([a.lat,a.lng],[v['lat'],v['lng']])<=3.5 and w.buildings.clear((a.lat,a.lng),(v['lat'],v['lng']))

def footprint_clear(w,p,heading,kind):
    half=2.7 if kind=='van' else 2.2
    front=shift(*p,math.cos(heading)*half,math.sin(heading)*half)
    back=shift(*p,-math.cos(heading)*half,-math.sin(heading)*half)
    return w.buildings.containing(p) is None and w.buildings.clear(back,front,radius=1.1)

def seeds(w,a):
    if a.floor_level or not a.placed_at or a.location_loading_until:return []
    cell=cell_of(a.lat,a.lng,7);la0,la1,ln0,ln1=_decode_bbox(cell)
    out=[]
    for i,kind in enumerate(KINDS):
        vid=f'vehicle:{cell}:{i}';rng=seeded(vid)
        point=None
        for _ in range(60):
            p=[rng.uniform(la0,la1),rng.uniform(ln0,ln1)]
            if w.buildings.containing(p) is None and w.buildings.clear(p,p,radius=3.0) and all(dist(p,[v['lat'],v['lng']])>8 for v in out):point=p;break
        if point:
            out.append(dict(id=vid,kind=kind,lat=point[0],lng=point[1],heading=rng.uniform(-math.pi,math.pi),speed=0.,fuel=12.,tank=60.,engine=False,
                            hull=80.,motor=80.,tires=90.,owner=None,seats=[None]*KINDS[kind]['seats'],capacity=KINDS[kind]['capacity'],
                            items=[{'id':1,'code':'fuel','qty':1,'cond':None},{'id':2,'code':'scrap','qty':2,'cond':None}],next_item=3,revision=1,receipts=[],_version=0))
    return out

async def save(s,v):
    expected=v.get('_version',0);state=stock(v)
    if expected==0:
        s.add(WorldVehicle(id=v['id'],revision=1,state=state));version=1
    else:
        version=expected+1
        res=await s.execute(update(WorldVehicle).where(WorldVehicle.id==v['id'],WorldVehicle.revision==expected).values(state=state,revision=version).execution_options(synchronize_session=False))
        if res.rowcount!=1:raise VehicleConflict('vehicle changed; retry')
    return version

def restore(row):return {**copy.deepcopy(row.state),'_version':row.revision}
async def load(s):
    result={}
    for row in (await s.execute(select(WorldVehicle))).scalars():
        v=restore(row)
        if any(v['seats']) or v['engine'] or v['speed']:
            v.update(seats=[None]*len(v['seats']),engine=False,speed=0.);v['revision']+=1
            v['_version']=await save(s,v)
        result[v['id']]=v
    await s.commit();return result

def release(a,v):
    seat=seated(a,v)
    if seat is None:a.vehicle_id=None;return
    v['seats'][seat]=None
    if seat==0:v.update(engine=False,speed=0.)
    v['revision']+=1;a.vehicle_id=None;a.speed=0.;a.raw=(a.lat,a.lng,1.);a.dirty=True

def exit_point(w,a,v):
    for side in (-1,1):
        for back in (0,-2,2):
            p=shift(v['lat'],v['lng'],side*2.2*math.sin(v['heading'])+back*math.cos(v['heading']),-side*2.2*math.cos(v['heading'])+back*math.sin(v['heading']))
            if w.buildings.containing(p) is None and w.buildings.clear((v['lat'],v['lng']),p):return p
    return None

def action(w,a,v,args,now):
    if a.dead:return {'ok':False,'why':'dead'}
    if a.floor_level:return {'ok':False,'why':'vehicles are outside on the ground floor'}
    op=args.get('op');seat=seated(a,v)
    if op=='exit':
        if seat is None:return {'ok':False,'why':'you are not in this vehicle'}
        if abs(v['speed'])>.8:return {'ok':False,'why':'brake before leaving the vehicle'}
        point=exit_point(w,a,v)
        if point is None:return {'ok':False,'why':'both exits are blocked; move to clear ground'}
        release(a,v);a.lat,a.lng=point;a.raw=(*point,1.)
        return {'ok':True,'lat':a.lat,'lng':a.lng,'message':'Outside the vehicle.'}
    if not permitted(a,v,drive=op in ('enter_driver','engine','drive')):return {'ok':False,'why':'this vehicle belongs to another base; select that base with the required access'}
    if op in ('enter_driver','enter_passenger'):
        if a.vehicle_id and a.vehicle_id!=v['id']:return {'ok':False,'why':'leave your current vehicle first'}
        if seat is not None and ((op=='enter_driver' and seat==0) or (op=='enter_passenger' and seat>0)):
            return {'ok':True,'replay':True,'seat':seat,'lat':a.lat,'lng':a.lng}
        if a.channel or a.pending_work:return {'ok':False,'why':'finish or cancel your work first'}
        if not reachable(w,a,v):return {'ok':False,'why':'approach the vehicle'}
        if abs(v['speed'])>.8:return {'ok':False,'why':'wait for the vehicle to stop'}
        target=0 if op=='enter_driver' else next((i for i in range(1,len(v['seats'])) if not v['seats'][i]),None)
        if target is None or v['seats'][target]:return {'ok':False,'why':'that seat is occupied'}
        if seat is not None:
            v['seats'][seat]=None
            if seat==0:v['engine']=False
        if v['owner'] is None:v['owner']=bases.owner(a)
        v['seats'][target]={'player':a.id,'life':a.life_id};v['revision']+=1
        a.vehicle_id=v['id'];a.lat,a.lng=v['lat'],v['lng'];a.raw=None;a.speed=0.;a.sprinting=False;a.quiet=False;a.dirty=True
        from app.game import study
        study.pause(w,a)
        return {'ok':True,'seat':target,'lat':a.lat,'lng':a.lng,'message':'Driver seat. Start the engine, then steer.' if target==0 else 'Passenger seat.'}
    if op=='engine':
        if seat!=0:return {'ok':False,'why':'use the driver seat'}
        if not v['engine'] and (v['fuel']<=0 or v['motor']<=0 or v['hull']<=0):return {'ok':False,'why':'this vehicle needs fuel or repair'}
        v['engine']=not v['engine'];v['speed']=0.;v['revision']+=1
        return {'ok':True,'message':'Engine started.' if v['engine'] else 'Engine stopped.'}
    if op=='fuel':
        if not reachable(w,a,v) or seat is not None:return {'ok':False,'why':'stand beside the parked vehicle to refuel'}
        if v['engine'] or abs(v['speed'])>.8:return {'ok':False,'why':'turn the engine off before refueling'}
        if v['fuel']>v['tank']-10:return {'ok':False,'why':'the tank cannot hold another fuel can'}
        if not a.take('fuel',1):return {'ok':False,'why':'find a fuel can'}
        v['fuel']+=10;v['revision']+=1;a.dirty=True
        return {'ok':True,'message':'Added 10 fuel units.'}
    if op in ('deposit','withdraw'):
        rid=str(args.get('request',''));signature=[a.id,op,args.get('item'),args.get('qty'),args.get('revision')]
        if not 8<=len(rid)<=80:return {'ok':False,'why':'missing cargo transfer identifier'}
        for receipt in v['receipts']:
            if receipt['id']==rid:return copy.deepcopy(receipt['result']) if receipt['signature']==signature else {'ok':False,'why':'transfer identifier was already used'}
        if args.get('revision')!=v['revision']:return {'ok':False,'why':'cargo changed; try again'}
        if abs(v['speed'])>.8 or not (seat is not None or reachable(w,a,v)):return {'ok':False,'why':'approach the stopped vehicle'}
        src=a.items if op=='deposit' else v['items'];item=next((x for x in src if x['id']==args.get('item')),None);qty=args.get('qty',1)
        if not isinstance(qty,int) or isinstance(qty,bool) or not item or not 1<=qty<=item['qty']:return {'ok':False,'why':'choose a quantity you have'}
        if op=='deposit':
            if item['id'] in a.worn.values():return {'ok':False,'why':'take off worn equipment before storing it'}
            if sum(ITEMS[x['code']]['w']*x['qty'] for x in v['items'])+ITEMS[item['code']]['w']*qty>v['capacity']+.001:return {'ok':False,'why':'vehicle cargo is full'}
            target=next((x for x in v['items'] if x['code']==item['code'] and x['cond']==item['cond'] and 'stack' in ITEMS[item['code']]),None)
            if target:target['qty']+=qty
            else:v['items'].append({**item,'id':v['next_item'],'qty':qty});v['next_item']+=1
        else:
            if a.weight()+ITEMS[item['code']]['w']*qty>w.carry_capacity(a)*1.25+.001:return {'ok':False,'why':'too heavy; retrieve fewer items'}
            a.add(item['code'],qty,item['cond'])
        item['qty']-=qty
        if not item['qty']:
            src.remove(item)
            if op=='deposit' and a.hands==item['id']:a.hands=None
        v['revision']+=1;a.dirty=True
        result={'ok':True,'message':'Cargo stored.' if op=='deposit' else 'Cargo retrieved.'}
        v['receipts']=(v['receipts']+[{'id':rid,'signature':signature,'result':result}])[-64:]
        return result
    return {'ok':False,'why':'choose a vehicle action'}

def control(w,a,v,args,now):
    if a.dead or seated(a,v)!=0 or a.vehicle_id!=v['id'] or not permitted(a,v,True):return {'ok':False,'why':'use your driver seat'}
    try:e,n,throttle=(float(args.get(k,0)) for k in ('east','north','throttle'))
    except (TypeError,ValueError):return {'ok':False,'why':'invalid driving input'}
    if not all(math.isfinite(x) for x in (e,n,throttle)):return {'ok':False,'why':'invalid driving input'}
    length=math.hypot(e,n)
    w.vehicle_controls[v['id']]={'east':e/max(1,length),'north':n/max(1,length),'throttle':max(-1.,min(1.,throttle)),'at':now}
    return {'ok':True}

def step(w,dt,now):
    for v in w.vehicles.values():
        occupied=[]
        for i,s in enumerate(v['seats']):
            if not s:continue
            a=w.actors.get(s['player'])
            if a is None or a.dead or a.life_id!=s['life'] or a.vehicle_id!=v['id'] or not permitted(a,v,i==0):
                v['seats'][i]=None;v['revision']+=1;w.vehicle_dirty.add(v['id'])
                if a:a.vehicle_id=None;a.raw=(a.lat,a.lng,1.);a.dirty=True
            else:occupied.append(a)
        driver=next((a for a in occupied if seated(a,v)==0 and a.connected),None)
        if driver is None:
            if v['engine'] or v['speed']:w.vehicle_dirty.add(v['id'])
            v['engine']=False;v['speed']=0.
        if v['engine'] and v['fuel']>0 and v['motor']>0 and v['hull']>0:
            spec=KINDS[v['kind']];c=w.vehicle_controls.get(v['id'],{});fresh=now-c.get('at',-99)<=.7
            throttle=c.get('throttle',0) if fresh else 0.;e,n=c.get('east',0),c.get('north',0)
            if fresh and math.hypot(e,n)>.1:
                want=math.atan2(n,e);turn=(want-v['heading']+math.pi)%(2*math.pi)-math.pi
                v['heading']+=max(-dt*1.8,min(dt*1.8,turn))
            target=(spec['max_speed'] if throttle>=0 else 3.)*throttle*(min(v['motor'],v['tires'])/100)
            change=(spec['accel'] if throttle else 9.)*dt
            v['speed']+=max(-change,min(change,target-v['speed']))
            before=[v['lat'],v['lng']];distance=v['speed']*dt
            for _ in range(max(1,math.ceil(abs(distance)/.4))):
                length=distance/max(1,math.ceil(abs(distance)/.4));p=shift(v['lat'],v['lng'],math.cos(v['heading'])*length,math.sin(v['heading'])*length)
                blocked=not footprint_clear(w,p,v['heading'],v['kind']) or not w.buildings.clear((v['lat'],v['lng']),p,radius=1.1)
                blocked|=any(other['id']!=v['id'] and dist(p,[other['lat'],other['lng']])<2.8 for other in w.vehicles.values())
                if blocked:
                    impact=abs(v['speed']);v['speed']=0.
                    if impact>1 and now-v.get('_impact_at',-99)>1:
                        v['hull']=max(0,v['hull']-impact*1.2);v['motor']=max(0,v['motor']-impact*.2);v['_impact_at']=now
                        if driver:w._ev(driver,'work',message='Vehicle collision. Brake and steer away.')
                    break
                v['lat'],v['lng']=p
                for z in list(w.zeds.values()):
                    if not z.alive or dist(p,[z.lat,z.lng])>1.6 or abs(v['speed'])<3 or z.state in ('down','rising'):continue
                    z.hp-=min(25,abs(v['speed'])*2);v['hull']=max(0,v['hull']-2);v['motor']=max(0,v['motor']-.2)
                    if z.hp<=0:w._kill(z,driver,skill='vehicle')
                    else:z.state='down';z.t_state=now+4;z.target=None
            v['fuel']=max(0,v['fuel']-dt*(.004+abs(v['speed'])*.0015));w.vehicle_dirty.add(v['id'])
            if now-v.get('_noise_at',0)>=3:
                w.noise(v['lat'],v['lng'],45+abs(v['speed'])*3,driver);v['_noise_at']=now
        else:
            v['engine']=False;v['speed']=0.
        for a in occupied:
            a.lat,a.lng=v['lat'],v['lng'];a.raw=None;a.speed=abs(v['speed']);a.heading=(90-math.degrees(v['heading']))%360;a.dirty=True

def view(w,a):
    if a.floor_level:return []
    result=[]
    for v in w.vehicles.values():
        at=[v['lat'],v['lng']];own=a.vehicle_id==v['id'];distance=dist([a.lat,a.lng],at)
        if not own and (distance>w.sight_m(a) or not w.visible((a.lat,a.lng),at)):continue
        allowed=permitted(a,v);seat=seated(a,v)
        result.append({k:copy.deepcopy(v[k]) for k in ('id','kind','lat','lng','heading','speed','fuel','tank','engine','hull','motor','tires','capacity','revision')}|{
            'name':KINDS[v['kind']]['name'],'reachable':reachable(w,a,v),'allowed':allowed,'can_drive':permitted(a,v,True),'seat':seat,
            'occupied':[bool(s) for s in v['seats']], 'items':copy.deepcopy(v['items']) if allowed and (own or reachable(w,a,v)) else [],
            'weight':round(sum(ITEMS[x['code']]['w']*x['qty'] for x in v['items']),2) if allowed else None})
    return result

def intercept(w,a,damage):
    v=w.vehicles.get(a.vehicle_id)
    if v is None or v['hull']<=10:return False
    v['hull']=max(0,v['hull']-damage);w.vehicle_dirty.add(v['id'])
    a.hp-=damage*.05;a.panic=min(100,a.panic+4);a.last_threat=w.now;a.dirty=True
    w._ev(a,'work',message='Zombies are battering the vehicle. Keep moving or find a safe exit.')
    return True
