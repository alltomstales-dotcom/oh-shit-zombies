"""Personal shelters and reusable storage. Hub commits these with the survivor."""
import copy
import math
from app.config import get_settings
from app.game.content import ITEMS


def distance(a, home):
    return math.hypot((a.lat-home["lat"])*111320,
                      (a.lng-home["lng"])*111320*math.cos(math.radians(a.lat)))


def reachable(world, actor):
    h = actor.home
    return bool(h and h.get("floor_level",0)==actor.floor_level and distance(actor, h) <= 2.7 and
                world.buildings.clear((actor.lat, actor.lng), (h["lat"], h["lng"])))


def summary(world, actor):
    h = actor.home
    if not h:
        return None
    from app.game import survival
    containers=[]
    for o in survival.objects(world,actor):
        if o.get('capacity',0)>0 and o.get('hp',1)>0:
            containers.append({**copy.deepcopy(o),'name':o.get('name',survival.OBJECTS[o['kind']]['name']),
                'reachable':survival.in_range(world,actor,o),
                'weight':round(sum(ITEMS[i['code']]['w']*i['qty'] for i in o.get('items',[])),2)})
    stored=h['items']+[i for o in h.get('objects',[])+[x for x in h.get('mutations',{}).values() if x] for i in o.get('items',[])]
    food=sum(i['qty'] for i in stored if (ITEMS[i['code']]['kind']=='food' or i['code']=='rawfood') and (not ITEMS[i['code']].get('perishable') or (i.get('cond') or 0)>0))
    water=sum(i['qty'] for i in stored if i['code']=='water')
    return {k: copy.deepcopy(h[k]) for k in
            ("name", "lat", "lng", "building", "capacity", "revision", "items")} | {
                "floor_level":h.get("floor_level",0),"jobs":jobs(world,actor),"food":food,"water":water,"defenses":sum(d.get("hp",0)>0 for d in h.get("defenses",{}).values()),"objective":survival.objective(actor),"containers":containers,"reachable": reachable(world, actor), "distance": round(distance(actor, h), 1),
                "weight": round(sum(ITEMS[i["code"]]["w"]*i["qty"] for i in h["items"]), 2)}


def jobs(world, actor):
    """What is running at home and when it finishes: absolute times, so nothing here changes per second."""
    from app.game import survival, study
    out = []
    for o in (actor.home or {}).get("objects", []):
        if o.get("hp", 1) <= 0:
            continue
        if o["kind"] in survival.GROW and "ready" in o:
            out.append({"id": o["id"], "kind": "crop", "name": survival.OBJECTS[o["kind"]]["name"],
                        "ready": round(o["ready"]), "lat": o["lat"], "lng": o["lng"]})
        if o.get("job"):
            out.append({"id": o["id"], "kind": "station", "name": o["job"]["name"].split(" (")[0],
                        "ready": round(o["job"]["ready"]), "lat": o["lat"], "lng": o["lng"]})
    s = study.view(world, actor)
    if s:
        out.append({"id": "study", "kind": "study", "name": ("Watching " if s.get("kind")=="media" else "Reading the ") + s["name"],
                    "ready": s["ready"], "left_s": s["left_s"]})
    return out


def returning(world, actor):
    """Said once on coming back to the game: what finished at home meanwhile. Rewards, never losses."""
    from app.game import study
    lines = []
    told = study.update(world, actor)
    if told:
        lines.append(told)
    ready = [j["name"] for j in jobs(world, actor) if j["kind"] != "study" and j["ready"] <= world.now]
    if ready:
        lines.append("Ready at home: " + ", ".join(sorted(set(ready))) + ".")
    return lines


def action(world, a, op, args):
    if a.dead:
        return {"ok": False, "why": "dead"}
    if a.channel or a.pending_work or world.now < a.busy_until-.05:
        return {"ok": False, "why": "finish your current action first"}
    if any(z.alive and z.target == a.id and z.state == "engaged" for z in world.zeds.values()):
        return {"ok": False, "why": "escape the zombies first"}
    if op == "home":
        from app.game import bases
        if bases.owner(a)!=a.id:return {'ok':False,'why':'only the owner can rename or move this base; select your personal home first'}
        if a.base_members and args.get('op')!='rename':return {'ok':False,'why':'remove base members before moving your home'}
        name = str(args.get("name", "My shelter")).strip()[:40] or "My shelter"
        if not get_settings().free_text:name = "My shelter"
        if args.get("op") == "rename" and a.home:
            if not reachable(world, a):
                return {"ok": False, "why": "return to your home cupboard first"}
            a.home["name"] = name
            a.home["revision"] += 1
        else:
            b = world.buildings.containing((a.lat, a.lng))
            if b is None:
                return {"ok": False, "why": "choose a room inside a building"}
            if a.home and (a.home["items"] or a.home.get('objects') or any(o and o.get('items') for o in a.home.get('mutations',{}).values())):
                return {"ok": False, "why": "empty your cupboard before moving home"}
            previous=a.home or {}
            a.home = {**previous,"name": name, "lat": a.lat, "lng": a.lng, "building": b.id,
                      "floor_level":a.floor_level, "capacity": 40.0, "revision": (a.home or {}).get("revision", 0)+1,
                      "items": [], "next_item": 1, "receipts": []}
        a.dirty = True
        return {"ok": True, "message": "Home cupboard ready. Supplies stay here between lives."}
    h = a.home
    if not h:
        return {"ok": False, "why": "choose a home first"}
    rid = str(args.get("request", ""))
    if not 8 <= len(rid) <= 80:
        return {"ok": False, "why": "missing transfer identifier"}
    signature = [a.id]+[args.get(k) for k in ("op", "item", "qty", "revision", "container")]
    for receipt in h.get("receipts", []):
        if receipt["id"] == rid:
            return copy.deepcopy(receipt["result"]) if signature == receipt["signature"] else {
                "ok": False, "why": "transfer identifier was already used"}
    if args.get("revision") != h["revision"]:
        return {"ok": False, "why": "cupboard changed; try again"}
    container=h
    if args.get('container'):
        from app.game import survival
        o=survival.target(world,a,args['container'])
        if not o or not o.get('capacity',0) or o.get('hp',0)<=0:
            return {'ok':False,'why':'storage container is unavailable'}
        if not survival.in_range(world,a,o):return {'ok':False,'why':'approach that storage container first'}
        if o.get('building') and o['building']!=h['building']:
            return {'ok':False,'why':'use furniture in your home building'}
        if o.get('generated'):
            survival.defaults(a);container=h['mutations'].setdefault(o['id'],copy.deepcopy(o))
        else:container=next(o2 for o2 in h['objects'] if o2['id']==o['id'])
    if container is h and not reachable(world, a):
        return {"ok": False, "why": "walk within 2.7 metres of your home cupboard"}
    direction = args.get("op")
    if direction not in ("deposit", "withdraw"):
        return {"ok": False, "why": "choose deposit or withdraw"}
    src = a.items if direction == "deposit" else container["items"]
    row = next((i for i in src if i["id"] == args.get("item")), None)
    qty = args.get("qty", 1)
    if not isinstance(qty, int) or isinstance(qty, bool) or not 1 <= qty <= 10000 or not row or qty > row["qty"]:
        return {"ok": False, "why": "choose a quantity you have"}
    if direction == "deposit" and row["id"] in a.worn.values():
        return {"ok": False, "why": "take off worn equipment before storing it"}
    if direction == "deposit":
        weight = sum(ITEMS[i["code"]]["w"]*i["qty"] for i in container["items"])
        if weight + ITEMS[row["code"]]["w"]*qty > container["capacity"]+.001:
            return {"ok": False, "why": "cupboard is full"}
        target = next((i for i in container["items"] if i["code"] == row["code"] and
                       i["cond"] == row["cond"] and "stack" in ITEMS[row["code"]]), None)
        if target:
            target["qty"] += qty
        else:
            container["items"].append({**row, "id": container["next_item"], "qty": qty})
            container["next_item"] += 1
    else:
        if a.weight()+ITEMS[row["code"]]["w"]*qty > world.carry_capacity(a)*1.25+.001:
            return {"ok": False, "why": "too heavy; withdraw fewer items or wear a backpack"}
        a.add(row["code"], qty, row["cond"])
    row["qty"] -= qty
    if row["qty"] == 0:
        src.remove(row)
        if direction == "deposit" and a.hands == row["id"]:
            a.hands = None
    h["revision"] += 1
    result = {"ok": True, "message": f'{"Stored" if direction == "deposit" else "Retrieved"} {qty} × {ITEMS[row["code"]]["name"]}.'}
    h["receipts"] = (h.get("receipts", []) + [{"id": rid, "signature": signature, "result": result}])[-64:]
    a.dirty = True
    return result
