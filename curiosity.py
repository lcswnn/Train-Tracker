import csv
import os
import requests
from datetime import date, datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 480, 800          # portrait canvas; rotated to 800x480 at display time
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MARGIN = 40
TZ = ZoneInfo("America/Chicago")

# curiosity.csv lives next to this script, same pattern as quotes.py.
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "curiosity.csv")


def load_facts():
    facts = []
    with open(CSV_PATH, newline="") as f:
        for row in csv.DictReader(f):
            if row["question"].strip():
                facts.append((row["topic"].strip(), row["question"].strip(),
                              row["answer"].strip()))
    return facts


def fetch_wikipedia_event():
    """One 'on this day in history' event from Wikipedia's feed API.

    Free, no key. Returns (topic, question, answer) like a CSV row.
    The pick is deterministic per date, so it's stable all day.
    """
    today = date.today()
    url = (f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/"
           f"selected/{today.month:02d}/{today.day:02d}")
    data = requests.get(url, headers={"User-Agent": "EInkDigest/1.0"},
                        timeout=15).json()
    events = data["selected"]
    ev = events[today.toordinal() % len(events)]
    answer = ev["text"].strip().replace(" (pictured)", "").replace("(pictured)", "")
    if len(answer) > 420:  # safety cap so long entries can't overflow the page
        answer = answer[:420].rsplit(" ", 1)[0] + "…"
    return ("HISTORY", f"WHAT HAPPENED ON THIS DAY IN {ev['year']}?", answer)


def pick_fact():
    """Alternate sources by day: even days use the curated CSV bank,
    odd days pull a fresh 'on this day' event from Wikipedia.
    Wikipedia failures fall back to the CSV so the page never breaks."""
    facts = load_facts()
    csv_fact = facts[date.today().toordinal() % len(facts)]
    if date.today().toordinal() % 2 == 0:
        return csv_fact
    try:
        return fetch_wikipedia_event()
    except Exception as e:
        print(f"Wikipedia event failed, using CSV: {e}")
        return csv_fact


def wrap(draw, text, font, max_width):
    """Greedy word wrap to a pixel width; returns a list of lines."""
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def centered(draw, y, text, font):
    """Draw text horizontally centered with its ink-top at y; return ink-bottom."""
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (r - l)) // 2 - l
    draw.text((x, y - t), text, font=font, fill=0)
    return y + (b - t)


def divider(draw, y):
    draw.line([(48, y), (WIDTH - 48, y)], fill=0, width=2)


def render_curiosity():
    """One curiosity per day: curated CSV on even days, a fresh
    Wikipedia 'on this day' event on odd days. Stable all day either way."""
    topic, question, answer = pick_fact()
    print(f"Curiosity: [{topic}] {question}")

    img = Image.new("1", (WIDTH, HEIGHT), 1)
    draw = ImageDraw.Draw(img)
    max_w = WIDTH - 2 * MARGIN

    # --- Header ---
    y = 44
    y = centered(draw, y, "CURIOSITY", ImageFont.truetype(FONT_BOLD, 34))
    y = centered(draw, y + 8,
                 datetime.now(TZ).strftime("%A, %B %d").upper(),
                 ImageFont.truetype(FONT_PATH, 22))
    divider(draw, y + 20)
    y += 44

    # --- Topic tag ---
    y = centered(draw, y, topic, ImageFont.truetype(FONT_PATH, 20))
    y += 18

    # --- The question, big and bold ---
    f_q = ImageFont.truetype(FONT_BOLD, 32)
    for line in wrap(draw, question, f_q, max_w):
        l, t, r, b = draw.textbbox((0, 0), line, font=f_q)
        draw.text((MARGIN - l, y - t), line, font=f_q, fill=0)
        y += (b - t) + 10
    divider(draw, y + 14)
    y += 38

    # --- The answer, short enough to read in ~15 seconds ---
    f_a = ImageFont.truetype(FONT_PATH, 25)
    for line in wrap(draw, answer, f_a, max_w):
        l, t, r, b = draw.textbbox((0, 0), line, font=f_a)
        draw.text((MARGIN - l, y - t), line, font=f_a, fill=0)
        y += (b - t) + 10

    # --- Footer ---
    centered(draw, HEIGHT - 78, "A new one tomorrow.",
            ImageFont.truetype(FONT_PATH, 20))

    return img


if __name__ == "__main__":
    # Standalone test: render and put it straight on the e-ink.
    from waveshare_epd import epd7in5_V2

    img = render_curiosity().rotate(90, expand=True)  # portrait -> landscape
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(img))
    epd.sleep()
    print("Curiosity on screen.")
