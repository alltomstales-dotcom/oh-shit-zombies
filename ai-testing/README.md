# AI testing harness

These are the tools the AI testers use. They run against a local copy of the game, never against a public server full of people.

- `player/`: the AI player. It sees the game 250 ms late and uses only the public client protocol, like a real player. It has reflex scripts, a fast decision seat (Jev from TypeSafe, or any model you plug in), and an optional planner. `schedule.py` runs scored lives in shuffled blocks, and `tabulate.py` builds the comparison table. The Jev key comes from `TYPESAFE_API_KEY` in a `.env` file (set `OSZ_ENV_FILE`).
- `loadtest/`: headless bots for load, soak and siege tests.
- `tools/`: profiling and the offline siege simulator.

The results are in `docs/devlog/REPORT.md`, `SWEEP.md` and `SIEGE.md`. The paths in these scripts assume the game's source sits at `../src` (set `OSZ_SRC`). Adjust them for your layout.
