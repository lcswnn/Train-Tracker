import math
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 480, 800          # portrait canvas; rotated to 800x480 at display time
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

LAT, LON = 41.9053, -87.6652     # near Division Blue Line
TZ = ZoneInfo("America/Chicago")

# Your usual time out the door (24h). The commute strip shows the two
# hours before and after this, so the "should I bring X?" question is
# always answered for the hour that matters.
DEPARTURE_HOUR = 7


def describe(code):
    """Return (label, icon_key) for an Open-Meteo WMO weather code."""
    if code == 0:
        return "Clear", "sun"
    if code == 1:
        return "Mainly clear", "sun"
    if code == 2:
        return "Partly cloudy", "partly"
    if code == 3:
        return "Overcast", "cloud"
    if code in (45, 48):
        return "Fog", "fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle", "rain"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Rain", "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow", "snow"
    if code in (95, 96, 99):
        return "Thunderstorm", "storm"
    return "Cloudy", "cloud"


# --- 1-bit icons drawn with PIL primitives. Simple solid shapes stay
# --- crisp on e-ink; downloaded image icons would dither badly.
# --- Each draws inside an (x, y, s) square.

def draw_sun(draw, x, y, s):
    cx, cy, r = x + s // 2, y + s // 2, s // 5
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    for deg in range(0, 360, 45):
        a = math.radians(deg)
        x1 = cx + int((r + 5) * math.cos(a))
        y1 = cy + int((r + 5) * math.sin(a))
        x2 = cx + int((r + 13) * math.cos(a))
        y2 = cy + int((r + 13) * math.sin(a))
        draw.line([x1, y1, x2, y2], fill=0, width=3)


def draw_cloud(draw, x, y, s):
    draw.ellipse([x, y + int(s * 0.45), x + s, y + int(s * 0.90)], fill=0)
    draw.ellipse([x + int(s * 0.12), y + int(s * 0.28),
                  x + int(s * 0.48), y + int(s * 0.64)], fill=0)
    draw.ellipse([x + int(s * 0.45), y + int(s * 0.12),
                  x + int(s * 0.85), y + int(s * 0.58)], fill=0)


def draw_partly(draw, x, y, s):
    draw_sun(draw, x, y, int(s * 0.55))
    draw_cloud(draw, x + int(s * 0.32), y + int(s * 0.32), int(s * 0.68))


def draw_rain(draw, x, y, s):
    draw_cloud(draw, x, y + int(s * 0.05), int(s * 0.70))
    base = y + int(s * 0.72)
    for i in range(3):
        rx = x + int(s * 0.28) + i * int(s * 0.20)
        draw.line([rx, base, rx - 7, base + 16], fill=0, width=4)


def draw_snow(draw, x, y, s):
    draw_cloud(draw, x, y + int(s * 0.05), int(s * 0.70))
    base = y + int(s * 0.78)
    for i in range(3):
        cx = x + int(s * 0.28) + i * int(s * 0.20)
        draw.ellipse([cx - 4, base, cx + 4, base + 8], fill=0)


def draw_storm(draw, x, y, s):
    draw_cloud(draw, x, y, int(s * 0.68))
    cx = x + s // 2
    bolt = [(cx + 6, y + int(s * 0.55)), (cx - 8, y + int(s * 0.80)),
            (cx - 1, y + int(s * 0.80)), (cx - 6, y + int(s * 1.00)),
            (cx + 8, y + int(s * 0.72)), (cx + 1, y + int(s * 0.72))]
    draw.polygon(bolt, fill=0)


def draw_fog(draw, x, y, s):
    for i in range(3):
        yy = y + int(s * 0.30) + i * int(s * 0.20)
        draw.line([x + int(s * 0.15), yy, x + int(s * 0.85), yy], fill=0, width=4)


ICON_DRAWERS = {
    "sun": draw_sun,
    "partly": draw_partly,
    "cloud": draw_cloud,
    "rain": draw_rain,
    "snow": draw_snow,
    "storm": draw_storm,
    "fog": draw_fog,
}


def fetch_weather():
    """Current conditions, commute-hour detail, and today's stats."""
    params = {
        "latitude": LAT,
        "longitude": LON,
        "current": ["temperature_2m", "apparent_temperature",
                    "weather_code", "wind_speed_10m"],
        "hourly": ["temperature_2m", "precipitation_probability",
                   "weather_code"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "sunrise",
                  "precipitation_probability_max"],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "America/Chicago",
        "forecast_days": 2,
    }
    data = requests.get("https://api.open-meteo.com/v1/forecast",
                         params=params, timeout=15).json()
    cur, hr, daily = data["current"], data["hourly"], data["daily"]
    label, icon = describe(cur["weather_code"])

    # Commute strip: the 2 hours before departure through the 2 after.
    times = [datetime.fromisoformat(t) for t in hr["time"]]
    today = datetime.now(TZ).date()
    commute = []
    for h in range(DEPARTURE_HOUR - 1, DEPARTURE_HOUR + 3):
        target = datetime(today.year, today.month, today.day, h)
        i = next(i for i, t in enumerate(times) if t >= target)
        _, s_icon = describe(hr["weather_code"][i])
        rain = hr["precipitation_probability"][i] or 0
        commute.append({
            "label": datetime(today.year, today.month, today.day, h
                              ).strftime("%I %p").lstrip("0"),
            "icon": s_icon,
            "temp": round(hr["temperature_2m"][i]),
            "rain": round(rain),
        })

    sunrise = datetime.fromisoformat(daily["sunrise"][0]
                                     ).strftime("%I:%M %p").lstrip("0")
    return {
        "temp": round(cur["temperature_2m"]),
        "feels": round(cur["apparent_temperature"]),
        "wind": round(cur["wind_speed_10m"]),
        "condition": label,
        "icon": icon,
        "high": round(daily["temperature_2m_max"][0]),
        "low": round(daily["temperature_2m_min"][0]),
        "sunrise": sunrise,
        "rain_day": round(daily["precipitation_probability_max"][0] or 0),
        "commute": commute,
    }


def advise(w):
    """Rule-based 'what to wear' lines, most urgent first (max 3)."""
    tips = []
    max_rain = max(h["rain"] for h in w["commute"])
    if max_rain >= 40:
        tips.append(f"Bring an umbrella ({max_rain}% rain)")
    elif max_rain >= 20:
        tips.append(f"Rain possible ({max_rain}%)")

    feels = w["feels"]
    if feels < 25:
        tips.append("Heavy winter coat")
    elif feels < 35:
        tips.append("Winter coat weather")
    elif feels < 45:
        tips.append("Jacket weather")
    elif feels < 55:
        tips.append("Light jacket")
    elif feels < 65:
        tips.append("Long sleeves")
    elif feels < 75:
        tips.append("T-shirt weather")
    else:
        tips.append("Shorts weather")

    if any(h["icon"] == "snow" for h in w["commute"]):
        tips.append("Snow - wear boots")
    if w["wind"] >= 20:
        tips.append(f"Windy - {w['wind']} mph at the platform")
    return tips[:3]


def centered(draw, y, text, font):
    """Draw text horizontally centered with its ink-top at y; return ink-bottom."""
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (r - l)) // 2 - l
    draw.text((x, y - t), text, font=font, fill=0)
    return y + (b - t)


def centered_on(draw, cx, y, text, font):
    """Draw text centered on cx with its ink-top at y; return ink-bottom."""
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    x = cx - (r - l) // 2 - l
    draw.text((x, y - t), text, font=font, fill=0)
    return y + (b - t)


def section_head(draw, y, text):
    font = ImageFont.truetype(FONT_PATH, 20)
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    draw.text((36 - l, y - t), text, font=font, fill=0)
    return y + (b - t) + 12


def divider(draw, y):
    draw.line([(48, y), (WIDTH - 48, y)], fill=0, width=2)


def render_weather():
    """Build the 480x800 portrait commute-weather page; returns a PIL image."""
    w = fetch_weather()
    print(f"{w['temp']}F, {w['condition']} (H:{w['high']} L:{w['low']})")

    img = Image.new("1", (WIDTH, HEIGHT), 1)
    draw = ImageDraw.Draw(img)
    now = datetime.now(TZ).strftime("%I:%M %p").lstrip("0")

    # --- Header ---
    y = 36
    y = centered(draw, y, "CHICAGO, IL", ImageFont.truetype(FONT_PATH, 30))
    y = centered(draw, y + 8, now, ImageFont.truetype(FONT_PATH, 22))

    # --- Hero: icon + huge temp, condition, feels-like/high/low ---
    icon_s = 84
    y += 16
    ICON_DRAWERS[w["icon"]](draw, (WIDTH - icon_s) // 2, y, icon_s)
    y += icon_s + 10
    y = centered(draw, y, f"{w['temp']}°", ImageFont.truetype(FONT_PATH, 104))
    y = centered(draw, y + 10, w["condition"], ImageFont.truetype(FONT_PATH, 32))
    y = centered(draw, y + 8,
                 f"Feels like {w['feels']}°   H {w['high']}° / L {w['low']}°",
                 ImageFont.truetype(FONT_PATH, 24))

    # --- Commute strip: hourly temp + rain around departure ---
    divider(draw, y + 22)
    y = section_head(draw, y + 40, "MORNING COMMUTE")
    col_w = WIDTH // 4
    f_lab = ImageFont.truetype(FONT_PATH, 18)
    f_tmp = ImageFont.truetype(FONT_PATH, 24)
    f_rain = ImageFont.truetype(FONT_PATH, 18)
    isz = 40
    col_bottom = y
    for i, h in enumerate(w["commute"]):
        cx = col_w * i + col_w // 2
        y1 = centered_on(draw, cx, y, h["label"], f_lab)
        ICON_DRAWERS[h["icon"]](draw, cx - isz // 2, y1 + 6, isz)
        y2 = centered_on(draw, cx, y1 + 6 + isz + 6, f"{h['temp']}°", f_tmp)
        y3 = centered_on(draw, cx, y2 + 4, f"{h['rain']}%", f_rain)
        col_bottom = max(col_bottom, y3)
    y = col_bottom + 22

    # --- What to wear: boxed advice ---
    y = section_head(draw, y, "WHAT TO WEAR")
    tips = advise(w)
    f_tip = ImageFont.truetype(FONT_PATH, 24)
    line_h = 36
    box_h = len(tips) * line_h + 28
    draw.rectangle([(36, y), (WIDTH - 36, y + box_h)], outline=0, width=3)
    ty = y + 16
    for tip in tips:
        l, t, r, b = draw.textbbox((0, 0), "• " + tip, font=f_tip)
        draw.text((56 - l, ty - t), "• " + tip, font=f_tip, fill=0)
        ty += line_h
    y += box_h + 22

    # --- Bottom stats ---
    divider(draw, y)
    by = y + 20
    stats = [
        ("WIND", f"{w['wind']} mph"),
        ("SUNRISE", w["sunrise"]),
        ("DAY RAIN", f"{w['rain_day']}%"),
    ]
    scol = WIDTH // 3
    f_slab = ImageFont.truetype(FONT_PATH, 18)
    f_sval = ImageFont.truetype(FONT_PATH, 26)
    for i, (lab, val) in enumerate(stats):
        cx = scol * i + scol // 2
        y1 = centered_on(draw, cx, by, lab, f_slab)
        centered_on(draw, cx, y1 + 6, val, f_sval)

    return img


if __name__ == "__main__":
    # Standalone test: render and put it straight on the e-ink.
    from waveshare_epd import epd7in5_V2

    img = render_weather().rotate(90, expand=True)  # portrait -> landscape for the driver
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(img))
    epd.sleep()
    print("Weather on screen.")
