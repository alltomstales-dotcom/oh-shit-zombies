# OSZ shared progress checklist

Claude and Codex are collaborating on the existing OSZ checkout. Last updated 2026-10-12.
Active pickup: [CURRENT_STATUS.md](CURRENT_STATUS.md). Historical handoffs below are retained; newest evidence is at the end.

- [x] Review original direction and Claude's implementation; preserve its changes.
- [x] Isolated local desktop movement smoke test (60 fps; no JS errors).
- [x] Faster fresh desk movement: 2.0 m/s instead of 1.4 m/s.
- [x] Authoritative fatigue/leg wound/critical health speed penalties, and distance-based endurance use.
- [x] Share the authoritative movement pace with client prediction.
- [x] Suppress repeated GPS watch error toasts.
- [x] Add distinct swing, push, zombie lunge and zombie damage feedback.
- [x] Generate and extract authored clay action poses; survivor swings/pushes and matching shambler variant attacks.
- [x] Add both missing PWA icons using existing clay art.
- [x] Existing tests plus movement and production configuration regressions passed: 43 tests. Async SQLite requires host execution here; sandbox connections stalled before fixture completion.
- [x] Verify movement and complete frame alignment in desktop Chromium; mobile combat: 8 actions, 2 kills, health 82.7, no JS errors.
- [x] Bot pacing sample: 12 ten-minute walks per policy, density 1.3. Walkers: no grabs/deaths; mixed: 0 deaths, 1 infection; fighters: 4 deaths, 6 infections.
- [x] Commit and push the complete ready OSZ project to private Gitea.
- [x] Deploy to a separate new Railway project with persistent Postgres.
- [x] Verify initial public HTTPS, session/WebSocket flow, reload persistence, assets and phone layout (412px viewport, no horizontal overflow, no JS errors).
- [x] Single tap-to-walk mobile navigation; GPS anchors the area, ignores drift/coarse fixes, and recenters after physical travel beyond 200m plus uncertainty.
- [x] Verify Stop, preserved virtual walking during GPS updates, edge uncertainty and coarse-fix rejection in desktop Chromium with phone emulation.
- [x] Manual SCREAM plus random severe-panic screams, visible sound ring, synthesized voice and server cooldown/range tests.
- [x] Increase the existing close-combat camera zoom by 1.5x.
- [x] Verify navigation, scream and combat zoom update on public Railway.
- [x] Implement persistent survivor experience and five skills with earned progression and bounded benefits. Local phone playtest earned 60 XP through two searches and exploration, reached level 2 and Scavenging 1, and preserved exact progression on reload; 51 regression tests pass.
- [x] Verify progression on public Railway and across a replacement app instance. Two genuine searches plus exploration earned 60 XP, level 2 and Scavenging 1; exact progress persisted through deployment `<deploy-id>`. Existing phase-1 session/loot remained compatible.
- [x] Make searchable containers visible and verify search-to-pack loot flow. Local phone run discovered a medical case, walked to it, received disinfectant, dropped/picked up gear, drank water and retained the empty marker across reload; no JS errors.
- [x] Verify this exploration release and claimed-container state across a Railway redeploy. Replacement deployment <deploy-id> SUCCESS, old instance REMOVED; empty marker and consumed water persisted with the existing session.
- [x] Building phase: fetch real structure outlines; generate rooms, doors and windows; implement entry, collision, sight and interior loot.
- [x] Verify survivor data survives an app redeploy: existing token accepted without a replacement session, survivor born 2026-10-10T14:56:49Z still present after the 15:08 deployment.
- [x] Send Tom the phone-playtest URL and controls.

## Playable buildings (complete)

- [x] Fetch actual OSM extract: 84 closed Minneapolis building ways, 83 supported layouts.
- [x] Deterministic fictional rooms, entrance/room doors, windows, wall collision/visibility and bounded path finding; entrance clearance regression fixed.
- [x] Background cache module and additive persistent region/opening tables. Generated outage shelters are explicitly labelled by source. Tests verify cache and doors survive a fresh loader.
- [x] 61 regression tests pass across progression, loot and building foundation.
- [x] Wire the foundation into World/Hub, survivor/zombie movement, combat and interior loot. Wall collision prevents attacks/searches/pickups through barriers; zombies seek and batter openings; solid walls reduce sound.
- [x] Draw playable interiors and connect phone tap paths, door/window controls and room prompts. Background route planning uses an immutable geometry snapshot. New geometry/GPS placements clear wall overlaps.
- [x] Complete local two-room building excursion and real server restart persistence verification. 75 server tests and the client wall-rounding regression pass; both room claims, connecting door and window persist with an existing session.
- [x] Complete public Railway building excursion and replacement-instance persistence verification.

## Playtest targets

Fresh movement should let you reposition and escape a pack. Low endurance, leg wounds and critical health should make escape harder. Stand clear to recover endurance. GPS anchors the play area. The survivor moves using map taps/keys; real walking inside the 200m center radius is ignored. Real travel beyond that radius recenters the area. The threshold is based on the original GPS center, never virtual survivor position.

Swing and shove should read as different actions; zombie attacks should visibly wind up and strike. The authored zombie atlas currently matches shambler variant 8; other appearances retain procedural attack animation. Zombie damage marks persist as health falls. Additional character-specific frame sets can follow playtest feedback.

## Build boundaries

This is a first playable tension-loop build. Playable building interiors complete the required third phase. Hunger/thirst/tiredness needs, corpse survivors carrying packs, bases, recipes and seasons remain later work. Live ZombieQuest is a separate project. Deploy OSZ from a native Linux staging directory because prior Railway uploads from WSL /mnt/c corrupted snapshots.

## Art provenance

Existing base clay art: Claude's Qwen-Image renders. Action atlas: OpenAI built-in image generation using survivor p1 and zombie s8 as references. Raw atlas is in art/action_atlas_01.png; extracted WebP frames are in app/static/assets/. Prompt: 4 swing poses, 4 two-handed shove poses, 4 zombie lunge/swipe poses, consistent clay style, full-body transparent cutouts. Connected outlines are extracted rather than nominal grid cells because poses cross grid boundaries.

## Release state

Initial playable build committed and pushed to private Gitea as `8195027` (master). Public URL: https://osz-production.up.railway.app. Separate Railway project: `<deploy-id>`, service osz with one persistent Postgres and one app replica. Native deployment staging: /tmp/osz-railway-20261010. Initial deployment: <deploy-id> (SUCCESS).

User clarified the navigation model after the initial release: one mode, GPS only centers and ignores drift, free tap-to-walk wandering. 200m is approximately twice the normal daylight phone view width (~106m); combat zoom does not alter this threshold. Physical travel recenters only when the reported uncertainty circle clears the boundary; fixes coarser than 80m are ignored.

## Expanded goal

Tom explicitly requested completion through phases 1–3. See [PHASE_PLAN.md](PHASE_PLAN.md) for the required exploration/loot, experience/skills, and playable building-interior checklist. These now belong to the active goal.

Latest gameplay release: `357bd3d`, deployment `<deploy-id>` SUCCESS. Public phone test passed SCREAM, Stop, tap movement, drift/uncertainty/coarse-fix handling, 200m recenter, reload and reconnect. Claude memory and revision-aware gbrain shared note updated with release evidence and expanded phases1–3.

## Phases 1–3 complete — 2026-10-10

Latest gameplay commit `e4432f7` is pushed to private Gitea master. Final separate OSZ Railway replacement `<deploy-id>` is SUCCESS; prior `<deploy-id>` is REMOVED. Phone URL: https://osz-production.up.railway.app. Live ZombieQuest remains untouched.

All required phases are implemented and verified: exploration/searchable themed containers and pack use; persistent survivor XP/level and five bounded skills; real supported OSM building outlines with fictional ground-floor rooms, doors/windows, collision, interior loot, visibility/sound and zombie interaction, plus labelled generated shelters when geometry is unavailable.

Final local and public headful Chromium Pixel 7 excursions entered real building `osm:w:157025243`, searched both room containers, opened the connecting door and window, screamed and physically exited using EXIT BUILDING. They checked XP>=50, level>=2, Scavenging>=1, supplies added to pack, 412px layout without overflow and no JS errors. These final excursions needed zero combat actions; earlier local excursion fought an interior zombie. Public replacement then preserved both EMPTY room containers and shared openings with the existing session. Older phase-1 empty container/consumed water and phase-2 exact 60 XP/level2/skills also survived. Public phone navigation passed tap walking, Stop, preserved virtual goal during GPS updates, drift/coarse-fix rejection, 200m physical recenter, reload and reconnect. Future-timestamp SCREAM render regression passed.

75 server tests and standalone client wall-rounding regression passed. Final exit correction: server sends survivor coordinates at nine decimal places; client leaves 1cm tolerance beneath the authoritative .28m body clearance to prevent rounded positions beside walls deadlocking prediction. Earlier precision/replanning and atomic geometry restoration fixes remain included.

Phone instructions: allow GPS to center your area, then tap to walk; Explore points toward supplies. Tap containers and Search, then use/equip from Pack. Approach a building door, OPEN ENTRANCE, tap inside, open room doors/search rooms; EXIT BUILDING routes outside through the open entrance. SCREAM attracts nearby zombies. Stand clear to recover endurance.

Limits: interiors are generated fictional single floors, not surveyed floorplans. Unsupported complex/multipart or huge footprints are skipped. More character-specific attack frames, deeper needs/crafting/bases and richer buildings remain later work. Current app intentionally runs one replica for its in-memory simulation with persistent Postgres. Deployment must use native Linux staging /tmp/osz-railway-20261010; WSL /mnt/c uploads previously corrupted snapshots. Railway config-as-code migration is due before 2026-12-01.

Standing authorization: continue authorized implementation, testing, commit/push and OSZ deployment without repeated user confirmation. Checklist and phase plan now record the completed scope; preserve historical notes above.

## Pixel phone feedback and faster exploration — 2026-10-10

Subsequent reference review and next phases are tracked in
[SURVIVAL_ROADMAP.md](SURVIVAL_ROADMAP.md). Storage, worn equipment, furniture,
construction and gathering are still planned; do not count them as implemented.

- [x] Fix EXIT BUILDING from closed entrances and rooms; walk to and open doors in sequence, with server distance/collision checks.
- [x] Recover exit routing after a mobile WebSocket reconnect.
- [x] Triple walking outside combat (fresh 6m/s); keep combat at 2m/s with fatigue/injury penalties.
- [x] Add four-times current-speed SPRINT, 12 stamina/second only while moving, 10-stamina start threshold, automatic stop at exhaustion and explicit Stop.
- [x] Fit interior exploration to the phone width, improve character/container scale and touch selection, retain 1.5x closer combat.
- [x] Use half-mile (804.672m) GPS recenter; ignore drift/coarse fixes, require three consistent outside fixes over eight seconds, preserve virtual movement, and keep walking available with weak indoor GPS.
- [x] Guard intentional GPS relocation against stale server snapshots.
- [x] Add two completed RNG building-search attempts per survivor/building. Persist attempts and discovered themed caches; interrupted searches use no attempt, and each discovered cache must still be searched for loot.
- [x] Replace frequent synthetic effects with 40 recorded Foley/voice MP3 clips (357KB total), randomized variants, footsteps, real doors, muted/background audio handling and bounded voice count. Keep source/license credits accessible in the menu.
- [x] 82 server tests, client wall-rounding regression and JavaScript syntax checks pass.
- [x] Local and public Android touch tests pass closed-door escape, search/discover/loot/exit, sprint toggle, recorded audio load/play/mute, indoor GPS drift and weak-GPS navigation; existing loot/XP and the two new search attempts/caches survive replacement.
- [x] Final deployment GPS/reconnect checks and Claude handoff recorded. Final gameplay `09aa693`, Railway `<deploy-id>` SUCCESS; public half-mile recenter, saved reload/reconnect, closed-door escape with dropped socket and search persistence pass with no JavaScript errors.

Tom's actual report revealed gaps beyond the original open-entrance browser checks. Read-only inspection found his survivor exhausted, about 80 health and existing XP intact. Tests now include starting inside a closed building and losing the socket during Exit, plus a 150m-accuracy indoor GPS fix. Phone instructions: refresh after deployment, tap to walk, EXIT BUILDING handles closed doors, stand still/drink to recover stamina, SPRINT toggles a burst, SEARCH BUILDING has two discovery chances and revealed containers require their own Search.

Real hardware sound perception and long-session balance remain feedback work; browser tests use Android touch emulation at 393x851 and Pixel 7 settings, not a physical Pixel 9a. Interiors remain fictional ground floors in supported OSM outlines.


## 2026-10-10 — Phases 4–8 implementation in progress

Tom expanded the goal to completing the survival loop through Phase 8. Claude
handoff: these changes are local work until the release gate below is checked.

- [x] Wearable equipment, condition-scaled coverage, one backpack slot, categorized Pack.
- [x] Owner home profile independent of survivor life, atomic partial storage transfers.
- [x] Functional furniture, timed salvage/rest/move, window defenses and escape protection.
- [x] Finite generated resources, tools, recipes, construction preview/rotation and collision.
- [x] Hunger/thirst/sleep, food freshness, cooking/filtering, gardening/fishing and utilities.
- [x] Stone/ore mining, furnaces, smelting and metal construction recipes.
- [x] Local mobile equipment/storage/leave/return browser loop; zero JavaScript errors.
- [x] 119 server tests and client wall rounding regression pass.
- [x] Long mobile wood → stone → ore → smelt → metal excursion (genuine gathered materials; survivor later died during utility continuation).
- [x] Mobile cooking/water/power/refrigeration loop (public site, 0.2.3; details below).
- [x] Restart and live app replacement preserve resources, storage and construction (three replacements; details below).
- [x] Commit/push to Gitea, deploy separate OSZ Railway, update shared Claude/gbrain notes.


## 2026-10-10 evening — Claude: release validation, faults found by playing, share readiness

Codex's session ran out with the last three boxes above open. Claude picked up at 18:00 CDT.
Live is **0.2.6**, gameplay `195dffa`, Railway deployment `2c867d30` SUCCESS,
https://osz-production.up.railway.app. One app replica, Postgres, ZombieQuest untouched.

Commits: `0c52d13` endurance does not recover during work (Codex's change, committed as written),
`614c9cb` 0.2.0, `e6d5081` 0.2.1, `f6cfad1` 0.2.2, `6b69ebc` 0.2.3, `12317e3` 0.2.4,
`5080cfc` 0.2.5, `195dffa` 0.2.6.

### Faults found and fixed

- [x] **Whole server froze when players were in different towns.** A noise or a reach test checked
  walls against every zombie in the world before checking distance, and the wall search walks a
  22m grid between the two points. Fixed at both call sites, with a hard limit on the span, a
  regression test, and a watchdog that logs every thread and restarts the app if the loop stalls 45s.
- [x] **Walks of several blocks were refused** ("open a nearby door or window first"). The route
  search now scales its budget with distance; a 444m downtown route plans in 0.11s.
- [x] **A new survivor could be killed standing still within half a minute.** Nothing notices a
  survivor for the first 40s of a life unless they walk 15m or fight.
- [x] **Busy map servers left real streets with placeholder shelters for a day.** One retry, a
  20MB fallback limit, an hourly re-check, and neighbouring regions load before they are reached.
- [x] **Doors opened onto the next building's wall.** The entrance went on the longest wall, which
  in a terrace or city block is often shared. In a downtown Minneapolis sample of 235 buildings,
  31 had no way out and 81 had only one. Doors and windows facing a neighbour now move to a wall
  facing open ground, keeping their ids and saved state, independent of map load order. Same
  sample afterwards: 2 with no way out, 5 with one.
- [x] **A closed gate could never be opened; fences, gates and barriers could never be repaired or
  dismantled.** The reach test counted the object's own barrier as a wall in the way.
- [x] **"Walk here" to a fence or gate was always refused.** The route now ends beside it.
- [x] **Nobody stays stuck in a building.** The two buildings in the sample that still had no way
  out (one enclosed by its neighbours, one with a room cut off by its own partition) are covered
  by a last resort: when EXIT BUILDING can plan no exit, the survivor is put on the nearest open
  ground and told they climbed out over the roof. Checked on the public site in both buildings.
- [x] **A smashed window or door could never be boarded again**, so a home stayed open for good
  once zombies broke in. Boards now go over a broken frame and hold until they fail.
- [x] Session rate limit keyed on the real client address behind the proxy.

### Share readiness

- [x] Link preview (title, description, 1200x630 image), three-step how-to on the title screen,
  first-life tips, the next goal shown under the buttons, "Mapping nearby buildings…" while a new
  area loads, an Invite a friend button (share sheet or clipboard).
- [x] A new area maps in about 2s (Denver, real outlines). Two players in different cities: health
  checks 40–300ms throughout.

### Validation evidence

- [x] 137 server tests, client wall-rounding regression and JavaScript syntax checks pass.
- [x] **Public phone run, real controls, one session (0.2.3):** dismantle furniture, scavenge,
  stone axe, workbench, pickaxe, chop, saw planks, kindling, mine stone, furnace, mine ore, smelt x3,
  lantern, generator fuelled and on, cold-storage cabinet, cooking fire, rain barrel, garden, cook
  a meal, collect and filter water, fishing rod, fish, store food in the cabinet. Zero JavaScript errors.
- [x] **Replacement 1** (`8bab5edc`): same session, 7 built objects with their health, 10 depleted
  nodes, cabinet contents, exact inventory and tool condition, stored items, worn slots, home name.
- [x] **Death rule on the public site:** the test survivor was killed mid-run. The next life started
  at full health on the same account with all 7 built objects, cabinet and cupboard contents and
  depleted nodes intact; carried gear and skills were gone, as designed.
- [x] **Replacement 2** (`58ddf309`, 0.2.4): the above still holds; the home's entrance now leads
  outside and EXIT BUILDING uses it.
- [x] **Fortification on a phone layout (local server, same code, 0.2.4):** set a home, store in
  the cupboard, rest in a bed, build a fence, a gate and a crate, open and close the gate, repair
  the fence, partial deposit and withdrawal from the crate, walk home, board a window (80/80), a
  zombie batters it to 58, repair to 80, boarding the last exit refused ("someone needs it to
  escape"), leave by the door with the window still boarded. Two server restarts keep the objects,
  crate contents, cupboard, barricade and exact inventory. Zero JavaScript errors, no sideways scroll.
  Test fixture only: planks and nails were given rather than gathered, wandering zombies were
  switched off, and the one zombie was placed outside the window; a real scream drew it.

- [x] **Fortification on the public site (0.2.6), real controls, no test fixture, zero JavaScript
  errors.** New account `FortLive`, home in `osm:w:126116972`, 02:00–02:21 UTC 11 Oct:
  dismantled furniture for planks and nails; boarded the window 80/80 (over a frame zombies had
  already smashed); a zombie battered it to 61; repaired 61 → 80; left by the entrance with the
  window still boarded; built a fence (60); a zombie tore it down to 44; repaired to 60.
  Replacement `2c867d30` afterwards: same session, barricade 80, window still boarded, fence 60,
  home name and exact inventory unchanged.
- [x] On the older test account the first public barricade went from 80 to 0 and the window behind
  it was smashed while nobody was repairing it. That is what showed the re-boarding gap.

### Not verified

- A physical phone, iOS Safari, real GPS movement and how the sounds come across.
- Balance by a person. The scripted player died five times across the evening (once standing in
  the open sawing with a broken bat and 54 health). Noisy work in the open draws a crowd quickly.
- A long real absence (offline needs are capped in tests only).
- Twice a zombie was inside the test home while its window was boarded at full strength and both
  doors showed closed and intact. Where it came from was not established (most likely it was
  placed inside the outline). Worth a look before leaning on home defence as a safe room.
- Zombies reach a boarded opening only when they have a clear line to it; ones arriving on the
  other side of the building go for a door instead. A quiet street can take ten minutes to send one.
- Buildings are never unloaded from memory; map tiles come straight from tile.openstreetmap.org.
- Test players (ClaudeNewbie, ClaudeSuburb, ClaudeRural, ClaudeDenver, CityA, CityB, ClaudeFirst,
  FortLive, FortScout2, Sealed0Live, Sealed1Live and others) exist in the live database, with a
  boarded window and a fence left standing downtown.


## Handoff to Codex — 2026-10-11 (Claude)

Read this section first. The evening's faults, evidence and open points are in the section above.

### Where things stand

- Live: **0.2.6**, https://osz-production.up.railway.app (`/healthz` returns the version).
  master = origin/master = `bc5d095` plus this handoff; gameplay is `195dffa`; Railway deployment
  `2c867d30`. Working tree clean, nothing pending from Claude.
- Checked again on 2026-10-11: 137 server tests, the client wall-rounding regression and
  `node --check` on every client script pass.
- Every release box in this file and every Phase 4–8 acceptance box in `SURVIVAL_ROADMAP.md` is
  ticked, each saying where it was verified. The one open box is "Later world and story scope".
- Your uncommitted endurance change (no recovery during work other than rest) was committed as
  written in `0c52d13`.

### What changed in the code, by file

- `app/game/buildings.py`
  - `MAX_SPAN_CELLS` caps how far `candidates()` and `clear()` look in one call (the freeze fix).
  - `route()` now tries each standing spot from `beside_barrier()` and calls `_route()`, which is
    the old search with a budget that grows with distance.
  - `clear(..., ignore=None)` skips the built object with that id.
  - `Building.default_edges()`, `Building.relayout(entrance, window)` and
    `_layout(entrance=None, window=None, rooms=None)`: move the outside door and window, keep each
    opening's id and saved state by label, keep the rooms.
  - `Buildings.open_air(b, i)` and `Buildings.face_open_air(ids)`: called from `Buildings.add()`
    and from `building_loader.py` after a region is merged. Bumps `revision` once per call.
  - `barriers()`: a boarded opening blocks even when its frame is smashed.
- `app/game/survival.py`: `in_range()` passes `ignore=o['id']`; a broken opening can be boarded.
- `app/game/sim.py`: `World.climb_out()`, `World.arriving()`, distance checks before wall tests in
  `noise()` and `_reachable()`, and `_zed_obstacle()` batters a boarded smashed opening.
- `app/game/hub.py`: `_start_watchdog()`; the exit handler calls `climb_out()` when
  `exit_plan()` answers "no walkable exit for this outline".
- `app/game/content.py`: `arrival_calm_s=40`, `arrival_calm_m=15` in `TUNE`.
- `app/game/building_loader.py`: one Overpass retry, 20MB cap, hourly re-check of generated
  regions, neighbouring regions preloaded.
- `app/static/js/buildings.js`: draws and collides with boards over a smashed frame.
- Share items: Open Graph tags, `assets/share.jpg`, title-screen how-to, first-life tips, goal
  line, Invite a friend button, `x-real-ip` for the session limiter.
- New tests are in `tests/test_buildings.py`, `tests/test_survival_work.py`,
  `tests/test_building_world.py`, `tests/test_sim.py` and `tests/test_building_loader.py`.

### Releasing

    P=~/OhShitZombies; D=/tmp/osz-railway-20261010
    rsync -a --delete --exclude __pycache__ --exclude '*.pyc' $P/app/ $D/app/
    cp $P/Dockerfile $P/requirements.txt $P/railway.json $P/.railwayignore $D/
    cd $D && railway up --service osz --detach < /dev/null     # never from /mnt/c

Bump `VERSION` in `app/main.py` and poll `/healthz` until it shows. A replacement with no code
change is `railway redeploy --service osz -y < /dev/null`. Tests need the sandbox off:
`PYTHONDONTWRITEBYTECODE=1 ~/venvs/osz/bin/python -m pytest -q -p no:cacheprovider`.

### Playtest harness (in `/tmp`, lost on a reboot)

- Playwright: `/tmp/claude-1000/-mnt-c-Users-user-Downloads-PPW/<deploy-id>/scratchpad/pw/node_modules/playwright/index.mjs`.
- Claude's scripts: `/tmp/claude-1000/-mnt-c-Users-user-Downloads-PPW/<deploy-id>/scratchpad/osz/`.
  - `live-fort2.mjs`: public fortification run on a fresh account, resumable,
    `OPENING=Window|Entrance`. `fort2-snap.mjs pre|post` compares state across a replacement.
  - `public-resume.mjs`: the whole utilities loop on the public site, resumable.
  - `afterdeath.mjs`: persistence check that still works after the test survivor has died.
  - `live-exit.mjs`, `sealed-local.mjs`: leaving a building, including one with no exit.
  - `fixture_server.py` + `fortify-local.mjs`: the real app on port 8022 with a test-only
    `/__fixture` route (give items, place or clear zombies). It is not part of the app.
- Public test accounts: player 47, home "Phone shelter" in `osm:w:41763761`, session in
  `/tmp/osz-survival-public-storage.json`; `FortLive`, home "Fort test" in `osm:w:126116972`,
  session in `fort2-storage.json`. Do not print the session files.
- `/tmp/osz-phase8-persistence.mjs` now fails on the inventory comparison because that survivor
  died; use `afterdeath.mjs`. `/tmp/osz-public-survival-full.mjs` has `z.p.to` where `z.p.b` is
  meant and does not wait for endurance.

### Things that cost time

- Let a "Walk here" finish before acting. The client runs ahead of the server at 6m/s, and
  stopping early gets "walk closer to the selected object".
- Tap targets must be on the canvas: check `document.elementFromPoint` first, because the HUD
  and the dev overlay take taps near the bottom of the screen.
- The boarded flag reaches the client about 0.7s after the action answers.
- A new life has a hammer and a saw. Furniture in whatever building the survivor stands in gives
  3 planks and 4 nails a piece with the hammer alone, which is far safer than rubble or trees.
  Depletion is per player, and a new life loses carried planks.
- To get a zombie onto a barricade: it batters boards only with a clear line to that opening's
  outside point, and otherwise goes for a door. Scream reach equals sight (55m by day, 22m at
  night, about half through walls); work noise carries 35m. An account that has fought around its
  home for an hour has no zombies left nearby; a fresh account a few blocks away got one in minutes.
- For a zombie to damage a fence, stand about a metre from it and let it walk up.
- `pkill -f` matches the calling shell. Use `pgrep` and check `/proc/<pid>/comm`.
- Do not read a server's `/proc/<pid>/environ` to inspect settings: it printed a storage secret
  into a transcript once. Ask for named variables only.

### Suggested next work, most useful first

- [ ] Find out how a zombie gets inside a home whose window is boarded at full strength and whose
  doors are closed and intact (seen twice on the public site). Check where the director and
  region load place zombies relative to building outlines.
- [ ] Balance with a person playing. The scripted player died five times in one evening.
- [ ] Region load blocks the game loop for about 1s in the densest areas; `sync_geometry` and
  `_zed_obstacle` walk every loaded building on each call; buildings never unload.
- [ ] A physical phone, iOS Safari, real GPS movement, sound, and a long real absence.
- [ ] Map tiles come straight from tile.openstreetmap.org, which is not meant for an app with
  many players.
- [ ] Ask Tom before removing anything from the live database: the test players listed above, a
  boarded window in `osm:w:126116972` and a fence (`built:60:1`) beside it.
- [ ] "Later world and story scope" in `SURVIVAL_ROADMAP.md` needs its own scope first.

Left running on this machine: your local servers on ports 8010, 8012, 8013 and 8014. Claude's
servers on 8021 and 8022 are stopped.


## 2026-10-11 — Phone redesign draft; waiting for Claude's plan

Tom requested fresh GPS-led phone startup and GPS placement for EVERY new life,
including after death, plus a world-first phone UI and remembered-area overview.
He then explicitly instructed Codex to wait for Claude's independent review/plan
of https://www.youtube.com/watch?v=Q7ecB76Yboo and merge both perspectives before
building. **No redesign implementation should begin before the merge.**

Codex draft: `MOBILE_WORLD_PLAN.md` in the OSZ repo. It includes code diagnosis,
reference evidence limits, proposed UX, five stages, acceptance gates and a merge
checklist. `AGENTS.md` records Tom's rule to always update plan/status/shared notes
at progress milestones and handoff, plus the current wait-for-Claude gate.

Findings: startup favors saved server coordinates; browser-wide gpsCenter preserves
old virtual positions within half a mile; new_survivor copies death coordinates;
renaming/new tokens reuse the same device account. An 82%-height modal covers the
map and intercepts input while the simulation runs. Proposed stages: M1 GPS lifecycle,
M2 object action cards/compact drawers/quick belt, M3 joystick plus tap walking,
M4 durable remembered exploration/overview, M5 atmosphere/shelter reliability/tuning.

Guide evidence: metadata and all 11 storyboard sheets sampled about every 10 seconds;
full video download HTTP403 and captions HTTP429. No claim to have heard commentary
or measured animation timing. Caches: /tmp/osz-q7-guide-info.json and
/tmp/osz-q7-reference/sheet-00.jpg through sheet-10.jpg; ephemeral, not repo assets.

Review baseline: master/origin `61ad423`, live gameplay `195dffa`, /healthz confirms
0.2.6. Reran 137 server tests, client wall regression and JS syntax checks: passed.
Locally reproduced director spawning inside a building with all openings closed;
plausible cause of the public sealed-home incidents, not a confirmed incident trace.
Loaded-region skipping also prevents same-process hourly expiry refresh.

Current status: documentation only; no app/production changes, no processes started
or stopped for this review. Next step: read Claude's independent plan, compare
observations and decisions, merge into MOBILE_WORLD_PLAN.md, synchronize this
handoff, then begin M1. Preserve existing core-phase completion and Claude's fixes.


### Windows Chrome offline guide located — 2026-10-11

Tom downloaded the guide using logged-in Windows Chrome. Located its exact
Q7ecB76Yboo references in Default profile's YouTube IndexedDB, with associated
TRANSFER_STATUS_TYPE_COMPLETED and successful offline orchestration records.
Normal Chrome download records have no matching standalone media file.

Windows root: C:/Users/user/AppData/Local/Google/Chrome/User Data/Default/IndexedDB/
- https_www.youtube.com_0.indexeddb.leveldb/000004.log: matching guide/offline metadata.
- https_www.youtube.com_0.indexeddb.blob/: 65 blobs, about 49.4 MiB, recent download
  files mostly under 1b/00 (2026-10-11 around 07:59 local filesystem timestamps).

The blob folder is supporting offline storage, not a verified extracted MP4;
individual blob-to-stream mapping and independent playback remain unverified.
Do not claim full-video review yet. Chrome's History also contains the exact guide.
Read-only inspection; no cookies/session credentials exported, no browser data
changed. Pass these paths to Claude for its guide review. The plan still waits
for Claude's independent observations and merge before implementation.


## Transcript incorporated; build authorization after merge — 2026-10-11

Tom provided the guide transcript. Codex reviewed it and added a mechanic-to-phone
mapping, implementation priorities, candidate later actions, and explicit source
limits to MOBILE_WORLD_PLAN.md. Most useful lessons: GPS-centered nearby supplies,
retreat/aim/shove with stamina awareness, weight decisions, urgent treatment,
object-focused shelter routines and remembered outings. Guide advice is not a
verified OSZ specification; questionable/version-dependent rules are not copied.

Tom explicitly authorized implementation immediately after reading and merging
both independent plans. No extra approval prompt. Claude's independent plan has
not appeared in the repo yet; merge gate remains pending. No app/deployment change.
AGENTS.md records this authorization and existing required progress-note updates.
Next: read Claude's output, compare evidence/controls/priority, publish one merged
plan and begin its first stage. Core live release remains 0.2.6.


## 2026-10-11 — Claude's independent guide review is in the repo (for the merge)

`GUIDE_REVIEW_CLAUDE.md` is Claude's review of the same Project Zomboid beginner guide and a
proposed plan. Documentation only; no app or deployment change. Live is still 0.2.6.

- Evidence: the whole video at 480p, one frame every five seconds (181 frames, times stamped),
  eight frames read at full size, and a timecoded transcript checked against the one Tom pasted.
  Files and the download method are listed at the top of the review. They are in `/tmp`.
- Main finding: the systems are mostly there; what is missing is what fills them. Loot is handed
  over instead of chosen, nothing is left after a fight, nothing at home takes time, a life has
  no calendar, crowds are small, and moving fast costs nothing in noise.
- It agrees with `MOBILE_WORLD_PLAN.md` on M1 to M4 and proposes nine content items (C1 to C9)
  slotted around them, with a size and an acceptance check for each.
- Three points for the merge: no launch relocation while a survivor is hunted; pull the
  sealed-home spawn fix forward beside M1; test joystick pace indoors.
- It corrects four sampled times in the plan's reference table (the window menu is at 2:42).
- Five questions for Tom are in its section 8.

Next: Codex reads it, the two plans are reconciled into `MOBILE_WORLD_PLAN.md`, then M1 starts.
The merge gate in that file is Codex's to tick. Claude has not edited `MOBILE_WORLD_PLAN.md`.


## 2026-10-11 — Plans merged; M1 + C1 start

Read Claude's GUIDE_REVIEW_CLAUDE.md (`71a3946`) in full and reconciled it with the
Codex draft/transcript mapping. MOBILE_WORLD_PLAN.md is now the active merged plan.
Merge checklist complete; corrected video times; adopted C1–C9 with explicit
sequencing and defaults. New lives GPS; existing hunted life defers launch relocation;
protected-home spawn fix moves beside M1; proportional indoor joystick; server-side
chosen loot before corpse rewards; optional slow jobs preserve quick current loops;
calendar/events share area clocks. One home, category icons, real-day calendar and
future measured ~60 herd are recorded defaults, not unanswered approval questions.

Implementation begins M1/C1 under Tom's explicit authorization. Live remains0.2.6.
Next concrete task: server placement handshake/client launch/new-life handling and
regressions, then sealed-home spawn avoidance. Review/merge only in this commit.


## 2026-10-11 — M1/C1 local implementation and verification

Merged plan implementation started. GPS launch/new-life placement, atomic handshake,
request idempotency, stale snapshot/position epochs, recent accurate fix handling,
hunted-launch deferral and explicit manual fallback implemented. Removed death-site
respawn. Director/cell/late-map spawn rules protect sealed homes without evicting
established interior occupants. 156 server tests and both client regressions pass.
Headful phone emulation passes first GPS/old anchor, virtual walk, drift, reconnect,
reload, death GPS respawn (local-only fixture), denied GPS and manual map selection.
No JS errors. Physical device, real background travel and one-hour public defense
still unverified. App0.3.0 prepared; not live yet. See MOBILE_WORLD_PLAN.md latest
milestone for files/process/harnesses. Next: release/public tests, then M2. Shared
progress notes remain required. No approval prompt needed.

### M1 reconnect follow-up — 2026-10-11

OSZ 0.3.0 (`ad50856`) deployed successfully as Railway deployment
`<deploy-id>`. Public fresh GPS start, drift, virtual
walking, ordinary reconnect, GPS reload and existing progression persistence pass.
Full public acceptance remains pending. Extra closed-building reconnect testing
found two issues: a committed placement snapshot precedes its action reply (now
acknowledged idempotently), and the exit planner measures reach from a passage
segment while the opening action measured its center. This mismatch can reject a
valid edge approach as “too far”. The action now uses the same passage reach.
These follow-up changes are local and under regression checks; not yet deployed.
Local fixture server restarted as process1505167 on8015, same isolated test DB.
Next: verify closed Exit after socket interruption, release0.3.1, repeat public
GPS/travel/exit checks. M2 world UI and chosen loot have not started.

### M1 Exit regression resolved locally — 2026-10-11

The remaining failure was client prediction: final exit waypoints did not wait
for the authoritative body before sending Open. Now the final door approach
waits within0.35m and keeps sending movement at the normal rate; reconnect can
resume the leg. Local headful closed two-room building test now passes with a
socket interruption immediately after pressing EXIT BUILDING: both doors open,
actor reaches outside, no horizontal overflow or JavaScript errors. New Node
regression exercises the actual stepDesk handler and verifies no premature Open.
157 server tests and all three client regressions pass. Preparing0.3.1 with the
snapshot acknowledgement, passage reach consistency and final-waypoint wait.
Public0.3.1 verification and physical Pixel9a remain pending. Current local
fixture process1506047 (8015), trace instrumentation outside repo only.

### M1/C1 release pickup — 2026-10-11

Live OSZ0.3.1 commit `b11d1ea`, Railway SUCCESS deployment
`<deploy-id>`; prior0.3.0 deployment REMOVED.
https://osz-production.up.railway.app/healthz returns0.3.1.
Public headful touch Chromium393x851 tests PASS: fresh GPS despite old local
anchor; virtual tap walk; drift ignored; ordinary socket reconnect preserves
virtual position; page reload anchors current GPS; coarse fix ignored; three
consistent fixes over8.6s recenter beyond half a mile; closed two-room building
Exit survives immediate socket loss, opens both doors and physically exits. No
JavaScript errors or horizontal overflow. Existing session accepted with no new
session, exact gear preserved across deployment; XP60/level2/skills preserved.
Local current-code death/new-survivor at fresh GPS and denied GPS/manual map tests
PASS. Server157 tests; GPS, wall and final-door client regressions PASS.

Next M2+C2: atomic chosen-loot shelves first, then selected-world cards, compact
pack/storage/loot drawers and quick belt, then C3/C4. Full-table UI remains in the
current release. Do not claim physical Pixel9a, real/background GPS, Safari or
one-hour empty sealed-home observation tested. C1 spawn coverage is deterministic
server tests only. No live data was reset; test-only death route remains outside
repo, localhost fixture1506047 on8015. Native release staging /tmp/osz-railway-20261010.
Useful harnesses: /tmp/osz-phone-gps-check.mjs, -death-check.mjs, -fallback-check.mjs,
-travel-check.mjs, -persist-check.mjs; /tmp/osz-playtest.mjs --closed-exit and
--progression-persist. Session files remain private; never copy their contents
into notes. Progress synchronized to repo, Claude build memory/index and gbrain.

### M2/C2 implementation in progress — 2026-10-11

Chosen loot implemented locally: per-life persistent searched shelves; search
keeps contents in container; Take accepts quantity, revision and bounded durable
receipt. Clone/save/publish transfers conserve stock on retries and storage failure.
Reveal completion is staged until save succeeds, with retry; legacy claims never
refill. Six new loot tests cover partial stock, restart state, duplicate/concurrent
taps, range/weight/quantity, failed save and reveal retry. Full163 server tests PASS.

Mobile UI first pass (not yet browser verified/released): selected-world cards,
focused loot/storage/station drawers, quick water/food/treatment/gear/build belt,
compact existing pack at32% height, expanded optional view, world taps and combat
still available, collapse on movement/combat/attack and near-threat warning.
Furniture taps now select the actual object instead of opening all Work tabs.
Changed files include app/game/loot.py, sim/store/hub/ws routes, world-ui.js,
main/work JS, index and styles; tests/test_loot.py. Next: actual headful phone
playtest, fix layout/targeting/access, chosen loot restart/transfer tests then
release together. Live remains0.3.1 (`b11d1ea`).

### M2/C2 local acceptance and release preparation — 2026-10-11

Preparing0.4.0. Search reveals durable per-life shelves without automatic taking
or equipping. Quantity transfers use revisions, durable receipts and clone/save/
publish. Legacy claims stay depleted. Remaining shelves survive daily reseeding
and restart. Original container/pack regressions retained and adapted to explicit
taking; new tests are separately in tests/test_chosen_loot.py. Full164 server
tests pass, as do all three Node regressions and JS syntax checks.

Headful touch393x851 PASS: real room search leaves pack unchanged; Take1 updates
stock and pack; partial remainder survives an actual server restart; map tap
selects correct stash/furniture; world card has stable action nodes across snapshots;
pack stays compact; Shove closes it; closed-door Exit reaches outside; selected
furniture can choose home, focused storage deposits/retrieves water, quick belt
drinks, and clear-map walking works from an expanded drawer. Portrait drawer32%;
landscape851x393 side drawer keeps survivor visible and no horizontal overflow.
Fixed nearest-hit selection, expanded portrait coverage and camera placement after
rendered inspections. Category icons are original SVG; reduced toast/label clutter.
No shared-world pause or menu shield. Public release checks are still pending.

Current local server1513539,8016, /tmp/osz-world-ui-v1.db (actual app, no fixture).
Old local GPS fixture1506047 on8015 remains separate. Harness: tools/mobile_world_check.mjs
(committed; Playwright import configurable), /tmp/osz-world-ui-persist-check.mjs and
/tmp/osz-world-shelter-check.mjs. Screenshots /tmp/osz-world-drawer-phone.png,
/tmp/osz-world-object-card.png, /tmp/osz-world-landscape.png. Private session state
/tmp/osz-world-ui-storage.json; never print or commit it.

Next: native OSZ Railway deployment, public touch outing + actual replacement/
remainder/gear/skills checks, then C3/C4 and M3. M2 is not fully accepted yet:
public ten-minute outing, station-work UI, actual incoming-hit/threat behavior and
physical Pixel9a checks remain open. Goal stays active; matching the full guide
vibe is not claimed. Progress notes synchronized with Claude and gbrain.

### M2 public release and marker follow-up — 2026-10-11

0.4.0 commit `1ee042e` deployed SUCCESS as Railway
`<deploy-id>`. Public headful touch tests PASS: search
leaves items in shelf, Take1 and remainder,32% portrait drawer, combat access,
physical Exit, home from object card, storage deposit/withdraw, quick water and
walking from expanded drawer. Existing independent profile gear and XP60/level2/
skills survive deployment; GPS coarse rejection/half-mile travel also PASS.

Extra home/loot selection test FAILED: setting home at a room container made its
marker intercept a container tap. Fixed locally by offsetting only the home icon
and its hitbox38px left, using one shared constant; neither storage/world position
moves. Local fresh search -> home/storage/quick drink -> exact container/furniture
selection/remaining loot/landscape tests all PASS with no JS errors. Preparing
0.4.1 follow-up; public cold replacement and separated marker proof next.
Public private session/evidence preserved separately at /tmp/osz-world-ui-public-*
for that check. Original local /tmp/osz-world-ui-* files now hold a newer local
test profile; never confuse the bases. Goal remains active, C3/C4/M3/M4 and later
merged work still pending.

### M2 target selection hardening — 2026-10-11

0.4.1 `35dbe27` live SUCCESS deployment `<deploy-id>`.
Cold replacement preserved the public test survivor's exact shelf remainder,
revision and home. Public GPS launch/walking/drift/reconnect/reload PASS.
One initial clean container-selection check timed out, while an instrumented
retry selected the exact stash and furniture and passed without JS errors.
The world handlers still gave openings/home an unconditional priority over a
closer visible container. Hardened all four target types to compete by actual
screen distance in selection.js; added a Node priority/tie regression. Local
clean persistence/furniture/landscape browser check and all four Node regressions
PASS. Preparing0.4.2 with this selection change, then repeating clean public
cold-state checks. Do not count an instrumented retry as the full initial-tap
acceptance gate. No database or world locations changed.

### M2/C2 release pickup — 2026-10-11

Live0.4.2 `316f724`, successful cold redeployment
`<deploy-id>` (previous40a98c5b app REMOVING/removed).
0.4.0 introduced chosen shelves/world cards/drawers/belt;0.4.1 separated home/loot
markers;0.4.2 unified nearest-object targeting. No live data reset.

Public cold-start observation confirms the remaining automated tap failure was a
readiness race: saved shelf was available while mapping=true and inside=null.
Waiting for the visible room/container then testing genuine taps PASS on a fresh
Railway process: exact saved remainder/revision, same home, zero new session,
correct container/furniture, stable action DOM, movement closes expanded pack,
landscape survivor visible/no overflow, zero JS errors. tools/mobile_world_persist_check.mjs
now commits this correct readiness gate; do not tap hidden data coordinates.
Initial clean checks that raced loading are recorded above, not silently counted
as passes. Nearest targeting is retained as a useful independent hardening.

Other public evidence: search does not auto-take; Take1 and remainder;32% portrait
drawer; combat controls work; home from object, cupboard deposit/withdraw and quick
drink; clear-world movement from expanded drawer; closed two-door Exit survives
immediate socket loss and reaches outside. Fresh GPS, virtual wander, drift,
reconnect/reload and half-mile/coarse checks pass. Old independent gear and XP60/
level2/skills preserved. Server164 tests and four Node regressions pass.

Next C3/C4 then M3/M4 and later merged stages. M2 core UI/C2 delivered, not the
entire guide-vibe goal. Remaining M2 gates: focused station crafting/repair UI,
actual incoming-hit/threat responses, ten-minute public outing and physical phone.
C1 hour-long defense observation, real background GPS and Safari also unverified.
Goal remains active. Refresh an already-open phone page to load the new UI.

Repo tools/mobile_world_check.mjs and tools/mobile_world_persist_check.mjs accept
OSZ_PLAYWRIGHT_MODULE for the cached Playwright install. Actual public private
evidence/session: /tmp/osz-world-ui-public-evidence.json and
/tmp/osz-world-ui-public-storage.json (mode600). Local -ui-* files now refer to a
newer local test profile; respect evidence.base. /tmp/osz-world-shelter-check.mjs
uses current evidence's base. Local server1513539 on8016 /tmp/osz-world-ui-v1.db;
GPS test-only fixture1506047 on8015 remains isolated. Native Railway staging
/tmp/osz-railway-20261010. Screenshots in /tmp/osz-world-*.png, no credentials
recorded. Shared progress synchronized to repo, Claude memory/index and gbrain.

### C3 themed supplies — implementation and local checks, 2026-10-11

Prepared0.4.3 (not deployed yet): kitchen/bathroom/bedroom/garage tables; beans,
peaches and soup use existing hunger25 mechanics with distinct weights. Tissues,
soap, toothbrush and paperback are weighted personal belongings, without medical
or crafting benefits. Original personal-category SVG; cupboard names, weight and
food relief visible in compact loot/pack drawers. Hello exposes item descriptions
and hunger/thirst. Household split-room labels vary deterministically across
footprints; room IDs, sample positions, collisions and openings unchanged. Small
unsplit homes keep Interior and get kitchen supplies; no extra fictional walls.
Special fire/police/medical destinations retain priority. Searched personal shelves
and hidden cache records remain authoritative; old claims never regenerate.

Local171 server tests and four Node client regressions PASS. New test exercises
12 real search completions per four room themes (48 total), clearly distinct
sets, no automatic take, food use, stacking/weight/store roundtrip, deterministic
geometry and old shelf/legacy claim preservation. Browser phone checks running
against actual isolated app1523374 on8017, /tmp/osz-room-supplies.db, using
tools/mobile_world_check.mjs. Prior1513539 on8016 and GPS fixture1506047 on8015
untouched. Public0.4.2 remains316f724 deployment<deploy-id>.
Next finish browser acceptance, release if clean, then C4 shared searchable bodies
and M3 joystick/combat/pace noise. Hardware and extended M2 gates remain open.

### C3 local acceptance / release preparation — 2026-10-11

Local actual phone browser PASS against8017: search/Take1/remainder, compact
drawer, combat usable, Exit, zero JS errors. Additional real residential kitchen
search showed Tinned Peaches and Tinned Beans, hunger25 and category SVG in the
drawer; hello contains personal-item descriptions. Screenshot visually reviewed:
/tmp/osz-themed-shelf-phone.png. Server48 themed search completions across four
types distinguish contents;171 server tests and four Node regressions pass.
Reusable browser harness tools/mobile_room_check.mjs added. C3 local acceptance
complete,0.4.3 preparing commit/push/deployment; public acceptance still pending.
Existing0.4.2 public private session/evidence will verify unchanged saved shelf
and home after deployment. Next C4 then M3; entire gameplay-feel goal remains open.

### C3 release pickup — 2026-10-11

Live0.4.3 gameplay37feed7; Railway SUCCESS
<deploy-id>. Committed/pushed Gitea; native staging
/tmp/osz-railway-20261010. Public health returns0.4.3. Public real phone-emulated
kitchen search PASS: peaches and beans, hunger25 shown, food/personal metadata
exposed, no JS errors. Existing public private profile PASS after app replacement:
exact saved shelf items/revision, same home, zero new session, correct container
selection, furniture card, stable buttons, movement closes expanded pack,
landscape no overflow, zero JS errors. No data reset or alteration to Tom's session.
Local171 server tests (including48 themed searches) and four Node regressions
PASS; local full phone search/take/remainder/combat/Exit and themed shelf PASS.
C3 complete with this evidence; physical Pixel9a remains unverified. Broader M2
station-work/hit/threat/ten-minute outing gates remain open. Goal remains active.

Next C4 shared static bodies until daily reshuffle, blood and low-yield look-tied
loot; begin with durable world corpse state and atomic shared transfers (personal
loot_shelves cannot own a communal body). Existing zed_dead model only records
id/until, not location/look/loot; evolve persistence safely. Then M3 joystick and
C5 pace noise/Knock, M4 remembered area, followed by C6–C9/M5.

Repo tools/mobile_room_check.mjs and mobile_world_persist_check.mjs reproduce
public checks with OSZ_PLAYWRIGHT_MODULE pointing at cached Playwright. Existing
public mode600 evidence/session files /tmp/osz-world-ui-public-evidence.json and
/tmp/osz-world-ui-public-storage.json unchanged. Local -ui-* now belong to8017
cohort; respect evidence.base. Screenshot /tmp/osz-themed-shelf-phone.png was
visually reviewed locally, then overwritten by successful public themed search.
Local actual app1523374 on8017 uses /tmp/osz-room-supplies.db (started before
version constant bump, health reports0.4.2 despite C3 code; restart for new backend
work). Prior1513539 on8016 and isolated GPS fixture1506047 on8015 untouched.
Refresh open phone page for new UI. Shared repo/Claude memory/index/gbrain updated.

### C4 shared bodies in progress — 2026-10-11

Implemented (not deployed): additive world_corpse table, position/look/blood
and shared sparse stock until daily reshuffle. Body creation and fixed-zombie
death record commit together before publishing; failed creation remains hidden
and retries. Search is4s/noisy22m/reach2.5m with wall/engaged checks, reveals
without auto-taking,5XP only for first shared search. Take clones player/body
and commits both documents in one transaction with database revision check and
idempotent player receipt. Failures roll back both. Old zed_dead/players/shelves
untouched; director corpse IDs use UUID to avoid restarting t:1 collisions.
Nearest24 bodies inside sight/LOS sent as static data only on ID/revision/reach
changes; drops/zombie actors remain separate. Client uses existing fallen sprites
and blood, tap-card/Approach/Search/Look/compact shared-loot drawer. No40s fade.
Existing art has chef/scrubs/builder looks, no firefighter; rare corresponding
knife/bandage/helmet or shirt, worn equipment condition2–5. Most nothing or cloth.
Firefighter body gear awaits corresponding original art in C9; don't pretend
the scarf look is a firefighter.

Local182 tests and four Node regressions PASS.11 new body tests cover shared
stock, concurrent players/receipt replay, reconnect/store load, failure rollback,
expiry, visibility/cap, snapshot delta, noise/reach/walls, deterministic scarce
yields and unique temporary IDs.1200 look rolls yield<27% items,<.1kg/body,
less than one fifth of ordinary room quantity per opportunity. Actual normal
phone combat at8018 killed natural lurcher, searched via real taps, revealed
cloth, body/stock persisted through reload; zero JS errors. Screenshot
/tmp/osz-body-phone.png visually reviewed. Two-client real Take check running;
scripted hourly balance and process replacement still pending.

Actual local app1526030 on8018 /tmp/osz-bodies.db, no fixture/death/spawn endpoints.
Private mode600 /tmp/osz-body-storage.json, -evidence.json. Reusable repo
tools/mobile_body_check.mjs and mobile_body_stock_check.mjs. Existing8015/16/17
processes untouched. Public still0.4.3 37feed7 deploymentd6991428.
Next finish C4 acceptance/release then M3 joystick and C5 pace noise/Knock.
Goal active; hardware and extended M2 checks remain open.

### C4 local acceptance / release preparation — 2026-10-11

184 server tests and four Node regressions pass. Natural local lurcher kill
produced cloth; two actual phone-emulated clients shared it, Take1 added it to
pack, other client observed depletion, reload preserved depleted stock. Actual
local process1526030 stopped, verified absent, then replacement1527172 loaded
same /tmp/osz-bodies.db on8018. Browser confirms same body/look, exact searched
stock/revision, zero new session and zero JS errors after replacement. Additive
new table leaves existing survivors/doors/shelves/death markers intact.

Scripted balance tools/corpse_balance.py:30 fighter walks,9.04 simulated hours,
20.69 kills/hour; granting every corpse item with zero search/travel/carry costs
still gives3.76 items/hour. Separate explicit one-room-search/minute budget
using real generator yields Kitchen173/Bathroom169/Bedroom139/Garage249 items/hour.
8/30 fighters died; this is a conservative loot ceiling against a stated room
budget, not measured human phone outing pacing.1200 look rolls also sparse and
damaged, no guaranteed weapon/clothing. Rare firefighter gear needs the matching
original look in C9. New-life static-snapshot reset and replay preserving unrelated
unsaved actor dirtiness covered by regression.

Preparing0.4.4 commit/push/deploy then public old-shelf/home upgrade, actual fight/
body search and process-replacement checks. C4 local core accepted; public
acceptance pending. Existing hardware/extended M2 gates open. Next M3/C5.

### C4 public checks in progress — 2026-10-11

Live0.4.4 gameplayb3117ad; successful Railway deployment
<deploy-id>.184 server tests/four Node checks pass.
Public old shelf/home/session/selection/furniture/landscape regression PASS.
Public body search/drawer/reload PASS; public two-client conserved Take1 and
shared depletion/reload PASS on retry. Initial transfer readiness wait timed out;
read-only reconnect probe later showed alive/hp100, GPS ready, body reachable.
Exact first timeout cause unproven; don't call it a proven hunted-GPS failure.

Audit found initial public fight harness could accept an existing communal body.
Probe found that test profile had kills0, so initial public body-search pass is
NOT proof of its own fight. Local isolated natural fight had no pre-existing
bodies and remains valid. Hardened harness now requires own kill-count increase
and new body, uses Approach when needed, persists expected kills and asserts
kill count across reload/process replacement. Fresh own-fight public check running
(prefix /tmp/osz-body-public-fight), separate from confirmed shared Take profile
(/tmp/osz-body-public). Metadata/private session files mode600; never print them.
Next public own-fight and cold-process proof, then mark C4 core accepted and
start M3/C5. Existing guides/hardware/extended gates remain open. Goal active.

### C4 public acceptance complete — 2026-10-11 (Claude, picking up from Codex)

Codex ran out of usage with the own-fight check still to run; Claude finished it.
Live 0.4.4, gameplay `b3117ad`. Same code redeployed for a cold process: Railway
`<deploy-id>` SUCCESS, `0150c0cd` REMOVED.

- Tested publicly, hardened `tools/mobile_body_check.mjs` (prefix
  `/tmp/osz-body-public-fight`): the test survivor's own kill count rose, a body
  that was not there before appeared (shambler, look 5), tap selected it, Search
  body opened the compact drawer, reload kept the body, its (empty) stock and the
  kill. No JavaScript errors. An empty body is the common roll and is expected.
- Tested publicly after the process replacement, `mobile_body_persist_check.mjs`:
  same body, same look, exact stock and revision, kill count kept, no new session,
  no JavaScript errors.
- Tested locally at the same commit: 184 server tests, four Node regressions,
  syntax checks on every client script and tool.
- Still unverified: a person on a physical phone; a body with loot taken on the
  public site by the profile that killed it (the public Take 1 evidence is the
  separate shared profile `/tmp/osz-body-public`); the daily reshuffle clearing
  bodies on the live database.

C4 core is accepted on this evidence. Next: M3 + C5 (joystick beside tap walking,
pace noise, quiet walk, Knock). Codex's local servers on 8010 to 8018 were left
running and untouched.

### M3 + C5 released as 0.5.0 — 2026-10-11 (Claude)

Live 0.5.0, gameplay `09f338c`, Railway `<deploy-id>`
SUCCESS (`e867b6e0` REMOVED). Deployed from `/tmp/osz-railway-20261010`.

**Implemented**
- Thumb stick (`main.js`, "thumb steering"): a drag that starts in the lower left
  62% x 58% of the map becomes a floating stick; a touch there that does not travel
  12 px is still a tap. One play mode, no switch. Under half push creeps, above it
  is 60 to 100% of the server pace. Release, pointer cancel, lost capture, blur,
  hidden tab, death, socket close and Stop all end steering. The stick only sets
  the target position; pace, collision, fatigue and sprint stay with the server.
- Layout: SHOVE sits beside SWING, SPRINT is a pill above the pack button, so the
  left thumb is free. QUIET and a "heard N m" chip are in the top row. SCREAM moved
  into the You sheet (menu button, bottom row). A dashed ring marks the zombie SWING
  would reach (red when it is a finish).
- Pace noise (`sim.py` `heard_m`, `creeping`, `_zed_range`): heard at 5 m standing,
  3 m creeping, 11 m at fighting pace, 20 m travelling, 35 m sprinting; 40% of that
  through a wall (was a flat 5 m while moving). New dials in `TUNE`: `noise_quiet_m`,
  `noise_travel_m`, `noise_sprint_m`, `noise_wall_mult`, `quiet_speed`,
  `quiet_sight_mult`, `knock_noise_m`, `knock_inside_m`.
- Quiet walk: action `quiet` (start/stop), 1.2 m/s, excludes sprint, cleared on
  disconnect. An unaware zombie must be 40% nearer to spot a creeper; one already
  chasing is not fooled, so creeping cannot shake a pursuer in plain sight.
- Knock: `opening` action with `op=knock` on a closed door or window. 10 m noise
  outside; idle zombies inside within 14 m come to the door and groan within about
  two seconds. The reply carries no occupant information; the phone says "No answer.
  That is not a promise." unless an unseen groan within 20 m arrives in 3.2 s.

**Tested locally (commit `09f338c`)**
- 191 server tests (7 new in `tests/test_noise.py`): pace tiers; quiet/sprint
  exclusion and cap; creeping past at 15 m unnoticed while travel pace is noticed;
  sprint heard at 28 m while travel is not; a chaser is not shaken off by creeping;
  through a wall at 5 m a creep is not heard, a walk and a sprint are; knock brings
  an unseen occupant toward the door and an empty house is silent.
- Five Node regressions (new `tests/stick_client_regression.mjs` runs the shipped
  stick code) and syntax checks on every client script and tool.
- `tools/mobile_stick_check.mjs` at 393x851 touch Chromium: layout without overlap
  or overflow; tap in the stick zone still walks; full push moved 6 m in 1.5 s
  heard at 20 m; second finger swings twice while steering; gentle push creeps at
  1.0 m/s heard at 3 m; release stops; QUIET and SPRINT toggle and exclude each
  other; SCREAM only in the sheet; door card Open/Knock/More; same layout and
  steering checks at 851x393 and 360x560.
- `tools/mobile_stick_fight_check.mjs`: natural zombies, left finger closes and
  backs away, right finger strikes: 3 own kills at 100 health.
- `tools/mobile_world_check.mjs` (search, Take 1, drawer, combat, Exit) still passes.

**Tested publicly on 0.5.0**
- `mobile_stick_check.mjs`: every step above passes (full push 5.6 m, creep 0.96 m/s).
- `mobile_stick_fight_check.mjs`: own kill with 2 swings accepted while steering,
  2.2 m backed away, 100 health, no JavaScript errors.
- Saved data across the release: `mobile_world_persist_check.mjs` (exact shelf
  remainder, home, no new session, selection, landscape) and
  `mobile_body_persist_check.mjs` on the own-fight profile both pass.

**Bot pacing, 120 walks of 15 minutes, mixed policy** (`tools/walk_bots.py`, new
`--pace` and `--quiet`; "old" is the same build with the new radii set to 11 m):
| Walk | Noticed per hour | Grabbed per hour | Died |
|---|---|---|---|
| Day, travel pace 6 m/s, old and new | 32.9 | 11.7 | 4% |
| Night, travel pace, old | 42.5 | 38.8 | 19% |
| Night, travel pace, new | 59.0 | 42.2 | 24% |
| Night, 1.35 m/s, old | 23.5 | 22.7 | 13% |
| Night, 1.35 m/s, new | 33.4 | 28.3 | 11% |
| Night, creeping, new | 11.1 | 16.0 | 10% |
Daylight travel is unchanged because sight (20 m) already equals the travel radius.
At night fast travel draws about 39% more attention and creeping cuts it to a
third. These bots never change pace in response, so the death figures are a
ceiling for a player who does. The radii are first values, not final balance.

**Still unverified**
- A person on a physical phone: thumb reach, whether the stick zone steals taps
  meant for objects low on the left, grip covering threats, 412 px width, safe
  areas, a slower device, iOS Safari.
- Shove and Sprint pressed by the second finger (only Swing was automated).
- A knock answered on the public site: the public knock was on an empty building.
  The answered case is covered by the server test only.
- Doorway precision with the stick, and whether creeping indoors is slow enough.
- Blur, hidden tab, death and socket close ending steering are implemented and
  read, not exercised in a browser.
- Harness note: in Chromium's `Input.dispatchTouchEvent`, lifting one finger of two
  is a `touchEnd` that lists the finger being lifted. A `touchMove` listing only the
  remaining finger leaves the other down, and later presses silently do nothing.

Local test server for this build: port 8019, `/tmp/osz-stick.db`, pid in
`/tmp/osz-stick.pid`, start script `/tmp/osz-stick-serve.sh`. Codex's servers on
8010 to 8018 untouched. Playwright used:
`~/.npm/_npx/e41f203b7505f1fb/node_modules/playwright/index.mjs`.

Next: M4 remembered exploration and Area overview, then C6 to C9 and the M5
remainder. Open M2 gates (station recipes, ten-minute public outing) are unchanged.

### M4 released as 0.6.0 — 2026-10-11 (Claude)

Live 0.6.0, gameplay `d6c2fd6`. Railway `<deploy-id>`
SUCCESS, then the same build redeployed for a cold process:
`<deploy-id>` SUCCESS (`ca135d09` REMOVED).

**Implemented**
- `app/game/memory.py` and a new additive table `player_memory` (one JSON row per
  player, like `player_home`). A memory holds: geohash-8 cells seen (about
  38 m by 19 m, value = day number, cap 5000, oldest days dropped first); marks for
  containers this player opened (kind, position, items left, time; cap 200); and
  where the last survivor fell. It is keyed by player, so it outlives a life.
- Observation runs in `_step_actor`: 15 sample points around the survivor, again
  after 8 m of movement or on a new day; marks are refreshed from the life's
  `loot_shelves` every 3 s. Unplaced survivors (0,0) and map-loading arrivals are
  not observed. First use seeds whole geohash-7 blocks from the current life's
  `explored` list, with no contents invented.
- Hub: the row is loaded in `join` in the same breath as `add_actor` (no await in
  between), so a step can never start a blank memory over a saved one. Saved in
  `save_all` for dirty players; dropped from RAM once the player has gone and it
  is saved.
- Action `memory` (lat, lng optional) returns only cells within 1200 m of the
  asked point (cap 3000), marks within 3600 m, the death mark and the total known.
  It bypasses action handling: it cancels no work and is not an action.
- Client `app/static/js/area.js`: AREA in the top row pulls the camera out (three
  zooms, about 350 m, 650 m and 1.3 km across a phone). Fog: clear in current
  sight, dim where seen before (dimmer after a week), dark elsewhere. Home, last
  death, containers (amber = had items, grey = emptied) and YOU are drawn; a tap
  on a mark shows its name, distance and bearing, what was left and how long ago,
  with "It may have changed." Drag pans up to 3 km. Opening stops walking and
  cancels work; nothing in the overview walks or teleports. Only zombies already
  in sight are drawn. SWING, SHOVE and SPRINT stay on screen; a grab, or one of
  yours within 8 m, closes the overview with a message; so do combat buttons,
  movement keys and death.

**Tested locally (commit `d6c2fd6`)**
- 199 server tests (8 new in `tests/test_memory.py`): standing still costs
  nothing and marks nothing new; walking extends the strip; a request about a
  point 5 km away returns none of it; reading the map does not cancel work; age in
  days and oldest-first forgetting at the cap; a container mark with what was left
  and when, and nothing for a container never opened; memory outlives the survivor
  and records the death; seeding from `explored`; and through the hub with a real
  database: save, a replacement hub reloads it on join, death and a new survivor
  keep it, and it leaves RAM after the player has gone.
- Five Node regressions and syntax checks on every client script and tool.
- `tools/mobile_area_check.mjs` at 393x851 touch Chromium: opens with the ground
  around the start; navigation, belt and stick hidden while SWING/SHOVE stay; a
  drag pans without moving the survivor; a tap sets no walking goal; zoom out and
  in; Back restores the street; a stick walk grows the memory (15 to 30 cells); an
  opened container appears and its card reads "2 items left when you last looked,
  just now. It may have changed."
- `mobile_area_check.mjs persist` after stopping and restarting the local server:
  same session, 38 cells and the mark still there.
- `mobile_stick_fight_check.mjs`, new step: with a zombie chasing from 10 to 16 m
  the overview was opened and closed itself as it arrived (`areaClosedOnThreat`),
  then the fight was won at 100 health.
- `mobile_stick_check.mjs` still passes with the extra AREA button.

**Tested publicly on 0.6.0**
- `mobile_area_check.mjs`: every step above passes (15 to 30 cells, container mark).
- After the cold redeploy: `mobile_area_check.mjs persist` passes (35 cells, the
  mark, no new session); `mobile_stick_check.mjs` passes; `mobile_stick_fight_check`
  wins its own fight (the chasing-zombie chance for the overview did not arise
  there, so that step is local evidence only).
- Saved data from before the release: `mobile_world_persist_check.mjs` and
  `mobile_body_persist_check.mjs` both pass.

**Not built in this stage**
- Player-placed pins, marks for depleted trees/rocks, pinch zoom, a route home
  from the overview (the note gives distance and bearing; Walk home is still in
  the Home tab).

**Still unverified**
- A person on a physical phone; legibility of the dim/dark fog in daylight.
- The public outing in the plan (two streets, a container, home, revisit after
  respawn). Death keeping memory is covered by server tests, not by a browser.
- A real half-mile GPS recenter keeping the old area (true by construction: memory
  is keyed by player, not by anchor; not exercised).
- Memory size and redraw cost for a player near the 5000-cell cap on a slow phone.
- Tiles for the overview still come from tile.openstreetmap.org; panning 3 km at
  three zooms asks for more of them than the street view did.

Harness files: `/tmp/osz-area-public-storage.json` and `-evidence.json` (mode 600,
never print). Local server 8019 now runs 0.6.0 from `/tmp/osz-stick-serve.sh`.

Next: C6 optional slow jobs at home, then C7, C8, C9 and the M5 remainder. Open
gates from earlier stages are unchanged: M2 station recipes and ten-minute outing,
M3 doorway precision, and everything that needs a person and a physical phone.

### C6 released as 0.7.0 — 2026-10-11 (Claude)

Live 0.7.0, gameplay `2209f05`. Railway `<deploy-id>`
SUCCESS, then the same build redeployed for a cold process:
`<deploy-id>` SUCCESS (`a5e36b3b` REMOVED).

**Implemented** (all additive; the world clock is wall time, so everything below is
a stored timestamp and needs no ticking while the player is away)
- Vegetable plot: recipe `plot` (3 seeds, 2 branches), object kind `plot`, ready a
  real day after planting, harvest 10 ingredients and 3 seeds, replants for another
  day. `survival.GROW` holds time and yield per bed kind. The five-minute `garden`
  recipe is unchanged and a bed already in the ground keeps its own `ready`.
- Smoked rations: `survival.SLOW["smoke"]` (3 ingredients, 4 branches, beside a
  cooking fire you built). Work op `slow` takes the materials after 5 s and writes
  `job` on the fire with what it will give and when; op `take` collects it once
  (3 Smoked Rations, 30 cooking experience). The job keeps the rules it was started
  under. One job per fire; a fire with a job on it cannot be dismantled. New item
  `smoked`: hunger 60, calm 20, not perishable.
- Skill manuals: ten items `manual_<skill>` (kind `book`), rare finds in bedroom,
  kitchen, bathroom, garage and police tables (under 12% of a room table). Action
  `study` (`app/game/study.py`): inside your own home building, the book leaves the
  pack and `Actor.study` records `done_s` and `since`. Progress is `done_s` plus
  time since `since`, so it counts while the game is closed and cannot double-count.
  Walking 2 m away or being grabbed banks the time and pauses. After an hour the
  skill joins `Actor.studied` and `progression.award` doubles it for this life.
  One book at a time; a skill already learned refuses the book without using it.
- Home tab: "Running at home" lists crops, station jobs and the book with fixed
  finish times (`home.jobs`), Walk there, and Stop / Keep reading. Fire and plot
  cards show time left, Harvest and Collect are disabled until ready, and the Cook
  drawer puts what is on the fire first. Top chip reads "Reading · N min left".
- Coming back: `home.returning` adds `away.home` to the hello message ("You
  finished the ...", "Ready at home: ..."), shown as one message.
- Dials: `plot_grow_s`, `smoke_s`, `study_s`, `study_leave_m`.

**Tested locally (commit `2209f05`)**
- 209 server tests (10 new in `tests/test_slow_jobs.py`): the plot is refused at
  0 and at 24 h less a minute, harvested once, then refused; the quick garden and
  an old bed keep 300 s; smoking completes with nobody present, is collected once,
  refuses a second job, an early collect and dismantling; an interrupted start
  costs nothing; a job keeps its start-time rules; reading for an hour doubles one
  skill and not another; leaving pauses, repeated taps and repeated views give the
  same finish time; one book at a time; a grab closes the book; every skill has a
  manual in some table; the home list does not change per second; and through the
  hub with a real database: start a plot, a smoke job and a book, drop the player,
  a new hub a day later reports all three, collects and harvests once, and a third
  hub offers nothing again.
- Five Node regressions and syntax checks.
- `tools/mobile_slow_check.mjs` at 393x851 touch Chromium, five stages with the
  local server stopped and restarted between each (the hour and the day stood in
  by `tools/slow_clock_fixture.py`, which edits a local SQLite file only):
  home (set home, empty list explains itself); read (manual seeded by the fixture:
  Read at home, book leaves pack, chip counts, Stop pauses, Keep reading resumes);
  smoke (told "You finished the Carpentry Manual" on return; walked out, gathered,
  built a fire, started smoking from the fire's own Cook drawer, early collect
  refused, planted a plot, card and Home list agree); collect (told "Ready at
  home: Smoke rations.", collected 3 once, second refused); harvest (10 and 3
  once, second refused, another 24 h).

**Tested publicly on 0.7.0**
- `mobile_slow_check.mjs home` and `smoke` pass: a fire was built and smoking
  started at about 18:08 UTC with real gathered materials, and a plot planted.
- After the cold redeploy: earlier harnesses still pass (`mobile_area_check
  persist`, `mobile_world_persist_check`, `mobile_stick_check`).
- Real hour, public, 19:08:19 UTC 2026-10-11 on 0.8.0 (the job was started on
  0.7.0 at about 18:08 UTC and came through the 0.8.0 cold redeploy):
  `mobile_slow_check.mjs collect /tmp/osz-slow-public` printed
  `{"toldOnReturn":true,"collectedOnce":3,"secondCollectRefused":true,"noNewSession":true,"errors":[]}`.
  A run 40 s before the hour was up correctly reported nothing ready.
- PENDING, real time: `... harvest /tmp/osz-slow-public` after 18:10 UTC on
  2026-10-12.

**Still unverified**
- Reading on the public server: no manual has been found there yet (rare loot),
  so public evidence for study is the server tests and the local browser run.
- A person on a physical phone; whether an hour and a day feel right; whether
  manuals turn up often enough to matter.
- Toasts, including the return message, can cover the Explore button for a few
  seconds (existing toast placement).
- The plot may be placed on any clear ground, including a street, like other
  non-solid builds.

Harness files: `/tmp/osz-slow-public-storage.json` and `-evidence.json` (mode 600,
never print). Local server 8019 runs 0.7.0; its database has clock-shifted test
survivors named SlowCheck.

Next: C7 (life day counter, area-shared rain, one shared event), then C8, C9 and
the M5 remainder.

### C7 released as 0.8.0 — 2026-10-11 (Claude)

Live 0.8.0, gameplay `01cf6fb`, Railway `<deploy-id>`
SUCCESS (`f11e95ec` removed). No cold redeploy was run for this release: C7 stores
nothing.

**Implemented** (`app/game/weather.py`; nothing is saved, everything is a pure
function of area and the real clock, area = geohash-5, about 4.9 km)
- Life day: `body.day`, real days from the survivor's start, day 1 first. Shown on
  a chip beside the noise chip and on the death card. It triggers nothing.
- Rain: decided per area in four-hour blocks, about a quarter of them. Barrels
  fill every 10 s instead of 30 s; work noise carries 0.6 as far. Chip reads
  "Day N · Rain"; streaks are drawn outdoors only.
- Helicopter: at most one pass per area per three-hour block (chance 0.35), only
  when the middle of the area is in daylight. Heard for 90 s, overhead for 600 s.
  Overhead it is a certain loud noise (200 m) every 8 s at each survivor who is
  outdoors, so idle zombies walk toward them. Inside any building, or in the
  first hour of a life, it passes over. Events `heli` coming / overhead / gone;
  a chip, messages and a synthesised rotor sound on the client.
- Dials: `rain_*`, `heli_*` in `content.py`. Utilities failing is not built (the
  plan defers it).
- Tests now run under a calm sky by default (`calm_sky` in `tests/conftest.py`),
  except `tests/test_weather.py`.

**Tested locally (commit `01cf6fb`)**
- 217 server tests (8 new): day 1 for a new life and day 4 at 3.5 days; the day
  number does not change the sky; rain is the same for two points in one area,
  lasts the block, differs in another town, and is 20 to 30% of blocks; rain
  gives 5 barrel units where dry gives 2 and work noise 21 instead of 35; two
  survivors of different ages in one area get the identical helicopter events,
  once per phase; overhead draws an idle zombie 80 m from a survivor outdoors and
  not while the survivor is inside (and the test fails with the pull set to 0);
  a first-hour survivor and the warning phase draw nothing; about one or two
  passes a day, daylight only, never across a block edge.
- Five Node regressions. Client scripts are now also checked as modules (copy to
  .mjs, `node --check`): plain `node --check` missed a duplicate `const` that
  stopped the page loading during development.
- `tools/mobile_sky_check.mjs` against `tools/serve_fast_sky.py` (local test
  server with the sky sped up): "Day 1 · Rain"; heard first with chip and
  message; overhead indoors says stay inside; stepping out turns the chip red
  with "get indoors"; gone removes it; no overflow in portrait or landscape.
- Bots (`walk_bots.py --heli`, mixed policy, 120 walks of 15 min at travel pace,
  the bot stays outdoors for the whole ten minutes):
  day 32.9 notices/h and 4% died without, 49.6/h and 9% with;
  night 59.0/h and 24% without, 87.4/h and 42% with. Night passes were removed
  for that reason.

**Tested publicly on 0.8.0**
- `mobile_sky_check.mjs <public> <prefix> day`: "Day 1 · Rain", agreeing with the
  real schedule (rain over the test area until 20:00 UTC on 2026-10-11).
- Earlier harnesses still pass: area persist, stick check, and the steered fight,
  which this time also saw the Area overview close itself as a chasing zombie
  arrived (`areaClosedOnThreat: true`), so M4 threat dismissal now has public
  evidence.

**Still unverified**
- A real helicopter pass on the public server. The next ones over the test area
  (44.9778, -93.265) are heard at 12:44:17 and 17:05:07 UTC on 2026-10-12;
  `weather.next_helicopter(lat, lng, now)` prints later ones.
- Whether a person hears the rotor sound as a helicopter, and whether ten minutes
  and 200 m feel fair, above all for someone walking outdoors on GPS who cannot
  step inside a building.
- No rain sound. Rain and the helicopter are not shown in the Area overview.

Next: C8 (herds, only after geometry indexing and load gates), C9 (sprite
overlays) and the M5 remainder. From 0.7.0 the real-hour `collect` has now
passed publicly (19:08 UTC 2026-10-11, see the C6 entry); the real-day
`harvest` is still waiting.

### C8 gate: bounded geometry, released as 0.8.1 — 2026-10-11 (Claude)

Live 0.8.1, gameplay `1fc23c3`, Railway `<deploy-id>`
(previous `c812b300` removed). This is the prerequisite the plan sets for herds,
not herds themselves. **C8 stays unticked.**

**Why.** A tick grew with every town anyone had walked through. Measured with the
new `python -m tools.geometry_load` (synthetic towns of 600 houses, three walking
survivors, 40 s at 5 ticks a second, a door opened every 5 s; step + three views):

| towns loaded | buildings | before, mean ms | after, mean ms | after, p95 ms |
|---|---|---|---|---|
| 1 | 600 | 4.2 + 71.5 | 1.8 + 4.1 | 2.2 + 7.6 |
| 4 | 2,400 | 23.5 + 81.6 | 3.2 + 4.7 | 4.1 + 7.4 |
| 12 | 7,200 | 59.9 + 96.1 | 3.4 + 5.3 | 4.2 + 7.3 |
| 30 | 18,000 | not run | 3.9 + 5.4 | 5.5 + 8.5 |

Twelve towns before was 156 ms mean and 250 ms at p95 against a 200 ms tick.
Rare single views of 75 to 139 ms remain with 7,200 to 18,000 buildings loaded;
I take them to be Python's heap sweep over that many objects, not measured
separately, and it is the reason for the unloading below.

**Implemented**
- `buildings.py`: the buildings table counts its own changes (`_Table`), and the
  search grid, the door-by-id lookup and the loading order are rebuilt only when
  that count or a layout changes (`Buildings.stamp()`), not on every `revision`
  bump from an opened door. `candidates(..., line=True)` walks only the grid cells
  a sight line or step passes through; `near()`, `first_blocking()` and `remove()`
  are new. `opening()` is a lookup, with a remembered miss for homes in towns
  nobody is in.
- `sim.py`: nearby buildings, the zombie obstacle test and outdoor stash placement
  use the grid. `view(actor, known)` describes the walls only when the
  `building_key` differs from the one the hub last sent. A shelf's in-view flag
  (`stashes[][8]`) is a sight test only in the building the survivor stands in,
  `False` in other buildings and `null` outdoors: the client reads it nowhere else.
- `survival.sync_geometry`: boards are put up or taken down only when the set of
  boarded openings or the loaded buildings change.
- `building_loader.py`: `forget_far()` drops a region nobody has been within
  700 m of for 15 minutes, after saving door states, unless a zombie stands in it
  or a neighbouring loaded region shares the building. It comes back from the
  database with no network.

**Tested locally**
- 226 server tests (9 new: `tests/test_geometry_index.py` holds the grid, the
  thin-line search, `near` and `first_blocking` to a walk over every building on
  1,500 random steps and looks; two loader tests cover forgetting, the zombie
  guard, shared border buildings and the offline return). The line test fails
  with the padding removed and the loader test fails with the zombie guard
  removed. Five Node regressions pass.
- Phone, local 8019: `mobile_stick_check` and `mobile_room_check` pass.

**Tested publicly on 0.8.1** (19:33 UTC, after the cold redeploy)
- `mobile_stick_check`: all fields true, creep heard 3 m, full push 20 m.
- `mobile_area_check persist /tmp/osz-area-public`:
  `memorySurvivedRestart: true, known: 35, noNewSession: true`.
- `mobile_world_persist_check` on the public evidence files: all true.
- `/healthz` five times: 0.08 to 0.11 s.

**Still unverified**
- `forget_far` has not been watched on the public server: it needs 15 minutes
  with nobody near a loaded region, and it only logs at INFO.
- The multi-town numbers are synthetic towns on this machine, not production.
- A region that fell back to placeholder shelters is still not refreshed while
  someone stays in it (the M5 "expired-region refresh" item); it is refetched
  the next time it loads, which unloading now makes happen sooner.

Next: C8 proper. A herd as one simulated thing on a shared schedule, drawn as a
crowd, that breaks into zombies only when it notices someone; then the load gate
with herds awake.

### C8: herds, released as 0.9.0 — 2026-10-11 (Claude)

Live 0.9.0, gameplay `aa5e53d`, Railway `<deploy-id>`
(previous `1be8c208` removed). **C8 is ticked** on the measurements below; what
is still unverified is listed at the end.

**Implemented**
- `app/game/herds.py`. A herd is one object with a count. When and where one
  crosses is a pure function of the geohash-6 region and the real clock
  (`_crossing(region, block)`, two-hour blocks, chance 0.3, 45 to 70 strong,
  25 minutes at 0.5 m/s), so everyone meets the same herd and a restart does not
  invent another. It is brought into the world only when its planned place comes
  within 260 m of a survivor older than an hour and nobody could see it arrive.
- Walking: keeps to the streets (never inside a building, not through an open
  door), slides along walls, and when blocked goes round one way and keeps to
  that way. A loud noise turns the whole herd towards it for up to 90 s; a noise
  made within 35% of its reach wakes it on whoever made it. A building mapped on
  top of it (footprints arriving late) moves it to the nearest open ground.
- Noticing uses the rule one zombie follows, measured from the nearest part of
  the column: within sight with a clear line, or moving feet heard through a
  wall; keeping low shortens it, a new arrival is not noticed. Then the herd is
  replaced by its zombies (`h:<herd>:<wake>.<i>`, shamblers, temporary) standing
  where the figures were drawn. Once none of them is after anyone for 120 s,
  those left (eight or more) are one herd again and walk on.
- It leaves the world when nobody is within 416 m, or when its time is up and
  nobody is looking.
- Client: one row per herd in view (`herds: [id, lat, lng, count, seed, facing]`);
  the crowd is drawn from those numbers with the zombie sprites, figures that
  would stand inside a building are left out. A herd is "seen" to 1.8 times
  normal sight (99 m by day), which is beyond the lit circle on a phone, so
  there it is an amber arrow with `HERD · 107 m` at the edge. Events: heard (a
  direction, from 140 m), seen, woke. The Area overview shows the column.
- Six more zombie looks, `zed_s10` to `zed_s15` (postman, police officer,
  farmer, bride, firefighter, teacher), and four survivor sprites `surv_p4` to
  `surv_p7`, from the same Qwen-Image prompts as the first batch (raws and job
  list in `art/raw_v2/`). `ZED_VARIANTS` is 16. The spawner keeps its old random
  draw and takes the look from a hash of the zombie id: 601 zombies in 81 cells
  compared equal in place, kind, health and pace before and after. The four
  survivors are files only: the player sprite is still fixed to `surv_p1`,
  because the swing and shove frames exist for that one only.

**Measured (the C8 check)** `python -m tools.geometry_load --towns 1 --players 1
--seconds 90`, step + view, mean ms, on this machine while a browser check ran:

| around one survivor | zombies | step | view |
|---|---|---|---|
| no herd | 26 | 1.17 | 1.31 |
| one herd of sixty walking | 26 | 1.13 | 1.29 |
| a pack of six awake (`--herds 1 --size 6 --awake`) | 32 | 1.64 | 1.44 |
| one herd awake | 86 | 5.74 | 2.87 |
| two herds awake | 146 | 22.98 | 3.20 |

Twelve towns, three survivors, two herds awake: step 16.3 (p95 25, max 32), views
8.8 (p95 12). So a walking herd costs nothing measurable and less than a pack of
six awake; two awake herds take about a tenth of the 200 ms tick. The step from
one to two awake herds is steeper than double; I did not profile it.
- Health check with two herds awake, real local server and database
  (`serve_herd.py 8021 load 2`, `mobile_herd_check.mjs … load`): 60 requests,
  median 1.6 ms, p95 2.8, worst 9 (limit 300). Phone browser: 120 zombies in
  sight, 51 frames a second, ping median 17 ms.

**Tested locally**
- 239 server tests (13 new in `tests/test_herds.py`). Each of these rules was
  removed in turn and its test failed: arriving in sight, sparing a new
  survivor, the schedule not bringing a woken herd back, not noticing a new
  arrival, keeping low, a wall hiding it, the count after gathering again, the
  open doorway, the building mapped on top, going round one way. Five Node
  regressions pass.
- Phone, `tools/serve_herd.py 8021` + `tools/mobile_herd_check.mjs`, four runs
  of four: heard at 121 m, seen at 111 m as an edge marker, 60 of 60 figures
  drawn at 40 m with no zombies of its own, woke into 60, 55 to 57 frames a
  second walking and 48 to 51 awake, no page errors.
- Found by that check and fixed: a herd trapped inside a building whose outline
  loaded after it; a blocked herd bouncing off a long wall at random.
- The test server removes all ordinary zombies (they were killing the waiting
  scout) and has no schedule; it is not evidence about the real schedule.

**Tested publicly on 0.9.0** (21:20 to 21:35 UTC)
- `/healthz` `{"ok":true,"version":"0.9.0"}`, five times 0.08 to 0.09 s; the new
  sprites are served.
- `mobile_stick_check`: all fields true, creep heard 3 m, full push 20 m.
- `mobile_area_check persist /tmp/osz-area-public`:
  `memorySurvivedRestart: true, known: 35, noNewSession: true`.
- `mobile_world_persist_check` on the public evidence files: all true.
- A new survivor's state messages carry `herds` (6 of 6, no rows) with no page
  errors.

**Still unverified**
- No real scheduled herd has been met on the public server. The schedule puts
  these near the usual test point (44.9778, -93.265): 2026-10-12 14:46 UTC
  (nearest 106 m, 68 strong) and 16:23 UTC (95 m, 53 strong). A survivor older
  than an hour standing there should get the "heard" warning, and at 16:23
  perhaps the edge marker. `/tmp/osz-area-public` holds such a survivor.
- After a restart a woken herd's zombies are gone and the schedule may bring the
  herd back for the rest of its 25 minutes (`herd_spent` is memory only).
- When a herd gathers again its figures jump from where the zombies stood to the
  column; and a figure that was drawn beside a wall can start a few metres off
  when it wakes.
- How it feels to a person on a phone: whether 99 m of warning and 0.5 m/s is
  fair, whether sixty is too many once awake, and how often one should come.
  All of it is in `TUNE` (`herd_*`).
- Not profiled: why two awake herds cost four times one.

Next: C9 (overlays on the survivor for bag, bandage, blood and held weapon; the
four new survivors need a way to be chosen and their own action frames, or the
fallback pose), then the M5 remainder. Still waiting on the clock: the C6
harvest check after 18:10 UTC on 2026-10-12.

### C9: the survivor shows their state, released as 0.9.1 — 2026-10-11 (Claude)

Live 0.9.1, gameplay `ec03c8a`, Railway `<deploy-id>`
(previous `db91c87a` removed). **C9 is ticked** for the one survivor sprite; the
limits are at the end.

**Implemented** (client only, `app/static/js/main.js`, from state the server
already sent)
- Painted on a copy of the frame, only where the figure is, and kept until the
  state changes: blood stains in three bands (health under 75, 50, 25); an open
  wound as a dark mark at its body part, brighter with a drip while it bleeds;
  a bandage as a pale band there, clean or dirty.
- Pinned to fixed points of the standing pose (`PART_AT`, measured on
  `surv_p1`): a worn rucksack or school bag behind the shoulder, a helmet, and
  the weapon in hand. Each weapon picture lies its own way, so `HELD` turns each
  one until its business end points up from the fist. All of it mirrors with
  the figure.
- During the authored swing and shove frames only the stains are drawn: those
  frames carry their own bat and their poses differ.
- Eight new gear sprites in the same clay style (helmet, rucksack, school bag,
  boots, leather jacket, fire jacket, fire trousers, gloves; raws and prompts in
  `art/raw_v2/`). Dropped gear now has a picture instead of a grey square.
- The firefighter look `zed_s14` can leave a fire jacket (the note in the C4
  entry waited for that look to exist). Body loot follows all sixteen looks: the
  postman no longer inherits the office worker's table by `variant % 10`.

**Tested locally**
- 239 server tests; the body-loot test now covers sixteen looks and fails with
  the old `% 10`. Five Node regressions.
- `tools/mobile_look_check.mjs` on 8019: a new survivor's real state shows the
  bat in hand and the school bag; then, with the connection muted in the page
  and state set by hand, ten screenshots (three hurt bands, open and bleeding
  wounds, clean and dirty bandages on head, arm, thigh, neck, shin, helmet,
  both bags, all five weapons, facing both ways), 60 frames a second, no page
  errors. That second part proves the drawing, not the rules behind it.
- `mobile_stick_fight_check` on 8019: own kill, swings while steering, no page
  errors (the survivor was not wounded in that fight).

**Tested publicly on 0.9.1** (21:45 to 21:55 UTC)
- `/healthz` `{"ok":true,"version":"0.9.1"}`; the gear sprites are served.
- `mobile_look_check`, `mobile_stick_check`, `mobile_area_check persist
  /tmp/osz-area-public` and `mobile_world_persist_check` on the public evidence
  files: all pass.

**Still unverified or not done**
- A wound received in a real fight has not been photographed; the wound and
  bandage marks were only seen with state set by hand.
- With a knife or axe in hand the swing still shows the bat frames, and the
  helmet and bag are missing for the 0.4 s of a swing or shove.
- Torso and leg clothing (shirt, leather, fire gear, gloves, boots) is not drawn
  on the figure, by the C9 rule "not new sprite sets per outfit".
- The four new survivor sprites `surv_p4` to `surv_p7` are still not selectable:
  the anchor points and the action frames belong to `surv_p1`.
- No person has judged it on a physical phone.

Next: the M5 remainder (human tuning and atmosphere, expired-region refresh).
Waiting on the clock on 2026-10-12: a scheduled herd past the test point at
14:46 and 16:23 UTC, and the C6 harvest check after 18:10 UTC.

### M5 map refresh and sealed-home soak, M4 pins: released as 0.9.2 — 2026-10-11 (Claude)

Live 0.9.2, gameplay `a5e6914`, Railway `<deploy-id>`
(previous `571707f2` removed). 247 server tests, five Node regressions.

**Implemented**
- *Expired-region refresh* (`app/game/building_loader.py`). A loaded region
  whose map has run out is asked for again in place (`refresh_due`, one region
  per pass, the survivor's own region first, the 5 s politeness gap kept). Until
  now that only happened on load, so a street that got placeholder shelters in a
  map-server hiccup kept them while anyone stayed. When real outlines arrive
  the shelters leave in the same moment, except any that is a home, is boarded,
  or has a survivor standing in it (`in_use`, `refreshed`): that one stays, is
  written back into the region's row so it survives a restart, and a real
  building that would stand on it is left out until a later refresh finds the
  shelter empty. The same keep rule now guards the load-time refresh, which
  used to drop a home shelter outright.
- A map-server outage no longer replaces real outlines whose thirty days ran
  out with placeholders: the known map is kept and asked for again in an hour.
- A map answer of "nothing here" is stored as `empty` and asked for again after
  a day, not every hour. An Overpass reply of 200 with a `remark` and no
  elements (a query that timed out) is treated as a failure, not as an empty map.
- What existed only inside a replaced shelter goes with it: room supplies, a
  survivor's search record (also for someone who was away, on their return),
  unsaved door states. Survivors in that region get one line: "The real map of
  these streets has arrived. Buildings have changed."
- *Sealed homes* (C1). `tools/sealed_home_soak.py`: one synthetic town where
  every house is a shut home, with street packs, the director for two survivors
  and a herd of sixty woken on the middle street. It counts any zombie inside a
  house while that house is shut, judging "shut" itself, not by the rule under
  test. A four-minute version is in the test suite.
- *Area map* (M4). The player's own pins: tap empty ground, choose Supplies,
  Danger, Shelter or Come back; tap a pin to remove it. Forty at most, kept
  with the remembered map across lives (`memory.pin`; not an action, like
  looking at the map). Used-up resource spots (felled trees, quarried rock) are
  marked from the home record that already held them.

**Tested locally**
- Refresh: four new server tests, each failing on the old code (kept shelters,
  the overlapping real building left out, row and restart; still-away server
  asked once an hour; expired real map kept through an outage; empty and
  timed-out answers; supplies and search records of a vanished shelter).
- Refresh, live: `tools/seed_placeholders.py` + `tools/mobile_map_refresh_check.mjs`
  on port 8022 against the real map server. A phone-sized survivor standing
  still saw 6 shelters, then 19 real buildings 49 s later and 36 with no
  shelters left once the neighbouring regions followed; told once, not moved,
  no supplies left pointing into vanished shelters, 60 frames a second.
- Soak: six simulated hours (seeds 1 to 3, owner in and away): 11 to 34 street-pack
  zombies, 45 to 74 director zombies and a herd per run, 25 to
  49 break-ins per run, **0 zombies inside a shut home**. With the protection
  rule switched off the same tool finds them (7 in six four-minute runs), so
  the watch is not blind.
- Pins: three server tests; `tools/mobile_pin_check.mjs` on 8019 (four
  thumb-sized buttons, pin lands under the finger, tap names it, both pins
  there after a reload, remove leaves one, survivor not moved).
  `mobile_area_check` and `mobile_stick_check` still pass.

**Tested publicly on 0.9.2** (22:07 to 22:25 UTC)
- `/healthz` 0.9.2 in 0.08 to 0.11 s.
- `mobile_pin_check`: 5 of 6 runs pass. The first run straight after the deploy
  failed and its output was not kept, so the cause is unknown.
- `mobile_area_check persist /tmp/osz-area-public` (`known: 35`, no new
  session), `mobile_world_persist_check` on the public evidence files and
  `mobile_stick_check`: all pass.

**Still unverified or not done**
- The live refresh has not been seen on the public server: it needs a region
  that fell back to shelters there. It logs `map of <region> refreshed` at INFO.
- A home in a kept shelter was tested on the server, not walked on a phone.
- The soak is a simulation in a synthetic town. The public one-hour sealed-home
  observation and Tom's original saved-home case are still open, so the M5 box
  and C1 stay unticked.
- The used-up resource mark was drawn on the phone with its place set by hand;
  the rule behind it has a server test only.
- Pins show only in the Area view, not as arrows on the street.

**Crouch and vaulting (the M5 "evaluate" item): looked at, nothing built**
- Crouch: QUIET already is the sneak (footsteps carry 3 m instead of 20 m,
  harder to spot, measured in `mobile_stick_check`). Project Zomboid's sneak is
  the same idea (PZwiki, by search summary: 20% sound radius and 40% detection
  chance while sneaking); whether cover lowers being seen there is disputed
  among its players. A second button would add nothing. A later bounded rule
  could be "QUIET against a wall is harder to see".
- Vaulting: an open or smashed window is already a way through, at no cost.
  The Zomboid rule worth borrowing is the price of a smashed one: about a second
  to climb, and a cut unless the glass was cleared with a tool in hand or gloves
  are worn (which would give the new gloves a use). Not built: it adds a way to
  get hurt, and the plan asks for this after the controls have been tried by a
  person on a phone. No generic Jump button.
- pzwiki.net refuses automated reads (403 on pages and on its API), so these
  numbers came from search summaries and should be checked by a person.

Next: what is left needs a clock or a person. On 2026-10-12: the scheduled herd
past the test point at 14:46 and 16:23 UTC and the C6 harvest check after
18:10 UTC. Open without a person: M2 station recipes on the object card, M3
doorway precision. Open with a person: everything marked physical phone.

### M2 whole outing on a phone, two polish fixes: released as 0.9.3 and 0.9.4 — 2026-10-11 (Claude)

Live 0.9.4, gameplay `8ad1133`, Railway `<deploy-id>`
(0.9.3 was `464efe1` / `ca049b9d`). 248 server tests, five Node regressions.

**What was found first.** The M2 boxes for door and window cards, station
recipes, threat collapse and work progress were unticked, but the code for all
of them is there (`app/static/js/world-ui.js`). What was missing was a run of
the whole thing on a phone. So this stage is mostly evidence, not new features.

**Implemented**
- `tools/mobile_outing_check.mjs`: a new survivor on the street walks to a
  building, opens the door from its card, searches the shelf and takes one
  thing from the drawer, drinks from the belt, makes the room home from a piece
  of furniture, stores what was found, takes a piece of furniture apart, and
  boards a window with the wood from the window's card. It asserts the full
  Pack / Home / Work sheet never opened. It swings at any zombie within reach
  and redoes a step that a fight interrupted. It only picks a building whose
  shelf and a window are in the room behind the front door.
- 0.9.3: a boarded window no longer offers the OPEN WINDOW chip (the server
  refused it anyway). A building tagged only `building=yes` is shown as
  "Building", not "Yes" (one new server test).
- 0.9.4: toasts are placed under the top bar when they appear. They used to
  sit at a fixed height, over the "Nearby: Chest" line whenever the goal text
  ran to two lines.

**Tested locally** (8019, fresh test database)
- Outing: passes in 64 to 69 s on a fresh database. On a database left by
  earlier runs it often fails: the nearest simple building has its window
  boarded already, and the bigger ones need exploring that the check does not
  do; a passive version of the check was also killed several times before the
  survivor was made to swing from the first step.
- Toast placement at 393x851, 851x393 and 360x560: under the bar, clear of the
  controls. `mobile_stick_check` passes.

**Tested publicly** (23:37 to 23:46 UTC)
- Outing on 0.9.3: third attempt passed in 52 s; on 0.9.4: passed first time in
  54 s (door opened, bandage / helmet taken, drank, home made, stored, bed
  dismantled for 3 planks and 4 nails, window boarded, 0 sheet openings, hp
  100, 59 to 60 frames a second). The two failed attempts on 0.9.3 were the
  check's own navigation (a window in another room), not the game; they got as
  far as dismantling.
- On 0.9.4: toast placement at the three sizes, `mobile_stick_check`,
  `mobile_area_check persist` (`known: 35`). On 0.9.3: also
  `mobile_world_persist_check` and `mobile_pin_check`.

**Left on the public server by these runs.** Four test survivors named
OutingCheck with homes: two in "Minneapolis Public Service Center" and one in
each of the two small "Roof" buildings south of the test point, each of which
now has one boarded window. Remove them from the dashboard database if they are
in the way; nothing else depends on them.

**Still unverified or not done**
- The M2 "public ten-minute outing" box stays unticked: this was a script, it
  took under a minute, nothing attacked it (0 swings in both public passes) and
  it never equipped anything. It shows the path works end to end without the
  full sheet; it does not show ten minutes of a person playing.
- Station recipes were not part of this run (a station has to be built first;
  the C6 smoke stage drove a camp fire by direct calls, not by its card).
  Gathering, rest and utility buttons on the cards were likewise not tapped.
- The threat warning and the collapse of drawers under a real attack were not
  seen here, because nothing attacked.
- M3 doorway precision with the thumb stick is untouched.

Next: nothing further can be closed without a clock or a person. On 2026-10-12:
the scheduled herd past the test point at 14:46 and 16:23 UTC, and the C6
harvest check after 18:10 UTC. Then Tom on a physical phone.

### M3 doorway precision: the thumb stick slides along any wall, released as 0.9.5 — 2026-10-12 (Claude)

Live 0.9.5, gameplay `d1ace93`, Railway `<deploy-id>`
(SUCCESS). Client only: `app/static/js/buildings.js`, `app/static/js/main.js`.

**What was wrong.** The stick's step used the rule everything else uses: when a
step is blocked, try it on one compass axis. That slides along walls that run
north-south or east-west and along no others. On a building turned from the
compass, a push that met the wall stopped dead, and a push that clipped a door
frame got in about half the time.

**Implemented**
- `buildings.js` `slide()`: blocked, the step keeps the part that runs along
  whatever blocks it (nearest blocker first), so it slides along a wall at any
  angle and goes round the end of a wall, which is what a door frame is. It
  moves a hair (at most 1 mm a frame) off the wall as it goes so rounding
  cannot leave the survivor stuck to it; a push square on to a wall goes nowhere.
- `main.js` uses `slide` while steering by thumb or keys. A tapped walk keeps
  the plain `move`, so that a blocked route is still noticed and planned again.
- Zombies, herds and the server's own survivor step are unchanged. I wrote the
  same rule for the server (`Buildings.follow`) and took it out again: on a
  phone the server's body kept up equally well with the plain rule in all
  three runs below, so there was no evidence for changing authoritative
  movement.
- `tools/doorway_precision.mjs` (no browser, no server): the page's own wall
  rules stepped at 60 frames a second against a 12 x 10 m building with one
  open 2.4 m doorway, turned 0 to 60 degrees; start 4 m out and up to 2.5 m to
  one side; stick held up to 35 degrees off straight; paces 2, 6 and 24 m/s
  (fighting, exploring, sprinting: the exploring pace is 6 m/s, not walking
  pace). `tools/mobile_doorway_check.mjs`: the same on a phone-sized browser
  against real buildings.

**Measured** (`node tools/doorway_precision.mjs`; "in" means indoors within 8 s)

| at 6 m/s | clean through | clips the frame | meets the wall leaning towards the gap | leaning away or square on (should stay out) |
|---|---|---|---|---|
| plain rule, building square to the compass | 93 of 93 | 12 of 28 | 16 of 16 | 0 of 86 |
| plain rule, turned 15 to 60 degrees | 93 of 93 | 13 to 19 of 28 | 0 to 1 of 16 | 1 to 4 of 86 |
| sliding rule, every angle | 93 of 93 | 28 of 28 | 16 of 16 | 0 of 86 |

The sliding rule gives the same row at 2 and 24 m/s. The plain rule at 24 m/s
wrongly carried up to 13 of 86 "leaning away" pushes indoors.

**Tested locally**
- 248 server tests pass (unchanged count: no server change). Six Node
  regressions pass, the new one being `tests/doorway_client_regression.mjs`
  (the table above at 2, 6 and 24 m/s must be perfect for `slide`; a 5 degree
  lean at a creep gets in within 40 s).
- `mobile_doorway_check` on a fresh local database: beside an 18 m wall of the
  federal courthouse turned 62 degrees, stick held 45 degrees into it at 6 m/s:
  slid 13.7 m to the far end, phone 0.27 to 0.34 m off the wall throughout,
  server body 0.29 to 0.74 m off it and at most 1.3 m behind, together once
  stopped. Then its front door (2.4 m, turned 59 degrees), standing 3 m out and
  1.03 m to one side so that a straight push clips the frame: went round the
  frame and in, then turned hard along the inside of the wall; phone and body
  both indoors, 0.07 m apart.
- Red checks: the same check against the old phone rule fails ("got 11.6 m
  along a 18 m wall"), locally and against public 0.9.4 before the deploy.
  With the phone's new rule and the server's old or new rule it passes, which
  is why the server rule was not kept.
- `mobile_stick_check` and `mobile_outing_check` (54 s) pass.

**Tested publicly** (0.9.5, 00:02 to 00:10 UTC on 2026-10-12)
- `mobile_doorway_check`: slid 13.6 m, phone 0.27 to 0.34 m off the wall, body
  at most 1.65 m behind and together once stopped; through the door round the
  frame, phone and body indoors together.
- `mobile_stick_check` passes; `mobile_outing_check` passes in 57 s (0 swings,
  0 sheet openings, hp 100, 60 frames a second).

**Left on the public server by these runs.** Two more test survivors:
DoorwayCheck (the red check on 0.9.4 and the 0.9.5 run each joined under that
name, so there may be two), and a fifth OutingCheck with a home in a "Roof" building. The
courthouse's front door was opened by the check.

**Still unverified or not done**
- One wall, one door and one push angle were tried on a phone; the breadth is
  in the browserless table, which uses a made-up building. Inner doors,
  windows climbed through and furniture were not tried.
- The sliding survivor moves in a faint sawtooth, up to 7 cm out from the wall
  and back about once a second at exploring pace. I judged it too small to see;
  nobody has looked at it on a physical phone.
- A thumb on glass is not a held direction: all of this is Chromium touch
  emulation. The M3 phone test box stays unticked.
- The rest of the M3 line (target and facing feedback, Finish, range cues) was
  not looked at in this pass, so the box stays unticked.

Next: unchanged. On 2026-10-12 the scheduled herd past the test point at 14:46
and 16:23 UTC, and the C6 harvest check after 18:10 UTC. Then Tom on a physical
phone.

## Codex follow-up: playable details and building depth (0.10.0 work)
Tom reports body taps not working, missing character selection and clumsy interior UI after Claude's final 0.9.5 handoff. Preserve all C1–C9 work; this is new follow-up scope.

- [x] Implement body hit regions matching rotated sprites and labels, plus a nearby-body affordance. Existing server range, LOS, shared stock and interruption rules remain authoritative.
- [x] Implement eight-look appearance picker under Worn, remembered per device. Alternate characters use procedural swing/push; authored p1 bat poses only play for p1 holding a bat.
- [x] Correct body look descriptions to the current 16-shambler roster (including firefighter 14).
- [x] Implement raised exterior wall faces and low interior cutaway. This first depth pass retains the map projection; it is not a full isometric camera.
- [x] Implement extra windows on sufficiently long portions of the established outward window wall, appended after legacy door/window/room IDs and room placement. Short walls and shared terrace faces stay conservative.
- [x] Expand door/window touch targets from midpoint circles to the full opening segment.
- [ ] Verify updated server regressions, phone touch selection/search/drawer, appearance change/reload, and interior movement/doors. Distinguish injected render fixtures from real combat or persisted protocol tests.
- [ ] Commit/push and deploy current 0.10.0 to OSZ; verify health and phone checks publicly.
- [ ] Improve interior flow further: target hints, room transitions, clutter overlap and reachable search affordances in crowded rooms.
- [ ] Full isometric view: one reversible projection shared by tiles, actor feet, furniture, openings, selection and touch-to-walk; depth-sort walls/entities and hide obstructing foreground walls. Preserve overview and GPS logic.
- [ ] Multiple playable floors: building-level floor metadata and deterministic layouts; durable actor floor/building state; stair transitions and escape path; floor-scoped zombie sight/path/collision, bodies, containers and constructed objects; save migration/reload/death tests. Do not draw pretend upper floors and call them playable.
- [ ] Physical Pixel 9a acceptance remains with Tom; automated Chromium touch emulation is not a physical phone test.

Next concrete action: finish the local phone/regression checks, release this usability pass, then build the shared isometric camera and floor foundations. Old scheduled herd/harvest gates from Claude remain open and time-dependent.

### Storage steering incorporated in 0.10.0 work
Tom additionally reports deposits into household chests are unclear or broken. Existing server storage supports the home cupboard, household wardrobes/counters and built crates; map loot containers have a separate shared-search purpose. The compact storage drawer previously placed deposit rows after all stored items, burying them on a phone.
Implemented: visible Store shortcut when a home exists, closest reachable owner storage selection, Store from pack / Stored supplies tabs defaulting to deposit, Store 1 / Store qty, Take 1 / Take qty, capacity remaining, worn-equipment and full-container feedback. The world and combat controls remain visible. Real cupboard and household-container transfer/reload checks are in tools/mobile_storage_check.mjs; results pending at this entry.
Local existing whole outing passes with the new drawer: 58s, actual door/search/loot/drink/home/deposit/dismantle/barricade, no full sheet, hp100, 44fps while another browser check runs. Previous isolated outing before the storage change: 67s, hp100,59fps. Real tilted-wall/doorway check also passes after extra windows.
Appearance change/reload + render-fixture body tapping pass; injected body tests do NOT prove actual kills/search/persistence. Existing server corpse tests pass unchanged. 249 server tests and seven Node regressions pass; all browser modules parse.

### Indoor zoom steering incorporated in 0.10.0 work
Tom requests desktop mouse-wheel zoom and mobile pinch-to-zoom because fitting large footprints makes objects too small to click. Implemented in app/static/js/indoor-zoom.js with the existing map projection shared by drawing, taps and walk targets. Indoor scale ranges 0.5×–8× with a 64px/metre ceiling; enlarged views follow the survivor rather than leaving them offscreen at the footprint centre. Zoom/reset is visible indoors and the factor is remembered on the device. A second canvas finger cancels stick/walking and consumes both releases; a finger on combat controls still attacks. Single-finger indoor taps/stick steering are retained. Tests/zoom_client_regression.mjs covers bounds, wheel, pinch and release; tools/mobile_storage_check.mjs now includes CDP two-finger and wheel acceptance.
Storage protocol acceptance before zoom change: real home cupboard deposit/withdraw, generated wardrobe deposit and reload durability, worn schoolbag deposit blocked, no browser errors. Indoor zoom phone check pending. Full isometric projection and playable upper floors remain open subsequent phases.

### 0.10.0 local acceptance and release preparation
Implemented and locally verified: eight character choices/change/reload; fallen-body/head/label touch selection and nearby-body shortcut; raised wall/cutaway depth pass; extra independent windows with legacy opening IDs and unchanged room points; full-opening touch targets; compact storage with visible deposit/withdraw tabs and single-item transfer; indoor mouse-wheel and pinch zoom with reset and no movement on pinch release.
Evidence: 249 server tests, eight Node regressions, all browser modules parsed as modules; tools/mobile_details_check.mjs passed (body render fixtures only); tools/mobile_look_check.mjs passed (real starter state plus explicitly injected overlay render states); tools/mobile_doorway_check.mjs passed real tilted wall and door; tools/mobile_outing_check.mjs passed twice (67s and58s, real doorway/loot/home/storage/work, no full sheet); tools/mobile_storage_check.mjs passed real cupboard deposit/withdraw, household wardrobe deposit/reload, worn-item rejection, wheel and real two-finger CDP pinch without walking. Browser checks are emulation, not physical Pixel9a.
Running current isolated server: port8023, SQLite /tmp/osz-polish-v010.db, exec session28975. Older servers8015–8018 are historical fixture/backend versions: do not use for current verification. New harnesses tools/mobile_details_check.mjs and tools/mobile_storage_check.mjs. Screenshots /tmp/osz-details-phone.png, /tmp/osz-storage-phone.png, /tmp/osz-polish-outing-*.png.
No actual new kill/body search was played in this pass; unchanged corpse server search/persistence tests passed, and previous released C4 body search acceptance remains historical. Full isometric camera, floor/stair foundations, crowded-room polish, character-specific authored animation/precise gear attachment on alternate looks, physical phone and scheduled clock gates remain open. New appearance is device-local and does not grant depicted clothing/gear stats.
Release action next: commit/push current worktree and stage current app to native Linux, deploy separate OSZ service, then public details/storage checks. Never deploy the old0.4.x stage without refreshing it.

## 0.10.0 live acceptance / next delivery phases
Gameplay commit5b367ab pushed to Gitea. Railway deployment<deploy-id> SUCCESS; /healthz returns0.10.0. Public tools/mobile_storage_check.mjs passes real cupboard deposit/withdraw, wardrobe deposit/reload, worn rejection, wheel and CDP pinch without movement. Public tools/mobile_details_check.mjs passes eight choices/change/reload, fallen-head taps both orientations and nearby-body shortcut; bodies in that harness are render fixtures, not proof of natural kill/server search. Actual new kill/body-search outing remains to run.
Tom explicitly requests continuing until all listed remaining work is finished. Updated delivery order:
- Phase9 usability pass: 0.10.0 released; remaining crowded-room targeting/action feedback and actual body-search outing.
- Phase10 full isometric projection: implement shared projection/inverse across tiles, actors, buildings, props, hit testing and walking; foreground cutaway and depth sorting; preserve north-up Area overview/GPS. Not yet built.
- Phase11 playable floors/stairs: stable floor layouts/loot, actor floor persistence, stair transitions/escape, floor-aware zombies/collision/visibility/bodies/home construction, migrations/reload/death. Not yet built.
- Phase12 combat/atmosphere/acceptance: character-specific animations and attachment points, target/facing/Finish review, extended remembered-area outing, shelter/herd/farming/absence gates, balance. Physical Pixel9a, Safari and actualGPS travel cannot be certified by Chromium emulation; retain explicit hardware gates.
Later separate scope remains vehicles/hauling, occupations/traits, survivor corpse-pack recovery and shared-base membership, per SURVIVAL_ROADMAP.md; these were not claimed released.
Current local server8023 /tmp/osz-polish-v010.db (session28975), current native deployment stage/tmp/osz-railway-20261010 refreshed from repo. No browser checks running after public acceptance. Continue from current0.10.0, never historical8015–8018 fixtures.

## Phase10 isometric implementation milestone (0.11.0 work)
Shared reversible 30-degree isometric projection now lives in projection.js. World tiles, footprints, actor feet, props, body/container/home/opening hit tests, construction preview and tap walking use the same transform/inverse. Keyboard/thumb screen directions convert back to east/north before collision and movement; aim effects, heard-noise and herd direction cues project forward. Area overview stays north-up. Optional flat-map preference is in the pack settings; 3D is default. Interior fit and wheel/pinch zoom operate on projected footprint bounds, zoomed views follow the actor. Tiles fetch the inverse viewport bounds rather than leaving empty rotated corners. Sight and scream/range rings are ground ellipses.
Wall faces and world furniture join the actor depth queue; entered walls and walls covering the survivor cut away. Closed windows show glass panels, doors use wood faces. Unselected container labels no longer pile up over household furniture. Backend collision/save/gameplay remain unchanged in this phase.
Local checks so far: nine Node regressions including coordinate round trips at every zoom; public-style mobile_storage_check on local current UI passes deposit/withdraw, wardrobe reload, wheel and pinch; mobile_details_check passes appearance/reload and body hit fixtures. New tools/mobile_projection_check.mjs uses real terrain, a real canvas tap and held touch stick: tap walks to its projected target; thumb moved3.10m exactly aligned (cosine1), no browser errors. Whole outing and adapted doorway checks still running. Inspect /tmp/osz-isometric-world.png and /tmp/osz-storage-phone.png for actual current screenshots. Do not deploy until the remaining checks complete.
Next: finish Phase10 acceptance/release, then Phase11 floor foundations. Older browser harnesses that calculate north-up screen pixels directly must be updated to __osz.project/__osz.screenVector before they can test the new view; their old assumptions are not evidence of a game bug.

### Phase10 local acceptance / 0.11.0 release preparation
All249 server tests pass; nine Node regressions plus module parsing pass. Real isometric indoor outing passed73s (actual door open/search/loot/drink/home/deposit/dismantle/barricade, hp100,55fps,0 full-sheet opens). Adapted tilted-wall and frame-clipping doorway test passes: phone0.27–0.342m off wall, server≤1.51m behind then converged; through2.4m doorway turned59degrees and hard turn indoors, both bodies inside together. The old fixed5s wall deadline first expired at13.49m of required15m; rerun with a deadline computed from distance/current pace plus4s passed. No collision tolerance/range/physics test was loosened. Debug trace contains only geometry, positions and health. Updated harnesses use the same projected screen coordinates as the game.
Current projection/interaction/storage regressions are locally accepted. Phase10 release next; public checks pending. Phase11 stairs/floors is still planning, not implemented. Continue after release. Backend on local8023 is still the0.10.0 process; gameplay backend unchanged in this camera phase, static code is current0.11.0. Stage current source before deploying.

## 0.11.0 public acceptance / Phase11 foundations in progress
Live gameplay9aa15fd; Railway<deploy-id> SUCCESS. Public real projection check passes: projected tap walks correctly and touch-stick direction matches exactly (3.20m, cosine1). Public storage/zoom check passes cupboard deposit/withdraw, wardrobe deposit/reload, wheel/pinch and no movement on pinch release.
Phase11 foundations now under construction in the worktree, NOT released: Actor has saved floor level/building/epoch; isolated simulation layers reuse geographic footprints and keep ground zombies separate; stairs require proximity/LOS and no melee hold; upper movement cannot leave the footprint through an opened window; per-floor opening/room IDs stay distinct; actor and opening-state foundational tests pass3/3. A new BuildingLevel persistence model is added but Hub load/save, storage/loot floor filters, stale-position epoch checks, stair UI and end-to-end/cold-restart checks are still pending. Original249-test run found a building-key positional assumption; preserve revision at key[0] while adding floor identity to the key. Do NOT deploy this foundation yet.
Next concrete step: complete floor-aware protocol, durability and client stairs, run the full regression suite and actual upper-floor phone/cold-state checks; then release Phase11. Phase12 extended combat/atmosphere/acceptance and physical phone gates remain open.

## Phase11 implementation / local acceptance in progress (2026-10-12)
Playable floors now have isolated zombie/collision/loot/body layers, distinct upper openings and rooms, saved actor floor/building/epoch, and a BuildingLevel table for persistent opening states and cold-map geometry. Floor-aware household furniture/storage, built objects and discovered loot keep ground stock separate. Delayed movement packets from previous floors are rejected; upstairs transit jumps and open-window walking outside are rejected. Stairs show on the world and floor button, with approach/up/down actions. Exit building walks to stairs, opens internal doors as needed and descends before exiting on ground.
Verification: 256 server tests, nine Node regressions and all JS module parses passed. Seven floor tests include real Hub/database cold reload with no loaded map, independent upper openings, ground zombie isolation, range/melee guards, separate loot/furniture and upstairs exit via an interior door. First actual normal-server Chromium phone run passes up, independent floor loot, reload upstairs and automatic descent/exit; second rerun/storage extension in progress. Physical phone remains unverified. Do not deploy until full final-current-backend floor/storage checks finish. Current new local backend8024, /tmp/osz-floors.db, session11827. Live remains0.11.0 9aa15fd / Railwaybbb71995.
Next: verify upstairs storage and the final server build; actual natural kill/body search, then Phase11 release and Phase12 polish/extended acceptance.

## Phase11 local acceptance / 0.12.0 preparation
- [x] Playable two-floor buildings, three-floor large offices/apartments/commercial buildings; small sheds/garages remain one floor. Floors/layouts are fictional game geometry inferred from footprint, not surveyed real interiors.
- [x] Stair approach/up/down controls, world stair symbol, floor indicator, automatic internal-door/stair descent with Exit building.
- [x] Floor-specific zombies, corpses, loot, openings, furniture and construction; saved floor epochs reject stale movement. Ground hordes cannot bite upstairs. No walking outside through upper windows.
- [x] Durable floor/opening blueprint, cold reload without map, upstairs home/storage and existing save defaults; normal new phone launch still starts at current GPS on ground.
- [x] Nine floor server tests including third-floor limits, upper bodies, blocked-room exit and missing-blueprint isolation. Full suite258 tests; final full-suite run underway at entry.
- [x] Actual normal-server phone check passes up, separate upper loot, upstairs home/deposit, GPS launch reset to ground with saved upstairs stock, climb up again, automatic descent/exit; no browser errors.
- [ ] Public floor acceptance after release; physical Pixel9a remains open.
Correction to earlier local milestone: the initial reload-upstairs assertion briefly observed the pre-GPS snapshot and was not valid phone-launch acceptance. The completed harness explicitly waits for GPS launch to finish on ground, confirms upstairs stock, then climbs again. Cold Hub/database test independently proves saved upstairs position for non-GPS resume. No GPS behavior was changed to satisfy the test.
Current backend8024 session11827 runs the accepted floor implementation (the final missing-blueprint safety fix is covered by tests and will be in0.12.0). Live remains0.11.0 until deployment. Existing natural kill/body search rerun and ground storage/zoom regressions are running. Phase12 remains target/facing/Finish feedback, character anchor/animation polish, longer outings/remembered area and clock/hardware gates. Do not mark all work complete.

## 0.12.0 live / Phase12 in progress
Committed/pushed583b06c; separate OSZ Railway<deploy-id> SUCCESS. Public actual-phone-emulation floor check passes: up, floor-specific loot, upstairs cupboard deposit, fresh GPS launch on ground with saved upstairs stock, climb up again, automatic descent and exit. Ground cupboard/wardrobe storage, reload, wheel and pinch all pass locally. Full258 server tests, nine Node regressions and module parses pass before release.
Current Phase12 worktree: per-character standing equipment and wound pins measured against all eight existing illustrations; alternate-character swings rotate held tools procedurally. A compact INTERACT chooser lists nearby bodies, furniture, containers, stairs and openings to resolve crowded/overlapping targets without a full-sheet menu. Implementation is not yet accepted/released. Authored attack art remains p1 bat and the existing p8 zombie; other poses are procedural, not falsely advertised as new sprite art.
Natural real kill/body search attempts: real kills succeeded twice; first search drawer timeout and second body-foot selection timeout. These do not prove body-search acceptance. Added diagnostic output and changed the real-body tap to the visible fallen torso; rerun pending. Existing server body/conserved stock tests remain passing. Keep this gate open until the normal-server UI path actually completes.
Next: target/facing/Finish range feedback, nearby chooser acceptance, real body search, long outing/remembered area and slow clock gates. Physical Pixel9a/Safari/actualGPS travel remain human hardware acceptance. Current0.12.0 release is accepted for floors; entire task is not complete.

## Phase12 local progress (not yet released)
- [x] Per-character standing gear/wound pins for all eight existing illustrations; procedural weapon rotation follows alternate-body swing/shove poses. No new raster sprites generated.
- [x] Server supplies actual swing/shove/shoot target IDs; client highlight/facing uses those IDs, with in-reach/Finish/approach/blocked distance text. The weakest downed target chosen by server now matches the preview.
- [x] INTERACT compact nearby-object chooser for overlapping bodies/shelves/furniture/openings/stairs; map/combat remain visible. Raised door/window faces now have touch regions matching their rendered pane, as well as ground segments.
- [x] Real natural own kill, fallen-torso tap, body search → compact drawer, searched stock/reload passed on8024. That natural body happened to be empty; actual transfer stock remains covered by existing conserved-stock server tests and prior C4 acceptance.
- [x] Current8025 real stick fight passes own kill,2.7m retreat, accepted swing while steering,hp100,no JS errors. Complete interior outing passes56s actual door/search/take/drink/home/deposit/bed dismantle/window boards,0 full-sheet opens,hp100,53fps while other browser checks run.
- [ ] Updated character/reload and actual nearby chooser checks running; full259 server tests passed before final shove-target addition. Eleven Node regressions after pose/opening hit additions; final suite pending.
- [ ] Ten-minute extended normal-server exploration running: at122s84real canvas legs475m,hp100,min45fps,two remembered-map checks. Not yet a ten-minute acceptance claim.
Handoff:8025 /tmp/osz-combat-v0121.db session54220 runs Phase12 backend;8024 remains floor backend, earlier8023 camera/backend legacy. Live0.12.0 583b06c/e93fc9b9 publicly accepted floors. Pending public Phase12 and clock/hardware gates. Details harness's phone reload initially waited forever on GPS hunt/start policy; appearance/body-render regression now explicitly uses a map start to isolate those features from GPS. Separate floor harness continues testing actual phone GPS launch. Do not conflate these scopes.

## 0.12.1 Phase12 polish release preparation
Implemented server-matched swing/shove/shoot target previews and facing, Finish/in-reach/approach/blocked distance hints; eleven Node regressions now include distinct character poses and raised opening-face touches. All eight existing character illustrations have individual hand, helmet, bag and wound anchors; alternate weapon poses animate procedurally. INTERACT is a compact nearby-target chooser with44px rows for crowded-room bodies, storage furniture, shelves, doors/windows and stairs.
Local actual chooser acceptance passes choosing stairs→normal upstairs action→upper shelf; map/combat remain visible,no overflow,no JS errors. Character changes/reload + both rotated-body head hit fixtures pass with explicit map-start isolation from GPS hunt policy. Actual natural own kill/torso tap/body search/compact drawer/reload passed earlier; current real stick fight and complete interior outing pass as recorded above. Final259 server tests and eleven Node regressions/module parsing running before release. Ten-minute local exploration still running (245s,172real legs792m,hp100,min45fps,3 remembered-map checks,1 chooser check): not complete yet and not a public ten-minute claim.
Pending after release: public chooser/character/real combat and extended exploration; production scheduled harvest/herd cannot be marked passed early. Physical Pixel9a/Safari/GPS movement remain explicit human gates. Optional later vehicles/occupations/shared membership are beyond the agreed implemented1–8 and10–12 delivery scope.

## 0.12.1 live / extended acceptance running
Committed/pushed0c2571f; separate OSZ Railway<deploy-id> SUCCESS; public health reports0.12.1. Final259 server tests, eleven Node regressions, all JS module parses pass. Local actual nearby chooser and character/reload fixture checks pass; complete interior outing and natural stick combat pass. Existing pins check passes put/remove/reload and remembered depletion markers,44px mobile actions,60fps.
Synthetic sealed-home soak rerun:600simulated seconds for owner home/away,3seeds6runs,73–92zombies at once including street packs/director/herd;0zombies inside while outside openings stayed sealed. Break-ins were counted separately and legitimately allowed. This is a simulation fixture, not600wall-clock public seconds.
Local10min canvas exploration still running at366s254legs998m,hp100,min45fps. New public10min exploration and public chooser are running; do not prematurely tick the ten-minute gate. Current local herd fixture8026 (/tmp/osz-herd-v0121.db,session1214) and current isometric heard/seen/woken browser check running. It explicitly seeds a herd locally; production scheduled-herd gate remains open until its actual time. C6 public crop isn't due until18:10UTC2026-10-12; current clock about03UTC. Do not harvest early or edit the live clock/data to claim it.
Tiny follow-up in worktree: extra and upper windows should expose Smash just like the original Window; glass sound recognizes all window labels. Header/active pickup notes will be updated after final acceptance. Physicalphone/Safari/realGPS travel still need human hardware evidence.

## 0.12.2 final edge-case preparation
Extra/upper windows retain their original opening kind in the action card, so Smash is available independently of the display label; glass sounds match Window2/Upperwindow. Unit tests cover all label variants and actual upper-window smash without ground damage or walking outside. Stairs now wait for initial map loading and clear the actor safely against refreshed ground geometry on descent; a server regression covers a newly arrived ground wall.
Current suite261 server tests + eleven Node regressions/module parse final run pending; 259 passed before these two floor tests. Local GPS API emulation passes new-player GPS, real touch-stick movement preserved through three drift fixes, recenter after four consistent1050m fixes over9seconds, and a fresh app opening at a different current GPS location. Public GPS equivalent running. This is emulated geolocation, not physical phone travel.
Public0.12.1 nearby chooser and appearance/reload/body-hit fixture checks pass. Natural public stand-and-fight body harness timed out without an own kill; it is not a body-search pass. Local own-kill/body search/reload is accepted. Real current combat test also passes Finish preview and auto-close Area on chasing threat,2ownkills,hp100,2.1m retreat,accepted swings while steering.
Current herd fixture check passes heard61m→seen51m→60 figures drawn39.7m→32individual zombies wake,55fps awake,health max2.9ms. Synthetic herd fixture is explicitly local; scheduled public herd remains open.
Long canvas runs initially stalled on controls/object hit regions: harness now excludes actual navigation bounds, raised opening faces, prop hits, container/body screen regions; longer clear targets are allowed. It skips pressing disabled Stop after touch release. Earlier interrupted/stalled runs are NOT complete ten-minute acceptance. Current corrected local/public runs continue; at182s local800m/public793m,hp100,no JS errors. Final elapsed/results pending.
Production crop remains due18:10UTC2026-10-12; physical Pixel9a/Safari and actual GPS travel/absence remain human/time gates. All requested gameplay features are implemented; retain truthful acceptance gaps in the active checklist.

## Sustained local/public acceptance passed; final upstairs persistence fix
Corrected10minute normal-server canvas exploration checks completed601seconds each, no injected world state and no JS errors. Public396real accepted legs2681m,hp100,min45.6fps,7 remembered-map checks. Local388legs2571m,hp100,min47fps,7 overview checks and1 compact nearby chooser check. Current public full interior outing rerun is underway; do not equate the exploration benchmark with a single human enter/loot/craft/home story. The earlier stalled/interrupted harness runs are superseded, not treated as passes.
Public GPS API-emulation check also passes fresh current-GPS launch, independent touch-stick movement through drift, four consistent1050m fixes causing recenter, and new opening at a different GPS location. Actual physical phone GPS travel remains unverified. Public appearance/reload/body render fixtures and compact chooser pass; local actual kill/body search/reload and actual Finish/steered combat pass. Public stand-and-wait body harness got no own kill before its deadline, so no new public natural-body acceptance is claimed.
0.12.2 f753b85 deployed to Railway<deploy-id> (status/health next check). Adds all-window Smash metadata and safe stairs after map refresh. Suite261 server tests and11 Node checks before release.
Final discovered Phase11/C1 persistence gap being fixed: upper inhabitants now save physical position/health with the building blueprint and restore calmly. A saved cleared upstairs room stays clear, including after corpse/death expiry. Unknown upper rooms in a sealed home cannot seed a new inhabitant. Two new regressions pass alongside11 previous floor cases (13floor tests). Full263-test run and final-current-backend8028 phone check pending. Final source not yet committed/deployed. Current8028 session records to follow.
Time/hardware gates remain: scheduled public herd at14:46/16:23UTC and public crop18:10UTC2026-10-12; physical Pixel9a/iOS Safari, actual GPS/audio/long absence and human balance review. Core requested feature delivery complete; retain those acceptance gates without claiming hardware or future-time evidence.

## 0.12.3 final release preparation — 2026-10-12
Upstairs residents now retain position and health through a cold Hub/database reload; saved cleared floors remain cleared, and protected homes do not receive freshly seeded upstairs residents. Home status labels its floor. Walk home selects stairs for an upstairs cupboard instead of walking repeatedly toward its ground footprint; cross-building upstairs travel directs an exit first. Storage explains floor mismatches.
Accepted locally on current backend8028: real stairs, separate upper loot, upstairs home water deposit/reload, current GPS ground launch, Home Floor2→Walk home→stairs→Upstairs, automatic descent/exit, no browser errors. Final263 server tests,12 Node regressions, all browser module parses and git diff check passed. See CURRENT_STATUS.md for authoritative requested-feature checklist and carefully distinguished acceptance evidence. Public final deployment/floors/storage regression follows; scheduled herd/crop and physical phone/human balance gates remain open.

## Final 0.12.3 public acceptance and handoff — 2026-10-12
Gameplay commit ffd41df is pushed to Gitea; separate OSZ Railway<deploy-id> SUCCESS. Public /healthz reports0.12.3. Final263 server tests,12 Node regressions and all browser module parses pass. Public normal-server floors check passes actual stairs, independent upper loot, upstairs water storage/reload, fresh GPS ground placement, Floor2 home label/Walk home→stairs, automatic descent and exit; no browser errors. Public storage check passes cupboard deposit/withdraw, actual wardrobe deposit/reload, worn-item rejection, wheel/pinch zoom and no pinch-release walk; no browser errors.
Requested delivery implementation through survival1–8 and current isometric/floors/combat/interactions follow-up is complete. CURRENT_STATUS.md is the authoritative concise pickup; historical checklist evidence remains preserved. These are automated Chromium phone-viewport checks, not physical Pixel9a or Safari certification. The scripted ten-minute exploration and62s interior story are separate, not a human integrated outing. Remaining acceptance: scheduled public herd14:46/16:23UTC and crop harvest after18:10UTC2026-10-12; physical phone/audio/GPS/background/long-absence; human ten-minute balance and original saved-home/public one-hour sealed-home observation. Station/gather/rest actions exist, but a human phone review of those buttons remains unverified. Contextual glass-clear/vault injury rules and vehicles/occupations/shared home membership remain explicitly later scope.
Own old backends8023–8025 and seeded herd8026 stopped. Current own local8028 was restarted on final0.12.3 with SQLite /tmp/osz-final-v0123.db, exec session96577; local health reports0.12.3. Historical/Claude8015–8021 untouched. Native deploy stage /tmp/osz-railway-20261010. Tests/tools are committed; browser storage/session artifacts must remain private. No approval prompts or implementation approval pending.

## 0.12.4 live: launch trailer on the title screen (Claude, 2026-10-12 05:15 UTC)
Tom sent https://youtu.be/MRGjiGp57as ("Oh shit, Zombies. Soft launch video.", the promo, uploaded by Tom to his own YouTube account) and asked for it to be embedded in the loading page.
- Implemented: a "Watch the trailer" card under Play near me on the title screen (`index.html` `#trailer`, styles in `style.css`, new `app/static/js/trailer.js`, thumbnail `assets/trailer_thumb.webp`, a 480x270 copy of YouTube's thumbnail made today). The card is a plain link to the video; a tap swaps it for YouTube's no-cookie player in place (autoplay, plays inline, no related videos from other channels). Nothing is requested from YouTube before the tap. `main.js` calls `stopTrailer()` when Play is tapped and when the server's hello hides the title, because a hidden player keeps its sound. `.titleBox` now has `max-height:100%; overflow-y:auto` and 14 px top padding: on a 360x640 phone the title was already as tall as the screen and the card pushed the name off the top. `.tag` gained a text shadow because the text now sits higher over the art.
- Tested locally (scratch server 8031, since stopped): new `tests/trailer_client_regression.mjs` (failed first with the module missing) and new `tools/mobile_trailer_check.mjs` on Pixel 7 393x851 and 360x640: no request to another site before the tap, card 84 px tall, tap stays on the page and opens no tab, the player's own title contains "Zombies", no player error, video time past 1 s after 5 s, 16:9 player on screen with the name and Play still on screen, Play removes the player at once, the title hides when the server answers, the small phone can scroll to the last line and back. Red checks: without `stopTrailer` the tool fails at "Play takes the player out at once"; without the scroll rule it fails at "small phone: the name and Play are on screen". 263 server tests, 13 Node regressions, all browser modules parse. Desktop 1280x800 looked at by screenshot only.
- Deployed: gameplay `5f85a94`, Railway `<deploy-id>` SUCCESS from `/tmp/osz-railway-20261010`; public health reports 0.12.4.
- Tested publicly: `tools/mobile_trailer_check.mjs https://osz-production.up.railway.app` passes (video time 4.7 s after 5 s, no player error).
- Still unverified: a physical phone, and iOS Safari in particular (whether the video starts with sound after the tap there; only Chromium was used). No full outing or floors check was rerun on 0.12.4: the game code change is one `stopTrailer()` call at hello and at Play. The thumbnail is a copy and will not follow a thumbnail change on YouTube. If the video is made private or embedding is switched off, the card shows YouTube's error in the player; change `TRAILER` in `trailer.js` and the link in `index.html` to swap the video.
- Left on the public server: one `TrailerCheck` survivor. Codex's local 8028 was not restarted and still reports 0.12.3 from memory while serving the new static files. Remaining clock and hardware gates are unchanged (see CURRENT_STATUS.md).

## Next feature goal authorized — 2026-10-12
Tom asks continue remaining list in proposed priority order. Active expansion plan NEXT_SURVIVAL_PLAN.md: N1 corpse recovery→N2 curtains/glass→N3 occupations/traits→N4 shared bases→N5 vehicles, then broadcasts, learning and maintenance/utilities. N1 starts now; preserve Claude0.12.4 trailer. Existing goal tool is usageLimited and cannot create a replacement unfinished goal; this does not change user authorization to work or justify claiming completion.

## N1 recovery /0.13.0 release preparation — 2026-10-12
Implemented durable owner-only72h recovery packs preserving exact carried quantities/conditions; worn/held gear becomes ordinary recoverable items, home supplies untouched. Dead-life save and initial recovery stock commit atomically; retries and fast respawn cannot refill packs. Offline turning creates the same durable aftermath with expiry measured from death. Upper-floor pack state carries its floor/building. AREA lists your packs with floor/time/empty status. Death card explains recovery; compact Recover gear/search/Take controls reuse conserved corpse transactions. Nearby shortcut ignores strangers and prioritizes own reachable gear/newer packs. Claude0.12.4 trailer preserved.
268 server tests and14 Node regressions expected final rerun after shortcut extraction. Actual local fatal-neck-wound fixture (tools/serve_recovery.py8030,/tmp/osz-recovery-v013.db,session67642) death→new survivor→owner pack→compact recovery→knife cond2→reload conserved stock passes,no JS errors. Explicit seeded injury, not a production natural-death claim. Public deployment/smoke follows. Next N2 curtains/glass in NEXT_SURVIVAL_PLAN.md. Existing physical/clock gates unchanged.

## N1 live0.13.0 / N2 starting — 2026-10-12
883a66e pushed; OSZ Railway<deploy-id> SUCCESS; /healthz0.13.0. Final268 server tests,14 Node regressions and module parsing pass. Local seeded-fatal-wound actual death/recovery/reload pass as previously documented. Public existing storage/floors smoke running; no production death injection or natural-death recovery claim. NEXT_SURVIVAL_PLAN.md N1 delivered, N2 curtains/glass now starts.

## N2 curtains/glass /0.13.1 preparation — 2026-10-12
Curtains consume2 cloth and refund2 on removal; open/close blocks sight (including zombie targeting) while preserving sound and physical passages. State survives ground-opening reload/relayout and independently saved upstairs blueprints. Clear glass requires a usable held weapon or hammer/crowbar/axe and costs tool condition/endurance. Contextual ground-window Climb through has1.2s work/stamina/range/LOS/obstruction checks; upper windows remain stair-only exits. Walking through windows also pays climbing stamina/delay and uncleared glass can cut an ungloved hand (no zombie infection from glass); bare-handed smashing carries the same glass risk.
Window work uses private geometry and atomically commits opening/cloth/tool/survivor state before publication. Map-loader flushes serialize with Hub mutations; failed saves retry without leaking a free curtain. Work can cancel/move away without material loss. Mobile primary card stays compact with More always available; window options include curtains, glass and climb without the full Pack UI. Fixed stale opening drawer refresh after smashing. Added life IDs to hello/snapshots so a previous-life death snapshot cannot reset a fresh survivor during GPS placement.
Nine window server regressions plus existing suite total277 pass;14 Node regressions and all module parses pass. Local seeded-cloth browser pass is superseded by a normal unmodified server8032 /tmp/osz-normal-v0131.db(session93290) full browser pass: make home→dismantle actual furniture→earned cloth→hang/reload/open/close/remove curtain→cloth conserved→smash/clear glass→climb outside→no position pullback; no JS errors. Public N1 storage/floors smoke passed. N2 release/public earned-cloth window acceptance next; physical phone/human gates remain. Active new feature goal registered after completing the prior released guide implementation. Next N3: per-life occupations/traits with bounded starting skills and explicit strengths/tradeoffs; old lives unchanged, no reroll farming.

## N2 live0.13.1 public acceptance / N3 next — 2026-10-12
255a9fd pushed; OSZ Railway<deploy-id> SUCCESS, health0.13.1. Final277 server tests,14 Node regressions and browser module parses pass. Public normal-server mobile_windows_check earned cloth by making a home and dismantling actual furniture, then passed hang/reload/open/close/remove curtain, material conservation, Smash→Clear glass→Climb outside with no position pullback and no browser errors. Public mobile_floors_check passes upper loot, home deposit/reload, current GPS ground launch, floor-aware Walk home and automatic descent/exit. N1 earlier public cupboard/wardrobe storage/wheel/pinch pass retained. No production injury injection or physical-phone certification.
Current own local8032 was restarted on final0.13.1, SQLite /tmp/osz-normal-v0131.db, exec session30983. Own older8028 and supplied recovery/window fixtures8030/8031 stopped; their DBs and committed fixture tools remain for reproduction. Historical/Claude8015–8021 untouched. NativeRailwaystage /tmp/osz-railway-20261010.
NEXT_SURVIVAL_PLAN.md N1/N2 delivered and publicly smoked. Active expansion goal remains active; next is N3 occupations/traits, then N4 shared bases/N5 vehicles and the remaining N6–N8 systems. Prior guide-vibe implementation goal was closed based on its delivered/released merged implementation; new expansion has its own active goal. No implementation approval needed. Scheduled public herd14:46/16:23UTC and crop after18:10UTC2026-10-12 remain real-time acceptance gates, plus physical Pixel9a/Safari and human balance/saved-home observation.

## N3 occupations/traits — local acceptance, release pending (2026-10-12)

Candidate0.14.0 adds seven occupations and four paired traits. Title/death selectors remember device preferences; server persists immutable per-life choice before GPS placement. Starting ranks are bounded level1, small extras grant once, old saves stay neutral. Trait pace/carry/noise/panic/passive stamina changes retain fatigue/injury limits. Failed saves do not publish partial bonuses; retry and previous-life guards covered.

Evidence:283 server tests,15 Node regressions, JS module parse and diff checks. Cold Hub rejoin/retry preserves exact supplies/ranks. Ordinary local8033 mobile selectors→Medic/Nimble→GPS→Health→reload passed with no JS errors. Local fatal-wound8034 actual death→new-life selectors→Firefighter/Sturdy→fresh GPS passed; fixture did not alter production. Initial browser reload runs timed out; rerun with stage diagnostics passed on ordinary server; fatal fixture now checks respawn separately because its deliberate death interrupts a living reload. Public acceptance pending. Harness tools/mobile_background_check.mjs, title/Health screenshots /tmp/osz-background-*.png. Own8033 session87407, /tmp/osz-background-v014.db;8034 fatal session2655, /tmp/osz-background-fatal.db. Next: release/public check, then N4 shared bases. N1/N2 remain live0.13.1/255a9fd.

## N3 released — 0.14.0 /73111e6 (2026-10-12)

Railway<deploy-id> SUCCESS. Public tools/mobile_background_check.mjs passes Medic/Nimble selection→saved-before-GPS→Health→reload, unchanged profile/supplies despite different future preference, zero JS errors. Public mobile_floors_check also passes stairs/independent loot/upstairs storage/reload/current GPS/home navigation/automatic exit, zero JS errors.283 server tests/15 Node regressions/all JS parse/diff check pass. Local actual fatal-wound death→new Firefighter/Sturdy/freshGPS passed separately. N3 accepted/released; next N4 shared bases. Physical Pixel9a and public natural-death profile choice remain human/unverified checks.

N4 design investigation: current PlayerHome and simulation assume actor.id owns active storage. Implement canonical owner identity and one shared base object; never duplicate shared stock under a member's player ID. Durable invitations/membership/active-base selection survive death, with explicit leave/revoke restoring personal home. Owner alone controls invites, revocation, rename/relocation. Members may use storage/build/work while authorized; revoke cancels pending shared work. Transfer/retry/concurrent saving must commit shared revision and actor stock together. Shared generator/food/rain ticks must run once per base per instant, rather than once per member/floor. Preserve old PlayerHome records; new tables via existing create_all avoid destructive migration. Acceptance must cover two browser players, owner absent/restart, conserved stock/condition, rollback, lost invite/revoke rights, death/new-life membership and private-home preservation. Details and implementation still pending; no N4 code shipped.

Current own ordinary8033/session87407,/tmp/osz-background-v014.db; ordinary8032/session30983 retained. Fatal fixture8034/session2655 is being stopped after acceptance. Older historical/Claude servers untouched. Gameplay73111e6 pushed to Gitea; documentation follow-up pending. Shared Claude memory/gbrain synchronized at pre-release and final milestone.

## N4 shared bases — implementation/local acceptance in progress (2026-10-12)

Candidate0.15.0 (not released): BaseMembership/BaseSelection/BaseInvite new tables, hashed24h invitation code with Builder or Storage role, owner-only invite/rotate/revoke, explicit leave/personal/select. PlayerHome remains one canonical stockpile keyed by owner; active membership survives death and owner absence while personal home is preserved. Runtime binding publication updates all members/floors. Shared stock uses version comparison in DB with actor stock saved in the same transaction; versions publish after commit. Shared work is privately finished then saved with geometry/materials before publication. Revocation cancels shared work/study and restores personal home, also closes old invitation codes. Utility/food tick runs once per base per instant. Offline shared damage uses guarded save. Base switch flushes recent private investment.

Seven initial N4 server tests pass; full290 server suite plus15 Node regressions/all module parses passed before final additions. Ordinary8035 two independent Pixel7 Chromium contexts, actual GPS/map/home creation→private water deposit→owner invitation→member join→withdraw updates owner→owner closes page→member deposit→reload→personal stock retained→shared reselect→owner reconnect/revoke→member restored→old code rejected pass, no JS errors. Harness tools/mobile_bases_check.mjs, screenshot /tmp/osz-base-phone.png. Current8035 normal session2624,/tmp/osz-shared-v015.db;8033/8032 retained. Added further simultaneous-last-item, real flushed transaction rollback and recent personal investment/offline damage regressions, currently running. Re-run local against final backend before release; public acceptance pending. Files app/game/bases.py,home/hub/sim/store/survival,models/ws,client inventory/main/world-ui/index/style,tests/test_bases.py,tools/mobile_bases_check.mjs. Next validate additional tests/UI and final browser, then commit/push/OSZ Railway/public check. N4 checkbox stays unchecked until actual acceptance/release. N5–N8 remain full active goal.

## N4 shared bases — 0.15.0 release preparation (2026-10-12)

295 server tests (12 N4),15 Node regressions/all JS parses/diff checks pass. Additional regressions cover last-item competition by different members, receipt actor identity, flushed SQL commit rollback, stale version rollback of survivor and stock, revoked stale actor rejection, recent personal investment flush and owner-offline damaged defense saving. Member death/new life keeps membership/base while GPS is unplaced. Nearby same-base living teammates now appear with name/default survivor art, restricted by actual sight/floor/range; stranger positions are not exposed. They currently use default p1 art rather than mirroring device appearance preference.

Final local mobile_bases_check includes earned material from an actual member furniture dismantle reflected in owner view, visible teammate, exact shared water transfers, owner page closed, membership/stock reload, personal stock preservation and owner revoke/old invitation failure; no JS errors. The longer noisy-work version initially timed out at reload: diagnostic proved membership/hello loaded, hp100, not mapping, and stale GPS notice. Chromium static geolocation keeps an old timestamp after15s; harness now refreshes emulated location before reload/owner reconnect. Production freshness policy unchanged. Updated background harness uses the same fresh-fix emulation. Final ordinary8035 floors/upstairs storage/ground GPS/home navigation/automatic exit also passes. Own8035 nowsession23604,/tmp/osz-shared-v015.db; old8033/8032 retained. Invitation UI is under Home→Share a base / join friends and world cupboard→Sharing; copy button, Builder/Storage explanation, active-base chooser and Revoke. Stock still uses existing compact world drawer. Public acceptance pending commit/deploy. Next N5 vehicles after N4 public gate.

## N4 released/publicly accepted — 0.15.0 /1366666 (2026-10-12)

Railway<deploy-id> SUCCESS; health0.15.0. Public mobile_bases_check passes two independently authenticated mobile contexts, explicit code join, visible same-base teammate, actual member furniture dismantle seen by owner, conserved water deposit/withdraw, owner page closed/member stock transfer, reload membership/stock, switching preserves personal home supplies, owner reconnect/revoke, teammate hidden after revoke and old code rejected. No JS errors. Public mobile_floors_check passes stairs/separate floor loot/upstairs storage/reload/currentGPS/home navigation/automatic exit; no JS errors.295 server tests,15 Node regressions/all module parses/diff checks passed. No physical phone certification or production death injection. Source1366666 pushed, docs follow-up next. Own final ordinary8035 session23604,/tmp/osz-shared-v015.db;8033/8032 retained. Gbrain/Claude notes synchronized.

N4 completed. N5 vehicles/hauling next, then N6 broadcasts, N7 learning, N8 maintenance/utilities; full goal stays active. Vehicles must be durable world entities with conserved cargo/fuel, seats and driver control, server-authoritative motion/collision/noise, touch steering and contextual enter/exit; neither GPS nor stale client positions may teleport a vehicle. Reuse compact world cards/drawers and canvas isometric rendering. Vehicle state survives server replacement, disconnect/death releases controls, and simultaneous cargo/seat operations commit/retry safely. Parked spawn positions must be outside building footprints and repeatable without replenishing saved stock. Include an abandoned car and a useful hauling van; bounded starting fuel and refill from existing fuel cans. Reserve expanded parts/repair for N8 while giving collisions/breakdowns real consequences in N5. Acceptance: normal mobile drive/exit/load/reload flow, two-player seat/cargo contention, old saves/floors/GPS compatibility, collision and interrupted/disconnected input, then Gitea/Railway/public verification. Design decisions still to implement; no vehicle code shipped.

## N5 vehicles backend milestone — local/unreleased (2026-10-12)

Added app/game/vehicles.py + WorldVehicle table, root World vehicles/dirty/controls and Actor runtime vehicle_id. Stable per-cell car/van outdoor candidates, cargo45/100kg,2/4 seats, bounded starting fuel/canonical once-only stock. Lazy seeds save before publication and skip cached/failed cells for30s. Cargo quantity/condition, worn/weight limits and actor-scoped receipt replay; DB version CAS plus actor stock atomically saved. Claims attach to current base; Storage can handle cargo/passengers, Builder can drive. Seat switch/repeated entry, engine and fuel-can refill. Server motion uses bounded acceleration/turn/reverse, substep footprint/building/vehicle collision, impact condition loss, finite fuel/noise, .7s control expiry/braking. Avatar raw positions cannot move a seated player; riding gives no walking XP. Vehicle state saves every2s. Cold load releases seats/engine without refilling cargo/fuel. GPS placement atomically parks/releases actor without moving the vehicle. Death/disconnect/base-permission change releases controls; drop marks seat release dirty.

Eight new vehicle tests pass; prior full302 test run passed before eighth addition. Final303-test suite running session24200; re-poll or re-run final after last small disconnect-dirty edit. No N5 UI yet, no vehicle browser playtest, no release or push. Current live remains0.15.0/1366666 and docs276f7b3. Existing ordinary8035/session23604 runs old in-memory0.15 backend; do not use it as vehicle evidence. Changed app/models.py,game/vehicles.py,sim.py,hub.py,ws_routes.py,tests/test_vehicles.py plus these notes. Existing JS unchanged.

Immediate next: finish vehicle conflict reload/reconciliation (CAS rejects correctly but stale runtime should refresh so retry succeeds), then add car/zombie impact and vehicle attack protection/consequences. Review close-geometry/roof/car-width checks. Add client scene target/card/cargo drawer and native isometric car/van art, actual driving state/steering/engine/brake/exit UI with server position sync; freshGPS launch clears seat but parks car. Include overview remembered parked-car markers. Then normal local two-player mobile drive/haul/fuel/seat/cargo/reload/death/disconnect/permissions checks, full tests, notes, commit/push/Railway/public acceptance. Keep N5 unchecked and full N5–N8 goal active. Preserve all N1–N4/Claude trailer changes.

N5 test follow-up: session24200 completed successfully, full303 server tests/diff check pass. Last disconnect-dirty edit targeted rerun follows. Code remains uncommitted; no deploy. CURRENT_STATUS.md/AGENTS.md now point to local N5 work.

## N5 mobile controls and resilience milestone — local, unreleased (2026-10-12)

Candidate0.16.0 now has native isometric car/van art, contextual vehicle cards and compact cargo drawer, driver/passenger entry, engine/reverse/brake/exit buttons, touch stick/keyboard/tap steering, server-position camera tracking and speed/fuel/hull HUD. Normal8036 mobile_vehicle_check passed discovery→board→fuel cargo take→stick drive2.28m→brake→engine off→exit→refuel, zero JS errors; screenshot /tmp/osz-vehicle-phone.png. This is emulated Pixel7 Chromium, not a physical phone certification.

Added periodic CAS-conflict durable refresh with stale-control removal, GPS parking input cleanup, out-of-sight-safe remembered vehicle Area markers, full front-to-back hull building clearance, bounded ram damage/corpse creation and vehicle-shell zombie protection. New ram regression caught a real dictionary-mutation crash on zombie death; iteration now snapshots live zombies. Vehicle kills do not train melee. Stop/Area also brakes driving. Latest additions require final browser rerun on restarted server and full suite (session57509) before release.

Live remains0.15.0/1366666; docs276f7b3. N5 uncommitted, checkbox stays open. Ordinary8036 old session76939 uses /tmp/osz-vehicles-v016.db; restart for final source. Test harness tools/mobile_vehicle_check.mjs. Next: final full tests/browser, seat/cargo contention and disconnected-driver/permission checks, release/public verification, then N6–N8. Preserve prior scheduled crop/herd/human gates.

## N5 release preparation —0.16.0 (2026-10-12)

308 server tests including13 vehicle regressions,15 Node regressions and all JS module parses pass. Final restarted ordinary8036/session44620 normal mobile flow passes map discovery→board→cargo fuel take→reload parks survivor without replenishing cargo/fuel→reboard→actual touch drive10.88m→brake→exit→refuel; zero JS errors. Final mobile_floors_check passes stairs/separate floor loot/upstairs stock/reload/currentGPS/home navigation/automatic exit; zero JS errors. Server tests cover actual two-player base join, competing driver seat/last fuel transfers, revoke persistence, cold load preserving damaged gear/cargo/fuel, transaction rollback, GPS park, motion version conflict refresh, ram corpse creation/no melee XP, shell protection, driver disconnect/old life release and stale input. Two-player vehicle browser ride and physical Pixel9a remain unverified; two-player authority/conservation has server evidence.

Releasing candidate0.16.0 now; N5 checkbox stays pending public smoke. Current own ordinary8036/session44620,/tmp/osz-vehicles-v016.db; older8035/8033/8032 retained. N6 next: radios with compact in-world listening and deterministic regional forecasts/shared event scheduling; N7 learning/media, N8 parts/utility preparation remain full active goal.

## N5 released/public acceptance —0.16.0 /32ee139 (2026-10-12)

Railway<deploy-id> deployed; public health0.16.0. Public mobile_vehicle_check passes normal discovery, boarding/cargo take, freshGPS reload parks survivor without replenishing cargo or fuel, reboard, actual stick drive16.28m, fuel consumption, brake, engine off, exit and refuel; zero JS errors. Initial public harness failed on its unguarded pre-state vehicles.some access; optional guard corrected, production unchanged, rerun passed. Public mobile_floors_check passes stairs/separate loot/upstairs storage/reload/currentGPS/home navigation/exit, zero JS errors.308 server/15 Node checks and all module parses passed locally. Physical phone and two-player vehicle browser ride remain unverified; seat/cargo/base contention/revoke have real two-player server tests. N5 accepted and checklist ticked.

N6 local/unreleased implementation has begun: portable loot radios/household radio fixtures, quiet compact scene broadcasts of district rain/upcoming existing helicopter/herd and possible rare shared gunfire/distress sounds. Deterministic six-hour regional schedule, finite140m/90m attraction, five-second dispatch window and durable WorldEvent receipt committed before noise prevent restart/player duplication. No surprise rewards or hidden-zombie coordinates. Full tests running44507; frontend/browser acceptance pending. N6–N8 stay active. Current ordinary8036/session44620 remains released0.16 code in memory; start separate8037 for N6.

## N6 local acceptance —0.17.0 candidate (2026-10-12)

Radios now appear as first-room household/emergency fixtures plus portable bedroom/garage loot. Contextual Listen opens a compact scene drawer with district rain, near-term existing helicopter/herd activity and possible distant gunfire/distress reports. No hidden zombie locations, items consumed or loud playback. Reports carry receive time and explicitly remain potentially outdated. Existing furniture mutations preserve prior fixture changes. Rare six-hour regional sound schedule is seeded identically for all players; attraction radius90/140m, durable WorldEvent fired receipt commits before publication, bounded5s event dispatch window, no per-player duplication or restart replay. Old event receipts prune at startup after7days. Missed events during downtime are skipped, not replayed against returning players.

Full312 server tests/15 Node/all JS parses passed; fifth radio test follows (fixture reach/broken fixture). Normal8037 mobile_radio_check passes ordinary map fixture discovery/currentGPS/reachable scene Listen/map remains visible/no gear consumption/reload repeat, zero JS errors; screenshot /tmp/osz-radio-phone.png. First local harness waited in a nonresidential building with no household radio; fixture generation now also provides an emergency radio in first commercial room, rerun passes. Final floors smoke running45187. Candidate uncommitted/unreleased; current live0.16.0/32ee139 docs c704be6. Ordinary8037/session19541,/tmp/osz-radio-v017.db;8036/session44620 retained0.16. Next final checks→push/deploy/public radio/floors, then N7 magazines/media/knowledge and N8 repairs/utilities.

N6 final local gate:313 server tests/15 Node/all module parses pass; normal8037 floors smoke passes including upstairs storage and currentGPS reload. Radio fixture reach and broken-radio rejection covered. Releasing0.17.0 candidate now; public radio/floors acceptance pending.

## N7 implementation design — pending (2026-10-12)

Preserve existing hour-long home manuals and every existing recipe for old saves. Add per-life durable knowledge/learned-media fields defaulting empty. Magazines teach new optional recipes (vehicle repair kits and protective equipment first) through bounded45–60s reading; existing recipes must not become newly locked. Recipe catalog exposes knowledge requirements and UI explains where to learn; server validates again at start and completion. New recipes supply N8 rather than silently changing old vehicles/utilities.

Add contextual training television/media at a usable nearby fixture, with a compact scene drawer and clear progress/Stop/Resume. Built-in short carpentry/first-aid segments make ordinary-map browser acceptance possible without injected loot; found tapes provide additional defined lessons. XP is bounded and once per lesson per life, repeats cannot farm it, books retain their existing multiplier. Moving away, attack, destroyed/moved fixture or revoked base should pause with banked progress. Cold reconnect must keep elapsed time/knowledge/once-only grants without playing phantom audio. Commit study start/item consumption before publication; rewards and survivor knowledge persist together. Preserve per-life progression and currentGPS fresh spawn.

Acceptance: no duplicate XP/unlocks on retry/reload/clock sampling, pause/resume/fixture/floor/revoke checks, failed-save conservation, old studies/recipes compatibility, normal mobile scene Watch→progress→completion→reload, recipe knowledge hints, Gitea/Railway/public verification. N8 follows with real repair parts/wear and district utility shutdown warnings/finite stored water/generator backups. No N7 code yet.

## N6 released/public acceptance —0.17.0 /9ab5070 (2026-10-12)

Railway<deploy-id> SUCCESS, public health0.17.0. Public mobile_radio_check passes ordinary map radio/currentGPS/scene Listen/map visible/no gear consumption/reload, zero JS errors. Public floors smoke passes stairs/separate loot/upstairs stock/reload/currentGPS/home navigation/exit. Vehicle public regression initially failed its single-direction >1m assertion; expanded ordinary actual-stick steering through up to four directions (parked hulls can face obstructions), rerun passes8.98m driving/cargo take/reload parks without refill/fuel/brake/exit/refuel, zero JS errors. No production game mutation or vehicle spawning fixture used.313 server tests/15 Node/all module parses/diff checks passed. New rare gunfire/distress dispatch and restart receipts have deterministic server tests, not a timed public event observation; original scheduled herd/crop real-time checks remain pending. No physical-phone certification. N6 checklist ticked; N7–N8 remain entire active goal.

Source9ab5070 pushed; documentation/harness follow-up next. Current own8037/session19541,/tmp/osz-radio-v017.db (0.17) and8036/session44620,/tmp/osz-vehicles-v016.db (0.16); older8035/8033/8032 retained. N7 design is written just above and in shared memory/gbrain: preserve all existing recipes/manuals, add magazines/new optional recipes and contextual television/training media with banked progress and once-only per-life XP/knowledge, atomic start/consumption. No N7 code yet. Next implement N7 then N8 vehicle repairs/finite utilities and finish public acceptance.

## N7 implementation milestone —0.18.0 candidate, local/unreleased (2026-10-12)

Added durable per-life knowledge/learned_media (old saves empty), Roadside Repair/Protective Clothing magazines45/60s, new optional repair-kit/reinforced-vest recipes with server knowledge guards at start and finish and mobile hints/disabled unknown recipes. Existing recipes and hour-long manuals remain available. New first-room training television fixture preserves prior fixture IDs/mutations; built-in woodworking/first-aid40–45s lessons plus found workshop/kitchen tapes give defined small XP once per lesson per life. Tapes stay reusable for other survivors. Compact scene Watch/Learning drawer has countdown/Stop/Resume; no playback audio or item depletion.

Generalized study retains banked progress; movement/floor change/destroyed fixture/attack pauses new studies before award, and paused completed-time media cannot auto-award on a later tick until Resume. Vehicle entry pauses instead of discarding study. Base revocation banks progress. Start/item consumption use private saved Actor before publication; new media/recipe completions queue pending_learning then commit current candidate before publishing XP/knowledge. Failed completion retains old XP and retries; cold saved state includes completed lesson identity/XP together. Return-from-offline processing uses private candidate and records new completion/pause messages for immediate save.

Prior full319 server tests passed before final return/craft/boarding additions; targeted learning/legacy studies running44854. Local normal8038 mobile_learning_check running80327 (map→actualTV→Watch→Stop/Resume→once-onlyXP→reload). Existing8038/session34740 holds pre-latest return/boarding source; restart for final acceptance. DB/tmp/osz-learning-v018.db. No release/push yet; live remains0.17.0/9ab5070, docs99d652a. Files study/sim/store/hub/home/floors/survival/vehicles/content/ws/client inventory/main/work/world-ui, tests/test_learning.py and tools/mobile_learning_check.mjs. Next complete final checks/browser and release/public N7, then N8 real vehicle repair/parts/wear and district utility shutdown warnings/finite water/generator backups. Full goal active, N7/N8 boxes unchecked.

## N7 final local acceptance/release preparation —0.18.0 (2026-10-12)

321 server tests (8 learning),15 Node regressions/all module parses/diff check pass. Restarted ordinary8038/session58890 normal mobile_learning_check passes actual map television→scene Watch→Stop after5s with banked remainder→Resume→exact20 carpentry XP→Learned disabled→freshGPS reload retains exact XP/completion and gear, zero JS errors. The first browser run earned correct XP but could not see Learned: Resume mistakenly reopened generic Learning instead of the television drawer. Fixed routing preserves media context; rerun passes. Final local mobile_floors_check passes all floor/storage/GPS/exit checks, mobile_vehicle_check passes normal driving19.51m/cargo/reload/fuel/brake/exit/refuel; zero JS errors. Screenshot /tmp/osz-learning-phone.png.

Tests include magazine identical-start retry/once-only unlock; all old recipes still unlocked; unknown recipes refused at start and knowledge checked again at finish without material loss; media sampling/retry/movement/floor/destroyedTV/paused deadline; required tapes/reusable tape/no repeatXP; real failed start save/cold magazine completion; pending media completion failed DB save leaves published XP unchanged, successful retry/cold state exact; vehicle entry keeps banked study. Offline-return new completion/pause saves private candidate before publication. Release/public N7 gate next; checkbox remains pending public acceptance. Current live0.17.0/9ab5070 docs99d652a, source0.18 uncommitted.

N8 design next: durable shared district first-visit shutdown schedule (power/water independently2–7real days, seeded offsets, never per-life resets), radio/body warnings; finite shared building pipe reserve after water cutoff with empty-bottle refill conserving bottle/water under CAS/receipt and actor save. Existing rain barrels should collect only actual rain (fix magical dry filling) and generators consume elapsed offline fuel once per base, with grid/generator powering TV/fridge and clear backup status. Preserve old homes, recipes and vehicle stock. Vehicle maintenance adds battery/engine/tire wear and condition limits, finite repair-kit/hull scrap/tire/battery replacements, tools and permission/receipt guards; normal mechanic/car-cargo repair flow plus sink/refill phone check, shutdown/backup/offline/concurrency/rollback tests and release/public gates. No N8 code yet.
