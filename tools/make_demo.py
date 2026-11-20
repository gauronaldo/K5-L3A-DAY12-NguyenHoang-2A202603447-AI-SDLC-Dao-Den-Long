#!/usr/bin/env python3
"""Render the demo video off-screen from the real client (autopilot gameplay + menus + evidence cards).

    python3 -m pip install imageio-ffmpeg && python3 tools/make_demo.py --out docs/demo/demo.mp4

Evidence cards show real outputs captured when the video is made (verify.py, bench.json, soak.json, git).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["DDL_HOME"] = tempfile.mkdtemp()

from panda3d.core import loadPrcFileData  # noqa: E402

W, H, FPS = 1280, 720, 30
loadPrcFileData("", "window-type offscreen\nwin-size %d %d\naudio-library-name null\n" % (W, H))

from direct.gui.DirectGui import DirectFrame  # noqa: E402
from panda3d.core import TextNode  # noqa: E402

from lantern import config as C  # noqa: E402
from lantern.client import Autopilot, Game, P  # noqa: E402
from lantern.sim import InputState, Simulation  # noqa: E402


class Recorder:
    def __init__(self, g, out):
        import imageio_ffmpeg
        self.g = g
        self.frames = 0
        self.proc = subprocess.Popen(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-", "-vf", "vflip", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "26", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)

    def frame(self, dt=1.0 / FPS):
        g = self.g
        g._sync(dt)
        g.graphicsEngine.renderFrame()
        tex = g.win.getScreenshot()
        self.proc.stdin.write(bytes(tex.getRamImageAs("RGB")))
        self.frames += 1

    def hold(self, seconds):
        for _ in range(int(seconds * FPS)):
            self.frame()

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


class Card:
    """Full-screen text card for captions and evidence."""

    def __init__(self, g):
        self.g = g
        self.frame = DirectFrame(parent=g.aspect2d, frameColor=(0.03, 0.04, 0.1, 0.96), frameSize=(-2, 2, -1, 1))
        self.title = g.text("", parent=self.frame, pos=(0, 0.78), scale=0.09, fg=C.hex_rgb("#F2C14E"))
        self.body = g.text("", parent=self.frame, pos=(-1.6, 0.62), scale=0.042, align=TextNode.ALeft)
        self.frame.hide()

    def show(self, title, body):
        self.g.set_text(self.title, title)
        self.g.set_text(self.body, body)
        self.frame.show()

    def hide(self):
        self.frame.hide()


class Caption:
    def __init__(self, g):
        self.node = g.text("", parent=g.a2dTopCenter, pos=(0, -0.24), scale=0.055, bg=(0, 0, 0, 0.6))
        self.g = g

    def set(self, s):
        self.g.set_text(self.node, s)


def play(rec, g, night, seconds, scenario=None, seed=11, yaw=None, caption=None, cap=None):
    g.campaign.night = night
    g.show_intro()
    g.start_night()
    if scenario is not None:
        g.sim = Simulation(seed, scenario, night=night)
        g._build_dynamic()
        g.set_ambient(g.sim.lit_count, len(g.sim.lanterns))
    bot = Autopilot(seed)
    if cap:
        cap.set(caption or "")
    for _ in range(int(seconds * FPS)):
        for _ in range(2):                        # 60 Hz logic, 30 fps video
            if g.sim.state == "playing":
                g.feed(bot(g.sim))
        if yaw is None:                           # follow the bot's facing smoothly
            fx, fz = g.sim.player["facing"]
            import math
            target = math.degrees(math.atan2(fx, fz))
            diff = (target - g.cam_yaw + 180) % 360 - 180
            g.cam_yaw += diff * 0.04
        else:
            g.cam_yaw = yaw
        rec.frame()
    if cap:
        cap.set("")


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "demo", "demo.mp4"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)

    verify = run([sys.executable, os.path.join(ROOT, "tools", "verify.py"), "--phase", "phase-4"])
    bench = json.load(open(os.path.join(ROOT, "docs", "proof", "phase-4", "bench.json"), encoding="utf-8"))
    soak = json.load(open(os.path.join(ROOT, "docs", "proof", "phase-4", "soak.json"), encoding="utf-8"))
    gitlog = run(["git", "log", "--oneline", "-14"])
    tags = run(["git", "tag", "--list"])

    g = Game(seed=11)
    rec = Recorder(g, a.out)
    card, cap = Card(g), Caption(g)

    card.show("Đảo Đèn Lồng — demo v1.0.0",
              "Nguyễn Hoàng · 2A202603447 · Day 12 AI SDLC\n\n"
              "Nội dung: menu → Đêm 1, 2, 3 → dầu đèn & Bóng Mực hút dầu → hỗ trợ tiếp cận\n"
              "→ bảng xếp hạng → bằng chứng: test + scenario, bench, soak, git tags.")
    rec.hold(6)
    card.hide()
    g.show_panel("menu")
    rec.hold(3)
    g.campaign.reset()
    g.show_intro()
    rec.hold(4)

    play(rec, g, 1, 40, cap=cap, caption="Đêm 1 — gom đom đóm, thắp đèn (autopilot)")
    play(rec, g, 1, 12, cap=cap, seed=5, caption="Tỏa Sáng: choáng + đẩy lùi Bóng Mực", yaw=None, scenario={
        "player": {"carried": 12, "successful_lights": 1}, "random_motes": True,
        "shades": [{"pos": [6, 1, 6]}, {"pos": [-7, 1, 5]}, {"pos": [3, 1, -8]}]})
    play(rec, g, 2, 18, cap=cap, caption="Đêm 2 — Đảo Cau: cầu tre, bục nhảy, Gió Lạc, Bùa Gió", scenario={
        "player": {"pos": [16, 0, 15]}, "random_motes": True}, seed=8)
    play(rec, g, 3, 18, cap=cap, caption="Đêm 3 — Đảo Chuông: tầng, dốc, tháp chuông, gió mạnh", scenario={
        "random_motes": True, "time_left_s": 300}, seed=9)
    fuel = {"player": {"pos": [2, 0, 12], "carried": 6}, "random_shades": False,
            "lanterns": [{"id": "L1", "lit": True, "fuel": 22}, {"id": "L2", "pos": [8, 0, 26], "lit": True, "fuel": 80},
                         {"id": "L3", "pos": [-5, 0, 24], "ever_lit": True}],
            "shades": [{"id": "S1", "pos": [1.2, 1, 23.8], "state": "drain", "target_lantern_id": "L1"}]}
    g.campaign.night = 1
    g.show_intro()
    g.start_night()
    g.sim = Simulation(7, fuel, night=1)
    g._build_dynamic()
    g.cam_yaw = 0.0
    cap.set("Ticket-03: thanh dầu, đèn yếu nhấp nháy 1 Hz, Bóng Mực hút dầu")
    for _ in range(5 * FPS):
        g.feed(InputState())
        g.feed(InputState())
        rec.frame()
    g.settings["colorblind"] = True
    cap.set("Bảng màu dễ phân biệt: viền #00B3FF, cảnh báo trắng + ⚠, đèn tắt xẹp + rách")
    for _ in range(5 * FPS):
        g.feed(InputState())
        g.feed(InputState())
        rec.frame()
    g.settings["colorblind"] = False
    cap.set("")
    g.toggle_pause()
    rec.hold(2.5)
    g.show_panel("settings", back="pause")
    rec.hold(3)
    g.show_panel("keys")
    rec.hold(3)
    g.to_menu()
    for name, score, won, t in (("Mây_Nhỏ", 1265, 2, "2026-11-20T20:10:00+07:00"), ("ongdang", 1840, 3, "2026-11-20T19:00:00+07:00"),
                                ("lantern_1", 640, 1, "2026-11-20T18:30:00+07:00")):
        g.leaderboard.add(name, score, won, 11, achieved_at=t)
    g.show_leaderboard()
    rec.hold(3.5)
    g.show_panel(None)

    lines = [l for l in verify.splitlines() if l.strip()][-30:]
    card.show("Bằng chứng 1/3 — python3 tools/verify.py --phase phase-4", "\n".join(lines))
    rec.hold(9)
    card.show("Bằng chứng 2/3 — bench.json & soak.json (chạy thật)",
              "python3 main.py --bench --seed 42 --duration 30 --out bench.json\n" +
              json.dumps({k: bench[k] for k in ("avg_fps", "p1_low_fps", "frame_ms_p95", "frames", "load_ms",
                                                "peak_mem_mb", "vsync_off", "renderer", "os")}, indent=1, ensure_ascii=False) +
              "\n\npython3 soak.py --seed 7 --nights 10 --out soak.json\n" +
              json.dumps({k: soak[k] for k in ("nights", "crashes", "mem_start_mb", "mem_end_mb", "duration_s")},
                         ensure_ascii=False))
    rec.hold(9)
    card.show("Bằng chứng 3/3 — git log & tags", "git tag --list\n" + tags + "\ngit log --oneline -14\n" + gitlog)
    rec.hold(8)
    card.show("Hết", "Repo: github.com/gauronaldo/K5-L3A-DAY12-NguyenHoang-2A202603447-AI-SDLC-Dao-Den-Long\n\n"
                     "Bảng truy vết yêu cầu → bằng chứng: docs/proof/phase-1..4/README.md")
    rec.hold(4)
    rec.close()
    print("wrote %s (%d frames, %.1f s)" % (a.out, rec.frames, rec.frames / FPS))


if __name__ == "__main__":
    main()
