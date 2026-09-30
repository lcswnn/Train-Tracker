"""Screen base class, registry, and shared e-ink drawing helpers.

A screen is a focused page: it declares which providers it needs and
renders a full-frame 1-bit image from their data. Register with @register.

Design rules (NASA instrument x editorial):
- 1-bit black on white. No gray, no gradients.
- Huge numbers for the one thing that matters; small caps labels.
- Thin rules (2px) to separate zones; whitespace does the rest.
- Every helper measures real ink boxes so stacked lines never collide.
"""
from PIL import Image, ImageDraw, ImageFont

import config

W, H = config.WIDTH, config.HEIGHT
MARGIN = 48

SCREENS = {}


def register(cls):
    SCREENS[cls.name] = cls()
    return cls


class Screen:
    name = "base"
    dwell = 40          # seconds this screen stays up in the rotation
    providers = ()      # provider names main.py should gather for render()

    def render(self, data):
        """data: {provider_name: provider.get() result or None}."""
        raise NotImplementedError


def font(size, bold=False):
    return ImageFont.truetype(config.FONT_BOLD if bold else config.FONT_PATH,
                              size)


def blank():
    img = Image.new("1", (W, H), 1)
    return img, ImageDraw.Draw(img)


def ink(draw, xy, text, fnt):
    """Draw with the ink-top at xy; return the ink-bottom y."""
    l, t, r, b = draw.textbbox((0, 0), text, font=fnt)
    draw.text((xy[0] - l, xy[1] - t), text, font=fnt, fill=0)
    return xy[1] + (b - t)


def centered(draw, cx, y, text, fnt):
    l, t, r, b = draw.textbbox((0, 0), text, font=fnt)
    x = cx - (r - l) / 2 - l
    draw.text((x, y - t), text, font=fnt, fill=0)
    return y + (b - t)


def label(draw, x, y, text):
    """Small section label, e.g. DEPARTURE."""
    return ink(draw, (x, y), text, font(20))


def rule(draw, y, x0=MARGIN, x1=None):
    draw.line([(x0, y), (x1 or W - MARGIN, y)], fill=0, width=2)


def wrap(draw, text, fnt, max_width):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= max_width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def unavailable(draw, what):
    """Standard 'data unavailable' state. Screens call this when a
    provider returned None (no cache + fetch failed)."""
    centered(draw, W // 2, H // 2 - 30, what, font(28, bold=True))
    centered(draw, W // 2, H // 2 + 20, "data unavailable", font(22))
