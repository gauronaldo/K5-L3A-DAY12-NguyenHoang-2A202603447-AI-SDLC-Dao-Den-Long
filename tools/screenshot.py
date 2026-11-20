#!/usr/bin/env python3
"""Render scripted moments of the real 3D client off-screen and save PNGs as visual evidence.

    python3 tools/screenshot.py [--phase phase-1]
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from panda3d.core import Filename, loadPrcFileData  # noqa: E402

loadPrcFileData("", "window-type offscreen\nwin-size 1280 720\nframebuffer-multisample 1\nmultisamples 4\n"
                    "audio-library-name null\n")

from lantern.client import LanternGame  # noqa: E402
from lantern.sim import InputState, Simulation  # noqa: E402

SHOTS = [
    ("01_title", 7, None, []),
    ("02_gameplay_pulse", 7,
     {"player": {"pos": [4, 0, 17], "carried": 6},
      "lanterns": [{"id": "L1", "lit": True, "deposited": 5}, {"id": "L2", "deposited": 3}],
      "shades": [{"id": "S1", "pos": [6, 1, 15]}, {"id": "S2", "pos": [-3, 1, 10]}]},
     [(0, {"move": (0.0, 1.0)}), (8, {"pulse": True}), (9, {"pulse": False, "move": (0.0, 0.0)})]),
    ("03_deposit_lantern", 7,
     {"player": {"pos": [0, 0, 23], "carried": 5}, "random_shades": False, "shades": [],
      "lanterns": [{"id": "L1", "deposited": 0}]},
     [(0, {"interact": True}), (1, {"interact": False})]),
    ("04_win", 7,
     {"player": {"pos": [0, 0, 23], "carried": 1}, "random_shades": False, "shades": [],
      "lanterns": [{"id": "L1", "deposited": 4}, {"id": "L2", "lit": True}, {"id": "L3", "lit": True},
                   {"id": "L4", "lit": True}, {"id": "L5", "lit": True}]},
     [(0, {"interact": True})]),
    ("05_lose_hit", 7,
     {"player": {"flames": 1, "carried": 4}, "random_shades": False, "shades": [{"pos": [2.0, 1, 0]}]},
     []),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="phase-1")
    a = ap.parse_args()
    out = os.path.join(ROOT, "docs", "proof", a.phase, "screenshots")
    os.makedirs(out, exist_ok=True)
    game = None
    for name, seed, scenario, script in SHOTS:
        if game is None:
            game = LanternGame(seed=seed, scenario=scenario)
        else:
            game.fixed_seed, game.scenario = seed, scenario
            game.new_game()
        if name != "01_title":
            game.start_play()
            game.running = False   # drive the simulation manually below
            inp = InputState()
            changes = dict(script)
            for k in range(30):
                for f, v in changes.get(k, {}).items():
                    setattr(inp, f, v)
                game.inp = inp
                game.feed(inp)
                if game.sim.state != "playing":
                    break
            game.cam_yaw = 20.0
        for _ in range(3):
            game._sync(0.06)
            game.graphicsEngine.renderFrame()
        path = os.path.join(out, name + ".png")
        game.win.saveScreenshot(Filename.fromOsSpecific(path))
        print("saved", os.path.relpath(path, ROOT), "| state=%s score=%d" % (game.sim.state, game.sim.score))


if __name__ == "__main__":
    main()
