# OSZ survival roadmap: a reason to come home

Review date: 2026-10-10. Baseline: gameplay `09aa693`, release notes `4fae07c`.
Tom requested a review of the gbrain gameplay references and the missing storage,
inventory, clothing, armor, furniture, bases, construction, mining and tree cutting.
The reference review describes the baseline. Core Phases 4–8 are now implemented;
release verification is tracked in BUILD_CHECKLIST.md. Later world/story work is
separately scoped below.

## Reference review

Located gbrain page `mnt-c-users-user-downloads-ppw-zomboid-research-reference`.
Reviewed the cached one-frame-per-second sheets for both user-supplied Shorts
and the Steam trailer. Live YouTube fetches were throttled; the cached footage
and sheets are available in Claude's `scratchpad/pz` directory. Frame sampling
supports scene/UI observations, not precise animation timing or long-session balance.

- [RinYT: Project Zomboid is Boring](https://youtube.com/shorts/GXVmE-Dgi4o):
  a crowd overruns a furnished doorway, a locked exit forces a window escape,
  a weapon is dropped, and the player treats distinct injuries while still pursued.
  Overweight inventory and nearby furniture are visible. These are edited highlights.
- [Big Bad Beaver: How to Play Project Zomboid in 60 seconds](https://youtube.com/shorts/OzEjXR9DyZc):
  separate bag inventory, clothing, condition and body protection, place-specific
  supply runs, and shove/knockdown/finish combat. Frame sheets show a firefighter
  jacket and trousers with protection properties, plus tool and clothing loot.
- [Project Zomboid Steam page and trailer](https://store.steampowered.com/app/108600/Project_Zomboid/):
  furnished homes, unseen rooms, night lighting, fences, crates, crops, fishing and
  a generator establish a home-life loop between dangerous excursions. The official
  feature list connects chopping trees and sawing wood to scavenging and fortification.
  Trailer scenes are edited promotion, not a measure of normal play duration.

Mining was requested by Tom. These two Shorts do not establish a mining loop;
ore gathering and smelting below are our proposed OSZ expansion, not a video observation.
Historical gbrain version/date and numerical claims were not needed or revalidated here.

## What existed at the reference-review baseline

| System | Existing OSZ baseline | Missing gameplay |
| --- | --- | --- |
| Inventory | Persistent Pack, quantities, weight, weapon condition, Hold/Eat/Drink/Drop/pickup | Bags, equipment slots, categories, batch transfers and comparison |
| Storage | One-time loot containers and persistent claims | Reusable containers accepting deposits/withdrawals; persistent ground items |
| Clothing / armor | No clothing catalogue or worn slots; wounds select body parts | Wearable protection by covered body part, condition, repair and tradeoffs |
| Furniture | Generated rooms and loot icons | Visible, useful beds, cupboards, counters, chairs and workbenches |
| Home / defenses | Rooms, shared doors/windows, collision and zombie battering | Home designation, storage, barricades, repairs and destructible construction |
| Gathering / crafting | Hand axe is a weapon; tools appear as loot | Chop trees, salvage furniture, saw logs, material recipes and tool use |
| Survival needs | Endurance, panic, wounds/infection, eating calms, water restores endurance | Hunger, thirst, sleep, cooking, water collection and useful utilities |
| Longer stories | Exploration, XP/skills, combat and death card | Supply goals, defending investments, corpse-pack recovery, richer place types and shared projects |

Code reviewed: `app/game/content.py`, `sim.py`, `store.py`, `app/models.py`,
and the Pack UI in `app/static/js/main.js`. The baseline item catalogue had
ten codes. World drops are held in `World.drops`; they are not durable storage.
Search caches are personal discovery rewards, not general storage containers.

## Design direction

The next playable loop is:

**Choose a home → scavenge useful gear/materials → haul it back → store/equip/craft
→ improve the home → survive the next outing or an approaching crowd.**

Every feature should support a choice: carry food or lumber; light protection or
heavy protection; quiet salvage or noisy chopping; reinforce the front door or
leave a second escape route. Keep phone tap walking, Stop, Exit and single-mode
GPS behavior usable throughout. New panels must not take over the whole game flow.

## Phase 4 — Equipment, inventory and reusable storage

- [x] Make Pack easier to use: categories, weight/remaining capacity, condition,
  explicit worn/held states, quantity selection and readable item comparisons.
- [x] Add worn head/torso/legs/hands/feet/back slots. Start with ordinary clothes,
  boots, gloves, leather outerwear, firefighter gear and a backpack.
- [x] Apply scratch/bite protection only to covered body parts; damage clothing
  when it intercepts an attack. Good armor reduces risk rather than guaranteeing
  immunity. Show coverage, condition and any movement cost before wearing.
- [x] Make bags meaningful through bounded capacity benefits, without infinite
  nested bags or inventory duplication. Continue counting the mass of all carried items.
- [x] Add a reusable storage crate or cupboard in a supported room: deposit,
  withdraw, quantity transfer and capacity feedback, at actual interaction range.
- [x] Let the player name/mark a home and see distance/direction back, with manual
  tap walking. GPS recenter must not move the home or stored supplies.
- [x] Persist storage separately from a survivor life; start with owner-only
  access. A death creates a new survivor but leaves the player's home supplies.
  Future shared bases require explicit membership and permissions.
- [x] Make deposits/withdrawals durable and atomic with inventory changes;
  retries, disconnects and simultaneous taps must never create or erase items.
- [x] Acceptance (public phone run; three app replacements; death rule seen live;
  protection, wear and old saves by test): find clothes/bag, equip them, haul supplies home, deposit part
  of a stack, leave, return and retrieve it; reload and app replacement preserve
  exact quantities, condition and worn slots. Verify protection and wear at the
  correct body parts, old-save compatibility, death ownership and phone layout.

## Phase 5 — Furnished shelters and fortification

- [x] Furnish rooms deterministically by type: kitchen cupboards/counters,
  bedroom bed/wardrobe, workshop bench/shelves, living-room seating.
- [x] Use visible furniture as actual storage/rest/work surfaces. Keep the two
  RNG building searches as extra hidden-cache discovery; exhausted discovery
  attempts must never disable normal furniture access or home storage.
- [x] Add limited move/dismantle furniture actions, with weight, tools, time and
  noise. Require all placed furniture to leave entrances and reachable routes.
- [x] Barricade/reinforce doors and windows using scavenged planks/nails/tools;
  show defense health and permit repair/removal. Zombies damage these defenses.
- [x] Add a small home screen showing stored food/water, defenses and next useful
  supply targets. A home marker alone does not count as a completed base system.
- [x] Acceptance (public site 0.2.6 with real controls and no fixture, then an app replacement;
  also a local run; a building with no exit is left over the roof): furnish/store/rest, reinforce an opening, observe zombie damage,
  repair it and escape through another opening. Nothing can permanently trap a
  survivor, and furniture/storage/defense changes survive reload and replacement.

## Phase 6 — Tree cutting, salvage, crafting and construction

- [x] Add finite, persistent trees/resource nodes in suitable game areas; show
  generated resources honestly where detailed map vegetation data is unavailable.
  Current raster tiles cannot provide authoritative individual tree positions.
- [x] Chop a tree with an axe: timed noisy work, endurance cost and tool wear;
  leave a depleted node/stump and heavy logs, not instantly awarded planks.
- [x] Saw logs into planks; salvage furniture for wood, nails, cloth and scrap.
  Useful loot adds a hammer, saw, nails, cloth and repair materials.
- [x] Add a compact recipe panel: missing ingredients/tools, result and duration.
  Initial outputs: bandages from cloth, simple repairs, crates, barricades, fences,
  gates and a workbench. Grant Carpentry experience for completed useful work.
- [x] Place simple structures on a metre-based game grid with a preview, rotation
  and collision validation. Persist player-built objects independently of the
  OSM cache, which can refresh or expire. Zombies can break defenses.
- [x] Preserve usable exits and approach paths, replan tap routes around new
  obstacles, and avoid building inside other actors or unsupported geometry.
- [x] Acceptance (chop, saw, build, fence, zombie damage to it and repair on the public site;
  crate and gate on a local server; interruption and conservation by test): chop → haul → saw → store → construct a crate/fence/gate →
  repair damage. Interruptions, retries and restarts conserve materials and nodes;
  noisy work can attract threats without becoming mandatory combat every time.

## Phase 7 — Food, water, sleep and working utilities

- [x] Add gradual hunger/thirst/sleep needs with visible effects; keep endurance
  distinct from sleep debt. Short phone sessions must still make useful progress.
- [x] Add simple cooking, beds/rest, water collection/filtering and rain barrels.
  Define forgiving, capped offline effects before enabling needs on live saves.
- [x] Add a useful lantern and later powered appliances/generator: fuel, maintenance,
  noise, light and clear benefits. Initial refrigerator furniture is ordinary
  storage until food spoilage and power are actually implemented.
- [x] Introduce small farming/foraging/fishing loops tied to food and water demand,
  with food freshness and power benefits. Weather/season pressure is follow-up work.
- [x] Acceptance (public phone run; a long real absence is covered by test only):
  a supply trip sustains the survivor, a prepared home helps recovery,
  and a working resource system makes the next trip a choice; returning after time
  away is understandable and does not cause an unexplained offline death.

## Phase 8 — Mining and metalwork

- [x] Add finite rock/quarry and ore nodes, pickaxes, noise/endurance/tool wear,
  depletion and explicit refresh rules. Placement uses appropriate mapped land use
  where available, otherwise labelled game-generated deposits.
- [x] Stone first supports useful recipes; ore then requires a furnace, fuel and
  metalworking tools to become reinforcement, repair parts or advanced equipment.
  Avoid an extra mining grind that has no use in shelter or survival.
- [x] Extend material construction to stone/metal after wood placement works well.
- [x] Expand destination-specific supply leads (medical, fire/police, hardware,
  food), day/night lighting, generated locks/alarms and existing crowd encounters.
- [x] Acceptance (public phone run and app replacement): gather → process → craft a useful upgrade; deposits, buildings
  and resources persist without duplication, with clear mobile feedback.

## Later world and story scope

Tom authorized this expansion on2026-10-12; active ordered checklist is NEXT_SURVIVAL_PLAN.md. N1 recovery shipped0.13.0; N2 curtains/glass is ready for0.13.1. The original phase history below is retained.

- [ ] Survivor corpse-pack recovery, vehicles/hauling, occupations/traits,
  shared-base membership and broadcasts/world events. These require their own
  scope and acceptance gates rather than being silently included in this phase.

## Implementation and release rules

- Keep simulation rules on the server and existing single-replica World architecture.
  No language rewrite is required for these systems.
- Add durable world-object/container state with stable IDs, ownership, revisions
  and transactional item transfers. Existing survivor JSON gains defaults for new
  equipment/needs; migrations preserve every current session and claimed cache.
- Reuse the existing action channels, noise, endurance and condition systems for
  work actions; interruption must not silently consume a full recipe or repeat XP.
- Separate generated furniture/resources from player mutations. Never discard
  deposits, placed objects or depletion when map caches refresh or cells unload.
- Gameplay release gates include phone controls, inaccessible-storage prevention,
  conservation of items/materials, old saves, death rules and actual app replacement.
- First target: a 10–15 minute outing with equipment discovery, a carry decision,
  supplies safely stored at home and a visible next objective. Later targets add
  fortification and resource processing to that same loop.
- The original reference-review commit changed documentation only. The Phases 4–8
  implementation releases after the mobile, persistence and deployment gates pass.
