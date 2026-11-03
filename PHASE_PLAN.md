# OSZ: playable exploration, progression and buildings

## Current next plan — phone experience, 2026-10-11

See [MOBILE_WORLD_PLAN.md](MOBILE_WORLD_PLAN.md) for GPS-led startup/new-life
placement, world action cards, compact inventory, hybrid thumb controls and a
remembered-area overview. Status: Codex draft awaiting Claude's independent guide
review; Tom requires merging both plans before implementation. Shared progress
updates are required by [AGENTS.md](AGENTS.md).

## Core survival phases — implementation, 2026-10-10

Phases 1–3 and the mobile feedback release below are complete. Tom has now requested
the missing longer survival loop. [SURVIVAL_ROADMAP.md](SURVIVAL_ROADMAP.md) records
the footage/code review, exact gaps, dependencies and unchecked acceptance gates:

1. **Phase 4:** inventory improvements, wearable clothing/armor/backpacks, reusable
   durable storage and a marked home. Implemented with atomic storage and phone equipment controls.
2. **Phase 5:** functional furniture, a furnished base and repairable barricades.
3. **Phase 6:** tree cutting, salvage, recipes and wood construction.
4. **Phase 7:** hunger/thirst/sleep, cooking, water and useful utilities.
5. **Phase 8:** mining, smelting and useful metal upgrades. Vehicles, shared bases,
   occupations and world stories retain their own later acceptance gates.

Core implementations are in Gitea `db44caf`. Release verification finished on
2026-10-10: live is 0.2.6 (gameplay `195dffa`) and every Phase 4–8 acceptance box in
SURVIVAL_ROADMAP.md is ticked. Evidence, the faults fixed on the way and the pickup list
are in BUILD_CHECKLIST.md, ending with "Handoff to Codex — 2026-10-11". Preserve every
existing survivor and mobile control.

Tom explicitly expanded the fun goal on 2026-10-10: complete phases 1 through 3 below. These are required deliverables, not optional future ideas. Preserve the working single-mode phone controls and keep the live ZombieQuest project separate.

## Phase 1 — Explore and loot

- [x] Place discoverable searchable containers around the local play area; distinguish containers that are untouched, searching, emptied, or unavailable.
- [x] Give the player a reason to explore: nearby leads, varied container types and rewards, useful supplies and occasional valuable gear.
- [x] Tap a container to approach it; offer a clear Search action in range. Show search progress, interruption and a readable loot result.
- [x] Make loot enter the pack reliably, with usable/equippable items, quantities, condition and weight. Preserve searched-container state across reload/redeploy; no infinite repeat farming.
- [x] Make searching create noise and exposure. Ensure opening searches are achievable without being guaranteed safe.
- [x] Playtest the full mobile loop: discover → walk → search → receive loot → equip/use → survive and explore again.

## Phase 2 — Experience and skills

- [x] Persist per-survivor total experience, level and skills. Show current progress and the next milestone in the pack/status panel.
- [x] Earn experience for meaningful successful exploration/searches, combat and treatment. Failed actions and repeated taps earn nothing.
- [x] Improve skills through relevant use: scavenging, melee, fitness and first aid. Use bounded bonuses so injuries, endurance and danger still matter.
- [x] Provide readable milestone feedback and explain each skill's effect. Balance early progress so it is visible during a short play session.
- [x] Verify save/reload/redeploy, no duplicate awards, and new-life reset; preserve old survivor records without schema failures. 51 tests passed; public mobile play earned 60 XP, reached level 2 and Scavenging 1, and retained all progression across replacement deployment `<deploy-id>`. Earlier saved loot/session remained compatible.

## Phase 3 — Playable buildings

- [x] Obtain actual building geometry around the GPS play area; current map tiles are raster and cannot provide collision geometry by themselves.
- [x] Generate deterministic, usable floor layouts within supported outlines: rooms, walls, doors and windows. Handle small or unsuitable structures with a sensible simpler layout.
- [x] Render clear enterable buildings and interiors with the existing art direction; the combat camera zoom is 1.5x closer.
- [x] Implement walkable entrances, walls that block movement, doors that open/close, windows and room transitions. Keep tap navigation usable on a phone around obstacles.
- [x] Put loot in room-appropriate containers. Make interior exploration, sound, visibility and zombie pursuit respect boundaries and openings.
- [x] Persist relevant world interactions and provide a fallback when map geometry cannot be fetched; do not block the game on a remote map request.
- [x] Playtest a complete mobile excursion: locate a building → enter → open a door → search rooms/containers → confront or escape zombies → leave with loot.

Final building verification: 75 server tests and the client wall-rounding regression passed. Headful Chromium with Pixel 7 controls entered real OSM building `osm:w:157025243`, opened its entrance and room door, searched both rooms, opened a window and exited. An earlier excursion fought an interior zombie (two combat actions). Local server restart preserved both EMPTY room containers and shared door/window states using the existing session. The complete public phone excursion passed on gameplay commit `e4432f7`; replacement deployment `<deploy-id>` preserved both room claims, shared door/window state and existing sessions. Public navigation/SCREAM and prior loot/progression persistence checks passed.

## Release gates

- [x] Tests cover progression, loot state and spatial rules, with real browser playtests of the complete loops.
- [x] All ready code and assets committed and pushed to private Gitea.
- [x] Updated separate OSZ Railway service passes HTTPS, WebSocket, phone layout and persistence checks.
- [x] BUILD_CHECKLIST.md and Claude's shared gbrain/memory notes reflect the actual result, limitations and next work.
- [x] Tom has the playtest URL and concise instructions.

The goal stays active until the playable requirements above are implemented and verified. A plan or a green narrow test is not completion.

## Pixel phone feedback and faster exploration — 2026-10-10

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
