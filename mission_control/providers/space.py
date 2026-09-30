"""Space provider: ISS live position + Moon phase.

- ISS: wheretheiss.at, free, no key. Distance from home via haversine.
- Moon: computed locally from the synodic month. No API needed, and it
  never fails -- the provider still goes through the cache layer so the
  interface stays uniform.
"""
import math
from datetime import datetime, timezone

import requests

import config
from providers.base import Provider

ISS_ID = 25544  # NORAD catalog number for the ISS
SYNODIC_MONTH = 29.53058867
# A known new moon: 2000-01-06 18:14 UTC.
REF_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)

PHASE_NAMES = ["New Moon", "Waxing Crescent", "First Quarter",
               "Waxing Gibbous", "Full Moon", "Waning Gibbous",
               "Last Quarter", "Waning Crescent"]


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2)
         * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def moon_info(now):
    days = (now - REF_NEW_MOON).total_seconds() / 86400
    phase = (days % SYNODIC_MONTH) / SYNODIC_MONTH  # 0=new, 0.5=full
    illumination = (1 - math.cos(2 * math.pi * phase)) / 2
    idx = int(phase * 8 + 0.5) % 8
    return {"phase": phase, "illumination": illumination,
            "name": PHASE_NAMES[idx]}


class SpaceProvider(Provider):
    name = "space"

    def fetch(self):
        r = requests.get(
            f"https://api.wheretheiss.at/v1/satellites/{ISS_ID}",
            timeout=15).json()
        now = datetime.now(timezone.utc)
        return {
            "iss": {
                "lat": r["latitude"],
                "lon": r["longitude"],
                "alt_km": round(r["altitude"]),
                "vel_kmh": round(r["velocity"]),
                "dist_km": round(haversine_km(config.HOME_LAT,
                                              config.HOME_LON,
                                              r["latitude"], r["longitude"])),
            },
            "moon": moon_info(now),
        }
