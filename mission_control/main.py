"""Mission Control entry point.

On the Pi:  python3 main.py          (runs the dayparted rotation forever)
On the Mac: python3 main.py --preview  (renders each screen to PNGs in
            ./previews/ -- no Pi hardware imports needed)

Dayparts (config.DAYPARTS): the frame changes personality by time of
day -- MORNING OPS, SLOW DAY, TOMORROW BRIEF, SLEEP. Each screen gathers
its providers (cached, with stale fallback), renders, displays, and
dwells. A failed screen is skipped, never fatal.

Phone control: main.py also serves a tiny web UI (control.py) at
http://frame.local:5000 -- pin a screen, resume rotation, refresh now,
pause/resume.

Pinning: tapping a screen in the web UI pins it -- the frame stays on
that screen (live screens keep refreshing in place) until another
screen is picked or rotation is resumed. The pick survives restarts.
With nothing pinned, the dayparted rotation runs as before.
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


def _wait(seconds, ctl, abort=None):
    """Sleep in small increments, waking early on pause/override (or when
    `abort()` goes true, e.g. a new pinned screen) so the phone UI stays
    responsive even during a long dwell. Never overshoots the requested
    time, so short refresh intervals stay on schedule."""
    end = time.time() + seconds
    while True:
        if ctl.paused or ctl.has_pending() or (abort and abort()):
            return
        remaining = end - time.time()
        if remaining <= 0:
            return
        time.sleep(min(5, remaining))


def _slot_end(name, dwell, ctl, show, abort=None):
    """Dwell on a screen, re-rendering live screens in place.

    Screens opting in via a `refresh` attribute (seconds) repaint
    periodically during their dwell so countdowns stay honest;
    everything else just waits out the dwell. Stops early on pause,
    on a queued phone-UI override, or when `abort()` goes true
    (used for pinned screens: a new pick ends the dwell at once).
    A failed refresh ends the dwell instead of killing the service.
    """
    interval = getattr(SCREENS[name], "refresh", 0) or 0
    end = time.time() + dwell
    while True:
        _wait(min(interval if interval else dwell,
                  max(end - time.time(), 0)), ctl, abort)
        if (ctl.paused or ctl.has_pending() or (abort and abort())
                or time.time() >= end):
            return
        if not interval:
            return
        try:
            show(name, "live refresh")
        except Exception as e:
            print(f"[{name}] refresh render failed, ending dwell: {e}")
            return


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

def _run_loop(ctl, show):
    """Main service loop. Separated from run() so the hardware setup
    stays thin -- and so the loop logic itself can be tested without
    an e-ink panel."""
    seen_rev = ctl.rev  # tracks pin changes while frozen
    while True:
        sticky = ctl.get_sticky()
        part = daypart_for(datetime.now(TZ).hour) if not sticky else None
        if ctl.paused or (not sticky and not part["screens"]):
            # Frozen -- but a phone-UI override is still honored
            # immediately instead of being swallowed, and so is a
            # new pinned screen.
            target = ctl.take_forced()
            if target in SCREENS:
                try:
                    show(target, "phone override")
                except Exception as e:
                    print(f"[{target}] render failed, skipping: {e}")
            elif target:
                print(f"[{target}] unknown screen, skipping")
            elif ctl.rev != seen_rev:
                seen_rev = ctl.rev
                pinned = ctl.get_sticky()
                if pinned in SCREENS:
                    try:
                        show(pinned, "pinned (paused)")
                    except Exception as e:
                        print(f"[{pinned}] render failed: {e}")
            else:
                time.sleep(5)
            continue
        if sticky:
            if sticky not in SCREENS:
                print(f"[sticky] unknown screen {sticky!r}; unpinning")
                ctl.set_sticky(None)
                continue
            rev = ctl.rev
            # Consume any one-shot override: the pin is the target anyway.
            # Without this, a Refresh tap's queued force would never clear
            # and _slot_end would return instantly forever -- a refresh
            # loop flashing the panel nonstop.
            ctl.take_forced()
            try:
                show(sticky, "pinned")
            except Exception as e:
                print(f"[{sticky}] render failed: {e}")
                time.sleep(30)
                continue
            # Stay here indefinitely: live screens (departure) keep
            # refreshing in place; any new pick ends the dwell at once
            # via the rev guard.
            _slot_end(sticky, 3600, ctl, show,
                      abort=lambda: ctl.rev != rev)
            continue
        rev = ctl.rev
        for name in part["screens"]:
            # A pin (or unpin) mid-rotation breaks back out so the new
            # selection takes effect within seconds, not at the next
            # dwell boundary.
            if ctl.paused or ctl.get_sticky() or ctl.rev != rev:
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
            _slot_end(target, part["dwell"], ctl, show,
                      abort=lambda: ctl.rev != rev)


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
        _run_loop(ctl, show)
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
