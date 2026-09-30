import time
from waveshare_epd import epd7in5_V2
from agenda import render_morning      # agenda.py, same folder
from weather import render_weather    # weather.py, same folder
from news import render_news          # news.py, same folder

PAGE_SECONDS = 15


def show(epd, img):
    """Rotate a portrait page to landscape and push it to the panel."""
    epd.display(epd.getbuffer(img.rotate(90, expand=True)))


def safe_render(name, fn):
    """Render one page; on failure log it and return None so a single
    broken fetch (dead Wi-Fi, bad calendar URL) skips that page instead
    of killing the whole loop."""
    try:
        return fn()
    except Exception as e:
        print(f"{name} failed, skipping: {e}")
        return None


def main():
    epd = epd7in5_V2.EPD()
    epd.init()      # once: init is slow, so it happens outside the loop

    pages = [
        ("agenda", render_morning),
        ("weather", render_weather),
        ("news", render_news),
    ]

    while True:
        for name, fn in pages:
            img = safe_render(name, fn)
            if img is not None:
                show(epd, img)
                time.sleep(PAGE_SECONDS)


if __name__ == "__main__":
    main()
