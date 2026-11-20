#!/usr/bin/env python3
"""Render scripted moments of the real 3D client off-screen and save PNGs as visual evidence.

    python3 tools/screenshot.py [--phase phase-2]
"""
import argparse
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("DDL_HOME", tempfile.mkdtemp())   # never touch the player's real settings

from panda3d.core import Filename, loadPrcFileData  # noqa: E402

loadPrcFileData("", "window-type offscreen\nwin-size 1280 720\naudio-library-name null\n")

from lantern.client import Game  # noqa: E402
from lantern.sim import InputState, Simulation  # noqa: E402

OFF = {"random_motes": False, "random_drifters": False, "wind_enabled": False}
# L1 low on fuel with a shade draining it, L2 healthy, L3 out (ever lit) - all in front of the camera
FUEL_SCENE = {"player": {"pos": [2, 0, 12], "carried": 6}, "random_shades": False,
              "lanterns": [{"id": "L1", "lit": True, "fuel": 22}, {"id": "L2", "pos": [8, 0, 26], "lit": True, "fuel": 80},
                           {"id": "L3", "pos": [-5, 0, 24], "ever_lit": True}],
              "shades": [{"id": "S1", "pos": [1.2, 1, 23.8], "state": "drain", "target_lantern_id": "L1"}]}


def play_scenario(g, night, scenario, script, ticks, yaw=20.0):
    g.campaign.night = night
    g.campaign.total = 0
    g.show_intro()
    g.start_night()
    g.sim = Simulation(7, scenario, night=night)
    g._build_dynamic()
    g.set_ambient(g.sim.lit_count, len(g.sim.lanterns))
    inp = InputState()
    for k in range(ticks):
        for f, v in script.get(k, {}).items():
            setattr(inp, f, v)
        g.inp = inp
        g.feed(inp)
        if g.sim.state != "playing":
            break
    g.cam_yaw = yaw


SHOTS = [
    ("01_menu", lambda g: g.show_panel("menu")),
    ("02_intro_night1", lambda g: (g.campaign.reset(), g.show_intro())),
    ("03_night1_pulse_hud", lambda g: play_scenario(
        g, 1, {"player": {"pos": [4, 0, 17], "carried": 8}, "random_motes": True,
               "lanterns": [{"id": "L1", "lit": True}, {"id": "L2", "deposited": 6}],
               "shades": [{"id": "S1", "pos": [6, 1, 14]}, {"id": "S2", "pos": [-3, 1, 9]}]},
        {0: {"move": (0.0, 1.0)}, 8: {"pulse": True}, 9: {"pulse": False, "move": (0.0, 0.0)}}, 30)),
    ("04_lantern_prompt", lambda g: play_scenario(
        g, 1, {"player": {"pos": [0, 0, 23.5], "carried": 4}, "random_shades": False,
               "lanterns": [{"id": "L1", "deposited": 3}]}, {}, 5, yaw=0.0)),
    ("05_night2_pad_drifter_charm", lambda g: play_scenario(
        g, 2, {"player": {"pos": [26, 0, 6], "carried": 7}, "random_shades": False,
               "drifters": [{"id": "D1", "pos": [30, 1.5, 9]}]}, {}, 20, yaw=60.0)),
    ("06_night3_tiers_wind", lambda g: play_scenario(
        g, 3, {"player": {"pos": [0, 0, -30]}, "random_shades": False, "random_motes": True,
               "wind_enabled": True, "time_left_s": 360}, {}, 1700, yaw=0.0)),
    ("07_offscreen_arrow", lambda g: play_scenario(
        g, 1, {"player": {"pos": [0, 0, 0]}, "random_shades": False,
               "lanterns": [{"id": "L%d" % i, "lit": True} for i in (1, 2, 4, 5)]}, {}, 3, yaw=180.0)),
    ("08_pause_menu", lambda g: (play_scenario(g, 1, {"random_shades": False}, {}, 5), g.toggle_pause())),
    ("09_settings", lambda g: g.show_panel("settings", back="pause")),
    ("10_result_lost", lambda g: (play_scenario(
        g, 1, {"player": {"flames": 1}, "random_shades": False, "shades": [{"pos": [0.5, 1, 0]}]}, {}, 3),
        g._night_finished())),
    ("11_dawn", lambda g: (setattr(g.campaign, "night", 3), setattr(g.sim, "state", "won"),
                           setattr(g.campaign, "total", 1840), g._night_finished())),
    # Phase 3 (Ticket-03)
    ("12_fuel_bars_drain", lambda g: play_scenario(g, 1, FUEL_SCENE, {}, 40, yaw=0.0)),
    ("13_colorblind", lambda g: (g.settings.__setitem__("colorblind", True),
                                 play_scenario(g, 1, FUEL_SCENE, {}, 40, yaw=0.0))),
    ("14_settings_colorblind", lambda g: (g._on_settings(), g.show_panel("settings", back="pause"))),
    ("15_result_dawn_survived", lambda g: (g.settings.__setitem__("colorblind", False), play_scenario(
        g, 1, {"random_shades": False, "time_left_s": 0.5,
               "lanterns": [{"id": "L1", "lit": True, "fuel": 70}, {"id": "L2", "lit": True}, {"id": "L3", "lit": True}]},
        {}, 40), g._night_finished())),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="phase-3")
    a = ap.parse_args()
    out = os.path.join(ROOT, "docs", "proof", a.phase, "screenshots")
    os.makedirs(out, exist_ok=True)
    g = Game(seed=7)
    for name, setup in SHOTS:
        setup(g)
        for _ in range(3):
            g._sync(0.06)
            g.graphicsEngine.renderFrame()
        path = os.path.join(out, name + ".png")
        g.win.saveScreenshot(Filename.fromOsSpecific(path))
        st = "state=%s score=%d" % (g.sim.state, g.sim.score) if g.sim else ""
        print("saved", os.path.relpath(path, ROOT), "| mode=%s %s" % (g.mode, st))


if __name__ == "__main__":
    main()
