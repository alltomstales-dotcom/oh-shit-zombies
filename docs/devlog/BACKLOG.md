# Oh shit, Zombies. — backlog and story plan

Owner of this list: the research session (Claude), at Tom's direction on 2026-11-02: "Drive as you think it should be and make the changes and make the story around how the game is developing. Not necessarily how the AI is playing it." Tom decides on going public, the name, the channel, money and merges into his own repo.

## Where it is today (the story's starting point)

- **Built:** 166 commits from 12 June to 1 November 2026. Tom directed it; Codex and Claude wrote it. It started as ZombieQuest, a GPS game, and turned into a Project Zomboid-style survival game on real OpenStreetMap streets.
- **What it has:** walking, buildings with floors, windows and curtains, looting and storage, a home base, crafting, food, water and sleep, mining and metalwork, occupations and traits, shared bases, vehicles, radio broadcasts and world events, books and recipes, herds of about 60 zombies, death and corpse recovery. Version 0.18.0, live on Railway for friends.
- **What's missing:** other players can't see each other. Nothing escalates: the pacing system eases off when you're hurt. There are no bosses, rare drops or challenge areas, and skills are small bonuses capped at level 5.
- **What testing found:** the AI tester survives too easily. Reflex scripts alone died once in 10 five-minute lives; the fast model (Jev) and the planners couldn't show a benefit because nothing was hard enough. This machine holds about 25 players.
- **Hardening done for strangers** (`~/osz-stack/src`, branch `public-hardening`): no real GPS (pick a city), generated names, a stalled phone can't freeze everyone, no teleporting, a delete freeze fixed, frames cut to about a fifth.

## The backlog, in order

Each item ends with the bot test that says whether it worked, and a devlog entry. That's an episode.

1. **Make it dangerous.** Difficulty sweep with bots (zombie density, speed, night, noise) until scripts alone die about 30 to 50% of the time in a run. Then make the pacing system escalate rather than ease off. Done when the sweep table exists and one setting is chosen. Survival stays the base game.
   - **Status 2026-11-02 20:40: done.** Commit `ea5af60`. 89 scored lives (SWEEP.md). Chosen setting `public`: density 4, zombies x1.8 speed, notice x2, no first-day grace, escalating director (hunts of 5 to 8 past half pressure), gentle first minute. Scripts died 5 of 10 (classic 0 of 8), random play died before 60 s 1 of 10. `DIFFICULTY=classic` keeps the old game. Night and Chicago only; daytime not swept.
2. **See each other.** Show other players nearby (position, name, what they're doing), so viewers who join can meet the AI and each other. Done when two bots see each other in a test and the load is measured again.
   - **Status 2026-11-02 21:15: done.** Commit `c801594`. Others in sight arrive in each frame (opaque per-life id, position, generated name, one-word state, facing), only on servers without real GPS. Three bots saw each other on the second scored attempt (the first failed on bugs in the test's walking). Load with and without presence differs by less than run-to-run noise; on the dangerous setting 30 players is over the edge (p95 1241 ms), 25 is fine (101/298 ms).
3. **Open the doors, without opening them yet.** Player cap 25 with a clear "server full" message, pre-fetched start cities, a several-hour soak test. Done when the soak runs clean. Going public itself needs Tom's tunnel token and his OK.
   - **Status 2026-11-03 02:05: built, soak not clean.** Commits `394e375` (cap 25 + "Server full." page with auto-retry; start cities pinned at boot), `6477e97` (privacy page), `22d31c5` and `7d53a17` (soak fixes: no world step per action, body rebuilt less, a ceiling and clean-up for director zombies). Cap and arrival tested: pass. Fresh boot loaded all 12 start regions in 3 min 4 s (bar said 2). Soak 3 h 15 min on `public`, ~18 bots, 1916 deaths: no restart, no errors, memory flat (143-171 MB), DB +0.9 MB; **ping p95 under 500 ms in only 68% of minutes, worsening by the hour** (cause of the slow growth not found). Recommendation: `MAX_PLAYERS=15` for a public night on `public` difficulty, or `classic`, until it is found. Danger re-checked on the final build: still 5 of 10.
4. **Siege mode v0, the main show** (agreed with the studio). A real landmark, a 30-minute timer, waves that spike and fall back, a boss every 5 minutes, an upgrade choice every 20 to 40 seconds, chests, an ending at 30:00, loot going home to the base. Wave table as data, tuned by bots. Done when bots' death times spread across the 30 minutes.
   - **Status 2026-11-03 04:19: v0 done.** Commit `d37e7e7`; design and as-built notes in `SIEGE.md`. Daley Plaza (the Picasso), Chicago; wave table as data (floors 2 to 42 alive, peak 42 not 300); five telegraphed bosses; a choice of three every ~20 to 40 s early; chests; helicopter at 30:00; haul into the home cupboard. Bar on the real socket, 20 bots on the final table: 1 of 20 dead before 10:00, 3 of 20 extracted, deaths in five of six blocks (pass). Offline, 120 runs: 18% / 13%. One whole siege recorded in a browser (`footage/siege/`). Load: ~2.5 ms of server time per heavy siege per tick; ~30 sieges at once comfortable on their own, 40 the edge; 20 sieges + 15 survival players fit at 67 to 82% CPU. Haul reaching a real cupboard checked end to end. Not done: no human has played it; shared bases get no haul; a siege started on a phone browser was not tried (only a phone-sized headless browser).
5. **AI player v2, for recordings.** Code lists 3 to 5 reachable goals with distance and risk, and the planner picks one and says why. A bandage rule in code. Rerun the arm comparison on the harder setting.
6. **Depth.** A perk choice at skill milestones, rare drops with a few modifiers, landmark challenge areas.
7. **Later, Tom's calls:** the name (it has a swear word, which limits ads), merging `public-hardening` into the real repo, whether Railway or this machine is the public home.

## Rules

- **Where to work:** in `~/osz-stack/src` on `public-hardening`. Never touch `the original private repo`, which has someone's uncommitted N8 work, or the live Railway game.
- **Bars first:** every change gets a bot test with a bar written down before it runs.
- **Server load:** measure it again after anything that adds traffic or zombies.
- **Devlog:** write it for viewers. Mistakes stay in.
