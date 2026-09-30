"""Mission Control entry point.

On the Pi:  python3 main.py          (runs the rotation forever)
On the Mac: python3 main.py --preview  (renders each screen to PNGs in
            ./previews/ -- no Pi hardware imports needed)

Rotation: each screen gathers its providers (cached, with stale
fallback), renders, displays, and dwells. A failed screen is skipped,
never fatal. During MORNING_HOURS the departure screen runs twice
per cycle.
"""
import argparse
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from providers import weather as _pw, space as _ps, cta as _pc
from screens import departure as _sd, conditions as _sc, space as _ss  # noqa
from screens.base import SCREENS

PROVIDERS = {
    "weather": _pw.WeatherProvider(),
    "space": _ps.SpaceProvider(),
    "cta": _pc.CTAProvider(),
}

TZ = ZoneInfo(config.TIMEZONE)


def gather(names):
    out = {}
    for n in names:
        try:
            out[n] = PROVIDERS[n].get()
        except Exception as e:
            print(f"[{n}] provider error: {e}")
            out[n] = None
    return out


def build_cycle():
    """List of (screen_name, dwell). Departure doubles up in the morning."""
    hour = datetime.now(TZ).hour
    order = [name for name, _ in config.ROTATION]
    dwell_of = {name: dwell for name, dwell in config.ROTATION}
    if config.MORNING_HOURS[0] <= hour < config.MORNING_HOURS[1]:
        order.insert(1, "departure")
    return [(n, dwell_of[n]) for n in order]


def preview(screen_name=None):
    os.makedirs("previews", exist_ok=True)
    names = [screen_name] if screen_name else list(SCREENS)
    for name in names:
        screen = SCREENS[name]
        try:
            img = screen.render(gather(screen.providers))
        except Exception as e:
            print(f"[{name}] render failed: {e}")
            continue
        path = f"previews/{name}.png"
        img.save(path)
        print(f"{name} -> {path}")


def run():
    from waveshare_epd import epd7in5_V2
    epd = epd7in5_V2.EPD()
    epd.init()
    print("Display initialized. Rotation:", [n for n, _ in build_cycle()])
    try:
        while True:
            for name, dwell in build_cycle():
                screen = SCREENS[name]
                try:
                    img = screen.render(gather(screen.providers))
                except Exception as e:
                    print(f"[{name}] render failed, skipping: {e}")
                    continue
                epd.display(epd.getbuffer(img))
                print(f"[{datetime.now(TZ):%H:%M}] {name} "
                      f"(dwell {dwell}s)")
                time.sleep(dwell)
    finally:
        epd.sleep()
        print("Display put to sleep.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true",
                    help="render screens to PNGs instead of the e-ink")
    ap.add_argument("--screen", default=None,
                    help="preview a single screen by name")
    args = ap.parse_args()
    if args.preview:
        preview(args.screen)
    else:
        run()
