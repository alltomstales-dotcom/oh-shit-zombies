"""What the models are told. Frozen before any scored life: see DEVLOG."""
RULES = ("Zombie survival game in real time. Zombies walk about 0.8 m/s, a few 1.3 m/s. You walk 2 m/s when one is close and "
         "6 m/s when clear, so you can outrun them unless one has hold of you. One that has hold of you comes with you and bites "
         "every 2 to 3 seconds. Each bite costs 3 to 7 health and opens a wound that bleeds until bandaged. Three or more on you "
         "at once means more bites and more infection. A script swings and shoves for you very quickly: one zombie is usually killed "
         "in a few seconds with little damage. Searching and bandaging are noisy or slow and are interrupted by being hit.")

OPTIONS = {
    'fight': "Stand here and let the combat script kill what is close. Good when one to three zombies are close and health is not low.",
    'flee': "Break free and run from the zombies, giving up on the current errand for now. Good when too many are close, or when health is low and they are still coming.",
    'indoors': "Go through the nearest door, close it behind you and stay. Good when many are coming, a door is close, and there is no reason to stay outside.",
    'goal': "Carry on with the current errand and ignore the zombies unless one grabs you. Good when nothing is close or they are too slow and far to matter.",
    'treat': "Stop and bandage a bleeding wound now, about 3.5 seconds standing still. Good when bleeding and nothing will reach you before it is finished.",
}


def tactic_question(legal):
    return {'tactic': {'type': 'choice',
                       'instructions': "Using `rules`, `you`, `zombies` and `errand`, choose what the survivor should do for the next two seconds to stay alive and still get the errand done.",
                       'criteria': {k: OPTIONS[k] for k in legal}}}


def slow_prompt(state, legal):
    import json
    opts = '\n'.join(f'- {k}: {OPTIONS[k]}' for k in legal)
    return (f"{RULES}\n\nCurrent state as JSON:\n{json.dumps(state)}\n\nChoose what the survivor should do for the next two seconds to stay alive and still get the errand done. "
            f"Options:\n{opts}\n\nAnswer with the option name only.")


PLAN = """You are the strategist for a survivor in a real-time zombie game. A fast script handles walking, doors and fighting; you only set the next errand, a few times in a life.

Rules: zombies shamble at 0.8 m/s and you walk at 6 m/s when clear. Noise draws them: searching a container can be heard 22 m away. It takes about 4 s and you can only search when nothing is on you. Bandages stop bleeding. Container kinds: medical holds bandages and disinfectant; toolbox and chest hold weapons; car and bag hold a mix. A building container needs a door opened first, which costs time and may be locked.

Mission: be alive when the timer ends, having searched at least 3 containers. More containers and better gear are better. Dying is the worst outcome.

State:
{state}

Reply with one JSON object and nothing else:
{{"goal": "loot", "target": "<id of a container listed above>", "why": "<one short sentence>"}}
or {{"goal": "explore", "bearing": "N|NE|E|SE|S|SW|W|NW", "why": "..."}} to walk 80 m that way and find more containers,
or {{"goal": "hide", "why": "..."}} to go indoors, shut the door and wait until your next decision,
or {{"goal": "treat", "why": "..."}} to bandage now, then ask again.
"""
