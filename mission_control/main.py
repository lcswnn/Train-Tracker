"""Mission Control entry point.

On the Pi:  python3 main.py          (runs the dayparted rotation forever)
On the Mac: python3 main.py --preview  (renders each screen to PNGs in
            ./previews/ -- no Pi hardware imports needed)

Dayparts (config.DAYPARTS): the frame changes personality by time of
day -- MORNING OPS, SLOW DAY, TOMORROW BRIEF, SLEEP. Each screen gathers
its providers (cached, with stale fallback), renders, displays, and
dwells. A failed screen is skipped, never fatal.

Phone control: main.py also serves a tiny web UI (control.py) at
http://frame.local:5000 -- jump to a screen, refresh now, pause/resume.
"""
import argparse
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import config
import control
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


def daypart_for(hour):
    """Pick the active daypart for an hour (24h). Handles overnight
    windows where end < start, e.g. SLEEP 22 -> 6."""
    for p in config.DAYPARTS:
        s, e = p["start"], p["end"]
        if s <= e:
            if s <= hour < e:
                return p
        elif hour >= s or hour < e:
            return p
    return config.DAYPARTS[0]


def current_daypart_name():
    return daypart_for(datetime.now(TZ).hour)["name"]


def _wait(seconds, ctl):
    """Sleep in small increments, waking early on pause/override so the
    phone UI stays responsive even during a long dwell."""
    end = time.time() + seconds
    while time.time() < end:
        if ctl.paused or ctl.has_pending():
            return
        time.sleep(5)


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


def _waveshare_lib():
    """Locate the Waveshare e-Paper python lib and put it on sys.path.

    The test scripts work from inside the cloned repo; this makes main.py
    work from anywhere (including the systemd service at boot)."""
    candidates = [
        os.path.expanduser("~/e-Paper/RaspberryPi_JetsonNano/python/lib"),
        os.path.expanduser("~/waveshare_epd"),
    ]
    for p in candidates:
        if os.path.isdir(p):
            if p not in sys.path:
                sys.path.insert(0, p)
            return
    raise ModuleNotFoundError(
        "waveshare_epd not found. Searched: " + ", ".join(candidates) +
        ". Locate yours with: find ~ -name epd7in5_V2.py 2>/dev/null")


def run():
    _waveshare_lib()
    from waveshare_epd import epd7in5_V2
    epd = epd7in5_V2.EPD()
    ctl = control.Controller()
    control.start(ctl, current_daypart_name)
    epd.init()
    print("Display initialized.")

    def show(name, context):
        """Render one screen and push it to the panel."""
        screen = SCREENS[name]
        img = screen.render(gather(screen.providers))
        epd.display(epd.getbuffer(img))
        ctl.set_current(name)
        print(f"[{datetime.now(TZ):%H:%M}] {name} ({context})")

    try:
        while True:
            part = daypart_for(datetime.now(TZ).hour)
            if ctl.paused or not part["screens"]:
                # Frozen -- but a phone-UI override is still honored
                # immediately instead of being swallowed.
                target = ctl.take_forced()
                if target in SCREENS:
                    try:
                        show(target, "phone override")
                    except Exception as e:
                        print(f"[{target}] render failed, skipping: {e}")
                elif target:
                    print(f"[{target}] unknown screen, skipping")
                else:
                    time.sleep(5)
                continue
            for name in part["screens"]:
                if ctl.paused:
                    break
                target = ctl.take_forced() or name
                if target not in SCREENS:
                    print(f"[{target}] unknown screen, skipping")
                    continue
                try:
                    show(target, f"{part['name']}, dwell {part['dwell']}s")
                except Exception as e:
                    print(f"[{target}] render failed, skipping: {e}")
                    continue
                _wait(part["dwell"], ctl)
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
