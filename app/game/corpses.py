"""Shared bodies: sparse look-tied supplies, bounded snapshots, atomic transfers."""
import copy
import uuid

from sqlalchemy import delete, select, update

from app.game.content import ITEMS, ZED_VARIANTS
from app.models import WorldCorpse, ZedDead
from app.rng import seeded

VIEW_LIMIT = 24
REACH_M = 2.5
RECOVERY_S = 72 * 3600
# A zombie's body rots away after this long. It used to last until the end of the day's spawn window,
# up to 24 hours, and where survivors keep dying (a start city's centre) hundreds piled up, each one
# checked for line of sight in every frame of everyone nearby. A survivor's own pack still keeps 72 hours.
ZOMBIE_BODY_S = 30 * 60


def survivor(a, now):
    """One durable pack per life. Never recreate stock from a dead save."""
    if a.remains is None:
        now=(a.death or {}).get('t',now)
        cid = f'survivor:{a.id}:{a.life_id}' if a.life_id else 'survivor:' + uuid.uuid4().hex
        a.remains = {'id':cid,'lat':a.lat,'lng':a.lng,'kind':'survivor','variant':0,
                     'name':a.name,'owner':a.id,'floor_level':a.floor_level,
                     'floor_building':a.floor_building,'until':now+RECOVERY_S,
                     'items':copy.deepcopy(a.items),'searched':False,'revision':1}
        a.items=[];a.hands=None;a.worn={}
        if a.death is not None:
            a.death.update(corpse=cid,recover_until=now+RECOVERY_S,
                           floor_level=a.floor_level,floor_building=a.floor_building)
        a.dirty=True
    return a.remains


def allowed(a, body):
    return body.get('owner') in (None,a.id)


def create(world, z):
    from app.game.sim import Actor
    until = world.spawner.expires(world.now) if world.spawner else world.now + 86400
    until = min(until, world.now + ZOMBIE_BODY_S)
    # Director IDs restart their sequence on app replacement. Bodies must not.
    cid = 'body:' + (uuid.uuid4().hex if z.temp else z.id + ':' + str(int(until)))
    rng = seeded(cid)
    stock = Actor(id=0)
    # Looks mirror ZED_ART in the client: shambler4 chef,1 scrubs,2 builder,14 firefighter.
    # Most bodies offer nothing, or one piece of cloth; no guaranteed equipment.
    special = {1:'bandage',2:'helmet',4:'knife',7:'shirt',14:'fire_jacket'} if z.kind == 'shambler' else {}
    code = special.get(z.variant % ZED_VARIANTS)
    roll = rng.random()
    if code and roll < .12:
        stock.add(code, 1, rng.randint(2, 5) if 'cond' in ITEMS[code] else None)
    elif roll < .22:
        stock.add('cloth', 1)
    return {'id':cid, 'lat':z.lat, 'lng':z.lng, 'kind':z.kind, 'variant':z.variant,
            'floor_level':world._level_key[1] if world._level_key else 0,'floor_building':world._level_key[0] if world._level_key else None,'until':until, 'items':stock.items, 'searched':False, 'revision':1}


def ready(world, body):
    return body['until'] > world.now and (
        not getattr(world, 'durable_corpses', False) or body['id'] in world.corpse_ready)


def reachable(world, a, body):
    from app.game.sim import dist_m
    return (body.get('floor_level',0)==a.floor_level and (not a.floor_level or body.get('floor_building')==a.floor_building) and ready(world, body) and dist_m(a.lat,a.lng,body['lat'],body['lng']) <= REACH_M
            and world.buildings.clear((a.lat,a.lng),(body['lat'],body['lng'])))


def visible(world, a):
    from app.game.sim import dist_m
    sight = world.sight_m(a)
    near = []
    box = sight / 111320.0
    for b in world.corpses.values():
        if abs(b['lat'] - a.lat) > box:          # most bodies are nowhere near: skip the distance sum
            continue
        d = dist_m(a.lat,a.lng,b['lat'],b['lng'])
        if d <= sight and ready(world,b):
            near.append((d,b['id'],b))
    # Nearest first, and stop at the limit: the wall test is the costly part, and only VIEW_LIMIT are shown.
    candidates = []
    for d,cid,b in sorted(near, key=lambda c: (c[0], c[1])):
        if world.visible((a.lat,a.lng),(b['lat'],b['lng'])):
            candidates.append((d,cid,b))
            if len(candidates) >= VIEW_LIMIT:
                break
    return [{k:copy.deepcopy(b[k]) for k in ('id','lat','lng','kind','variant','searched','revision')} |
            {'name':b.get('name'),'own':b.get('owner')==a.id,'recover_until':b['until'] if b.get('owner') else None,
             'can_loot':allowed(a,b),'reachable':reachable(world,a,b), 'items':copy.deepcopy(b['items']) if b['searched'] and allowed(a,b) else None}
            for _,_,b in candidates]


def reveal(a, body):
    from app.game.progression import award
    if not body['searched']:
        body['searched'] = True
        body['revision'] += 1
        award(a,'scavenging',5)
    a.pending_body_search = None
    a.events.append({'e':'body_found','corpse':body['id']})
    a.dirty = True


def take(world, a, body, args):
    rid = str(args.get('request',''))
    signature = ['corpse'] + [args.get(k) for k in ('corpse','item','qty','revision')]
    if a.dead:return {'ok':False,'why':'dead'}
    if not 8 <= len(rid) <= 80:return {'ok':False,'why':'missing loot transfer identifier'}
    for receipt in a.loot_receipts:
        if receipt['id'] == rid:
            return copy.deepcopy(receipt['result']) if receipt['signature'] == signature else {
                'ok':False,'why':'loot transfer identifier already used'}
    if not body or not body['searched']:return {'ok':False,'why':'search this body first'}
    if not allowed(a,body):return {'ok':False,'why':'this recovery pack belongs to another survivor'}
    if args.get('revision') != body['revision']:return {'ok':False,'why':'body changed; try again'}
    if a.channel or world.now < a.busy_until - .05:return {'ok':False,'why':'finish your current action first'}
    if any(z.alive and z.target == a.id and z.state == 'engaged' for z in world.zeds.values()):
        return {'ok':False,'why':'escape the zombies first'}
    if not reachable(world,a,body):return {'ok':False,'why':'approach the body first'}
    row = next((i for i in body['items'] if i['id'] == args.get('item')),None)
    qty = args.get('qty',1)
    if type(qty) is not int or not row or not 1 <= qty <= row['qty']:
        return {'ok':False,'why':'choose a quantity still on the body'}
    if a.weight()+ITEMS[row['code']]['w']*qty > world.carry_capacity(a)*1.25+.001:
        return {'ok':False,'why':'too heavy; take fewer items or wear a backpack'}
    a.add(row['code'],qty,row['cond'])
    row['qty'] -= qty
    if not row['qty']:body['items'].remove(row)
    body['revision'] += 1
    res = {'ok':True,'message':f"Took {qty} × {ITEMS[row['code']]['name']}.", 'revision':body['revision']}
    a.loot_receipts = (a.loot_receipts + [{'id':rid,'signature':signature,'result':res}])[-64:]
    a.dirty = True
    return res


async def load(session, now):
    await session.execute(delete(WorldCorpse).where(WorldCorpse.until <= now))
    await session.commit()
    rows = (await session.execute(select(WorldCorpse).where(WorldCorpse.until > now))).scalars().all()
    return {r.id:copy.deepcopy(r.state) for r in rows}


async def save_new(session, bodies, dead_rows, *, commit=True):
    for body in bodies:
        if await session.get(WorldCorpse,body['id']) is None:
            session.add(WorldCorpse(id=body['id'],until=body['until'],revision=body['revision'],state=copy.deepcopy(body)))
    for zid,until in dead_rows:
        if await session.get(ZedDead,zid) is None:session.add(ZedDead(id=zid,until=until))
    if commit:await session.commit()


async def update_stock(session, body, expected):
    """Commit caller's player update in the SAME transaction as conserved stock."""
    result = await session.execute(update(WorldCorpse).where(
        WorldCorpse.id == body['id'], WorldCorpse.revision == expected).values(
            revision=body['revision'],state=copy.deepcopy(body)))
    return result.rowcount == 1
