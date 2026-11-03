"""Tuning numbers and the item catalogue. Pure data.

Every number here is a dial. The bot harness in tools/ measures what a change does to pacing
(seconds between threats, fight length, deaths per hour) before it reaches a player.
"""
from __future__ import annotations

TUNE = {
    # --- what the survivor can perceive -------------------------------------------------
    "sight_day_m": 55.0,          # zombies inside this are drawn; beyond it you only hear them
    "sight_night_m": 22.0,
    "hearing_m": 110.0,           # groans beyond sight arrive as a direction, not a position

    # --- what zombies can perceive ------------------------------------------------------
    "zed_sight_day_m": 20.0,
    "zed_sight_night_m": 13.0,
    "noise_still_m": 5.0,         # how far the survivor can be heard standing still
    "noise_quiet_m": 3.0,         # creeping
    "noise_walk_m": 11.0,         # the pace kept in a fight
    "noise_travel_m": 20.0,       # crossing the map
    "noise_sprint_m": 35.0,
    "noise_wall_mult": 0.4,       # share of footstep range that gets through a wall
    "quiet_speed": 1.2,           # m/s while creeping
    "quiet_sight_mult": 0.6,      # how much nearer an unaware zombie must be to spot a creeper
    "knock_noise_m": 10.0,
    "knock_inside_m": 14.0,       # how far inside a knock on the door is answered
    "notice_rate_near": 1.3,      # chance per second to notice inside half the range
    "notice_rate_far": 0.40,
    "alert_s": (0.8, 1.4),        # it turns and groans before it starts walking
    "groan_pull_m": 16.0,         # a groan turns the heads of others this close
    "groan_pull_chance": 0.8,
    "lose_dist_m": 75.0,
    "lose_after_s": 14.0,         # seconds without perceiving you before it gives up

    # --- closing and holding on ---------------------------------------------------------
    "lunge_range_m": 2.6,         # inside this it grabs: it is "on you"
    "first_lunge_s": (0.9, 1.5),  # grab to first bite attempt
    "attack_every_s": (2.2, 3.2),
    "attack_miss": 0.12,
    "max_engaged": 6,             # more than this wait their turn in a ring behind
    "ring_m": 3.6,

    # --- the survivor's body ------------------------------------------------------------
    "hp_max": 100.0,
    "end_max": 100.0,
    "end_regen": 3.0,             # per second, only when nothing is on you
    "end_regen_delay_s": 2.0,
    "walk_end_per_m": 0.012,   # a long outing wears you down; standing still restores it
    "walk_speed_fresh": 2.0,  # m/s in combat; virtual exploration uses the multiplier below
    "walk_speed_explore_mult": 3.0,
    "sprint_mult": 4.0,
    "sprint_end_per_s": 12.0,
    "sprint_start_end": 10.0,
    "walk_speed_tired_floor": 0.62,
    "walk_speed_leg_wound": 0.82,
    "walk_speed_critical_hp": 0.78,
    "scream_cooldown_s": 10.0,
    "panic_scream_min": 60.0,
    "panic_scream_per_s": 0.04,  # chance rate at full panic, independent of tick frequency
    "panic_scream_gap_s": 20.0,
    "panic_up": 45.0,             # per second toward the target
    "panic_down": 5.0,
    "panic_per_chaser": 12.0,     # chasers within 15 m
    "panic_per_engaged": 22.0,
    "panic_hit_penalty": 0.35,    # hit chance lost at full panic
    "drop_panic": 70.0,           # above this, mobbed by 3+, a hit can knock the weapon away
    "drop_chance": 0.25,
    "carry_max": 12.0,

    # --- actions ------------------------------------------------------------------------
    "swing_reach_m": 3.4,
    "finish_reach_m": 5.2,        # one on the ground is worth a step forward
    "base_hit": 0.92,
    "finish_mult": 2.5,           # damage multiplier against a zombie on the ground
    "hit_stagger_s": 0.6,         # a landed hit interrupts its attack
    "hit_reset_s": (1.2, 1.8),
    "shove_cost": 5.0,
    "shove_recover_s": 0.55,
    "shove_knockdown": 0.55,
    "shove_stagger_s": 1.2,
    "shove_push_m": 2.0,
    "shove_targets": 2,
    "down_s": (3.0, 4.2),
    "rise_s": 0.9,
    "back_cost": 15.0,
    "back_channel_s": 0.8,
    "back_cooldown_s": 6.0,
    "back_push_m": 5.5,
    "back_stagger_s": 2.0,
    "bandage_s": 3.5,
    "disinfect_s": 2.0,
    "search_s": 4.0,
    "search_noise_m": 22.0,
    "pickup_m": 5.0,
    "stash_reach_m": 14.0,        # GPS is rough, so reach is generous
    "gun_range_m": 28.0,
    "gun_noise_m": 140.0,

    # --- wounds -------------------------------------------------------------------------
    "wound_weights": {"scratch": 62, "laceration": 28, "bite": 10},
    "infect": {"scratch": 0.07, "laceration": 0.25, "bite": 1.0},
    "bleed": {"scratch": 0.10, "laceration": 0.25, "bite": 0.35},   # health per second
    "neck_bleed_mult": 3.0,
    "scratch_clot_s": 120.0,
    "turn_after_h": (24.0, 48.0), # infected to dead, in real hours
    "offline_heal_per_h": 10.0,   # health comes back only away from the game
    "offline_bleed_cap_s": 120.0, # an open wound left when you quit bleeds this long at most

    # --- a new survivor's first day ------------------------------------------------------
    "grace_h": 24.0,
    "grace_notice": 0.6,
    "grace_bite": 0.5,
    # A survivor who has only just appeared (first start, or a new life where the last one fell)
    # is not noticed until they have had time to look around, or have walked off.
    "arrival_calm_s": 40.0,
    "arrival_calm_m": 15.0,

    # --- where the server believes you are -----------------------------------------------
    "pos_max_speed": 24.0,         # m/s virtual exploration cap; GPS remains an area anchor
    "pos_deadband_m": 4.0,
    "transit_jump_m": 60.0,       # a jump this big means a vehicle or a bad fix
    "transit_s": 8.0,

    # --- the world -----------------------------------------------------------------------
    "active_m": 220.0,            # zombies further than this from everyone stand still
    "unload_m": 420.0,
    "wander_speed": 0.22,
    "wander_r_m": 14.0,
    "wander_step_s": 0.6,         # an idle zombie's shuffle is simulated in steps this long (cost, not rules)
    "zed_speed_mult": 1.0,        # every zombie's walking pace, multiplied: a difficulty dial
    "temp_forget_s": 90.0,        # a director zombie idle this long, out of everyone's sight, is removed
    "temp_max_base": 60,          # at most this many director zombies at once...
    "temp_max_per_player": 3,     # ...plus this many per survivor on the map
    # The first moments after arriving (difficulty dials; 0 s means off, as it always was):
    "early_s": 0.0,               # this long after being placed in the world...
    "early_notice": 1.0,          # ...zombies notice you this much as fast,
    "early_speed": 1.0,           # ...and whatever chases you walks at this share of its pace
}

# kind -> stats. Danger comes from numbers, never from one strong zombie.
ZED_KINDS = {
    "shambler": {"hp": (20, 32), "speed": (0.70, 0.95), "dmg": (3, 7), "weight": 78},
    "lurcher":  {"hp": (16, 24), "speed": (1.15, 1.35), "dmg": (3, 6), "weight": 12},
    "crawler":  {"hp": (12, 18), "speed": (0.30, 0.45), "dmg": (2, 5), "weight": 10},
}
ZED_VARIANTS = 16   # how many looks the client has (zed_s0 to zed_s15); picked per zombie, purely cosmetic

BODY_PARTS = [
    ("left hand", 9), ("right hand", 9), ("left forearm", 14), ("right forearm", 14),
    ("left upper arm", 8), ("right upper arm", 8), ("torso", 12), ("neck", 4), ("head", 3),
    ("left thigh", 6), ("right thigh", 6), ("left shin", 5), ("right shin", 5),
]

# code -> item. `w` is weight. Weapons: dmg range, seconds to recover, endurance per swing,
# `wear` = chance a landed hit costs one point of condition (out of `cond`).
ITEMS = {
    "bat":      {"name": "Baseball Bat",  "w": 2.0, "kind": "weapon", "dmg": (9, 15),  "rec": 0.75, "end": 9,
                 "knock": 0.25, "wear": 0.125, "cond": 10},
    "crowbar":  {"name": "Crowbar",       "w": 2.3, "kind": "weapon", "dmg": (10, 16), "rec": 0.82, "end": 10,
                 "knock": 0.20, "wear": 0.05, "cond": 10},
    "knife":    {"name": "Kitchen Knife", "w": 0.4, "kind": "weapon", "dmg": (5, 9),   "rec": 0.45, "end": 5,
                 "knock": 0.0, "wear": 0.25, "cond": 10},
    "axe":      {"name": "Hand Axe",      "w": 1.6, "kind": "weapon", "dmg": (14, 22), "rec": 0.90, "end": 12,
                 "knock": 0.15, "wear": 0.14, "cond": 10},
    "pistol":   {"name": "Pistol",        "w": 1.1, "kind": "gun",    "dmg": (40, 60), "rec": 0.90, "end": 1,
                 "wear": 0.03, "cond": 10},
    "ammo":     {"name": "9mm Rounds",    "w": 0.03, "kind": "ammo", "stack": 60},
    "bandage":  {"name": "Bandage",       "w": 0.1, "kind": "medical", "stack": 10},
    "disinfectant": {"name": "Disinfectant", "w": 0.3, "kind": "medical", "stack": 5},
    "water":    {"name": "Water Bottle",  "w": 0.8, "kind": "drink", "stack": 3, "end": 35},
    "snack":    {"name": "Crisps",        "w": 0.2, "kind": "food", "stack": 5, "calm": 35},
}
# Clothing covers actual struck body parts; condition scales protection.
_torso = ["torso", "neck", "left forearm", "right forearm", "left upper arm", "right upper arm"]
_legs = ["left thigh", "right thigh", "left shin", "right shin"]
ITEMS.update({
 "shirt": {"name":"Cotton Shirt","kind":"clothing","slot":"torso","w":.3,"cond":10,"covers":_torso,"scratch":.12,"bite":.02},
 "pants": {"name":"Work Trousers","kind":"clothing","slot":"legs","w":.6,"cond":10,"covers":_legs,"scratch":.25,"bite":.08},
 "boots": {"name":"Work Boots","kind":"clothing","slot":"feet","w":1.1,"cond":10,"covers":["left shin","right shin"],"scratch":.35,"bite":.15},
 "gloves": {"name":"Leather Gloves","kind":"clothing","slot":"hands","w":.2,"cond":10,"covers":["left hand","right hand"],"scratch":.45,"bite":.2},
 "helmet": {"name":"Work Helmet","kind":"clothing","slot":"head","w":.5,"cond":10,"covers":["head"],"scratch":.3,"bite":.1},
 "leather": {"name":"Leather Jacket","kind":"clothing","slot":"torso","w":1.5,"cond":10,"covers":_torso,"scratch":.6,"bite":.35,"pace":.97},
 "fire_jacket": {"name":"Firefighter Jacket","kind":"clothing","slot":"torso","w":2.8,"cond":10,"covers":_torso,"scratch":.8,"bite":.6,"pace":.94},
 "fire_pants": {"name":"Firefighter Trousers","kind":"clothing","slot":"legs","w":1.8,"cond":10,"covers":_legs,"scratch":.75,"bite":.55,"pace":.96},
 "schoolbag": {"name":"School Backpack","kind":"bag","slot":"back","w":.7,"cond":10,"capacity":6},
 "rucksack": {"name":"Hiking Rucksack","kind":"bag","slot":"back","w":1.2,"cond":10,"capacity":12},
})
# Useful equipment is found through normal searches; all gear has a physical weight.
FISTS = {"name": "Bare Hands", "dmg": (2, 4), "rec": 0.5, "end": 6, "knock": 0.0, "stomp": (8, 12)}

STARTER_KIT = [("bat", 1), ("water", 2), ("snack", 1), ("bandage", 2)]

# What an abandoned bag or car boot holds, until loot moves into real buildings (phase 2).
STASH_TABLE = [
    ("bandage", 30, (1, 2)), ("water", 18, (1, 1)), ("snack", 14, (1, 2)), ("disinfectant", 8, (1, 1)),
    ("ammo", 8, (3, 7)), ("knife", 7, (1, 1)), ("bat", 5, (1, 1)), ("crowbar", 4, (1, 1)),
    ("axe", 3, (1, 1)), ("pistol", 3, (1, 1)),
]
STASH_KINDS = ["bag", "car", "chest", "medical", "toolbox"]
STASH_LOOT = {
    "bag": [("water", 35, (1, 2)), ("snack", 35, (1, 3)), ("bandage", 20, (1, 2)), ("knife", 10, (1, 1))],
    "car": STASH_TABLE,
    "chest": [("crowbar", 15, (1, 1)), ("axe", 12, (1, 1)), ("bat", 15, (1, 1)), ("pistol", 5, (1, 1)), ("ammo", 23, (4, 10)), ("water", 20, (1, 2)), ("bandage", 10, (1, 2))],
    "medical": [("bandage", 65, (2, 4)), ("disinfectant", 35, (1, 2))],
    "toolbox": [("crowbar", 35, (1, 1)), ("axe", 25, (1, 1)), ("knife", 25, (1, 1)), ("bandage", 15, (1, 2))],
}

# Zombies per map cell (a geohash-7 cell is roughly 150 m by 110 m at mid latitudes).
# Mostly empty streets, then a clump: the same number of zombies as an even spread, in fewer places.
PACKS_PER_CELL = [(0, 55), (1, 35), (2, 10)]
PACK_SIZE = [(1, 22), (2, 20), (3, 18), (4, 14), (5, 10), (6, 7), (8, 5), (10, 3), (14, 1)]
NIGHT_PACK_CHANCE = 0.55      # an extra pack that only comes out after dark
STASH_PER_CELL = [(1, 25), (2, 55), (3, 20)]
CELL_PRECISION = 7
SPAWN_WINDOW_S = 86400

# Clothing and bags broaden early supply runs without replacing consumables.
for _table in STASH_LOOT.values():
    _table.extend([("schoolbag",10,(1,1)),("gloves",8,(1,1)),("leather",8,(1,1)),
                   ("pants",6,(1,1)),("boots",5,(1,1)),("helmet",3,(1,1)),
                   ("fire_jacket",2,(1,1)),("fire_pants",2,(1,1)),("rucksack",3,(1,1))])

# Work tools and materials. Resource quantities are conserved by completed actions.
ITEMS.update({
 "hammer":{"name":"Hammer","kind":"tool","w":.6,"cond":30},
 "saw":{"name":"Handsaw","kind":"tool","w":.5,"cond":30},
 "pickaxe":{"name":"Pickaxe","kind":"tool","w":2,"cond":30},
 "rod":{"name":"Fishing Rod","kind":"tool","w":.5,"cond":20},
 "lantern":{"name":"Lantern","kind":"tool","w":.5,"cond":20},
 "log":{"name":"Log","kind":"material","w":3,"stack":20},
 "plank":{"name":"Plank","kind":"material","w":.6,"stack":50},
 "branch":{"name":"Branch","kind":"material","w":.15,"stack":50},
 "nails":{"name":"Nails","kind":"material","w":.02,"stack":100},
 "cloth":{"name":"Cloth","kind":"material","w":.1,"stack":50},
 "scrap":{"name":"Scrap Metal","kind":"material","w":.4,"stack":50},
 "stone":{"name":"Stone","kind":"material","w":.5,"stack":50},
 "ore":{"name":"Iron Ore","kind":"material","w":.7,"stack":50},
 "metal":{"name":"Iron Ingot","kind":"material","w":1,"stack":50},
 "plate":{"name":"Reinforcement Plate","kind":"material","w":.5,"stack":50},
 "seeds":{"name":"Seeds","kind":"material","w":.02,"stack":50},
 "fuel":{"name":"Generator Fuel","kind":"material","w":.8,"stack":10},
 "dirtywater":{"name":"Collected Water","kind":"material","w":.8,"stack":5},
 "rawfood":{"name":"Fresh Ingredients","kind":"material","w":.3,"stack":10},
 "meal":{"name":"Cooked Meal","kind":"food","w":.4,"stack":10,"calm":15,"hunger":45},
})
ITEMS['water']['thirst']=45
ITEMS['snack']['hunger']=25
STARTER_KIT.extend([('hammer',1),('saw',1)])
for _kind,_table in STASH_LOOT.items():
 _table.extend([('nails',14,(4,8)),('cloth',10,(2,4)),('scrap',8,(1,3)),('fuel',4,(1,2))])
 if _kind=='toolbox':_table.extend([('hammer',22,(1,1)),('saw',22,(1,1)),('pickaxe',10,(1,1))])

ITEMS["rawfood"].update(cond=100,perishable=True)
ITEMS["meal"].update(cond=100,perishable=True)

# Tagged destination gear remains a weighted find, never a guaranteed reward.
STASH_LOOT['fire_station']=[('fire_jacket',35,(1,1)),('fire_pants',25,(1,1)),('axe',20,(1,1)),('helmet',10,(1,1)),('bandage',10,(2,3))]
STASH_LOOT['police_station']=[('pistol',20,(1,1)),('ammo',40,(4,8)),('boots',20,(1,1)),('water',20,(1,2))]

# Ordinary household supplies share existing mechanics. Personal objects have
# weight but no invented medical or crafting benefit. Existing codes stay valid.
ITEMS.update({
 "beans":{"name":"Tinned Beans","kind":"food","w":.4,"stack":5,"hunger":25,"calm":10},
 "peaches":{"name":"Tinned Peaches","kind":"food","w":.35,"stack":5,"hunger":25,"calm":10},
 "soup":{"name":"Tinned Soup","kind":"food","w":.45,"stack":5,"hunger":25,"calm":10},
 "tissue":{"name":"Pocket Tissues","kind":"personal","w":.05,"stack":10,"description":"Someone's everyday supplies."},
 "soap":{"name":"Bar of Soap","kind":"personal","w":.1,"stack":5,"description":"A small reminder of an ordinary morning."},
 "toothbrush":{"name":"Toothbrush","kind":"personal","w":.03,"stack":5,"description":"Personal belongings left behind."},
 "paperback":{"name":"Dog-eared Paperback","kind":"personal","w":.2,"stack":5,"description":"A well-read keepsake."},
})
# These tables deliberately avoid the blanket outdoor gear/material additions:
# a bathroom is a place for first aid, a garage for tools, a bedroom for gear.
STASH_LOOT.update({
 'kitchen':[('beans',25,(1,2)),('peaches',20,(1,2)),('soup',20,(1,2)),
            ('water',15,(1,2)),('knife',10,(1,1)),('snack',10,(1,2))],
 'bathroom':[('bandage',30,(1,3)),('disinfectant',15,(1,1)),('cloth',15,(1,2)),
             ('tissue',15,(1,2)),('soap',15,(1,1)),('toothbrush',10,(1,1))],
 'bedroom':[('shirt',20,(1,1)),('pants',15,(1,1)),('schoolbag',15,(1,1)),
            ('leather',8,(1,1)),('cloth',17,(1,3)),('paperback',15,(1,1)),('tissue',10,(1,1))],
 'garage':[('hammer',20,(1,1)),('saw',18,(1,1)),('nails',20,(4,8)),
           ('scrap',15,(1,3)),('fuel',10,(1,1)),('crowbar',10,(1,1)),('axe',7,(1,1))],
})

# ---- C6: things that finish later. Additive: no existing code, table weight or timer changes.
# Smoked rations keep (they are not perishable), which is the point of waiting an hour for them.
ITEMS["smoked"]={"name":"Smoked Rations","kind":"food","w":.3,"stack":10,"hunger":60,"calm":20,
                 "description":"Slow food from the fire. It keeps."}
MANUALS={"carpentry":"Carpentry Manual","foraging":"Foraging Field Guide","mining":"Geology Handbook",
         "metalworking":"Metalworking Manual","cooking":"Cookery Book","scavenging":"Salvager's Notebook",
         "melee":"Self-Defence Manual","shooting":"Marksmanship Manual","fitness":"Training Guide",
         "first_aid":"First Aid Handbook"}
for _skill,_name in MANUALS.items():
 ITEMS["manual_"+_skill]={"name":_name,"kind":"book","w":.4,"teaches":_skill,
                          "description":"Read at home for an hour and this skill grows twice as fast for this survivor."}
STASH_LOOT['bedroom'].extend([('manual_fitness',3,(1,1)),('manual_melee',3,(1,1)),('manual_scavenging',3,(1,1)),('manual_foraging',3,(1,1))])
STASH_LOOT['kitchen'].append(('manual_cooking',4,(1,1)))
STASH_LOOT['bathroom'].append(('manual_first_aid',4,(1,1)))
STASH_LOOT['garage'].extend([('manual_carpentry',4,(1,1)),('manual_metalworking',3,(1,1)),('manual_mining',3,(1,1))])
STASH_LOOT['police_station'].append(('manual_shooting',6,(1,1)))
TUNE.update(plot_grow_s=86400.0,   # a vegetable plot: one real day
            smoke_s=3600.0,        # smoked rations: one real hour at the fire
            study_s=3600.0,        # a manual: one real hour of reading at home
            study_leave_m=2.0)     # get up and walk this far and the reading pauses

# ---- C7: shared by area and by the real clock. A life's day number is display only.
TUNE.update(rain_block_s=4*3600.0,   # weather is decided per area in four-hour blocks
            rain_chance=0.25,        # so it rains about a quarter of the time
            rain_barrel_s=10.0,      # seconds per unit of barrel water in rain (30 when dry)
            rain_noise_mult=0.6,     # work noise carries this much as far in rain
            heli_block_s=3*3600.0,   # at most one helicopter pass per area in each three hours
            heli_chance=0.35,        # of the daylight blocks: about one or two passes a day
            heli_min_light=0.4,      # it does not fly in the dark
            heli_warn_s=90.0,        # heard this long before it is overhead
            heli_over_s=600.0,       # overhead for ten minutes
            heli_pull_m=200.0,       # idle zombies this near someone outdoors come to look
            heli_pulse_s=8.0,        # how often it draws them again
            heli_spare_new_s=3600.0) # a survivor's first hour is passed over

# ---- C8: a herd is one walking thing on a shared schedule until it notices someone.
TUNE.update(herd_block_s=2*3600.0,   # at most one herd per region (about 1.2 km by 0.6 km) in each two hours
            herd_chance=0.3,         # of those blocks: a few a day cross each region, most of them out of reach
            herd_cross_s=1500.0,     # it takes twenty-five minutes to pass through
            herd_speed=0.5,          # metres a second: slower than a walk, so it can always be walked round
            herd_min=45, herd_max=70,
            herd_load_m=260.0,       # it is brought into the world when it is this near a survivor
            herd_hear_m=140.0,       # heard as a direction from here
            herd_see_mult=1.8,       # seen this many times further off than one zombie
            herd_notice_rate=1.5,    # chance per second to be noticed in the outer half of its range
            herd_noise_wake=0.35,    # a loud noise made within this share of its reach shows it who made it
            herd_turn_s=90.0,        # how long it walks towards a loud noise
            herd_regather_s=120.0,   # with none of them after anyone for this long, those left are a herd again
            herd_least=8,            # fewer than this left are just zombies
            herd_leave_s=300.0,      # a herd that has gathered again keeps walking at least this long
            herd_spare_new_s=3600.0) # a survivor's first hour does not call one in

# Portable broadcasts: no battery micromanagement until maintenance/utility phase.
ITEMS['radio']={'name':'Portable Radio','kind':'tool','w':.5,'description':'Listen quietly for local weather and danger reports.'}
STASH_LOOT['bedroom'].append(('radio',8,(1,1)))
STASH_LOOT['garage'].append(('radio',6,(1,1)))

# N7: optional knowledge recipes; prior recipes/manuals remain available.
ITEMS['mag_repair']={'name':'Roadside Repair Magazine','kind':'book','w':.2,'knowledge':'vehicle_kits','study_s':45,'description':'Read at home to learn vehicle repair kits.'}
ITEMS['mag_armor']={'name':'Protective Clothing Magazine','kind':'book','w':.2,'knowledge':'protective_gear','study_s':60,'description':'Read at home to learn a reinforced vest.'}
ITEMS['repair_kit']={'name':'Vehicle Repair Kit','kind':'material','w':1.2,'stack':4}
ITEMS['reinforced_vest']={**ITEMS['leather'],'name':'Reinforced Vest','w':3.2,'cond':15,'scratch':.8,'bite':.45,'pace':.94}
ITEMS['tape_workshop']={'name':'Workshop Training Tape','kind':'book','w':.2,'description':'Play at a nearby television. This lesson gives XP once per survivor.'}
ITEMS['tape_cooking']={'name':'Kitchen Survival Tape','kind':'book','w':.2,'description':'Play at a nearby television. This lesson gives XP once per survivor.'}
STASH_LOOT['garage'].extend([('mag_repair',6,(1,1)),('tape_workshop',4,(1,1))])
STASH_LOOT['bedroom'].extend([('mag_armor',5,(1,1)),('tape_cooking',4,(1,1))])
