"""Local leaderboard (Ticket-04 section 3): top 10, score desc then earliest first, stored as JSON."""
import datetime
import json
import os
import re

from .settings import data_dir

MAX_ENTRIES = 10
NAME_RE = re.compile(r"^\w{3,12}$", re.UNICODE)   # [A-Za-z0-9_] plus Vietnamese letters (bonus)


def valid_name(name):
    name = (name or "").strip()
    return bool(NAME_RE.match(name)) and "\n" not in name


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _sort_key(e):
    t = datetime.datetime.fromisoformat(e["achieved_at"])
    return (-e["score"], t.timestamp(), e.get("_order", 0))


class Leaderboard:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "leaderboard.json")
        self.entries = []
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            for i, e in enumerate(data.get("entries", [])):
                if valid_name(e.get("name")) and isinstance(e.get("score"), int):
                    e["_order"] = i
                    self.entries.append(e)
        except (OSError, ValueError):
            pass
        self.entries.sort(key=_sort_key)

    def add(self, name, score, nights_won, seed, achieved_at=None):
        name = (name or "").strip()
        if not valid_name(name):
            raise ValueError("name must be 3-12 letters, digits or _")
        if not 0 <= int(nights_won) <= 3:
            raise ValueError("nights_won must be 0..3")
        e = {"name": name, "score": int(score), "nights_won": int(nights_won),
             "achieved_at": achieved_at or now_iso(), "seed": int(seed),
             "_order": max([x.get("_order", 0) for x in self.entries] + [0]) + 1}
        self.entries.append(e)
        self.entries.sort(key=_sort_key)
        del self.entries[MAX_ENTRIES:]
        self.save()
        return e in self.entries

    def public(self):
        return [{k: v for k, v in e.items() if not k.startswith("_")} for e in self.entries]

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"entries": self.public()}, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def export(self, out_path):
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"entries": self.public()}, f, indent=2, ensure_ascii=False)
