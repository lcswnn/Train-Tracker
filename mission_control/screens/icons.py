"""1-bit weather icons, drawn with PIL primitives.

Simple solid shapes stay crisp on e-ink; image icons would dither badly.
Each draws inside an (x, y, s) square. Shared by every weather surface.
"""
import math


def describe(code):
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


ICONS = {
    "sun": draw_sun, "partly": draw_partly, "cloud": draw_cloud,
    "rain": draw_rain, "snow": draw_snow, "storm": draw_storm,
    "fog": draw_fog,
}
