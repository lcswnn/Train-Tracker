"""Phone control UI for Mission Control.

A tiny Flask server running in a background thread inside main.py's
process. From your phone (same home WiFi): http://frame.local:5000 --
then Share > Add to Home Screen for an app icon. The JSON endpoints
are also iOS-Shortcuts friendly.

How it works: the web UI writes commands into a thread-safe
Controller; the main loop in main.py checks it every few seconds.
No polling from the Pi side, no second process to supervise.

Controls:
  - Tap a screen to PIN it: the frame stays on that screen until you
    pick another one (or resume rotation). The choice survives
    restarts -- it's saved to a small state file.
  - Resume rotation: back to the daypart digest.
  - Refresh now (re-renders the current screen immediately)
  - Pause / resume (freeze the frame for the night)
"""
import json
import os
import threading

import config
from screens.base import SCREENS

STATE_FILE = os.path.join(config.CACHE_DIR, "frame_state.json")


class Controller:
    """Thread-safe command box between the web UI and the main loop."""

    def __init__(self):
        self._lock = threading.Lock()
        self.paused = False
        self._forced = None    # one-shot: render this screen next
        self.current = None    # last screen actually displayed
        self._sticky = None    # pinned screen; None = follow the digest
        self._rev = 0          # bumped on every sticky change
        self._load_state()

    # ---- persistence ------------------------------------------
    def _load_state(self):
        try:
            with open(STATE_FILE) as f:
                name = json.load(f).get("sticky")
            if name in SCREENS:
                self._sticky = name
                print(f"[control] restored pinned screen: {name}")
        except Exception:
            pass

    def _save_state(self):
        try:
            os.makedirs(config.CACHE_DIR, exist_ok=True)
            with open(STATE_FILE, "w") as f:
                json.dump({"sticky": self._sticky}, f)
        except Exception as e:
            print(f"[control] could not save state: {e}")

    # ---- sticky selection -------------------------------------
    def set_sticky(self, name):
        """Pin a screen (or None to resume the digest)."""
        with self._lock:
            if name is not None and name not in SCREENS:
                return False
            if name != self._sticky:
                self._sticky = name
                self._rev += 1
                self._save_state()
            return True

    def get_sticky(self):
        with self._lock:
            return self._sticky

    @property
    def rev(self):
        with self._lock:
            return self._rev

    # ---- one-shot overrides (refresh, frozen branch) -----------
    def force(self, name):
        """Queue a one-shot screen override. Returns False if unknown."""
        with self._lock:
            if name in SCREENS:
                self._forced = name
                return True
            return False

    def take_forced(self):
        with self._lock:
            name, self._forced = self._forced, None
            return name

    def has_pending(self):
        with self._lock:
            return self._forced is not None

    def set_paused(self, paused):
        with self._lock:
            self.paused = paused

    def set_current(self, name):
        with self._lock:
            self.current = name

    def status(self, daypart):
        with self._lock:
            return {
                "paused": self.paused,
                "daypart": daypart,
                "current": self.current,
                "sticky": self._sticky,
                "screens": sorted(SCREENS),
            }


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Mission Ctrl">
<title>Mission Control</title>
<style>
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body { background: #0a0a0a; color: #f2f2f2; font-family: -apple-system,
         Helvetica, Arial, sans-serif; margin: 0; padding: 24px 20px 40px; }
  h1 { font-size: 15px; letter-spacing: 4px; font-weight: 700; margin: 0 0 4px; }
  #status { color: #8a8a8a; font-size: 13px; margin-bottom: 28px;
            letter-spacing: 1px; min-height: 20px; }
  .grid { display: grid; gap: 14px; margin-bottom: 28px; }
  button { font-size: 19px; font-weight: 600; padding: 22px 16px;
           border-radius: 14px; border: 1px solid #2c2c2c; background: #161616;
           color: #f2f2f2; cursor: pointer; width: 100%; }
  button:active { background: #2a2a2a; transform: scale(0.98); }
  button.pinned { border-color: #f2f2f2; }
  button.wide { border-color: #3d3d3d; }
  button.accent { background: #f2f2f2; color: #0a0a0a; border: none; }
  button.accent:active { background: #cfcfcf; }
  .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  #note { margin-top: 24px; font-size: 12px; color: #5c5c5c; line-height: 1.6; }
</style>
</head>
<body>
  <h1>MISSION CONTROL</h1>
  <div id="status">connecting&hellip;</div>
  <div class="grid" id="screens"></div>
  <div class="grid">
    <button id="rotation" class="wide">&#8635;&nbsp; Resume rotation</button>
  </div>
  <div class="grid">
    <button id="refresh" class="wide accent">&#8635;&nbsp; Refresh now</button>
  </div>
  <div class="row2">
    <button id="pause" class="wide">&#10074;&#10074;&nbsp; Pause</button>
    <button id="resume" class="wide">&#9654;&nbsp; Resume</button>
  </div>
  <div id="note">Tapping a screen <b>pins</b> it &mdash; the frame stays
  there until you pick another screen or resume rotation. Your pick is
  remembered across restarts. Pause freezes the frame until you
  resume. Same WiFi only: <b>frame.local:5000</b>.</div>
<script>
async function api(path, method) {
  const r = await fetch(path, {method: method || 'GET'});
  return r.json();
}
async function refreshStatus() {
  try {
    const s = await api('/api/status');
    const el = document.getElementById('status');
    el.textContent = s.sticky ? 'PINNED \\u00b7 ' + s.sticky.toUpperCase()
      : (s.paused ? 'PAUSED' : s.daypart) +
        (s.current ? '  \\u00b7  ' + s.current.toUpperCase() : '');
    const grid = document.getElementById('screens');
    if (!grid.children.length) {
      s.screens.forEach(function(name) {
        const b = document.createElement('button');
        b.textContent = name.toUpperCase();
        b.id = 'screen-' + name;
        b.onclick = async function() {
          await api('/api/screen/' + name, 'POST');
          refreshStatus();
        };
        grid.appendChild(b);
      });
    }
    s.screens.forEach(function(name) {
      const b = document.getElementById('screen-' + name);
      if (b) b.classList.toggle('pinned', s.sticky === name);
    });
  } catch (e) {
    document.getElementById('status').textContent = 'unreachable \\u2014 is the Pi on?';
  }
}
document.getElementById('rotation').onclick = async function() {
  await api('/api/rotation', 'POST'); refreshStatus();
};
document.getElementById('refresh').onclick = async function() {
  await api('/api/refresh', 'POST'); refreshStatus();
};
document.getElementById('pause').onclick = async function() {
  await api('/api/pause', 'POST'); refreshStatus();
};
document.getElementById('resume').onclick = async function() {
  await api('/api/resume', 'POST'); refreshStatus();
};
refreshStatus();
setInterval(refreshStatus, 10000);
</script>
</body>
</html>
"""


def create_app(controller, daypart_fn):
    from flask import Flask, jsonify, Response
    app = Flask(__name__)

    @app.get("/")
    def index():
        return Response(PAGE, mimetype="text/html")

    @app.get("/api/status")
    def status():
        return jsonify(controller.status(daypart_fn()))

    @app.post("/api/screen/<name>")
    def pin_screen(name):
        ok = controller.set_sticky(name)
        return jsonify({"ok": ok}), (200 if ok else 404)

    @app.post("/api/rotation")
    def resume_rotation():
        controller.set_sticky(None)
        return jsonify({"ok": True})

    @app.post("/api/refresh")
    def refresh():
        # Re-render whatever is showing right now, immediately.
        controller.set_paused(False)
        if controller.current:
            controller.force(controller.current)
        return jsonify({"ok": True})

    @app.post("/api/pause")
    def pause():
        controller.set_paused(True)
        return jsonify({"ok": True})

    @app.post("/api/resume")
    def resume():
        controller.set_paused(False)
        controller.take_forced()  # clear any queued override
        return jsonify({"ok": True})

    return app


def start(controller, daypart_fn, port=config.CONTROL_PORT):
    """Launch the control server in a daemon thread. Returns the thread."""
    app = create_app(controller, daypart_fn)
    t = threading.Thread(
        target=app.run,
        kwargs={"host": "0.0.0.0", "port": port,
                "threaded": True, "use_reloader": False},
        daemon=True, name="control-ui")
    t.start()
    print(f"Control UI on http://frame.local:{port}")
    return t
