"""Explicit launch/respawn/travel placement, separate from virtual walking."""
import math
from app.game.sim import dist_m
from app.game.starts import by_id
from app.rng import seeded

GPS_RADIUS_M = 804.672
MAX_FIX_AGE_S = 15


def public_start(actor, args, now):
    """Public server: a survivor starts at a named map start. No device location is taken or kept."""
    start = by_id(args.get('start'))
    if start is None or args.get('reason') != 'launch':
        return {'ok': False, 'why': 'choose a map start'}
    if actor.lat != 0 or actor.lng != 0:
        return {'ok': False, 'why': 'this survivor has already started'}
    rng = seeded(f"start:{actor.id}:{actor.life_id}")
    args.update(lat=start['lat'] + rng.uniform(-40, 40) / 111320, lng=start['lng'] + rng.uniform(-40, 40) / (111320 * math.cos(math.radians(start['lat']))),
                accuracy=1.0, timestamp=now * 1000, source='manual')
    return None


def apply(world, actor, args, now):
    if actor.dead:
        return {'ok': False, 'why': 'dead'}
    source, reason = args.get('source'), args.get('reason')
    if source not in ('gps', 'manual') or reason not in ('launch', 'travel'):
        return {'ok': False, 'why': 'invalid placement intent'}
    try:
        lat, lng, accuracy, timestamp = (float(args[k]) for k in ('lat', 'lng', 'accuracy', 'timestamp'))
    except (KeyError, TypeError, ValueError):
        return {'ok': False, 'why': 'missing location fix'}
    if not all(math.isfinite(v) for v in (lat, lng, accuracy, timestamp)) or not (-90 < lat < 90 and -180 <= lng <= 180):
        return {'ok': False, 'why': 'invalid location fix'}
    if source == 'gps' and (not 0 < accuracy <= 80 or not -5 <= now - timestamp / 1000 <= MAX_FIX_AGE_S):
        return {'ok': False, 'why': 'get a fresh, accurate GPS fix', 'retry': True}
    hunted = any(z.alive and z.target == actor.id and z.state in ('chase', 'alert', 'engaged') for z in world.zeds.values())
    if reason == 'launch' and hunted:
        return {'ok': False, 'why': 'GPS start waits until you escape your pursuers', 'hunted': True, 'retry': True}
    if reason == 'travel' and (source != 'gps' or actor.gps_anchor is None or
            dist_m(*actor.gps_anchor, lat, lng) - accuracy <= GPS_RADIUS_M):
        return {'ok': False, 'why': 'stay in this play area until real travel exceeds half a mile'}
    fresh = actor.lat == 0 and actor.lng == 0
    if actor.floor_level:actor.floor_epoch+=1
    actor.floor_level=0;actor.floor_building=None
    actor.lat, actor.lng = lat, lng
    actor.raw = (lat, lng, max(1, accuracy))
    actor.channel = None
    actor.sprinting = False
    actor.speed = 0
    actor.position_mode = 'desk'
    world._wall_clearance(actor)
    actor.raw = (actor.lat, actor.lng, 1)
    actor.gps_anchor = [lat, lng] if source == 'gps' else None
    actor.placement_epoch += 1
    if fresh:
        actor.placed_at = now
        actor.location_loading_until = now + 20
        actor.transit_until = actor.location_loading_until  # bounded map-loading protection
    actor.dirty = True
    return {'ok': True, 'lat': actor.lat, 'lng': actor.lng, 'anchor': actor.gps_anchor,
            'placement_epoch': actor.placement_epoch,
            'adjusted': dist_m(lat, lng, actor.lat, actor.lng) > .5}
