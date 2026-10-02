"""CTA departures provider.

Live mode (CTA_API_KEY set): real Blue Line arrivals from the CTA
Train Tracker API (ttarrivals.aspx), filtered to DIRECTION below.
Mock mode (no key): deterministic departures on a ~8-minute headway,
so the DEPARTURE screen and rotation can be tested. The interface is
identical either way:
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
API_URL = "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx"

# Which way you're headed. Division/Milwaukee serves both directions;
# we only board trains going this way. Flip to "O'Hare" if that's
# your commute.
DIRECTION = "Forest Park"


def _mock_departures(now):
    # Deterministic: next train 2-9 min out, then every 8 min.
    mins_ahead = (8 - now.minute % 8) % 8 + 2
    t1 = now + timedelta(minutes=mins_ahead)
    return [
        {"time": (t1 + timedelta(minutes=8 * i)).isoformat(),
         "destination": "Forest Park", "delay_min": 0}
        for i in range(4)
    ]


def _real_departures():
    """Live arrivals from CTA Train Tracker, same shape as the mock.

    Raises on API errors or when fewer than two DIRECTION-bound ETAs
    come back -- the provider base then serves the last good fetch
    and the screen labels it with its age.
    """
    resp = requests.get(API_URL, params={
        "key": config.CTA_API_KEY,
        "mapid": config.CTA_MAPID,
        "outputType": "JSON",
    }, timeout=10)
    resp.raise_for_status()
    ctatt = resp.json().get("ctatt", {})
    if ctatt.get("errCd") != "0":
        raise RuntimeError(f"CTA API error {ctatt.get('errCd')}: "
                           f"{ctatt.get('errNm')}")
    etas = ctatt.get("eta") or []
    if isinstance(etas, dict):
        etas = [etas]  # a single ETA comes back as an object, not a list
    trains = []
    for e in etas:
        if e.get("destNm") != DIRECTION:
            continue
        delayed = e.get("isDly") == "1"
        trains.append({
            # arrT is naive ISO in Chicago time; board() attaches TZ.
            "time": e["arrT"],
            "destination": e.get("destNm", DIRECTION),
            # The API only says delayed-or-not, never by how much.
            # 5 is a sentinel that trips board()'s TRAIN DELAYED status;
            # delay_unknown keeps the screen from printing "5 min".
            "delay_min": 5 if delayed else 0,
            "delay_unknown": delayed,
        })
        if len(trains) == 6:
            break
    if not trains:
        raise RuntimeError(f"no {DIRECTION}-bound ETAs right now")
    return trains


def board(trains, now, walk_min, buffer_min):
    """The whole 'when do I leave' computation in one place.

    Rolls forward past missed trains: 'next' is the first train whose
    leave-by time is still in the future. If every train's leave-by has
    already passed, falls back to the soonest train with LEAVE NOW.
    """
    if not trains:
        raise ValueError("no trains to board")

    def _leave_by(t):
        dt = datetime.fromisoformat(t["time"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt - timedelta(minutes=walk_min + buffer_min)

    idx = next((i for i, t in enumerate(trains) if _leave_by(t) > now),
               len(trains) - 1)
    nxt, fol = trains[idx], trains[min(idx + 1, len(trains) - 1)]

    t1 = datetime.fromisoformat(nxt["time"])
    if t1.tzinfo is None:
        t1 = t1.replace(tzinfo=TZ)
    leave_by = t1 - timedelta(minutes=walk_min + buffer_min)
    leave_in = (leave_by - now).total_seconds() / 60
    delay = nxt.get("delay_min", 0)

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

    t2 = datetime.fromisoformat(fol["time"])
    if t2.tzinfo is None:
        t2 = t2.replace(tzinfo=TZ)
    return {
        "status": status,
        "leave_in_min": leave_in,
        "leave_by": leave_by,
        "walk_min": walk_min,
        "buffer_min": buffer_min,
        "next": {"time": t1, "destination": nxt["destination"],
                 "delay_min": delay,
                 "delay_unknown": nxt.get("delay_unknown", False)},
        "following": {"time": t2, "destination": fol["destination"]},
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
