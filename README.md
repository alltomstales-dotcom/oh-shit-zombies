# Oh shit, Zombies.

**A zombie survival game on real city streets, built in public by AI coding agents, tested by AI players, and documented as it goes.**

- **Play it (test server, 10 players at a time, it may be down sometimes):** https://birmingham-keith-commodities-pink.trycloudflare.com. This is a temporary address, and a permanent one is coming.
- **Watch it being built:** the devlog series on YouTube, https://www.youtube.com/@alltomstales
- **The written devlog:** [`docs/devlog/DEVLOG.md`](docs/devlog/DEVLOG.md), with the plan in [`docs/devlog/BACKLOG.md`](docs/devlog/BACKLOG.md). Mistakes stay in.

**How it's made.** Tom directs and answers questions. AI coding agents (mostly Claude and Codex) write the code, run the tests and keep the log. AI players test it: reflex scripts, a fast decision model and slower planners, all in [`ai-testing/`](ai-testing/). Every change gets a pass mark written down before it's tested. The narration voice and the music for the videos, and much of the rest of the production, run on DGX Spark machines from a friend in Detroit.

**Run from a phone.** Tom directs the whole project from his phone, mostly through [T3 Code](https://github.com/pingdotgg/t3code), Theo's open-source app (with the Ping team) for running coding agents like Claude Code and Codex on your own machine. Thanks, Theo.

**Fork it.** The code is under BSD Zero Clause: use it for anything, commercial or not, no strings attached. Some art has its own terms; see [`ASSETS_LICENSE.md`](ASSETS_LICENSE.md). If you build a different game with the same pattern, we'd love to hear about it.

---

A zombie survival walk around your own streets, in the browser. Free, non-commercial, for fun.
Inspired by Project Zomboid; it uses none of that game's art, text or code.

You are one survivor on the real map. The streets are mostly empty. Then they are not.
Zombies see and hear you, groan to pull the rest of the pack, close in at a shamble and grab.
You shove, swing, finish them on the ground, back away, bandage, and one day you die. A bite
always kills, a day or two later, and the game never tells you which wound it was.

## Run it

    python3 -m venv ~/venvs/osz && ~/venvs/osz/bin/pip install -r requirements.txt pytest pytest-asyncio pillow
    ./run_local.sh            # http://localhost:8010

- **Phone startup and new lives:** a fresh app opening and every new survivor use a current GPS fix. Gear, skills and home stay with an existing living survivor; home storage never moves. A hunted survivor must escape before launch relocation. Socket reconnects preserve virtual walking. If GPS is blocked or stale, Retry GPS or explicitly Choose on map; there is no silent phone fallback to old/death coordinates.
- **Play near me**: tap the map to walk on your phone or desktop. GPS sets the area center in the background. Small drift is ignored; physical movement beyond a half-mile radius (804.672m, allowing for reported GPS uncertainty) recenters the play area after three consistent fixes spanning at least eight seconds. Virtual walking does not trigger recentering. No movement mode switch is needed.
- **Stop walking** halts the current map walk. **SCREAM** attracts idle zombies within the normal sight radius (about 55m in daylight, 22m at night), with a 10s cooldown. Severe panic can make you scream involuntarily; these have a minimum 20s gap.
- Desktop: arrow keys or WASD walk; `J`/Space swing, `K` shove, `L` back away, `B` bandage, `F` shoot, `E` search/pick up, `I` pack and wounds, `R` scream.
- Add `?dev=1` for the stopwatch: frame rate, ping, tap-to-frame and tap-to-server times.

Fresh map movement is 6m/s outside combat and 2m/s in combat. Long walks spend endurance; exhaustion, leg wounds and critical health slow your survivor. Stop somewhere clear to recover endurance. GPS only recenters the play area after substantial real travel; it does not override virtual walking.

The shared build/readiness checklist is in [BUILD_CHECKLIST.md](BUILD_CHECKLIST.md).

## Exploration and loot

Follow the Explore lead or tap a labeled container to select it. Use Approach, then Search in range. Search reveals a persistent shelf; Take 1 or a chosen quantity, leaving the rest for later. Old claimed containers remain empty. Bags, car boots, chests, medical cases and toolboxes hold different supplies. Searches make noise and can be interrupted; empty containers stay marked. The pack has Drop / Drop 1 controls, and nearby dropped gear can be picked up again. Gear may be worn rather than pristine. Searching then walking out of range does not collect loot remotely.

## Movement and building discovery

Fresh virtual walking is 6m/s outside combat and 2m/s in combat, reduced by fatigue and injuries. **SPRINT** toggles four times the current pace, drains 12 stamina per second while moving, and stops when stamina runs out; starting needs 10 stamina. Stop walking also turns sprint off. Stand still to recover.

Inside, **SEARCH BUILDING** gives two completed RNG attempts per survivor per building. A four-second noisy search has a 70% discovery chance plus a small Scavenging bonus. Successful attempts uncover a room-themed hidden container: tap it, approach and Search to reveal its shelf, then choose what to take. Attempts, discoveries and claimed containers persist; interruptions consume no attempt. Recorded sound sources and licenses are at `/assets/audio/CREDITS.txt`.

## Experience and skills

Successful exploration, searches, walking, combat and wound care train Scavenging, Melee, Shooting, Fitness and First aid. The pack shows survivor level, XP and the next milestone. Skill benefits are capped; fatigue and wounds still matter. Progress stays with that survivor and resets on a new life.

## Buildings

Tap a building to approach its entrance. **OPEN ENTRANCE**, then tap inside. Roofs reveal a fictional ground floor: rooms, walls, doors, windows and supplies. Open connecting doors to search further; close doors to delay pursuit. **EXIT BUILDING** is always available inside and approaches/opens closed doors along a safe path outside. Interiors fit the screen width with enough margin to keep rooms visible. Zombies can break openings. Windows let you see through glass and can be opened as another route. Searches inside require being within 2.5m with no wall in the way. Close combat zooms 1.5x further.

Footprints come from cached OpenStreetMap geometry. Interior layouts are generated for the game. Smaller structures use a single room; unsupported complex/multipart or enormous footprints are skipped. If geometry is unavailable, explicitly labelled generated shelters keep exploration playable. Doors/windows and claimed room loot survive restarts.

## How it is put together

| Part | Where | What it does |
|---|---|---|
| Rules and numbers | `app/game/content.py` | Every dial (`TUNE`), items, zombie kinds, spawn tables |
| Simulation | `app/game/sim.py` | One shared `World`: zombies, survivors, fights, wounds. Pure Python, clock passed in |
| Spawning | `app/game/spawn.py` | Packs and stashes per map cell, the same for everyone, reshuffled daily |
| Pacing | `app/game/director.py` | Quiet, then a straggler, a group ahead, or a noise. The policy is pluggable |
| Storage | `app/game/store.py` | One JSON blob per survivor; what happens to the body while you are away |
| Loop | `app/game/hub.py` | Steps the world five times a second, sends each player what they can see |
| Socket | `app/routes/ws_routes.py` | `/ws`: positions and actions in, snapshots and results out |
| Client | `app/static/` | One canvas (map tiles, fog, clay sprites), DOM buttons, recorded Foley/voice samples and a quiet synthesized heartbeat. No build step |

A kill is a kill for everybody until the day rolls over. Actions are judged the moment they arrive,
not on the next tick, which is what keeps a tap feeling instant.

## Tests and tuning

    python -m pytest -q
    python -m tools.walk_bots --walks 80 --minutes 20 --policy all     # pacing numbers from scripted walkers
    python -m tools.make_assets <folder of raw renders>                 # raw PNGs -> app/static/assets

## Credits

- Map data and tiles © OpenStreetMap contributors (ODbL).
- Sprites, badges and scenes were generated with Qwen-Image 2.1. See `ASSETS_LICENSE.md` for what that means if you reuse them.
- Recorded action audio credits are in `app/static/assets/audio/CREDITS.txt`; the browser also synthesizes heartbeat and alert sounds.

- Additional action poses were generated with OpenAI image generation using the existing clay characters as references. Raw atlas: `art/action_atlas_01.png`.
- A second Qwen-Image batch (six more zombies, `zed_s10` to `zed_s15`, and four more survivors, `surv_p4` to `surv_p7`) used the same prompts and style clause; the raw renders and the job list are in `art/raw_v2/`. The survivors are not selectable in the game yet.
- The same folder holds the eight gear sprites made for the survivor overlays and dropped items (helmet, rucksack, school bag, boots, leather jacket, fire jacket, fire trousers, gloves).


## Shelter life: Phases 4–8

Most actions now happen in the world: tap furniture, a resource, a cupboard or an opening for up to three actions. More opens a focused drawer. Search shelves and storage use quantity transfers; workbench/campfire/furnace cards show their own recipes. The quick belt offers gear, drinking water, food, urgent treatment and Build.

Pack and world drawers default to32% of portrait height above the combat controls. Expanded views are optional; landscape drawers sit to the side. The camera stays in the free world area. Tapping clear ground, movement keys or combat closes drawers; incoming hits close them too. The world continues running. **Pack / Worn / Home / Work / Health** remain for detailed equipment, naming and the full catalogue.

- **Worn:** clothes protect covered body parts according to condition. One backpack
  adds capacity; every carried item still adds weight. Carrying more than capacity slows hauling
  and recovery; store heavy supplies before fighting. Take clothing off before storing it.
- **Home:** choose and name a room cupboard. Select a quantity and storage container
  to deposit/retrieve within 2.7m, with no wall in between. Home supplies and construction
  survive a new survivor life; carried possessions and skills belong to that life.
- **Work:** follow the next shelter goal, walk to furniture/resources, and perform timed
  work. Dismantle empty furniture, rest in beds, repair gear and reinforce openings while
  keeping an alternate escape. A smashed window or door can be boarded over again. Attacks or movement interrupt work without spending its recipe.
- **Build:** keep materials in your pack, select a recipe, tap a nearby grid location,
  review the preview, rotate if needed, then **Build here**. Keep exits and people clear.
  Wood/stone/metal barriers block movement and can be broken by zombies; gates can open.
- **Gather:** rubble provides starter materials and fuel. Make a stone axe, cut logs and
  saw planks; make a pickaxe at a workbench, mine stone/ore, and smelt ore with wood fuel
  at a furnace. Depleted nodes stay depleted; explore other areas for new deposits.
- **Recover:** food, drinking water and rest address separate needs. Collect barrel water
  and filter it at a cooking fire. Forage/fish, cook meals, plant garden beds, repair a lantern,
  or rebuild a noisy fuelled generator to power nearby cold storage. Fresh food spoils;
  a powered refrigerator slows spoilage tenfold. Offline needs are capped. Food freshness and generator fuel pause while the owner
  is away; barrels and crops can be ready when you return.

Furniture/interiors, doors and windows, individual trees, ponds, deposits, locks and alarms are
generated for gameplay. A generated door or window is placed on a wall that faces open ground,
not one shared with the next building. They do not identify actual room contents, accessible land or real security.
Barrels currently collect on a forgiving timer and crops mature in five minutes;
weather/season simulation, shared bases, vehicles and corpse recovery remain follow-up work.
See [SURVIVAL_ROADMAP.md](SURVIVAL_ROADMAP.md) and [BUILD_CHECKLIST.md](BUILD_CHECKLIST.md)
for scope and release evidence.
