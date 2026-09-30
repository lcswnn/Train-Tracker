"""Mission Control configuration. Every knob lives here.

Nothing outside this file needs to know your station, walk time, or keys.
"""
import os

# --- Display ---
# Landscape per the mission-control spec. For a portrait 8x10 frame,
# swap to WIDTH, HEIGHT = 480, 800. Screens read these at render time.
WIDTH, HEIGHT = 800, 480
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

TIMEZONE = "America/Chicago"
HOME_LAT, HOME_LON = 41.8800, -87.6275   # Chicago, near Division Blue Line

# --- Commute ---
STATION_NAME = "Division"
CTA_MAPID = "40320"          # Division/Milwaukee, Blue Line
CTA_ROUTE = "Blue"
WALK_MINUTES = 10            # door to platform: time it once, set it here
BUFFER_MINUTES = 3           # platform buffer before the train leaves
# Empty = mock departures (deterministic, for UI testing).
# Set the real key via environment: export CTA_API_KEY="..."
CTA_API_KEY = os.environ.get("CTA_API_KEY", "")

# --- Rotation: (screen name, dwell seconds) ---
ROTATION = [
    ("departure", 60),
    ("conditions", 40),
    ("space", 40),
]
# During these hours (24h) the departure screen appears twice per cycle.
MORNING_HOURS = (6, 9)

# --- Caching: seconds a provider result stays fresh ---
CACHE_DIR = os.path.expanduser("~/.cache/mission-control")
CACHE_TTLS = {
    "weather": 900,    # 15 min
    "space": 120,      # ISS moves fast; 2 min
    "cta": 60,         # departures; 1 min
}
