"""Per-life searched shelves. Reveal once; transfer explicitly and durably."""
import copy

from app.game.content import ITEMS
from app.game.progression import award


def reveal(a, stash):
    sid = stash['id']
    if sid in a.claimed:
        return
    # Actor.add supplies the same stacking and condition rules as a pack.
    from app.game.sim import Actor
    stock = Actor(id=a.id)
    for code, qty in stash['loot']:
        stock.add(code, qty, stash.get('condition', {}).get(code))
    a.loot_shelves[sid] = {k: copy.deepcopy(stash[k]) for k in
                          ('id', 'lat', 'lng', 'kind', 'building', 'room', 'owner', 'floor_level') if k in stash} | {
                              'items': stock.items, 'revision': 1}
    a.claimed.add(sid)
    a.pending_search = None
    a.dirty = True
    a.events.append({'e': 'found', 'stash': sid, 'items': copy.deepcopy(stock.items)})
    award(a, 'scavenging', 25)


def take(world, a, args):
    if a.dead:
        return {'ok': False, 'why': 'dead'}
    rid = str(args.get('request', ''))
    if not 8 <= len(rid) <= 80:
        return {'ok': False, 'why': 'missing loot transfer identifier'}
    signature = [args.get(k) for k in ('stash', 'item', 'qty', 'revision')]
    for receipt in a.loot_receipts:
        if receipt['id'] == rid:
            return copy.deepcopy(receipt['result']) if receipt['signature'] == signature else {
                'ok': False, 'why': 'loot transfer identifier already used'}
    shelf = a.loot_shelves.get(args.get('stash'))
    # Legacy claims have already paid out: they never regenerate a shelf.
    if shelf is None:
        return {'ok': False, 'why': 'search this container first; old claims are empty'}
    if args.get('revision') != shelf['revision']:
        return {'ok': False, 'why': 'container changed; try again'}
    if a.channel or world.now < a.busy_until - .05:
        return {'ok': False, 'why': 'finish your current action first'}
    if any(z.alive and z.target == a.id and z.state == 'engaged' for z in world.zeds.values()):
        return {'ok': False, 'why': 'escape the zombies first'}
    if not world._stash_accessible(a, shelf):
        return {'ok': False, 'why': 'approach the container first'}
    row = next((i for i in shelf['items'] if i['id'] == args.get('item')), None)
    qty = args.get('qty', 1)
    if type(qty) is not int or not 1 <= qty <= 10000 or not row or qty > row['qty']:
        return {'ok': False, 'why': 'choose a quantity still in the container'}
    if a.weight() + ITEMS[row['code']]['w'] * qty > world.carry_capacity(a) * 1.25 + .001:
        return {'ok': False, 'why': 'too heavy; take fewer items or wear a backpack'}
    a.add(row['code'], qty, row['cond'])
    row['qty'] -= qty
    if not row['qty']:
        shelf['items'].remove(row)
    shelf['revision'] += 1
    result = {'ok': True, 'message': f"Took {qty} × {ITEMS[row['code']]['name']}.",
              'revision': shelf['revision']}
    a.loot_receipts = (a.loot_receipts + [{'id': rid, 'signature': signature, 'result': result}])[-64:]
    a.dirty = True
    return result


def visible(world, a):
    from app.game.sim import dist_m
    return [{**copy.deepcopy(s), 'reachable': world._stash_accessible(a, s)}
            for s in a.loot_shelves.values()
            if s.get('floor_level',0)==a.floor_level and dist_m(a.lat, a.lng, s['lat'], s['lng']) <= 180]


def containers(world, a):
    # Daily world reseeding must not make a partially emptied personal shelf vanish.
    return [s for s in {**world.stashes, **a.loot_shelves}.values() if s.get('floor_level',0)==a.floor_level]
