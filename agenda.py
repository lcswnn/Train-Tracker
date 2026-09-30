import os
import requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
from icalendar import Calendar
import recurring_ical_events

WIDTH, HEIGHT = 480, 800          # portrait canvas; rotated to 800x480 at display time
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MARGIN = 36
TZ = ZoneInfo("America/Chicago")

# Secret iCal URL(s) from Google Calendar settings. Anyone holding this URL
# can read the calendar, so it lives in an environment variable -- never
# commit it. Comma-separate if you want several calendars merged.
#   export GCAL_ICAL_URL="https://calendar.google.com/calendar/ical/.../basic.ics"
ICAL_URLS = [u.strip() for u in os.environ.get("GCAL_ICAL_URL", "").split(",")
             if u.strip()]

MARKETS = [
    ("S&P 500", "ES=F"),
    ("NASDAQ", "NQ=F"),
    ("DOW", "YM=F"),
    ("BITCOIN", "BTC-USD"),
]


def fetch_calendar():
    """Today's timed events (agenda) and all-day events (reminders).

    Uses Google Calendar's secret iCal URL: no OAuth dance, no extra
    credentials -- just an HTTP GET. recurring_ical_events expands
    repeating events (standups, etc.) so they show up like normal ones.
    """
    if not ICAL_URLS:
        raise RuntimeError("GCAL_ICAL_URL is not set")
    now = datetime.now(TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    agenda, reminders = [], []
    for url in ICAL_URLS:
        cal = Calendar.from_ical(requests.get(url, timeout=15).text)
        for e in recurring_ical_events.of(cal).between(start, end):
            summary = str(e.get("SUMMARY", "")).strip()
            if not summary:
                continue
            dt = e["DTSTART"].dt
            if isinstance(dt, datetime):
                agenda.append((dt.astimezone(TZ), summary))
            else:  # a plain date means an all-day event
                reminders.append(summary)

    agenda.sort(key=lambda x: x[0])
    reminders = list(dict.fromkeys(reminders))  # dedupe, keep order
    return agenda, reminders


def fetch_markets():
    """Futures snapshot from Yahoo Finance's public chart API (no key)."""
    out = []
    for label, sym in MARKETS:
        try:
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/"
                f"{sym}?interval=1d&range=5d",
                headers={"User-Agent": "Mozilla/5.0"}, timeout=15).json()
            closes = [c for c in
                      r["chart"]["result"][0]["indicators"]["quote"][0]["close"]
                      if c]
            price, prev = closes[-1], closes[-2]
            out.append({"label": label, "price": price,
                        "chg": (price - prev) / prev * 100, "ok": True})
        except Exception as e:
            print(f"Market {sym} failed: {e}")
            out.append({"label": label, "ok": False})
    return out


def centered(draw, y, text, font):
    """Draw text horizontally centered with its ink-top at y; return ink-bottom."""
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (r - l)) // 2 - l
    draw.text((x, y - t), text, font=font, fill=0)
    return y + (b - t)


def section_head(draw, y, text):
    l, t, r, b = draw.textbbox((0, 0), text,
                               font=ImageFont.truetype(FONT_PATH, 22))
    font = ImageFont.truetype(FONT_PATH, 22)
    draw.text((MARGIN - l, y - t), text, font=font, fill=0)
    return y + (b - t) + 14


def divider(draw, y):
    draw.line([(48, y), (WIDTH - 48, y)], fill=0, width=2)


def triangle(draw, x, y, s, up):
    s = int(s)
    if up:
        draw.polygon([(x, y + s), (x + s, y + s), (x + s // 2, y)], fill=0)
    else:
        draw.polygon([(x, y), (x + s, y), (x + s // 2, y + s)], fill=0)


def render_morning():
    """Build the 480x800 portrait morning page; returns a PIL image."""
    try:
        agenda, reminders = fetch_calendar()
        cal_error = None
    except Exception as e:
        print(f"Calendar failed: {e}")
        agenda, reminders, cal_error = [], [], str(e)

    markets = fetch_markets()

    img = Image.new("1", (WIDTH, HEIGHT), 1)
    draw = ImageDraw.Draw(img)
    now = datetime.now(TZ)

    # --- Header ---
    y = 44
    y = centered(draw, y, now.strftime("%A, %B %d").upper(),
                 ImageFont.truetype(FONT_PATH, 32))
    y = centered(draw, y + 10, now.strftime("%I:%M %p").lstrip("0"),
                 ImageFont.truetype(FONT_PATH, 24))
    divider(draw, y + 22)
    y += 46

    # --- Today's agenda: timed events ---
    y = section_head(draw, y, "TODAY'S AGENDA")
    font_ev = ImageFont.truetype(FONT_PATH, 24)
    if cal_error:
        y = section_head(draw, y, "Set GCAL_ICAL_URL on the Pi")
    elif not agenda:
        l, t, r, b = draw.textbbox((0, 0), "Nothing scheduled.", font=font_ev)
        draw.text((MARGIN - l, y - t), "Nothing scheduled.", font=font_ev,
                  fill=0)
        y += (b - t) + 10
    else:
        for dt, summary in agenda[:5]:
            tstr = dt.strftime("%I:%M %p").lstrip("0")
            for text, fx, fnt in ((tstr, MARGIN, font_ev),
                                  (summary, MARGIN + 150, font_ev)):
                l, t, r, b = draw.textbbox((0, 0), text, font=fnt)
                draw.text((fx - l, y - t), text, font=fnt, fill=0)
            y += (b - t) + 12
    y += 18

    # --- Reminders: all-day events ---
    y = section_head(draw, y, "REMINDERS")
    font_re = ImageFont.truetype(FONT_PATH, 23)
    if not cal_error:
        if not reminders:
            l, t, r, b = draw.textbbox((0, 0), "—", font=font_re)
            draw.text((MARGIN - l, y - t), "—", font=font_re, fill=0)
            y += (b - t) + 10
        else:
            for rem in reminders[:4]:
                text = f"• {rem}"
                l, t, r, b = draw.textbbox((0, 0), text, font=font_re)
                draw.text((MARGIN - l, y - t), text, font=font_re, fill=0)
                y += (b - t) + 10
    y += 18

    # --- Market snapshot ---
    divider(draw, y)
    y = section_head(draw, y + 24, "MARKET SNAPSHOT")
    font_lab = ImageFont.truetype(FONT_PATH, 24)
    font_val = ImageFont.truetype(FONT_PATH, 22)
    for m in markets:
        l, t, r, b = draw.textbbox((0, 0), m["label"], font=font_lab)
        draw.text((MARGIN - l, y - t), m["label"], font=font_lab, fill=0)
        if m["ok"]:
            val = f"{m['price']:,.2f}  {m['chg']:+.2f}%"
            vl, vt, vr, vb = draw.textbbox((0, 0), val, font=font_val)
            vx = WIDTH - MARGIN - (vr - vl)
            if m["chg"] != 0:
                triangle(draw, vx - 26, y + (vb - vt) // 2 - 6, 12,
                         m["chg"] > 0)
            draw.text((vx - vl, y - vt), val, font=font_val, fill=0)
        else:
            vl, vt, vr, vb = draw.textbbox((0, 0), "—", font=font_val)
            draw.text((WIDTH - MARGIN - (vr - vl) - vl, y - vt), "—",
                      font=font_val, fill=0)
        y += (b - t) + 16

    return img


if __name__ == "__main__":
    # Standalone test: render and put it straight on the e-ink.
    from waveshare_epd import epd7in5_V2

    img = render_morning().rotate(90, expand=True)  # portrait -> landscape for the driver
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(img))
    epd.sleep()
    print("Morning page on screen.")
