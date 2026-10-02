"""Download public-domain classic paintings from Wikimedia Commons.

Usage -- run ONCE on your Mac, from the mission_control folder:
    python3 tools/fetch_art.py

Saves ~1600px JPEGs into assets/art/src/ plus captions.json.
The Pi never downloads art; everything is baked in. Run
tools/make_art.py next to dither the downloads for the e-ink panel.

Every work here is public domain (artist long dead / published
before 1931). If you add paintings, keep it that way.
"""
import json
import os
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
_UA = {"User-Agent": "MissionControlArt/1.0 (personal e-ink project)"}

# (filename stem, Wikimedia Commons "File:" title, caption for the frame)
PAINTINGS = [
    ("starry-night",
     "Van Gogh - Starry Night - Google Art Project.jpg",
     "STARRY NIGHT \u00b7 VAN GOGH, 1889"),
    ("great-wave",
     "The Great Wave off Kanagawa.jpg",
     "THE GREAT WAVE \u00b7 HOKUSAI, 1831"),
    ("pearl-earring",
     "1665 Girl with a Pearl Earring.jpg",
     "GIRL WITH A PEARL EARRING \u00b7 VERMEER, c. 1665"),
    ("the-scream",
     "The Scream.jpg",
     "THE SCREAM \u00b7 MUNCH, 1893"),
    ("wanderer",
     "Caspar David Friedrich - Wanderer above the sea of fog.jpg",
     "WANDERER ABOVE THE SEA OF FOG \u00b7 FRIEDRICH, c. 1818"),
    ("grande-jatte",
     "Georges Seurat - A Sunday on La Grande Jatte -- 1884 - Google Art Project.jpg",
     "A SUNDAY ON LA GRANDE JATTE \u00b7 SEURAT, 1884"),
    ("the-kiss",
     "The Kiss - Gustav Klimt - Google Cultural Institute.jpg",
     "THE KISS \u00b7 KLIMT, 1907\u201308"),
    ("impression-sunrise",
     "Claude Monet, Impression, soleil levant.jpg",
     "IMPRESSION, SUNRISE \u00b7 MONET, 1872"),
    ("almond-blossom",
     "Vincent van Gogh - Almond blossom - Google Art Project.jpg",
     "ALMOND BLOSSOM \u00b7 VAN GOGH, 1890"),
    ("cafe-terrace",
     "Vincent Willem van Gogh - Cafe Terrace at Night (Yorck).jpg",
     "CAFE TERRACE AT NIGHT \u00b7 VAN GOGH, 1888"),
]

_HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.normpath(os.path.join(_HERE, "..", "assets", "art", "src"))


def _api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def resolve():
    """Map each stem -> download URL via one batched Commons API call."""
    titles = ["File:" + t for _, t, _ in PAINTINGS]
    data = _api({"action": "query",
                 "titles": "|".join(titles),
                 "prop": "imageinfo",
                 "iiprop": "url",
                 "iiurlwidth": 1600,   # thumbnail: plenty for 800x480
                 "format": "json",
                 "formatversion": 2})
    by_title = {p["title"].removeprefix("File:"): p
                for p in data["query"]["pages"]}
    out = {}
    for stem, title, caption in PAINTINGS:
        page = by_title.get(title)
        if not page or page.get("missing"):
            raise RuntimeError(f"not found on Commons: File:{title}")
        info = page["imageinfo"][0]
        out[stem] = (info.get("thumburl") or info["url"], caption)
    return out


def download(url, dest):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=120) as r, \
            open(dest, "wb") as f:
        f.write(r.read())


def main():
    os.makedirs(SRC_DIR, exist_ok=True)
    urls = resolve()
    captions = {}
    for stem, _title, caption in PAINTINGS:
        url, _ = urls[stem]
        dest = os.path.join(SRC_DIR, stem + ".jpg")
        if os.path.exists(dest):
            print(f"skip {stem} (already downloaded)")
        else:
            print(f"get  {stem} ...")
            download(url, dest)
        captions[stem] = caption
    with open(os.path.join(SRC_DIR, "captions.json"), "w") as f:
        json.dump(captions, f, indent=1, ensure_ascii=False)
    print(f"done -> {SRC_DIR}  (next: python3 tools/make_art.py)")


if __name__ == "__main__":
    main()
