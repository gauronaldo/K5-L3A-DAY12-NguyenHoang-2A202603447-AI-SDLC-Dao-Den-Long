"""Persistent user settings (JSON in the user's data directory)."""
import json
import os

DEFAULTS = {
    "volume": 0.8,             # 0..1
    "mouse_sensitivity": 1.0,  # 0.2..3
    "colorblind": False,       # Ticket-03: "Bảng màu dễ phân biệt"
}


def data_dir():
    d = os.environ.get("DDL_HOME") or os.path.join(os.path.expanduser("~"), ".dao_den_long")
    os.makedirs(d, exist_ok=True)
    return d


class Settings(dict):
    path = None

    @classmethod
    def load(cls, path=None):
        s = cls(DEFAULTS)
        s.path = path or os.path.join(data_dir(), "settings.json")
        try:
            with open(s.path, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in DEFAULTS and type(v) is type(DEFAULTS[k]):
                    s[k] = v
                elif k in DEFAULTS and isinstance(DEFAULTS[k], float) and isinstance(v, int):
                    s[k] = float(v)
        except (OSError, ValueError):
            pass
        s.clamp()
        return s

    def clamp(self):
        self["volume"] = min(1.0, max(0.0, float(self["volume"])))
        self["mouse_sensitivity"] = min(3.0, max(0.2, float(self["mouse_sensitivity"])))

    def save(self):
        self.clamp()
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dict(self), f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)
