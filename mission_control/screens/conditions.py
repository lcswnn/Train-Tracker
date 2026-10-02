"""CONDITIONS: minimalist weather, not a weather app.

Giant temperature, the practical interpretation as a single strong
statement, and the next 6 hours across the bottom. Nothing else.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from screens.base import (Screen, register, blank, centered, label, rule,
                          font, unavailable, W, H, MARGIN)
from screens.icons import describe, ICONS

TZ = ZoneInfo(config.TIMEZONE)


def advise(w):
    """One strong practical line. Most urgent first."""
    max_rain = max([h["rain"] for h in w["hours"]] or [0])
    if max_rain >= 40:
        return "BRING AN UMBRELLA"
    feels = w["feels"]
    if feels < 32:
        return "WINTER COAT WEATHER"
    if feels < 45:
        return "JACKET WEATHER"
    if feels < 55:
        return "LIGHT JACKET"
    if w["wind"] >= 20:
        return "WINDY COMMUTE"
    if max_rain >= 20:
        return "SLIGHT CHANCE OF RAIN"
    return "GOOD MORNING FOR A WALK"


def fmt_12(hhmm):
    h, m = int(hhmm[:2]), hhmm[3:]
    ap = "AM" if h < 12 else "PM"
    h = h % 12 or 12
    return f"{h}:{m} {ap}"


@register
class ConditionsScreen(Screen):
    name = "conditions"
    dwell = 40
    # Live screen: re-render in place every 30 min so the hourly strip
    # rolls forward (provider cache TTL is 15 min, so data is fresh).
    refresh = 1800
    providers = ("weather",)

    def render(self, data):
        img, draw = blank()
        now = datetime.now(TZ).strftime("%I:%M %p").lstrip("0")

        wx = data.get("weather")
        if not wx:
            unavailable(draw, "CONDITIONS")
            return img
        w = wx["data"]
        cond_label, icon_key = describe(w["code"])

        # --- Top bar ---
        label(draw, MARGIN, 26, "CONDITIONS")
        l, t, r, b = draw.textbbox((0, 0), now, font=font(20))
        draw.text((W - MARGIN - (r - l) - l, 26 - t), now, font=font(20),
                  fill=0)
        rule(draw, 62)

        # --- Left: the temperature, huge ---
        y = 92
        y = centered(draw, 220, y, f"{w['temp']}°", font(150, bold=True))
        y = centered(draw, 220, y + 8, cond_label, font(30))
        centered(draw, 220, y + 8,
                 f"Feels {w['feels']}°  ·  H {w['high']}° / L {w['low']}°",
                 font(24))

        # --- Right: the supporting numbers, one 50px row each ---
        rx = 470
        stats = [("WIND", f"{w['wind']} mph"),
                 ("SUNRISE", fmt_12(w["sunrise"])),
                 ("SUNSET", fmt_12(w["sunset"])),
                 ("RAIN", f"{w['rain_day']}%")]
        sy = 96
        for lab, val in stats:
            label(draw, rx, sy + 10, lab)
            vf = font(28)
            l, t, r, b = draw.textbbox((0, 0), val, font=vf)
            draw.text((W - MARGIN - (r - l) - l, sy + 25 - (b - t) / 2 - t),
                      val, font=vf, fill=0)
            sy += 50

        # --- The interpretation: one strong line ---
        rule(draw, 308)
        centered(draw, W // 2, 320, advise(w), font(30, bold=True))
        rule(draw, 352)

        # --- Bottom: commute hours ---
        hours = w["hours"][:6]
        col_w = (W - 2 * MARGIN) // max(len(hours), 1)
        for i, h in enumerate(hours):
            cx = MARGIN + col_w * i + col_w // 2
            _, k = describe(h["code"])
            centered(draw, cx, 366, h["label"], font(18))
            ICONS[k](draw, cx - 17, 383, 34)
            centered(draw, cx, 421, f"{h['temp']}°", font(22))
            centered(draw, cx, 441, f"{h['rain']}%", font(15))

        return img
