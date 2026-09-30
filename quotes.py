import csv
import random
from PIL import Image, ImageDraw, ImageFont
from waveshare_epd import epd7in5_V2 

# Pick a random quote. csv.DictReader reads the header row so
# row["Quote"] grabs the column by name, and random.choice
# replaces your pandas .sample(). Pandas isn't installed on
# the Pi and would be too heavy for its 512MB of RAM.
with open("insparation.csv", newline="", encoding="utf-8") as f:
    rows = [row["Quote"].strip() for row in csv.DictReader(f) if row.get("Quote", "").strip()]
quote_str = random.choice(rows)
print(quote_str)

# Fit the quote to the page (same render code as your Mac preview)
WIDTH, HEIGHT = 800, 480
MARGIN = 40
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

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

# The only truly new part: hand the image to the HAT
epd = epd7in5_V2.EPD()
epd.init()
epd.display(epd.getbuffer(img))
epd.sleep()
print("On screen. E-ink keeps the image even with power off.")
