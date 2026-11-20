"""Ticket-04 tests: bench scene + statistics, soak, leaderboard, key bindings, text size. No panda3d needed."""
import json
import math
import os
import random
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lantern import bench_scene  # noqa: E402
from lantern import config as C  # noqa: E402
from lantern.leaderboard import Leaderboard, valid_name  # noqa: E402
from lantern.settings import ACTIONS, DEFAULT_KEYS, Settings, key_conflicts  # noqa: E402
from lantern.sim import InputState, xz_dist  # noqa: E402
from lantern.soak import random_input, soak  # noqa: E402


class BenchStats(unittest.TestCase):
    def test_formulas(self):
        dts = [10.0] * 99 + [100.0]
        st = bench_scene.frame_stats(dts)
        self.assertEqual(st["frames"], 100)
        self.assertEqual(st["avg_fps"], round(1000 * 100 / 1090.0, 1))   # 1000 N / sum dt
        self.assertEqual(st["p1_low_fps"], 10.0)                          # k = ceil(1) = 1 -> 1000 / 100
        self.assertEqual(st["frame_ms_p95"], 10.0)

    def test_p1_low_uses_k_worst(self):
        dts = [5.0] * 250 + [20.0, 40.0, 60.0]       # N = 253 -> k = ceil(2.53) = 3
        self.assertEqual(bench_scene.frame_stats(dts)["p1_low_fps"], round(1000 / 40.0, 1))


class BenchScene(unittest.TestCase):
    def test_scene_contents(self):
        sim = bench_scene.bench_sim(42)
        self.assertEqual(len(sim.shades), 200)
        self.assertEqual(len(sim.motes), 100)
        self.assertTrue(all(s["state"] == "wander" for s in sim.shades))
        self.assertEqual([l["id"] for l in sim.lanterns if l["lit"]], ["L1", "L2", "L3"])
        self.assertTrue(all(l["fuel_u"] == C.FUEL_MAX_U for l in sim.lanterns if l["lit"]))
        self.assertEqual(sim.player["pos"], [0.0, 0.0, 0.0])
        for s in sim.shades:
            self.assertLessEqual(math.hypot(s["pos"][0], s["pos"][2]), bench_scene.BENCH_RADIUS)
        self.assertEqual(bench_scene.bench_scenario(42), bench_scene.bench_scenario(42))   # seed 42 deterministic

    def test_frozen_rules(self):
        sim = bench_scene.bench_sim(42)
        start = [list(s["pos"]) for s in sim.shades]
        evs = []
        for _ in range(900):
            evs += sim.step(InputState())
        self.assertEqual([e["name"] for e in evs], ["night_start"])     # no spawn, hit, pickup, end
        self.assertEqual(len(sim.shades), 200)
        self.assertEqual(len(sim.motes), 100)
        self.assertTrue(all(l["fuel_u"] == C.FUEL_MAX_U for l in sim.lanterns if l["lit"]))
        self.assertTrue(all(s["state"] == "wander" for s in sim.shades))
        self.assertEqual(sim.state, "playing")
        moved = sum(1 for s, p in zip(sim.shades, start) if xz_dist(s["pos"], p) > 0.5)
        self.assertGreater(moved, 100)                                   # shades still move by wander rules

    def test_camera_orbit(self):
        for t, exp in ((0, (30, 15, 0)), (3.75, (0, 15, 30)), (7.5, (-30, 15, 0)), (15, (30, 15, 0))):
            got = bench_scene.camera_pose(t)
            for a, b in zip(got, exp):
                self.assertAlmostEqual(a, b, places=6)


class Soak(unittest.TestCase):
    def test_short_soak(self):
        out = soak(7, 3)
        self.assertEqual(out["nights"], 3)
        self.assertEqual(out["crashes"], 0)
        self.assertEqual(len(out["results"]), 3)
        self.assertEqual(out["seeds"], [8, 9, 10])
        self.assertLessEqual(out["mem_end_mb"], 1.2 * out["mem_start_mb"])

    def test_input_probabilities(self):
        rng, st, n = random.Random(1), {"move": (0, 0)}, 60000
        counts = {"jump": 0, "dash": 0, "pulse": 0, "interact": 0}
        moves = set()
        for k in range(n):
            i = random_input(rng, k, st)
            for b in counts:
                counts[b] += getattr(i, b)
            moves.add(i.move)
        for b, p in (("jump", 0.05), ("dash", 0.03), ("pulse", 0.02), ("interact", 0.10)):
            self.assertAlmostEqual(counts[b] / n, p, delta=0.005, msg=b)
        self.assertEqual(len(moves), n // 30)                            # direction changes every 30 ticks


class LeaderboardTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "lb.json")

    def test_names(self):
        for ok in ("Moi", "may_123", "abcdefghijkl", "Mây_Nhỏ"):
            self.assertTrue(valid_name(ok), ok)
        for bad in ("ab", "abcdefghijklm", "a b c", "x-y-z", ""):
            self.assertFalse(valid_name(bad), bad)

    def test_top10_order_tie_and_persistence(self):
        lb = Leaderboard(self.path)
        for i in range(12):
            lb.add("p%02d" % i, 100 * (i % 4), i % 4, 7, achieved_at="2026-11-20T10:%02d:00+07:00" % i)
        lb.add("late", 300, 3, 7, achieved_at="2026-11-20T11:00:00+07:00")
        lb.add("early", 300, 3, 7, achieved_at="2026-11-20T09:00:00+07:00")
        lb2 = Leaderboard(self.path)                                     # reload from disk
        names = [e["name"] for e in lb2.public()]
        self.assertEqual(len(names), 10)
        self.assertEqual(names[:5], ["early", "p03", "p07", "p11", "late"])
        scores = [e["score"] for e in lb2.public()]
        self.assertEqual(scores, sorted(scores, reverse=True))
        out = os.path.join(tempfile.mkdtemp(), "out.json")
        lb2.export(out)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual([e["name"] for e in data["entries"]], names)
        self.assertEqual(set(data["entries"][0]), {"name", "score", "nights_won", "achieved_at", "seed"})
        self.assertRegex(data["entries"][0]["achieved_at"], r"[+-]\d\d:\d\d$")   # ISO 8601 with time zone

    def test_rejects_invalid(self):
        lb = Leaderboard(self.path)
        with self.assertRaises(ValueError):
            lb.add("x", 10, 1, 7)
        with self.assertRaises(ValueError):
            lb.add("valid", 10, 4, 7)


class Keybinds(unittest.TestCase):
    def test_defaults_conflicts_persist(self):
        path = os.path.join(tempfile.mkdtemp(), "settings.json")
        s = Settings.load(path)
        self.assertEqual(s["keys"], DEFAULT_KEYS)
        self.assertEqual(set(ACTIONS), set(DEFAULT_KEYS))
        self.assertEqual(key_conflicts(s["keys"]), {})
        s["keys"]["jump"] = "e"
        self.assertEqual(key_conflicts(s["keys"]), {"e": ["jump", "interact"]})
        s["keys"]["jump"] = "j"
        s.save()
        self.assertEqual(Settings.load(path)["keys"]["jump"], "j")
        s.reset_keys()
        self.assertEqual(s["keys"], DEFAULT_KEYS)

    def test_accessibility_flags_default_off(self):
        s = Settings.load(os.path.join(tempfile.mkdtemp(), "s.json"))
        self.assertFalse(s["reduce_motion"])
        self.assertFalse(s["large_text"])


class TextSize(unittest.TestCase):
    def test_no_ui_text_below_18px(self):
        """aspect2d spans 720 px over 2 units -> 18 px = scale 0.05. Every text()/_btn() scale must be >= 0.05."""
        with open(os.path.join(ROOT, "lantern", "client.py"), encoding="utf-8") as f:
            src = f.read()
        small = [m.group(0) for m in re.finditer(r"scale=(0\.0[0-4]\d*)\b", src)]
        self.assertEqual(small, [])


if __name__ == "__main__":
    unittest.main()
