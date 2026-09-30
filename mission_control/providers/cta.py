"""CTA departures provider.

Mock mode (no CTA_API_KEY set): deterministic Blue Line departures on a
~8-minute headway, so the DEPARTURE screen and rotation can be tested
before the real key arrives. The interface is identical either way:
{"trains": [{"time": iso, "destination": str, "delay_min": int}, ...]}.

board() turns raw departures into the "when do I leave?" answer:
leave-by time, countdown, and the PLENTY OF TIME / LEAVE NOW status.
That logic lives here (data layer), not in the screen.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

import config
from providers.base import Provider

TZ = ZoneInfo(config.TIMEZONE)


def _mock_departures(now):
    # Deterministic: next train 2-9 min out, then every 8 min.
    mins_ahead = (8 - now.minute % 8) % 8 + 2
    t1 = now + timedelta(minutes=mins_ahead)
    return [
        {"time": t1.isoformat(), "destination": "Forest Park",
         "delay_min": 0},
        {"time": (t1 + timedelta(minutes=8)).isoformat(),
         "destination": "Forest Park", "delay_min": 0},
    ]


def _real_departures():
    # CTA Train Tracker: ttarrivals.aspx?key=...&mapid=40320&outputType=JSON
    # Implemented when the API key arrives; same return shape as mock.
    raise NotImplementedError("CTA_API_KEY not wired yet")


def board(trains, now, walk_min, buffer_min):
    """The whole 'when do I leave' computation in one place."""
    t1 = datetime.fromisoformat(trains[0]["time"])
    if t1.tzinfo is None:
        t1 = t1.replace(tzinfo=TZ)
    leave_by = t1 - timedelta(minutes=walk_min + buffer_min)
    leave_in = (leave_by - now).total_seconds() / 60
    delay = trains[0].get("delay_min", 0)

    if delay >= 5:
        status = "TRAIN DELAYED"
    elif leave_in > 20:
        status = "PLENTY OF TIME"
    elif leave_in > 5:
        status = f"LEAVE IN {int(round(leave_in))} MIN"
    elif leave_in > 0:
        status = "LEAVE SOON"
    else:
        status = "LEAVE NOW"

    t2 = datetime.fromisoformat(trains[1]["time"])
    if t2.tzinfo is None:
        t2 = t2.replace(tzinfo=TZ)
    return {
        "status": status,
        "leave_in_min": leave_in,
        "leave_by": leave_by,
        "walk_min": walk_min,
        "buffer_min": buffer_min,
        "next": {"time": t1, "destination": trains[0]["destination"],
                 "delay_min": delay},
        "following": {"time": t2, "destination": trains[1]["destination"]},
    }


class CTAProvider(Provider):
    name = "cta"

    def fetch(self):
        now = datetime.now(TZ)
        if config.CTA_API_KEY:
            trains = _real_departures()
        else:
            trains = _mock_departures(now)
        return {"trains": trains,
                "mock": not bool(config.CTA_API_KEY)}
