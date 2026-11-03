"""Turn the raw 1024 px renders into small WebP sprites for the client.

    python -m tools.make_assets <folder of raw PNGs>

Characters are trimmed to their outline and scaled to a common height so they stand the same
size in the street; items and badges are trimmed and fitted in a square.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "app" / "static" / "assets"
CHAR_H, ITEM_MAX, MOOD = 300, 200, 144


def trim(im: Image.Image, pad: int = 6) -> Image.Image:
    alpha = im.getchannel("A").point(lambda v: 255 if v > 12 else 0)
    box = alpha.getbbox()
    if box is None:
        return im
    l, t, r, b = box
    return im.crop((max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad)))


def main(src: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for f in sorted(Path(src).glob("*.png")):
        name = f.stem
        im = Image.open(f)
        if name.startswith("scene_"):
            if name == "scene_icon":
                rgb = im.convert("RGB")
                for size in (192, 512):
                    rgb.resize((size, size), Image.LANCZOS).save(OUT / f"icon-{size}.png", optimize=True)
            else:
                im.convert("RGB").save(OUT / f"{name}.webp", quality=84, method=6)
            print(f"{name}: scene")
            continue
        im = im.convert("RGBA")
        clear = im.getchannel("A").point(lambda v: 255 if v < 10 else 0).histogram()[255] / (im.width * im.height)
        if clear < 0.12:
            print(f"{name}: SKIPPED, no transparent background ({clear:.0%} clear)")
            continue
        im = trim(im)
        if name.startswith(("zed_", "surv_")):
            # crawlers lie flat: size them by width so they are as long as the others are tall
            if name.startswith("zed_c"):
                scale = CHAR_H * 1.05 / im.width
            else:
                scale = CHAR_H / im.height
        elif name.startswith("mood_"):
            scale = MOOD / max(im.size)
        else:
            scale = ITEM_MAX / max(im.size)
        im = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        im.save(OUT / f"{name}.webp", quality=88, method=6)
        print(f"{name}: {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main(sys.argv[1])
