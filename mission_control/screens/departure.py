"""DEPARTURE screen: "when do I leave for the Blue Line?"

Live screen (refresh=180): the main loop re-renders it in place every
3 minutes during its dwell so the countdown never sits stale.

Layout, top to bottom:
  - header bar: DEPARTURE · <station> — BLUE LINE, clock at right
  - the countdown: LEAVE IN / N MIN, or PLENTY OF TIME / LEAVE SOON /
    LEAVE NOW / TRAIN DELAYED -- the biggest thing on the device
  - LEAVE BY <time>: the actionable line, big
  - train + walk detail, then the following train
  - bottom strip: Blue Line service status (alerts, or "Normal service")
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import config
from providers.cta import board
from screens.base import (Screen, register, blank, centered, label, rule,
                          wrap, font, unavailable, W, H, MARGIN)

TZ = ZoneInfo(config.TIMEZONE)


def fmt_time(dt):
    return dt.strftime("%I:%M %p").lstrip("0")


@register
class DepartureScreen(Screen):
    name = "departure"
    dwell = 60
    # Live screen: re-render in place this often during its dwell so the
    # countdown never sits stale. (Other screens omit this and just dwell.)
    refresh = 180
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

        # --- The countdown: biggest thing on the device ---
        y = 92
        if b["status"].startswith("LEAVE IN"):
            mins = b["status"].replace("LEAVE IN ", "").replace(" MIN", "")
            y = label(draw, MARGIN, y, "LEAVE IN")
            y = centered(draw, W // 2, y + 6, f"{mins} MIN",
                         font(150, bold=True))
        else:
            # PLENTY OF TIME / LEAVE SOON / LEAVE NOW / TRAIN DELAYED
            y = centered(draw, W // 2, y + 10, b["status"],
                         font(72, bold=True))
        y += 10

        # --- Leave-by: the actionable line, big ---
        n = b["next"]
        y = centered(draw, W // 2, y,
                     f"LEAVE BY {fmt_time(b['leave_by']).upper()}",
                     font(40, bold=True))
        y += 6

        # --- Which train, and the walk ---
        detail = (f"{fmt_time(n['time'])}  →  {n['destination']}  ·  "
                  f"walk {b['walk_min']} min")
        if n["delay_min"]:
            # delay_unknown: live API says delayed but not by how much.
            detail += ("  ·  delayed" if n.get("delay_unknown")
                       else f"  ·  delayed {n['delay_min']} min")
        y = centered(draw, W // 2, y, detail, font(22))
        y += 4
        f2 = b["following"]
        centered(draw, W // 2, y,
                 f"next {fmt_time(f2['time'])} → {f2['destination']}",
                 font(18))

        # --- Bottom strip: Blue Line status ---
        rule(draw, H - 104)
        label(draw, MARGIN, H - 96, "BLUE LINE STATUS")
        if cta.get("stale"):
            age = int(cta["age"] // 60)
            tag = f"updated {age} min ago"
        elif cta["data"].get("mock"):
            tag = "mock data"
        else:
            tag = "live"
        l, t, r, bb = draw.textbbox((0, 0), tag, font=font(18))
        draw.text((W - MARGIN - (r - l) - l, H - 96 - t), tag,
                  font=font(18), fill=0)

        alerts = cta["data"].get("alerts", [])
        if not alerts:
            centered(draw, W // 2, H - 66, "Normal service", font(22))
        else:
            a = alerts[0]
            head = ("MAJOR ALERT — " if a["major"] else "") + a["headline"]
            lines = wrap(draw, head, font(22, bold=True), W - 2 * MARGIN)
            y2 = centered(draw, W // 2, H - 70, lines[0],
                          font(22, bold=True))
            if a["description"]:
                desc = wrap(draw, a["description"], font(20),
                            W - 2 * MARGIN)[0]
                if len(desc) > 88:
                    desc = desc[:87] + "…"
                centered(draw, W // 2, y2 + 4, desc, font(20))
            if len(alerts) > 1:
                more = f"+{len(alerts) - 1} more"
                l, t, r, bb = draw.textbbox((0, 0), more, font=font(18))
                draw.text((W - MARGIN - (r - l) - l, H - 70 - t), more,
                          font=font(18), fill=0)

        return img
