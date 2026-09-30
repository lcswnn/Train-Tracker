import html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 480, 800          # portrait canvas; rotated to 800x480 at display time
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MARGIN = 36
TZ = ZoneInfo("America/Chicago")

# Google News RSS: free, no API key. Titles come as "Headline - Source",
# so fetch_news() splits the source back off using the <source> element.
FEED_URL = ("https://news.google.com/rss/search?"
            "q=Chicago&hl=en-US&gl=US&ceid=US:en")
STORIES = 5


def fetch_news():
    """Top Chicago headlines from Google News RSS (stdlib XML parsing).

    Raises on network/parse failure; render_news() turns that into a
    friendly fallback page instead of crashing the digest loop.
    """
    r = requests.get(FEED_URL, headers={"User-Agent": "Mozilla/5.0"},
                     timeout=15)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    stories = []
    for item in root.findall(".//item")[:STORIES]:
        raw = html.unescape(item.findtext("title") or "").strip()
        src_el = item.find("source")
        source = (html.unescape(src_el.text).strip()
                  if src_el is not None and src_el.text else "")
        title = raw
        if source and raw.endswith(" - " + source):
            title = raw[: -len(" - " + source)].strip()
        if title:
            stories.append({"title": title, "source": source})
    return stories


def shorten(text, max_chars=130):
    """Word-safe truncation so long headlines don't eat the page."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def wrap_to_pixels(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def centered(draw, y, text, font):
    """Draw text horizontally centered with its ink-top at y; return ink-bottom."""
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (r - l)) // 2 - l
    draw.text((x, y - t), text, font=font, fill=0)
    return y + (b - t)


def divider(draw, y):
    draw.line([(48, y), (WIDTH - 48, y)], fill=0, width=2)


def render_news():
    """Build the 480x800 portrait news page; returns a PIL image."""
    img = Image.new("1", (WIDTH, HEIGHT), 1)
    draw = ImageDraw.Draw(img)

    try:
        stories = fetch_news()
    except Exception as e:
        print(f"News fetch failed: {e}")
        stories = []
    print(f"Got {len(stories)} stories")

    now = datetime.now(TZ)
    y = 44
    y = centered(draw, y, "CHICAGO", ImageFont.truetype(FONT_PATH, 34))
    y = centered(draw, y + 10, now.strftime("%A, %B %d"),
                 ImageFont.truetype(FONT_PATH, 22))
    divider(draw, y + 22)
    y += 48

    if not stories:
        centered(draw, y + 120, "Couldn't load headlines.",
                 ImageFont.truetype(FONT_PATH, 28))
        centered(draw, y + 170, "Check the Pi's connection.",
                 ImageFont.truetype(FONT_PATH, 22))
        return img

    font_head = ImageFont.truetype(FONT_PATH, 25)
    font_src = ImageFont.truetype(FONT_PATH, 17)
    for i, story in enumerate(stories):
        lines = wrap_to_pixels(draw, shorten(story["title"]), font_head,
                               WIDTH - 2 * MARGIN)[:3]
        for line in lines:
            # Left-aligned, newspaper style; ink-top placement avoids overlap.
            l, t, r, b = draw.textbbox((0, 0), line, font=font_head)
            draw.text((MARGIN - l, y - t), line, font=font_head, fill=0)
            y += (b - t) + 6
        if story["source"]:
            l, t, r, b = draw.textbbox((0, 0), story["source"], font=font_src)
            draw.text((MARGIN - l, y + 2 - t), story["source"],
                      font=font_src, fill=0)
            y += (b - t) + 8
        if i < len(stories) - 1:
            divider(draw, y + 13)
            y += 30

    # Footer: when this data was fetched.
    foot = f"Updated {now.strftime('%I:%M %p').lstrip('0')} · Google News"
    font_foot = ImageFont.truetype(FONT_PATH, 16)
    l, t, r, b = draw.textbbox((0, 0), foot, font=font_foot)
    draw.text(((WIDTH - (r - l)) // 2 - l, HEIGHT - 40 - t), foot,
              font=font_foot, fill=0)

    return img


if __name__ == "__main__":
    # Standalone test: render and put it straight on the e-ink.
    from waveshare_epd import epd7in5_V2

    img = render_news().rotate(90, expand=True)  # portrait -> landscape for the driver
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(img))
    epd.sleep()
    print("News on screen.")
