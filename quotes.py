import csv
import os
import random
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 480, 800          # portrait canvas; rotated to 800x480 at display time
MARGIN = 40
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# Path relative to this file, so it works no matter where you run from.
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "insparation.csv")


def wrap_to_pixels(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        w = draw.textbbox((0, 0), test, font=font)[2]
        if w <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_quote():
    """Pick a random quote and render the portrait page; returns a PIL image."""
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = [row["Quote"].strip() for row in csv.DictReader(f)
                if row.get("Quote", "").strip()]
    quote_str = random.choice(rows)
    print(quote_str)

    img = Image.new("1", (WIDTH, HEIGHT), 1)
    draw = ImageDraw.Draw(img)

    font_size = 60
    while font_size >= 20:
        font = ImageFont.truetype(FONT_PATH, font_size)
        lines = wrap_to_pixels(draw, quote_str, font, WIDTH - 2 * MARGIN)
        heights = [draw.textbbox((0, 0), l, font=font)[3] for l in lines]
        total_h = sum(heights) + (len(lines) - 1) * 10
        if total_h <= HEIGHT - 2 * MARGIN:
            break
        font_size -= 4

    y = (HEIGHT - total_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=font, fill=0)
        y += (bbox[3] - bbox[1]) + 10

    print(f"Rendered at font size {font_size}")
    return img


if __name__ == "__main__":
    # Standalone test: render and put it straight on the e-ink.
    from waveshare_epd import epd7in5_V2

    img = render_quote().rotate(90, expand=True)  # portrait -> landscape for the driver
    epd = epd7in5_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(img))
    epd.sleep()
    print("Quote on screen.")
