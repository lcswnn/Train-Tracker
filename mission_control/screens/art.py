"""Classic art screen: full-bleed dithered public-domain paintings.

assets/art/ready/ holds 1-bit 800x480 PNGs baked by tools/make_art.py.
This screen loads the next painting in rotation and shows it
full-bleed -- no providers, no network, renders instantly.

Add paintings: run tools/fetch_art.py + tools/make_art.py on your
Mac, copy assets/art/ready/ to the Pi, restart the service.
"""
import glob
import os

from PIL import Image, ImageOps

import config
from screens.base import H, W, Screen, blank, centered, font, register

_ART_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "assets", "art", "ready")
_INDEX = os.path.join(config.CACHE_DIR, "art_index")


def _files():
    return sorted(glob.glob(os.path.join(_ART_DIR, "*.png")))


def _next_index(n):
    """Rotation index persisted across reboots; advances every render."""
    try:
        with open(_INDEX) as f:
            idx = int(f.read().strip() or 0)
    except (OSError, ValueError):
        idx = 0
    try:
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        with open(_INDEX, "w") as f:
            f.write(str((idx + 1) % n))
    except OSError:
        pass
    return idx % n


@register
class ArtScreen(Screen):
    name = "art"
    providers = ()

    def render(self, data):
        img, draw = blank()
        files = _files()
        if not files:
            centered(draw, W // 2, H // 2 - 20, "ART", font(28, bold=True))
            centered(draw, W // 2, H // 2 + 20,
                     "run tools/make_art.py", font(22))
            return img
        art = Image.open(files[_next_index(len(files))]).convert("1")
        if art.size != (W, H):
            art = ImageOps.fit(art, (W, H), Image.LANCZOS).convert("1")
        img.paste(art, (0, 0))
        return img
