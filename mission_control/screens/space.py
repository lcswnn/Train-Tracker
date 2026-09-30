"""SPACE: the personality of the device. Sparse and beautiful.

ISS live distance, a drawn Moon phase, sunrise/sunset. Nothing else.
"""
import math
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from screens.base import (Screen, register, blank, centered, label, rule,
                          font, unavailable, W, H, MARGIN)

TZ = ZoneInfo(config.TIMEZONE)


def draw_moon(draw, cx, cy, r, phase):
    """Stylized phase: black disc, white 'lit' ellipse erased out of it,
    outline on top. phase 0=new, 0.5=full."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    k = math.cos(2 * math.pi * phase)
    if phase < 0.5:      # waxing: lit limb on the right
        lx = cx + r * k
        draw.ellipse([lx, cy - r, cx + r, cy + r], fill=1)
    else:                # waning: lit limb on the left
        rx = cx - r * k
        draw.ellipse([cx - r, cy - r, rx, cy + r], fill=1)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=0, width=3)


def fmt_12(hhmm):
    h, m = int(hhmm[:2]), hhmm[3:]
    ap = "AM" if h < 12 else "PM"
    return f"{h % 12 or 12}:{m} {ap}"


@register
class SpaceScreen(Screen):
    name = "space"
    dwell = 40
    providers = ("space", "weather")

    def render(self, data):
        img, draw = blank()

        sp = data.get("space")
        wx = data.get("weather")
        if not sp:
            unavailable(draw, "SPACE")
            return img
        s = sp["data"]

        # --- Header ---
        label(draw, MARGIN, 26, "SPACE")
        today = datetime.now(TZ).strftime("%A, %B %d").upper()
        l, t, r, b = draw.textbbox((0, 0), today, font=font(20))
        draw.text((W - MARGIN - (r - l) - l, 26 - t), today, font=font(20),
                  fill=0)
        rule(draw, 62)

        # --- Column dividers ---
        for x in (W // 3, 2 * W // 3):
            draw.line([(x, 96), (x, 420)], fill=0, width=2)

        # --- ISS: how far overhead right now ---
        cx = W // 6
        label(draw, cx - 80, 104, "ISS")
        iss = s["iss"]
        y = centered(draw, cx, 150, f"{iss['dist_km']:,}", font(64, bold=True))
        y = centered(draw, cx, y + 6, "km away", font(22))
        centered(draw, cx, y + 14,
                 f"{iss['vel_kmh']:,} km/h · alt {iss['alt_km']} km", font(18))

        # --- Moon: drawn phase ---
        cx = W // 2
        label(draw, cx - 80, 104, "MOON")
        draw_moon(draw, cx, 235, 58, s["moon"]["phase"])
        y = centered(draw, cx, 316, s["moon"]["name"], font(26))
        centered(draw, cx, y + 6,
                 f"{s['moon']['illumination'] * 100:.0f}% illuminated",
                 font(20))

        # --- Sun: rise and set ---
        cx = 5 * W // 6
        label(draw, cx - 80, 104, "SUN")
        if wx:
            w = wx["data"]
            label(draw, cx - 80, 160, "SUNRISE")
            centered(draw, cx, 182, fmt_12(w["sunrise"]), font(32))
            label(draw, cx - 80, 232, "SUNSET")
            centered(draw, cx, 254, fmt_12(w["sunset"]), font(32))
        else:
            centered(draw, cx, 200, "—", font(34))

        return img
