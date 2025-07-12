import os
import json


class Stats:
    def __init__(self, filename="stats.json"):
        self.stats_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), filename
        )
        self._load()

    def _load(self):
        try:
            with open(self.stats_path, "r") as f:
                self.stats = json.load(f)
        except Exception:
            self.stats = {}

    def save(self):
        with open(self.stats_path, "w") as f:
            json.dump(self.stats, f)

    def inc(self, key, value=1):
        self.stats[key] = self.stats.get(key, 0) + value
        self.save()

    def get(self, key, default=0):
        return self.stats.get(key, default)
