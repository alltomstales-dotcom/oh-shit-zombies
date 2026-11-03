# OSZ current status — 2026-10-12

Live: **0.15.0**, gameplay `1366666`, Railway `<deploy-id>` (SUCCESS). Includes Claude's title trailer and N1–N4 recovery, windows, backgrounds and shared bases.
Play: https://osz-production.up.railway.app

## Active expansion

Tom authorized the remaining feature list on2026-10-12. Follow [NEXT_SURVIVAL_PLAN.md](NEXT_SURVIVAL_PLAN.md). N1 recovery and N2 curtains/glass are released and locally accepted; N1 public existing-feature smoke and N2 public earned-cloth window flow pass. N3 occupations/traits is released/publicly accepted (283 server tests/15 Node regressions). N4 shared bases is released/publicly accepted. N5 vehicles/hauling is next; N5–N8 remain on the active goal. Existing delivery below is retained.

## Current local work

N5 backend is uncommitted/unreleased: vehicles table, server motion, seats, conserved cargo/fuel and GPS parking.303 server tests pass; latest small disconnect-dirty edit is getting a targeted rerun. Client controls/art/drawers and normal browser acceptance remain to build. See latest NEXT_SURVIVAL_PLAN.md/BUILD_CHECKLIST.md entry. Own8035 still runs the released0.15 backend in memory.

## Requested gameplay delivery

- [x] Appearance selection for eight existing survivors, remembered per device.
- [x] Current zombie roster enabled; body sprite/label hit regions, nearby search and compact loot drawer.
- [x] Clear home/wardrobe/crate deposits and withdrawals, capacity and worn-item feedback.
- [x] Desktop wheel and mobile pinch zoom indoors.
- [x] Shared isometric world projection, matching walk/touch targets and depth-sorted walls/actors/props.
- [x] Extra independently operable windows; all window labels offer Smash.
- [x] Playable two/three floors, stairs, separate zombies/loot/bodies/furniture/storage and automatic descent/exit.
- [x] Saved upstairs opening geometry, residents/health and cleared rooms; stairs handle a refreshed ground wall.
- [x] Home shows its floor; Walk home selects stairs when the cupboard is upstairs. Floor mismatch explains storage access.
- [x] Compact INTERACT picker for crowded rooms; server-matched attack/Finish previews, facing and reach hints.
- [x] GPS starts on current phone location, preserves independent walking through drift, recenters after consistent travel beyond half a mile.
- [x] Launch trailer (https://youtu.be/MRGjiGp57as) on the title screen: a card under Play, loaded from YouTube only when tapped, removed when the game starts.
- [x] Original Phases1–8 survival foundation retained: experience, skills, inventory, clothing/armor, reusable storage, furniture/fortification, trees/salvage/construction, food/water/sleep/utilities, mining/metalwork.

Alternate survivors animate procedurally with individual equipment/wound anchors.
Existing authored action art remains p1 bat and the matching zombie. Interiors/floor counts
are fictional game layouts based on map outlines, not surveyed real interiors.

## Current verification

- [x] N1 durable owner recovery: exact condition/quantity, atomic death save, fast respawn/retry, DB expiry/conservation; local fatal-wound browser death→new life→Recover gear→damaged knife/reload. Seeded injury, no new public natural-death recovery claim.
- [x] N2 normal public earned-cloth curtain/reload/open/close/remove/material conservation/glass clearing/window climb flow; no JS errors. Ground/upper saved geometry and private atomic material publication covered by server tests.

- [x] 295 server tests; 15 Node regressions and all browser modules parse.
- [x] N4 public two-player invitation/join/teammate/shared work/stock/owner absence/reload/personal preservation/revoke/old code checks pass. Server guards shared revision, atomic stock, membership and once-per-base utility ticks.
- [x] Cold Hub/database upstairs position/openings/resident position+health restore; cleared floors stay cleared.
- [x] Real local own kill → fallen torso tap → body search → compact drawer → searched stock survives reload.
- [x] Real steered combat: own kills, retreat while swinging, Finish preview, overview closes on chasing threat.
- [x] Public complete interior outing:62s, actual door/search/take/drink/home/store/dismantle/barricade,0 full-sheet opens,hp100,59fps.
- [x] Public sustained601s exploration:396 accepted real canvas legs,2681m,hp100,min45.6fps,7 remembered-map checks,no JS errors.
- [x] Local sustained601s exploration:388 legs,2571m,hp100,min47fps,7 overview checks,1 chooser check,no JS errors.
- [x] Public GPS API emulation: new/current launch, independent walking+drift, consistent1050m travel recenter, different GPS on fresh opening.
- [x] Public floors/upstairs storage/GPS ground restart/automatic descent+exit; local floor-aware Walk home check.
- [x] Public character/reload/body hit fixtures and compact nearby chooser.
- [x] Current local60-zombie herd: heard/seen/crowd/wakeup,55fps awake,health response max2.9ms.
- [x] Sealed-home fixture:600 simulated seconds ×6 owner-home/away cases,73–92 zombies,0 inside while sealed.
- [x] Final0.12.3 deployment/public floors and storage regression: floor-aware Walk home, stairs, deposit/reload, auto-exit, cupboard/wardrobe transfers, worn-item rejection, wheel/pinch, no accidental walk or JS errors.

- [x] 0.12.4 public `mobile_trailer_check`: nothing requested from YouTube before the tap, plays in place, scrolls on 360x640, gone when the game starts. Chromium only; no outing or floors rerun on 0.12.4.

The ten-minute run is scripted exploration. The complete interior story is a separate
62-second run. Neither is a human phone review. Public natural stand-and-fight body
harness timed out without an own kill; no new public natural-body pass is claimed.

## Remaining acceptance requiring time or hardware

- [ ] Scheduled public herd on2026-10-12 at14:46 or16:23UTC. Local seeded herd already passed.
- [ ] Public crop harvest after18:10UTC2026-10-12: `mobile_slow_check.mjs harvest /tmp/osz-slow-public`.
- [ ] Physical Pixel9a/iOS Safari: title trailer starting with sound after the tap, touch feel, audio, actual GPS travel/background/reconnect and a real long absence.
- [ ] Human balance review of a full ten-minute loot/home/craft outing, focused station/gather/rest buttons, and original saved-home/public one-hour sealed-home observation. Automated pieces above passed.

No implementation approval is pending. The newly authorized expansion includes occupations,
shared bases and vehicles; their progress is in NEXT_SURVIVAL_PLAN.md.

## Handoff pointers

- Long history: MOBILE_WORLD_PLAN.md and BUILD_CHECKLIST.md; preserve their historical entries.
- Claude memory: `~/.claude/projects/-mnt-c-Users-user-Downloads-PPW/memory/oh_shit_zombies_build.md`.
- gbrain: `mnt-c-users-user-downloads-ppw-oh-shit-zombies-build`, updated using revision-aware `/tmp/gbrain_read.py`.
- Title trailer: video id is `TRAILER` in `app/static/js/trailer.js` plus the link in `index.html`; thumbnail `assets/trailer_thumb.webp`.
- Current own normal local backend8035, version0.15.0, SQLite `/tmp/osz-shared-v015.db`, exec session23604. Own normal8033/session87407 and8032/session30983 retained. Fatal8034 stopped.
- Native Railway stage: `/tmp/osz-railway-20261010`; deploy only service `osz`. ZombieQuest untouched.
- Harnesses: `mobile_floors_check`, `mobile_interact_check`, `mobile_storage_check`, `mobile_details_check`, `mobile_body_check`, `mobile_stick_fight_check`, `mobile_gps_flow_check`, `mobile_extended_check`, `mobile_outing_check`, `mobile_trailer_check`, `mobile_bases_check` (ordinary/public two-player shared work/storage), `mobile_background_check` (ordinary/public reload and optional local fatal respawn), `mobile_recovery_check` (local fatal-wound fixture), `mobile_windows_check` (earned cloth on ordinary server/public; optional local cloth fixture) under tools.
- Own older servers8023–8026/8028 and supplied fixtures8030/8031 were stopped;8032 remains. Older8015–8021 are historical/Claude fixtures and should not be used as current evidence.
- Never print saved session/token files. Current screenshots are diagnostic `/tmp/osz-*.png` artifacts.

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
