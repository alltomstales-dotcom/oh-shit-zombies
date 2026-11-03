# Difficulty sweep, 2 November 2026 (backlog item 1)

Generated tables come from `player/sweep_table.py` over `player/sweep_runs/*/summary.json` and
`events.jsonl`. Bars and predictions were written in DEVLOG.md before each round ran.

## Setup

- Throwaway servers from the same code (image `osz-sweep`, later `osz-sweep2` with the early-minute
  dials), each with 1 CPU and 448 MB like the real one, on loopback ports 8131+, 4 to 6 at once.
  Each life gets a fresh SQLite copy of a template holding only the cached Chicago and Minneapolis
  map regions; both OpenStreetMap hosts resolve to 127.0.0.1 inside the containers, so no map
  request left this machine.
- Chicago, 300 s limit, a new account each life (so every life is a new survivor), the 250 ms-late
  bot from the arm test. Arm **b** is scripts alone, arm **a** random legal actions.
- All 89 scored lives ran between 19:17 and 20:31 CST, which is **night in Chicago** (sight 22 m).
  Daytime was not swept. Three smoke lives (`smoke_*`) are excluded.
- "Met" means a zombie had hold of the survivor, or got within 3.4 m and wasn't idle. Per-minute
  rates for minutes 4 and 5 are per minute actually lived (the dead don't count as zero).

## The chosen setting: `public` (sweep name P4)

Classic plus: density 4 (was 1.3), zombie speed x1.8, notice x2, no first-day grace (it was
notice x0.6 and bites x0.5 for a new survivor's first 24 h), the escalating director with groups up
to 6 bigger, hunts of 5 to 8 zombies once pressure passes half, lulls shrinking to 8 to 15 s, and a
gentle first minute: for 60 s after arriving, zombies notice you at a tenth of the rate and
whatever chases you walks at half pace.

| | lives | deaths | seconds at death | deaths before 60 s | dmg per zombie met |
|---|---:|---:|---|---:|---:|
| classic, scripts (b) | 8 | 0 | - | 0 | 0.0 |
| public, scripts (b) | 10 | 5 (50%) | 147, 181, 210, 213, 277 | 0 | 5.4 |
| public, random (a) | 10 | 8 (80%) | 42, 64, 64, 86, 93, 118, 135, 135 | 1 | 8.7 |

Bars (DEVLOG 19:17): scripts die 3 to 5 of 10: **pass (5, the top of the band)**. Random play doesn't
die in the first minute every time, own target at most 3 of 10: **pass (1 of 10)**. No scripted
death before 60 s and at most 5 damage in the first minute: **pass (0 and 0.0)**. Pressure escalates
(met and damage per minute higher in minutes 4 and 5 than 1 and 2): **pass, narrowly on met**
(1.05 to 1.18 a minute) and clearly on damage (0.0 to 12.6 a minute). Only dials changed: **pass**.

Use it with `DIFFICULTY=public` (the default in `~/osz-stack/docker-compose.yml`). `DIFFICULTY=classic`
is the old game, number for number, and the default in the app's own settings, so the Railway
build doesn't change unless someone chooses to. `DIFFICULTY_TUNE` takes JSON dial overrides.

## Every setting tried

Settings starting A were the first screen (stopped after its second round: zero damage in all
eight), B the wider screen, P the combinations, C_P4 the confirmation. A0_classic includes the six
extra classic lives run beside the confirmation.

| setting | arm | lives | deaths | seconds at death | deaths < 60 s | zombie-hit dmg per zombie met | zombies met per life | all health lost per life | hit dmg in first 60 s | met per minute, min 1-2 → 4-5 | hit dmg per minute, min 1-2 → 4-5 | containers |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|---:|
| A0_classic | b | 8 | 0 (0%) | - | 0 | 0.0 | 2.1 | 0 | 0.0 | 0.00 → 0.94 | 0.0 → 0.0 | 17.6 |
| A1_escalate | b | 2 | 0 (0%) | - | 0 | 0.0 | 2.5 | 0 | 0.0 | 0.25 → 1.00 | 0.0 → 0.0 | 18.5 |
| A2_dens2 | b | 2 | 0 (0%) | - | 0 | 0.0 | 0.5 | 0 | 0.0 | 0.00 → 0.25 | 0.0 → 0.0 | 20.0 |
| A3_dens3 | b | 1 | 0 (0%) | - | 0 | 0.0 | 2.0 | 0 | 0.0 | 0.50 → 0.00 | 0.0 → 0.0 | 18.0 |
| A4_speed13 | b | 1 | 0 (0%) | - | 0 | 0.0 | 2.0 | 0 | 0.0 | 0.00 → 0.50 | 0.0 → 0.0 | 19.0 |
| A5_nograce_notice16 | b | 2 | 0 (0%) | - | 0 | 0.0 | 2.5 | 0 | 0.0 | 0.25 → 1.00 | 0.0 → 0.0 | 18.5 |
| A6_noise15 | b | 1 | 0 (0%) | - | 0 | 0.0 | 2.0 | 0 | 0.0 | 0.00 → 1.00 | 0.0 → 0.0 | 19.0 |
| A7_night2 | b | 1 | 0 (0%) | - | 0 | 0.0 | 8.0 | 0 | 0.0 | 2.00 → 2.00 | 0.0 → 0.0 | 13.0 |
| B1_dens4 | a | 1 | 1 (100%) | 53 | 1 | 10.4 | 7.0 | 100 | 72.6 | 7.97 → 0.00 | 82.7 → 0.0 | 0.0 |
| B1_dens4 | b | 2 | 0 (0%) | - | 0 | 0.0 | 3.5 | 0 | 0.0 | 0.25 → 0.75 | 0.0 → 0.0 | 17.5 |
| B2_dens6 | a | 1 | 1 (100%) | 51 | 1 | 10.0 | 7.0 | 100 | 70.1 | 8.27 → 0.00 | 82.8 → 0.0 | 0.0 |
| B2_dens6 | b | 2 | 0 (0%) | - | 0 | 0.0 | 2.0 | 0 | 0.0 | 0.25 → 0.25 | 0.0 → 0.0 | 17.0 |
| B3_speed2 | a | 1 | 1 (100%) | 243 | 0 | 4.3 | 10.0 | 100 | 0.0 | 2.50 → 4.78 | 11.4 → 19.0 | 1.0 |
| B3_speed2 | b | 2 | 0 (0%) | - | 0 | 0.0 | 2.5 | 0 | 0.0 | 0.00 → 1.00 | 0.0 → 0.0 | 18.5 |
| B4_speed25 | a | 1 | 1 (100%) | 23 | 1 | 13.6 | 6.0 | 100 | 81.6 | 15.38 → 0.00 | 209.2 → 0.0 | 0.0 |
| B4_speed25 | b | 2 | 0 (0%) | - | 0 | 0.0 | 4.0 | 0 | 0.0 | 0.50 → 1.25 | 0.0 → 0.0 | 16.0 |
| B5_dens3_speed16_nograce | a | 1 | 1 (100%) | 49 | 1 | 11.9 | 4.0 | 100 | 47.6 | 4.93 → 0.00 | 58.6 → 0.0 | 0.0 |
| B5_dens3_speed16_nograce | b | 2 | 0 (0%) | - | 0 | 0.0 | 3.0 | 0 | 0.0 | 0.00 → 1.50 | 0.0 → 0.0 | 20.0 |
| B6_dens4_speed16_nograce_notice2 | a | 1 | 1 (100%) | 71 | 0 | 11.2 | 6.0 | 100 | 34.0 | 5.05 → 0.00 | 56.4 → 0.0 | 0.0 |
| B6_dens4_speed16_nograce_notice2 | b | 2 | 1 (50%) | 176 | 0 | 8.6 | 5.0 | 50 | 0.0 | 0.50 → 1.50 | 0.0 → 0.0 | 13.5 |
| B7_dens5_speed18_nograce_notice2 | a | 1 | 1 (100%) | 34 | 1 | 9.9 | 6.0 | 100 | 59.4 | 10.75 → 0.00 | 106.4 → 0.0 | 0.0 |
| B7_dens5_speed18_nograce_notice2 | b | 2 | 0 (0%) | - | 0 | 0.0 | 4.0 | 0 | 0.0 | 0.50 → 1.25 | 0.0 → 0.0 | 17.0 |
| B8_hard_director_dens3_speed15_nograce | a | 1 | 1 (100%) | 31 | 1 | 13.3 | 6.0 | 100 | 80.1 | 11.50 → 0.00 | 153.5 → 0.0 | 0.0 |
| B8_hard_director_dens3_speed15_nograce | b | 2 | 1 (50%) | 179 | 0 | 8.1 | 5.0 | 50 | 0.0 | 0.75 → 0.50 | 0.0 → 0.0 | 12.0 |
| C_P4 | a | 10 | 8 (80%) | 42, 64, 64, 86, 93, 118, 135, 135 | 1 | 8.7 | 6.4 | 86 | 19.8 | 3.61 → 1.25 | 30.4 → 6.2 | 0.5 |
| C_P4 | b | 10 | 5 (50%) | 147, 181, 210, 213, 277 | 0 | 5.4 | 6.2 | 51 | 0.0 | 1.05 → 1.18 | 0.0 → 12.6 | 12.8 |
| P1_dens4_speed16_notice2_nograce_early | a | 3 | 3 (100%) | 77, 96, 145 | 0 | 14.5 | 4.7 | 100 | 8.8 | 2.86 → 0.00 | 37.9 → 0.0 | 0.3 |
| P1_dens4_speed16_notice2_nograce_early | b | 6 | 1 (17%) | 252 | 0 | 2.3 | 6.7 | 18 | 0.0 | 0.75 → 1.43 | 0.0 → 8.2 | 15.0 |
| P2_hard_dens3_speed15_nograce_early | a | 3 | 2 (67%) | 73, 77 | 0 | 6.5 | 7.7 | 72 | 19.7 | 4.44 → 0.50 | 30.4 → 2.8 | 0.3 |
| P2_hard_dens3_speed15_nograce_early | b | 6 | 0 (0%) | - | 0 | 1.3 | 5.8 | 14 | 0.0 | 0.67 → 1.08 | 0.0 → 3.7 | 15.3 |
| P3_hard_dens4_speed18_notice2_nograce_early | a | 3 | 3 (100%) | 42, 49, 79 | 2 | 10.3 | 7.0 | 100 | 52.8 | 7.41 → 0.00 | 76.6 → 0.0 | 0.0 |
| P3_hard_dens4_speed18_notice2_nograce_early | b | 6 | 2 (33%) | 161, 197 | 0 | 4.2 | 6.5 | 36 | 0.0 | 0.92 → 2.17 | 0.0 → 9.5 | 12.8 |

Dials per setting (on top of classic):

| setting | dials |
|---|---|
| A0_classic | none |
| A1_escalate | escalating director |
| A2_dens2 / A3_dens3 | escalate, density 2 / 3 |
| A4_speed13 | escalate, zombie speed x1.3 |
| A5_nograce_notice16 | escalate, no first-day grace, notice x1.6 |
| A6_noise15 | escalate, footsteps heard x1.5 as far |
| A7_night2 | escalate, twice the night packs |
| B1_dens4 / B2_dens6 | escalate, density 4 / 6 |
| B3_speed2 / B4_speed25 | escalate, speed x2 / x2.5 |
| B5 | escalate, density 3, speed x1.6, notice x1.6, no grace |
| B6 | escalate, density 4, speed x1.6, notice x2, no grace |
| B7 | escalate, density 5, speed x1.8, notice x2, no grace |
| B8 | hard director (groups +6, hunts 5 to 8, lulls to 8 to 15 s), density 3, speed x1.5, no grace |
| P1 | B6 plus first minute: notice x0.25, chasers at 60% pace |
| P2 | B8 plus that first minute |
| P3 | hard director, density 4, speed x1.8, notice x2, no grace, plus that first minute |
| C_P4 (public) | P3 with a gentler first minute: notice x0.1, chasers at 50% pace |

## What it says, in short

- One zombie never beats a ready survivor (swing reach 3.4 m, grab range 2.6 m, and a landed hit
  interrupts its attack). Scripted lives are all or nothing: untouched, or caught by a pack.
- Density alone, even x4.6 the old, doesn't kill the script; neither does speed alone, even x2.5.
  It takes numbers and speed together, so that five arrive at once and running stops working.
- Random play is what limits how hard this can go: at every hard setting without the first-minute
  dials it died in 23 to 71 s.
- With the chosen setting, deaths come between 2:27 and 4:37, after the director has had time to
  climb.

## Not checked

- Daytime (all 89 lives were at night), Minneapolis and Manchester, lives longer than 5 minutes.
- Real players. The scripted bot fights well and loots fast; a person may die more or less.
- 10 lives per arm: 5 of 10 has a wide interval (roughly 2 to 8 of 10 at 90%). The band is about
  the right place, not a precise rate.
- Whether the harder world costs server CPU at 25 players: measured separately in item 2.

## Re-check on the final build (2026-11-03 01:47 to 02:00 CST)

After the soak fixes (`22d31c5`, `7d53a17`: actions judged against the last tick, a ceiling on the
director's zombies, idle unseen ones forgotten), the same setting on the final build, same harness,
night, Chicago:

| | lives | deaths | seconds at death | deaths before 60 s | dmg per zombie met | met per minute, min 1-2 → 4-5 |
|---|---:|---:|---|---:|---:|---|
| public, scripts (b), final build | 10 | 5 (50%) | 168, 188, 206, 213, 290 | 0 | 5.6 | 0.55 → 1.78 |
| public, random (a), final build | 10 | 9 (90%) | 48, 64, 65, 96, 106, 115, 139, 148, 222 | 1 | 9.0 | 3.20 → 2.96 |

All the bars pass again. The danger didn't move.
