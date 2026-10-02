"""Dither downloaded paintings into 1-bit e-ink-ready PNGs.

Usage -- on your Mac, after tools/fetch_art.py:
    python3 tools/make_art.py

Reads assets/art/src/*.jpg + captions.json; writes full-frame
800x480 1-bit Floyd-Steinberg PNGs + manifest.json into
assets/art/ready/. Copy the whole ready/ folder to the Pi alongside
the code (no need to copy src/ -- the Pi never needs the originals).
"""
import json
import os

from PIL import Image, ImageOps

W, H = 800, 480

_HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.normpath(os.path.join(_HERE, "..", "assets", "art", "src"))
READY_DIR = os.path.normpath(
    os.path.join(_HERE, "..", "assets", "art", "ready"))


def dither(src_path, dest_path):
    img = Image.open(src_path)
    img = ImageOps.exif_transpose(img).convert("L")
    img = ImageOps.fit(img, (W, H), Image.LANCZOS)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = img.convert("1", dither=Image.FLOYDSTEINBERG)
    img.save(dest_path)


def main():
    os.makedirs(READY_DIR, exist_ok=True)
    with open(os.path.join(SRC_DIR, "captions.json")) as f:
        captions = json.load(f)
    manifest = {}
    for stem, caption in captions.items():
        src = os.path.join(SRC_DIR, stem + ".jpg")
        if not os.path.exists(src):
            print(f"skip {stem} (no download; run tools/fetch_art.py)")
            continue
        dest = os.path.join(READY_DIR, stem + ".png")
        dither(src, dest)
        manifest[stem + ".png"] = caption
        print(f"baked {stem}.png")
    with open(os.path.join(READY_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    print(f"done -> {READY_DIR}")


if __name__ == "__main__":
    main()
