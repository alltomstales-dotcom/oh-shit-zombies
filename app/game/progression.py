"""Earned, per-life progression. Bonuses stay small enough for survival to matter."""
SKILLS = {
    "carpentry": ("Carpentry", "Complete wood recipes 5% faster per level."),
    "foraging": ("Foraging", "Complete gathering recipes 5% faster per level."),
    "mining": ("Mining", "Ore and stone gathering proficiency."),
    "metalworking": ("Metalworking", "Complete metal recipes 5% faster per level."),
    "cooking": ("Cooking", "Complete food and water recipes 5% faster per level."),
    "scavenging": ("Scavenging", "Search 6% faster per skill level (max 30%)."),
    "melee": ("Melee", "Deal 4% more melee damage per skill level (max 20%)."),
    "shooting": ("Shooting", "Gain 2 percentage points of gun accuracy per skill level (max 10)."),
    "fitness": ("Fitness", "Walking costs 6% less endurance and carry capacity rises 0.4kg per skill level."),
    "first_aid": ("First aid", "Treat wounds 8% faster per skill level (max 40%)."),
}


def threshold(level, base=30):
    return base * level * (level + 1) // 2


def skill_level(actor, skill):
    xp = max(0, int(actor.skill_xp.get(skill, 0)))
    level = 0
    while level < 5 and xp >= threshold(level + 1):
        level += 1
    return level


def level_for(xp):
    level = 1
    while level < 20 and xp >= threshold(level, 50):
        level += 1
    return level


def award(actor, skill, amount):
    if actor.dead or skill not in SKILLS or amount <= 0:
        return
    if skill in getattr(actor, "studied", ()):       # a manual read at home: double, for this life
        amount *= 2
    before, old_skill = level_for(actor.xp), skill_level(actor, skill)
    actor.xp += int(amount)
    actor.skill_xp[skill] = actor.skill_xp.get(skill, 0) + int(amount)
    actor.dirty = True
    actor.events.append({"e": "xp", "amount": int(amount), "skill": SKILLS[skill][0],
                         "level": level_for(actor.xp), "skill_level": skill_level(actor, skill),
                         "level_up": level_for(actor.xp) > before,
                         "skill_up": skill_level(actor, skill) > old_skill})


def view(actor):
    level = level_for(actor.xp)
    skills = []
    for key, (name, effect) in SKILLS.items():
        rank = skill_level(actor, key)
        skills.append({"id": key, "name": name, "level": rank,
                       "xp": int(actor.skill_xp.get(key, 0)),
                       "next": threshold(rank + 1) if rank < 5 else None,
                       "effect": effect})
    return {"xp": actor.xp, "level": level,
            "next": threshold(level, 50) if level < 20 else None, "skills": skills}
