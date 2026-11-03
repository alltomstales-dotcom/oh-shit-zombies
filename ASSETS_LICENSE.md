# Licences for things that aren't code

**Code** (everything that isn't listed below) is under the BSD Zero Clause licence in `LICENSE`: use it for anything, commercial or not, with no conditions and no attribution required.

**Our own writing** (the devlog in `docs/devlog/`, design notes, this file) is dedicated to the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

**Things with their own terms. Read these before reusing them:**

- **Sprites, badges and scenes in `app/static/assets/` and `art/`** (characters, zombies, items, scenes) were generated with Qwen-Image 2.1. That model is released under the Qwen Research Licence, which forbids commercial use of the model without a separate licence. Whether that reaches the images it produced is disputed. We can't promise these images are free for commercial use, so if you fork this for anything commercial, replace them. We plan to redraw them with a tool whose terms allow any use, and the devlog will say when that's done.
- **The extra action poses in `art/action_atlas_01.png`** were made with OpenAI image generation.
- **Sounds in `app/static/assets/audio/`** are CC0, from Kenney and ArcadeParty. See `CREDITS.txt` there.
- **Map data** comes from OpenStreetMap contributors under the [ODbL](https://www.openstreetmap.org/copyright). The game fetches it live; please respect their usage policy and cache what you load.
