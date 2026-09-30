# Mission Control

A quiet, always-on personal mission control: Raspberry Pi + e-ink,
NASA instrument panel × minimalist editorial design.

## Layout

```
mission-control/
  config.py                 # every knob: station, walk time, keys, rotation
  main.py                   # rotation loop; --preview renders PNGs on a Mac
  mission-control.service   # systemd unit: launch on boot
  providers/                # data sources (each cached, each fallible-safe)
    base.py                 # fetch-with-cache + stale fallback
    cta.py                  # departures; mock mode until CTA_API_KEY is set
    weather.py              # Open-Meteo, no key
    space.py                # ISS live position + locally computed Moon phase
  screens/                  # one focused page each
    base.py                 # Screen class, @register, drawing helpers
    icons.py                # 1-bit weather icons
    departure.py            # WHEN DO I NEED TO LEAVE?
    conditions.py           # minimalist weather + one strong advice line
    space.py                # ISS distance, drawn Moon, sunrise/sunset
```

## The pattern for adding a screen

1. Write a provider in `providers/` (subclass `Provider`, implement `fetch()`).
2. Write a screen in `screens/` (subclass `Screen`, `@register`, set
   `name` / `dwell` / `providers`, implement `render(data)`).
3. Add it to `ROTATION` in `config.py`.

Existing modules that map to future screens: `agenda.py` → TODAY,
`curiosity.py` → CURIOSITY, `news.py` → WORLD.

## On the Mac

```bash
python3 main.py --preview            # renders previews/departure.png etc.
python3 main.py --preview --screen space
```

## On the Pi

```bash
# copy the whole folder
scp -r mission-control lucaswaunn@frame.local:~/
ssh lucaswaunn@frame.local
cd ~/mission-control
python3 main.py                      # test the rotation

# launch on boot
sudo cp mission-control.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mission-control
```

Set your real walk time in `config.py` (`WALK_MINUTES`) — time the
door-to-platform walk once. When the CTA key arrives, add it as
`Environment=CTA_API_KEY=...` in the service file and
`sudo systemctl restart mission-control`.
