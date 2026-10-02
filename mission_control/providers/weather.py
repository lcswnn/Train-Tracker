"""Weather provider: Open-Meteo. Free, no key.

One call returns everything the CONDITIONS screen needs:
current conditions, the next-6-hours strip, and today's stats.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

import config
from providers.base import Provider

TZ = ZoneInfo(config.TIMEZONE)


def fmt_hour(h):
    ap = "AM" if h < 12 else "PM"
    return f"{h % 12 or 12} {ap}"


class WeatherProvider(Provider):
    name = "weather"

    def fetch(self):
        params = {
            "latitude": config.HOME_LAT,
            "longitude": config.HOME_LON,
            "current": ["temperature_2m", "apparent_temperature",
                        "weather_code", "wind_speed_10m"],
            "hourly": ["temperature_2m", "precipitation_probability",
                       "weather_code"],
            "daily": ["temperature_2m_max", "temperature_2m_min",
                      "sunrise", "sunset", "precipitation_probability_max"],
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": config.TIMEZONE,
            "forecast_days": 2,
        }
        data = requests.get("https://api.open-meteo.com/v1/forecast",
                            params=params, timeout=15).json()
        cur, hr, daily = data["current"], data["hourly"], data["daily"]

        # Next 6 hours starting with the current hour -- the strip
        # rolls forward through the day instead of freezing on the
        # morning commute.
        now = datetime.now(TZ).replace(minute=0, second=0, microsecond=0)
        hours = []
        for i, t in enumerate(hr["time"]):
            dt = datetime.fromisoformat(t)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)  # Open-Meteo: naive local time
            if dt < now:
                continue
            hours.append({
                "label": fmt_hour(dt.hour),
                "code": hr["weather_code"][i],
                "temp": round(hr["temperature_2m"][i]),
                "rain": round(hr["precipitation_probability"][i] or 0),
            })
            if len(hours) == 6:
                break

        return {
            "temp": round(cur["temperature_2m"]),
            "feels": round(cur["apparent_temperature"]),
            "code": cur["weather_code"],
            "wind": round(cur["wind_speed_10m"]),
            "high": round(daily["temperature_2m_max"][0]),
            "low": round(daily["temperature_2m_min"][0]),
            "sunrise": daily["sunrise"][0][11:16],
            "sunset": daily["sunset"][0][11:16],
            "rain_day": round(daily["precipitation_probability_max"][0] or 0),
            "hours": hours,
        }
