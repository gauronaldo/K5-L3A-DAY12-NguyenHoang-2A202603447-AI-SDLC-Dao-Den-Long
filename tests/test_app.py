"""Tests for the non-rendering parts of the client (settings, campaign, audio assets). No panda3d needed."""
import os
import sys
import tempfile
import unittest
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lantern import config as C  # noqa: E402
from lantern.campaign import Campaign  # noqa: E402
from lantern.settings import Settings  # noqa: E402

# Ticket-02 F6: music + effects for these moments
REQUIRED_SOUNDS = ["music", "pickup", "lantern_lit", "pulse", "hit", "jump", "dash", "win", "lose",
                   "shade_spawn", "countdown", "wind"]


class SettingsTest(unittest.TestCase):
    def test_roundtrip_and_clamp(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "settings.json")
        s = Settings.load(path)
        self.assertEqual(s["volume"], 0.8)
        s["volume"], s["mouse_sensitivity"] = 0.35, 9.0
        s.save()
        s2 = Settings.load(path)
        self.assertEqual(s2["volume"], 0.35)
        self.assertEqual(s2["mouse_sensitivity"], 3.0)   # clamped

    def test_colorblind_persisted(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "settings.json")
        s = Settings.load(path)
        self.assertFalse(s["colorblind"])
        s["colorblind"] = True
        s.save()
        self.assertTrue(Settings.load(path)["colorblind"])

    def test_corrupt_file_falls_back_to_defaults(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "settings.json")
        with open(path, "w") as f:
            f.write("{oops")
        self.assertEqual(Settings.load(path)["mouse_sensitivity"], 1.0)


class CampaignTest(unittest.TestCase):
    def test_three_nights_dawn_and_total(self):
        c = Campaign()
        self.assertEqual(c.intro()[0], "Đảo Bến")
        self.assertIn("Ông Đăng", c.intro()[1])
        self.assertEqual(c.night_over("lost", 120), "retry")   # lost night: replay it, score not counted
        self.assertEqual(c.night, 1)
        self.assertEqual(c.night_over("won", 500), "next")
        c.advance()
        self.assertEqual(c.intro()[0], "Đảo Cau")
        self.assertEqual(c.night_over("won", 400), "next")
        c.advance()
        self.assertEqual(c.night_over("won", 300), "dawn")
        self.assertEqual(c.total, 1200)
        self.assertEqual(c.nights_won, 3)


class AudioAssets(unittest.TestCase):
    def test_all_sounds_exist_and_are_valid_wav(self):
        for name in REQUIRED_SOUNDS:
            path = os.path.join(ROOT, "assets", "sounds", name + ".wav")
            self.assertTrue(os.path.exists(path), name)
            with wave.open(path) as w:
                self.assertGreater(w.getnframes(), 100)

    def test_client_maps_events_to_sounds(self):
        with open(os.path.join(ROOT, "lantern", "client.py"), encoding="utf-8") as f:
            src = f.read()
        for name in REQUIRED_SOUNDS[1:]:
            self.assertIn('"%s"' % name, src, name)


class Palette(unittest.TestCase):
    def test_client_uses_palette_keys(self):
        with open(os.path.join(ROOT, "lantern", "client.py"), encoding="utf-8") as f:
            src = f.read()
        for key in ("sky", "fog", "grass", "sand", "wood", "cloud_sea", "lantern_lit", "lantern_core", "lantern_off",
                    "mote_core", "mote_glow", "shade_body", "shade_rim", "shade_stunned", "may_cloak", "may_scarf",
                    "charm", "drifter", "gold", "ui_danger", "ui_text"):
            self.assertIn(key, C.PALETTE)
            self.assertTrue('"%s"' % key in src or key.upper() in src, key)


if __name__ == "__main__":
    unittest.main()
