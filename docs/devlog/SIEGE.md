# Siege mode — design for v0

Written 2026-11-03 02:20 CST, before any siege code. BACKLOG item 4. Research behind it:
memory note `osz-siege-mode-vampire-survivors` (Mad Forest's wave table is a sawtooth with a boss every
five minutes). We borrow the **pattern** only: no names, art, sounds or numbers presented as theirs.

## What it is

"Siege: survive 30 minutes." A second button on the title screen, next to Play. Survival stays exactly
as it is: the siege is a separate, solo run in its own small world, and nothing in survival changes
unless the siege brings something home.

- **Where:** Daley Plaza in the Chicago Loop, by the Picasso (41.88355, -87.62985). A real plaza with real
  buildings round it (the Richard J. Daley Center to the north), from the map region the server
  already caches (`dp3wmb`). No new map requests.
- **The arena:** a circle with a 35 m radius round that point. You can't walk out of it: the server
  holds your position inside. Zombies arrive from the ring just outside sight, from all directions.
- **The light:** fixed at dusk (light 0.6), whatever the real clock says, so every run is the same fight.
- **You start with:** a baseball bat, 2 bandages, full health. Not your survival survivor or their kit;
  your survivor waits at home, safe, for the whole run.

## The 30 minutes

- **A wave table, as data** (`app/game/siege.py`, `WAVES`): for each minute, the number of zombies that
  must be alive at least ("the floor"). When fewer are alive, more arrive, a few a second, until the
  floor is met. It's a sawtooth: it climbs, falls back to a breather, then climbs higher, with spikes.
  The shape is Mad Forest's minute by minute (15, 30, 50, 40, 30, 10, 20, 80, 100, 30, 10, 300, ...),
  **scaled down** to what one survivor with a bat can face and what this server can hold. The scale is
  measured, not assumed; the peak is not 300. Every number is in the table, so it can be retuned
  without code.
- **A boss every 5 minutes** (5:00, 10:00, 15:00, 20:00, 25:00): one huge zombie with a health bar,
  slower than the rest, hits harder, can't be knocked down by a shove. Each is stronger than the last.
  **Telegraphed:** 10 seconds before, a banner ("Something big is coming — from the north-east"),
  a loud groan, and a red marker on the arena edge where it will walk in. It drops a chest when it dies.
- **Level-ups:** kills give experience (bosses give a lot), plus a little for every second alive.
  Each level offers **a choice of three upgrades**; the run pauses while you choose (it is solo), and
  picks the first one for you after 20 s. Thresholds are set so the first levels come every 20 to 40 s.
  The pool (all ours, all small, stacking):
  heavier swings (+15% damage), quicker recovery (−10% swing time), wide arc (a swing also hits one
  more zombie in reach), thick jacket (−12% damage taken), fleet feet (+8% speed), second wind
  (heal 35, stop bleeding), slow mend (regain 0.4 health a second), shoulder charge (shoves knock down
  more and push further), deep breath (swings and shoves cost 25% less endurance), better weapon
  (bat → crowbar → hand axe), a roll of bandages (+2).
- **Chests:** every boss drops one, and one appears in the arena at random spots every 3 minutes
  (marked on screen). Walk onto it to open it: one free upgrade, picked at random from what you could
  still take, and one find for the haul. No paid anything, ever: viewers may be minors.
- **The end at 30:00:** a rescue helicopter. From 29:00 it is heard ("Helicopter inbound: hold on 60 s"),
  the last minute is the heaviest of the run, and at 30:00 it lifts you out: "EXTRACTED". That is the
  only way to win.
- **On screen:** a timer counting up to 30:00 at the top, score, level, kills, the next boss in, and
  the boss's health bar when one is out. On death the timer freezes red on the end card ("Siege over at
  12:34").
- **Score:** 10 a kill, 1 a second alive, 500 a boss, 3000 for extraction.

## Loot going home (minimal in v0)

Each chest adds one find to the run's **haul** (bandage, crisps, water, nails, plank, a knife or a
crowbar). When the run ends, extracted or dead, the haul goes into your survival home's storage, as far
as the home's capacity allows. No home: it stays in Chicago, and the end card tells you to set a home in
survival first. That's all of v0's link between the modes; ranks, unlocks and meta upgrades are later.

## How it's built

- `app/game/siege.py`: the wave table, bosses, upgrades, chests, timer and score as plain data and one
  `SiegeRun` class, which owns its own `World` (the same simulation survival uses, so zombies bite and
  grab exactly as they do there) with only the buildings near the plaza and no ambient spawns.
- `app/game/siege_hub.py`: runs every siege's world five times a second, on its own loop, with its own
  websocket (`/ws/siege`) using the same login token. The frame is the survival frame plus a `siege`
  block, so the client draws it with the code it already has.
- Survival hooks are optional and off by default: a survivor may carry upgrade modifiers (empty in
  survival) and a zombie may be a boss (never in survival). Survival's tests must pass unchanged.
- A siege counts as a player against the server cap, and there is a separate cap on concurrent
  sieges, set from the load test below.

## Bars, written before tuning

1. **Death times spread across the 30 minutes** (scripted bots, at least 20 runs): no more than half
   dead before 10:00, fewer than 1 in 5 reaching 30:00, and deaths in at least four of the six
   five-minute blocks.
2. **Concurrent sieges:** find the number this machine holds with tick time under the 200 ms budget
   and ping p95 under 500 ms, on its own and beside survival players.
3. **Survival unchanged:** the whole existing test suite passes; the danger check (scripts die 3 to 5
   in 10) is not rerun unless survival code paths change behaviour.
4. **It works in a browser:** one recorded clip shows the start button, the timer, a level-up choice,
   a boss warning and the end card.

## As built and tuned (added 2026-11-03 03:20; the design above is left as first written)

What tuning changed from the design, all siege-only data in `app/game/siege.py`:
- Start kit: a bat and **4** bandages (design said 2).
- Always at fighting pace (survival's 3x exploring pace outran every wave), walking costs a quarter of
  survival's endurance, and an **adrenaline trickle of 1.5 endurance a second** even mid-fight
  (survival only regains it standing still; in a siege that never happens). "Deep breath" adds +1.0.
- Base tuning is `classic`; zombie speed ramps x1.0 to x1.8 (public's pace) and health x1.0 to x2.5
  over the 30 minutes. Floors = shape x 0.09 x a ramp from 0.6 at 0:00 to 1.4 at 30:00, refilled at 1.5 a second:
  `2, 2, 3, 2, 2, 2, 2, 6, 7, 2, 2, 24, 2, 13, 2, 9, 9, 2, 6, 10, 10, 32, 22, 33, 34, 12, 18, 36, 37, 38`.
- Bosses at half the designed health and 0.7 of their bite: 110 / 170 / 240 / 310 / 400 health,
  bites x1.54 to x2.66. They stagger when hit but can't be knocked down or pushed.
- Levels: 3 + 2 x level experience to the next; a kill is 1, a boss 12, and staying alive gives 1 every 6 s.
  In the recorded run the first choices came at 0:30 and 1:06.
- Rooms near the plaza hold survival's loot tables; siege frames leave them out. Finds come from chests only.
- Tap-to-walk asks the server for a route; in a siege that's a straight line held inside the arena.
- Tuning tools: `tools/siege_sim.py` (offline, the same simulation), `loadtest/siege_bots.py` (real
  socket), grids in `player/siege_tune/`. Load-test knob `OSZ_SIEGE_START_S` (never on a played server).
