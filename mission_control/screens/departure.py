"""DEPARTURE: the hero screen. Answers WHEN DO I NEED TO LEAVE?

The countdown is the biggest thing on the device -- readable from
across the room. Everything else is supporting detail.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from providers.cta import board
from screens.base import (Screen, register, blank, centered, label, rule,
                          font, unavailable, W, H, MARGIN)

TZ = ZoneInfo(config.TIMEZONE)


def fmt_time(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


@register
class DepartureScreen(Screen):
    name = "departure"
    dwell = 60
    providers = ("cta",)

    def render(self, data):
        img, draw = blank()
        now = datetime.now(TZ)

        cta = data.get("cta")
        if not cta:
            unavailable(draw, "DEPARTURE")
            return img
        b = board(cta["data"]["trains"], now,
                  config.WALK_MINUTES, config.BUFFER_MINUTES)

        # --- Top bar ---
        label(draw, MARGIN, 26,
              f"DEPARTURE  ·  {config.STATION_NAME.upper()} — "
              f"{config.CTA_ROUTE.upper()} LINE")
        l, t, r, bb = draw.textbbox((0, 0), fmt_time(now), font=font(20))
        draw.text((W - MARGIN - (r - l) - l, 26 - t), fmt_time(now),
                  font=font(20), fill=0)
        rule(draw, 62)

        # --- The countdown: biggest type on the device ---
        y = 92
        if b["status"].startswith("LEAVE IN"):
            mins = b["status"].replace("LEAVE IN ", "").replace(" MIN", "")
            y = label(draw, MARGIN, y, "LEAVE IN")
            y = centered(draw, W // 2, y + 6, f"{mins} MIN", font(150, bold=True))
        else:
            # PLENTY OF TIME / LEAVE SOON / LEAVE NOW / TRAIN DELAYED
            y = centered(draw, W // 2, y + 10, b["status"], font(72, bold=True))
        y += 18

        # --- Supporting detail: which train, walk, leave-by ---
        n = b["next"]
        line1 = f"{fmt_time(n['time'])}  →  {n['destination']}"
        line2 = (f"walk {b['walk_min']} min  ·  "
                 f"leave by {fmt_time(b['leave_by'])}")
        if n["delay_min"]:
            # delay_unknown: live API says delayed but not by how much.
            line2 += ("  ·  delayed" if n.get("delay_unknown")
                      else f"  ·  delayed {n['delay_min']} min")
        y = centered(draw, W // 2, y, line1, font(30))
        y = centered(draw, W // 2, y + 10, line2, font(26))
        y += 26

        # --- Bottom row: next train + data freshness ---
        rule(draw, H - 84)
        f2 = b["following"]
        centered(draw, W // 2, H - 64,
                 f"next train {fmt_time(f2['time'])} → {f2['destination']}",
                 font(24))
        if cta.get("stale"):
            age = int(cta["age"] // 60)
            l, t, r, bb = draw.textbbox((0, 0), f"updated {age} min ago",
                                        font=font(18))
            draw.text((W - MARGIN - (r - l) - l, H - 40 - t),
                      f"updated {age} min ago", font=font(18), fill=0)
        elif cta["data"].get("mock"):
            l, t, r, bb = draw.textbbox((0, 0), "mock data", font=font(18))
            draw.text((W - MARGIN - (r - l) - l, H - 40 - t), "mock data",
                      font=font(18), fill=0)

        return img
