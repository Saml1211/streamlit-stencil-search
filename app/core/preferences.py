import json
import os
from threading import Lock

PREFERENCES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_preferences.json")

_DEFAULTS = {
    "document_search": True,
    "fts": True,
    "results_per_page": 20,
    "pagination": True,
    "ui_theme": "default",  # or "high_contrast"
    "visio_auto_refresh": False,
}

class UserPreferences:
    def __init__(self, file_path=PREFERENCES_FILE):
        self.file_path = file_path
        self._prefs = dict(_DEFAULTS)
        self._lock = Lock()
        self.load()

    def get(self, key):
        return self._prefs.get(key, _DEFAULTS.get(key))

    def set(self, key, value):
        self._prefs[key] = value

    def load(self):
        """Load preferences from disk, fallback to defaults on error/corruption/missing."""
        with self._lock:
            try:
                if not os.path.exists(self.file_path):
                    self._prefs = dict(_DEFAULTS)
                    self.save()
                    return
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Only keep known keys, fallback to defaults for missing
                    self._prefs = {k: data.get(k, v) for k, v in _DEFAULTS.items()}
            except Exception:
                self._prefs = dict(_DEFAULTS)
                self.save()

    def save(self):
        """Persist preferences to disk (atomic write)."""
        with self._lock:
            tmp_path = self.file_path + ".tmp"
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._prefs, f, indent=2)
            os.replace(tmp_path, self.file_path)

    def reset(self):
        """Wipe preferences and revert to defaults."""
        with self._lock:
            self._prefs = dict(_DEFAULTS)
            self.save()

    @staticmethod
    def defaults():
        """Expose a copy of the default preferences."""
        return dict(_DEFAULTS)