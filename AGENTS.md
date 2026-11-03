# Shared OSZ working rules

Claude and Codex are partners on this checkout. Read the latest handoff at the end
of BUILD_CHECKLIST.md and the current plan before starting work. The mobile plan
is MOBILE_WORLD_PLAN.md; the completed survival scope is SURVIVAL_ROADMAP.md.

Latest (2026-10-12): live 0.9.5 `d1ace93` (the thumb stick slides along walls at any angle and
round a door frame: client `buildings.js` `slide`, measured by `tools/doorway_precision.mjs` and
`tools/mobile_doorway_check.mjs`; the server's step is unchanged on purpose). Exploring pace is
6 m/s, not walking pace: use the real paces when measuring movement. 0.9.3/0.9.4 added
`tools/mobile_outing_check.mjs`, the whole M2 outing through cards and drawers, and two polish
fixes; before that 0.9.2 `a5e6914`; M1/C1, core M2/C2, C3, C4, M3 core, C5,
M4 and C6 to C9 are released. 0.9.0 added herds (`app/game/herds.py`), 0.9.1 the
survivor overlays, 0.9.2 the in-place map refresh (`building_loader.refresh_due`; live
check with `tools/seed_placeholders.py` + `tools/mobile_map_refresh_check.mjs`), the
sealed-home soak (`tools/sealed_home_soak.py`) and map pins (`tools/mobile_pin_check.mjs`).
A new action or argument name must be added to `ACTIONS`/`ARGS` in
`app/routes/ws_routes.py` or the socket drops it silently. What is left needs a clock
or a person: on 2026-10-12 a scheduled herd passes the test point at 14:46 and 16:23
UTC, and `tools/mobile_slow_check.mjs harvest /tmp/osz-slow-public` is due after 18:10
UTC. See the last entry of BUILD_CHECKLIST.md.

Merge gate completed (2026-10-11): Claude’s GUIDE_REVIEW_CLAUDE.md and Codex’s
draft are reconciled in MOBILE_WORLD_PLAN.md. Implementation is authorized;
M1 + C1 are first. Preserve the source reviews and current progress checklist.

Tom subsequently explicitly authorized starting the merged plan immediately once
both plans are reviewed and reconciled. Do not add another approval prompt.

**Claude's review is ready (2026-10-11, commit `71a3946`): read
[GUIDE_REVIEW_CLAUDE.md](GUIDE_REVIEW_CLAUDE.md).** It covers the full video and
transcript, where OSZ already matches, ten gaps in order, three points against
MOBILE_WORLD_PLAN.md (section 5), nine proposed items C1 to C9 with sizes and
acceptance checks (section 6), five questions for Tom (section 8) and a merge
checklist (section 9). Claude has not edited MOBILE_WORLD_PLAN.md; the merge and
its gate boxes are Codex's.

Current pickup:0.15.0 `1366666` live (Railway<deploy-id>). N1–N4 released;295 server tests/15 Node regressions. Public two-player bases/shared work/stock/reload/personal preservation/revoke and floors/storage/GPS/exit pass. Next N5 vehicles/hauling, then N6–N8. Current own8035/session23604,/tmp/osz-shared-v015.db;8033/8032 retained. Read CURRENT_STATUS.md and NEXT_SURVIVAL_PLAN.md. Preserve explicit shared identity and atomic stock.

N5 local pickup: uncommitted vehicles.py/model/sim/hub/ws/tests backend,303 full server tests passed, no client controls/art/browser acceptance yet. Existing8035 is old0.15 in memory. Follow latest NEXT_SURVIVAL_PLAN.md entry for conflict reconciliation and remaining work.

Active new goal (Tom,2026-10-12): remaining feature expansion in NEXT_SURVIVAL_PLAN.md. Prioritize corpse recovery, curtains/glass, occupations/traits, shared bases, vehicles, then broadcasts/learning/maintenance/utilities. Preserve the trailer.

## Required progress notes (Tom's instruction, 2026-10-11)

Always update shared notes as work progresses. At each meaningful milestone,
before a commit/release, and before stopping or handing off:

- Update the active plan's checkboxes, status, decisions and next concrete step.
- Record changes and verification evidence in BUILD_CHECKLIST.md. Distinguish
  implemented, tested locally, tested publicly, deployed and still unverified.
- Update Claude's shared build memory and revision-aware gbrain build page using
  the existing local helper. Preserve previous entries. If synchronization fails,
  record that failure and the pending update in the repo handoff.
- Leave current commit/deployment, changed files, running processes and useful
  harness paths. Never include tokens, session-file contents or credentials.

Shared memory:

Existing revision-aware helper: /tmp/gbrain_read.py (may disappear on reboot).

Standing user authorization covers implementation, verification, Gitea commits
and pushes, and deployment to the separate OSZ Railway service. Do not repeatedly
ask for permission for that work. Preserve live player data and Claude's changes.
Keep ZombieQuest separate. Deploy from native Linux staging, not /mnt/c.

Do not mark a plan step complete merely because code exists; record its actual
acceptance evidence and outstanding limitations. Do not delegate to subagents
unless the user explicitly requests delegation or parallel agent work.

N5 client pickup:0.16.0 uncommitted UI/art/controls + normal mobile vehicle flow passes; latest CAS/ram/Area/footprint changes in final tests. Read newest NEXT_SURVIVAL_PLAN entry. N5–N8 remain active.

Current pickup:0.16.0/32ee139 live/public vehicles and floors accepted; N1–N5 complete. N6 radios/events local uncommitted, full tests44507 and normal browser still pending. Read latest NEXT_SURVIVAL_PLAN entry.

Current pickup:0.17.0/9ab5070 live/public radios/floors/vehicles accepted; N1–N6 complete.313 server/15 Node checks. N7 design in NEXT_SURVIVAL_PLAN, no code yet; N7–N8 full goal stays active. Own8037/session19541 and8036/session44620 retained.

N7 local pickup:0.18.0 uncommitted magazines/knowledge/TV/tapes/banked studies/atomic start and pending completion.319 full tests passed before last edits; final checks pending. Live0.17 remains. Read newest NEXT_SURVIVAL_PLAN entry.
