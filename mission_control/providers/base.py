"""Provider base class: fetch with file cache and graceful degradation.

Contract: Provider.get() returns
    {"data": <dict>, "age": <seconds since fetch>, "stale": <bool>}
or None if there is no data at all (first run + network down).
Screens must handle None by rendering a "data unavailable" state,
never by crashing.
"""
import json
import os
import time

import config


class Provider:
    name = "base"

    def fetch(self):
        """Hit the source. Return a JSON-serializable dict. May raise."""
        raise NotImplementedError

    def _cache_path(self):
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        return os.path.join(config.CACHE_DIR, f"{self.name}.json")

    def get(self):
        ttl = config.CACHE_TTLS.get(self.name, 300)
        path = self._cache_path()
        cached = None
        if os.path.exists(path):
            try:
                with open(path) as f:
                    cached = json.load(f)
            except Exception:
                cached = None

        if cached and time.time() - cached["ts"] < ttl:
            return {"data": cached["data"],
                    "age": time.time() - cached["ts"], "stale": False}
        try:
            data = self.fetch()
            with open(path, "w") as f:
                json.dump({"ts": time.time(), "data": data}, f)
            return {"data": data, "age": 0, "stale": False}
        except Exception as e:
            print(f"[{self.name}] fetch failed: {e}")
            if cached:
                print(f"[{self.name}] using stale cache "
                      f"({(time.time() - cached['ts']) / 60:.0f} min old)")
                return {"data": cached["data"],
                        "age": time.time() - cached["ts"], "stale": True}
            return None
