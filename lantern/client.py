"""Panda3D 3D client: renders a Simulation and feeds it keyboard input at a fixed 60 Hz.

Everything here is presentation only. Gameplay lives in lantern/sim.py, so the
headless output is unaffected by anything in this file.
"""
import math
import os
import random
import time
import unicodedata

from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (AmbientLight, DirectionalLight, Filename, Fog, KeyboardButton,
                          MouseButton, PointLight, TextNode, TransparencyAttrib, Vec4)

from . import config as C
from . import meshes
from .sim import InputState, Simulation, world_move, xz_dist

T = C.TUNING
WARM = (1.0, 0.72, 0.32, 1)
DIM = (0.28, 0.22, 0.38, 1)
INK = (0.08, 0.02, 0.12, 0.88)
FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
]


def P(v, lift=0.0):
    """Simulation (x, y-up, z) -> Panda3D (x, y, z-up)."""
    return (v[0], v[2], v[1] + lift)


def ascii_vi(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


class LanternGame(ShowBase):
    def __init__(self, seed=None, scenario=None, autostart=False):
        ShowBase.__init__(self)
        self.disableMouse()
        self.setBackgroundColor(0.03, 0.025, 0.07, 1)
        self.render.setShaderAuto()
        self.fixed_seed, self.scenario = seed, scenario
        self.font = None
        for f in FONTS:
            if os.path.exists(f):
                font = self.loader.loadFont(Filename.fromOsSpecific(f).getFullpath())
                if font and font.isValid():
                    self.font = font
                    break
        self._build_static_world()
        self._build_hud()
        self.accept("escape", self.userExit)
        self.accept("r", self.new_game)
        self.accept("enter", self.start_play)
        self.taskMgr.add(self._update, "update")
        self.new_game()
        if autostart:
            self.start_play()

    # ------------------------------------------------------------ text helper
    def text(self, s, **kw):
        if self.font is None:
            s = ascii_vi(s)
        else:
            kw.setdefault("font", self.font)
        return OnscreenText(text=s, mayChange=True, **kw)

    def set_text(self, node, s):
        node.setText(s if self.font else ascii_vi(s))

    # ------------------------------------------------------------ world
    def _build_static_world(self):
        r = self.render
        amb = AmbientLight("amb")
        amb.setColor((0.22, 0.2, 0.34, 1))
        r.setLight(r.attachNewNode(amb))
        moon = DirectionalLight("moon")
        moon.setColor((0.35, 0.38, 0.6, 1))
        mnp = r.attachNewNode(moon)
        mnp.setHpr(30, -50, 0)
        r.setLight(mnp)
        fog = Fog("fog")
        fog.setColor(0.06, 0.035, 0.1)
        fog.setExpDensity(0.016)
        r.setFog(fog)

        island = meshes.cylinder(C.ISLAND_RADIUS, 3.0, 64)
        island.reparentTo(r)
        island.setZ(-3.0)
        island.setColor(0.16, 0.24, 0.2, 1)
        rim = meshes.cone(C.ISLAND_RADIUS, 14.0, 64)
        rim.reparentTo(r)
        rim.setP(180)
        rim.setZ(-3.0)
        rim.setColor(0.18, 0.14, 0.2, 1)
        sea = meshes.cylinder(400, 0.1, 64)
        sea.reparentTo(r)
        sea.setZ(-9)
        sea.setColor(0.22, 0.17, 0.32, 1)

        rng = random.Random(1234)   # decoration only, independent of the game seed
        lan_pos = [l["pos"] for l in Simulation(0, {"random_motes": False, "random_shades": False}).lanterns]
        for _ in range(26):
            a, d = rng.uniform(0, 2 * math.pi), rng.uniform(8, C.ISLAND_RADIUS - 1.5)
            p = (d * math.sin(a), 0, d * math.cos(a))
            if any(xz_dist(p, l) < 6 for l in lan_pos):
                continue
            if rng.random() < 0.55:
                tree = r.attachNewNode("tree")
                trunk = meshes.cylinder(0.18, 1.0, 8)
                trunk.reparentTo(tree)
                trunk.setColor(0.25, 0.17, 0.14, 1)
                top = meshes.cone(rng.uniform(0.9, 1.4), rng.uniform(2.0, 3.2), 10)
                top.reparentTo(tree)
                top.setZ(0.9)
                top.setColor(0.1, 0.22 + rng.random() * 0.08, 0.2, 1)
                tree.setPos(*P(p))
            else:
                rock = meshes.sphere(rng.uniform(0.4, 0.9), 8, 5)
                rock.reparentTo(r)
                rock.setScale(1, rng.uniform(0.7, 1.3), 0.6)
                rock.setPos(*P(p))
                rock.setColor(0.25, 0.23, 0.3, 1)
        stars = r.attachNewNode("stars")
        for _ in range(140):
            a, e = rng.uniform(0, 2 * math.pi), rng.uniform(0.25, 1.3)
            s = meshes.sphere(rng.uniform(0.6, 1.3), 4, 3)
            s.reparentTo(stars)
            s.setPos(300 * math.cos(e) * math.cos(a), 300 * math.cos(e) * math.sin(a), 300 * math.sin(e))
            s.setColor(1, 0.95, 0.8, 1)
        stars.setLightOff()
        stars.setFogOff()
        stars.flattenStrong()

    def _build_dynamic(self):
        if hasattr(self, "dyn"):
            self.render.clearLight(self.player_light_np)
            for l in getattr(self, "lan_lights", []):
                self.render.clearLight(l)
            self.dyn.removeNode()
        self.dyn = self.render.attachNewNode("dynamic")
        sim = self.sim

        self.lan_nodes = {}
        self.lan_lights = []
        for lan in sim.lanterns:
            root = self.dyn.attachNewNode("lantern-" + lan["id"])
            root.setPos(*P(lan["pos"]))
            pole = meshes.cylinder(0.12, 3.0, 10)
            pole.reparentTo(root)
            pole.setColor(0.3, 0.22, 0.18, 1)
            roof = meshes.cone(0.85, 0.6, 12)
            roof.reparentTo(root)
            roof.setZ(3.75)
            roof.setColor(0.45, 0.18, 0.15, 1)
            body = meshes.sphere(0.65, 14, 10)
            body.reparentTo(root)
            body.setZ(3.3)
            body.setScale(1, 1, 1.15)
            body.setLightOff()
            # creative: faint ring showing the shade-free safe zone
            safe = meshes.ring(T["safe_radius"] - 0.12, T["safe_radius"], 64)
            safe.reparentTo(root)
            safe.setZ(0.03)
            safe.setTwoSided(True)
            safe.setLightOff()
            safe.setTransparency(TransparencyAttrib.MAlpha)
            pl = PointLight("pl-" + lan["id"])
            pl.setColor((1.6, 1.0, 0.45, 1))
            pl.setAttenuation((1, 0, 0.012))
            plnp = root.attachNewNode(pl)
            plnp.setZ(3.3)
            self.lan_lights.append(plnp)
            self.lan_nodes[lan["id"]] = {"root": root, "body": body, "safe": safe, "light": plnp, "lit": None,
                                         "deposit": None}

        # Mây: cloak, head, conical leaf hat, small lantern
        self.player_np = self.dyn.attachNewNode("may")
        body = meshes.cone(0.5, 1.25, 16)
        body.reparentTo(self.player_np)
        body.setColor(0.25, 0.42, 0.75, 1)
        head = meshes.sphere(0.3, 12, 8)
        head.reparentTo(self.player_np)
        head.setZ(1.38)
        head.setColor(0.95, 0.8, 0.65, 1)
        hat = meshes.cone(0.78, 0.5, 18)
        hat.reparentTo(self.player_np)
        hat.setZ(1.55)
        hat.setColor(0.45, 0.62, 0.25, 1)
        stick = meshes.cylinder(0.03, 0.5, 6)
        stick.reparentTo(self.player_np)
        stick.setPos(0.45, 0.15, 0.7)
        stick.setColor(0.3, 0.2, 0.15, 1)
        self.hand_lantern = meshes.sphere(0.14, 10, 6)
        self.hand_lantern.reparentTo(self.player_np)
        self.hand_lantern.setPos(0.45, 0.15, 0.62)
        self.hand_lantern.setLightOff()
        plight = PointLight("may-light")
        plight.setColor((0.9, 0.6, 0.3, 1))
        plight.setAttenuation((1, 0, 0.08))
        self.player_light_np = self.hand_lantern.attachNewNode(plight)
        self.player_light = plight
        self.render.setLight(self.player_light_np)
        # creative: compass arrow to nearest unlit lantern
        self.compass = meshes.cone(0.18, 0.6, 8)
        self.compass.reparentTo(self.dyn)
        self.compass.setLightOff()
        self.compass.setColor(*WARM)

        self.mote_nodes = {}
        for m in sim.motes:
            self._add_mote(m)
        self.shade_nodes = {}
        self.effects = []

    def _add_mote(self, m):
        n = meshes.sphere(0.13, 8, 6)
        n.reparentTo(self.dyn)
        n.setLightOff()
        n.setColor(1.0, 0.92, 0.45, 1)
        n.setPos(*P(m, 0.6))
        n.setPythonTag("phase", (m[0] * 0.37 + m[2] * 0.71) % 6.28)
        self.mote_nodes[id(m)] = n

    def _add_shade(self, s):
        root = self.dyn.attachNewNode("shade-" + s["id"])
        blob = meshes.sphere(0.85, 14, 10)
        blob.reparentTo(root)
        blob.setScale(1, 1, 1.25)
        blob.setTransparency(TransparencyAttrib.MAlpha)
        blob.setColor(*INK)
        for dx in (-0.28, 0.28):
            eye = meshes.sphere(0.11, 6, 4)
            eye.reparentTo(root)
            eye.setPos(dx, 0.72, 0.25)
            eye.setLightOff()
            eye.setColor(0.85, 0.55, 1.0, 1)
        self.shade_nodes[s["id"]] = (root, blob)

    # ------------------------------------------------------------ HUD
    def _build_hud(self):
        tl, tr = self.a2dTopLeft, self.a2dTopRight
        self.hud_left = self.text("", parent=tl, pos=(0.06, -0.1), scale=0.06, fg=(1, 0.9, 0.7, 1),
                                  align=TextNode.ALeft, shadow=(0, 0, 0, 0.8))
        self.hud_right = self.text("", parent=tr, pos=(-0.06, -0.1), scale=0.06, fg=(1, 0.9, 0.7, 1),
                                   align=TextNode.ARight, shadow=(0, 0, 0, 0.8))
        self.hud_hint = self.text("WASD di chuyển · ←/→ hoặc chuột phải xoay camera · Space nhảy · "
                                  "E gửi sáng · Q xung sáng · R chơi lại",
                                  parent=self.a2dBottomCenter, pos=(0, 0.06), scale=0.045,
                                  fg=(0.85, 0.8, 0.95, 0.9), shadow=(0, 0, 0, 0.8))
        self.banner = self.text("", pos=(0, 0.25), scale=0.1, fg=WARM, shadow=(0, 0, 0, 1))
        self.sub = self.text("", pos=(0, 0.1), scale=0.06, fg=(0.95, 0.9, 1, 1), shadow=(0, 0, 0, 1))

    def _hud(self):
        sim, pl = self.sim, self.sim.player
        t = max(0.0, sim.time_left_s)
        cd = pl["pulse_cd"]
        self.set_text(self.hud_left, "Lửa: %s%s\nĐom đóm: %d/%d\nĐèn lớn: %d/%d\nXung sáng: %s" % (
            "♥ " * pl["flames"] if self.font else "*" * pl["flames"], "" if pl["flames"] else "-",
            pl["carried"], T["carry_capacity"], sim.lit_count, len(sim.lanterns),
            "sẵn sàng" if cd <= 0 and pl["carried"] >= T["pulse_cost"] else
            ("%.1fs" % cd if cd > 0 else "cần đom đóm")))
        self.set_text(self.hud_right, "Điểm: %d\nĐêm 1 – Đảo Bến\n%02d:%02d" % (sim.score, int(t) // 60, int(t) % 60))

    # ------------------------------------------------------------ flow
    def new_game(self):
        seed = self.fixed_seed if self.fixed_seed is not None else int(time.time()) & 0x7FFFFFFF
        self.sim = Simulation(seed, self.scenario)
        self.inp = InputState()
        self.cam_yaw = 0.0
        self.acc = 0.0
        self.running = False
        self.flash = 0.0
        self.last_mouse_x = None
        self._build_dynamic()
        self.set_text(self.banner, "Đảo Đèn Lồng")
        self.set_text(self.sub, "Đêm 1 – Đảo Bến\nGom đom đóm, thắp lại 5 Đèn Lồng Lớn, né Bóng Mực.\n"
                                "Nhấn Enter để bắt đầu")
        self._sync(0.0)

    def start_play(self):
        if self.sim.state == "playing" and not self.running:
            self.running = True
            self.set_text(self.banner, "")
            self.set_text(self.sub, "")

    def _read_input(self, dt):
        down = self.mouseWatcherNode.is_button_down
        k = lambda c: down(KeyboardButton.ascii_key(c))  # noqa: E731
        turn = (1 if down(KeyboardButton.right()) else 0) - (1 if down(KeyboardButton.left()) else 0)
        self.cam_yaw += turn * 110.0 * dt
        if self.mouseWatcherNode.hasMouse() and down(MouseButton.three()):
            mx = self.mouseWatcherNode.getMouseX()
            if self.last_mouse_x is not None:
                self.cam_yaw += (mx - self.last_mouse_x) * 180.0
            self.last_mouse_x = mx
        else:
            self.last_mouse_x = None
        x = (1 if k("d") else 0) - (1 if k("a") else 0)
        z = (1 if k("w") or down(KeyboardButton.up()) else 0) - (1 if k("s") or down(KeyboardButton.down()) else 0)
        self.inp.move = (float(x), float(z))
        self.inp.cam_yaw_deg = self.cam_yaw % 360.0
        self.inp.jump = down(KeyboardButton.space())
        self.inp.interact = k("e") or k("f")
        self.inp.pulse = k("q") or down(MouseButton.one())

    def feed(self, inp):
        """Advance one fixed tick with the given input (also used by tools/screenshot.py)."""
        for ev in self.sim.step(inp):
            self._on_event(ev)

    def _on_event(self, ev):
        name = ev["name"]
        if name == "pulse":
            fx = meshes.ring(0.47, 0.55, 64)
            fx.reparentTo(self.dyn)
            fx.setPos(*P(self.sim.player["pos"], 0.15))
            fx.setLightOff()
            fx.setTwoSided(True)
            fx.setTransparency(TransparencyAttrib.MAlpha)
            self.effects.append([fx, 0.0, "pulse"])
        elif name == "player_hit":
            self.flash = 0.35
        elif name == "lantern_lit":
            node = self.lan_nodes[ev["data"]["lantern_id"]]
            fx = meshes.sphere(0.7, 16, 10)
            fx.reparentTo(node["root"])
            fx.setZ(3.3)
            fx.setLightOff()
            fx.setTransparency(TransparencyAttrib.MAlpha)
            self.effects.append([fx, 0.0, "burst"])
        elif name == "shade_spawned":
            pass
        elif name == "game_over":
            d = ev["data"]
            if d["result"] == "won":
                self.set_text(self.banner, "Đảo Bến đã sáng lại!")
            elif d["reason"] == "dawn":
                self.set_text(self.banner, "Trời sáng mà đảo vẫn chìm trong sương...")
            else:
                self.set_text(self.banner, "Ngọn lửa của Mây đã tắt...")
            self.set_text(self.sub, "Điểm: %d\nNhấn R để chơi lại" % self.sim.score)

    def _update(self, task):
        dt = min(globalClock.getDt(), 0.25)  # noqa: F821 (Panda3D builtin)
        if self.running and self.sim.state == "playing":
            self._read_input(dt)
            self.acc += dt
            while self.acc >= C.DT and self.sim.state == "playing":
                self.feed(self.inp)
                self.acc -= C.DT
        self._sync(dt)
        return task.cont

    # ------------------------------------------------------------ render sync
    def _sync(self, dt):
        sim, pl = self.sim, self.sim.player
        now = globalClock.getFrameTime()  # noqa: F821
        self.player_np.setPos(*P(pl["pos"]))
        wx, wz = world_move(self.inp.move, self.inp.cam_yaw_deg)
        if wx or wz:
            self.player_np.setH(-math.degrees(math.atan2(wx, wz)))
        glow = 0.35 + 0.65 * pl["carried"] / T["carry_capacity"]
        self.hand_lantern.setColor(1.0, 0.65 + 0.3 * glow, 0.3 * glow, 1)
        self.hand_lantern.setScale(0.8 + 0.6 * glow)
        self.player_light.setColor((1.2 * glow, 0.8 * glow, 0.35 * glow, 1))
        if pl["invuln_t"] > 0:
            self.player_np.setAlphaScale(0.45 if int(now * 12) % 2 else 1.0)
        else:
            self.player_np.setAlphaScale(1.0)

        for lan in sim.lanterns:
            node = self.lan_nodes[lan["id"]]
            state = (lan["lit"], lan["deposited"])
            if (node["lit"], node["deposit"]) != state:
                node["lit"], node["deposit"] = state
                f = min(1.0, lan["deposited"] / float(T["lantern_cost"]))
                if lan["lit"]:
                    node["body"].setColor(*WARM)
                    node["safe"].setColor(1.0, 0.75, 0.35, 0.55)
                    self.render.setLight(node["light"])
                else:
                    node["body"].setColor(DIM[0] + 0.5 * f, DIM[1] + 0.35 * f, DIM[2], 1)
                    node["safe"].setColor(0.7, 0.6, 0.9, 0.22)
                    self.render.clearLight(node["light"])

        alive = {id(m) for m in sim.motes}
        for key in list(self.mote_nodes):
            if key not in alive:
                self.mote_nodes.pop(key).removeNode()
        for m in sim.motes:
            n = self.mote_nodes[id(m)]
            ph = n.getPythonTag("phase")
            n.setZ(0.55 + 0.2 * math.sin(now * 2.2 + ph))
            n.setScale(0.85 + 0.25 * math.sin(now * 5 + ph))

        for s in sim.shades:
            if s["id"] not in self.shade_nodes:
                self._add_shade(s)
            root, blob = self.shade_nodes[s["id"]]
            root.setPos(*P(s["pos"], 0.15 * math.sin(now * 3 + hash(s["id"]) % 7)))
            root.lookAt(*P(pl["pos"], s["pos"][1]))
            if s["state"] == "stunned":
                blob.setColor(0.45, 0.4, 0.6, 0.55)
                root.setScale(0.8)
            else:
                blob.setColor(*INK)
                root.setScale(1.0)

        unlit = [l for l in sim.lanterns if not l["lit"]]
        if unlit and sim.state == "playing":
            tgt = min(unlit, key=lambda l: xz_dist(l["pos"], pl["pos"]))
            self.compass.show()
            self.compass.setPos(*P(pl["pos"], 2.45))
            ang = math.degrees(math.atan2(tgt["pos"][0] - pl["pos"][0], tgt["pos"][2] - pl["pos"][2]))
            self.compass.setHpr(-ang, -90, 0)
        else:
            self.compass.hide()

        for fx in list(self.effects):
            fx[1] += dt
            if fx[2] == "pulse":
                k = fx[1] / 0.4
                fx[0].setScale(max(0.01, k * T["pulse_radius"] / 0.55))
                fx[0].setColor(1.0, 0.85, 0.5, max(0.0, 0.8 * (1 - k)))
            else:
                k = fx[1] / 0.8
                fx[0].setScale(1 + 4 * k)
                fx[0].setColor(1.0, 0.8, 0.4, max(0.0, 0.7 * (1 - k)))
            if k >= 1:
                fx[0].removeNode()
                self.effects.remove(fx)

        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt)
            self.setBackgroundColor(0.03 + self.flash, 0.025, 0.07 + self.flash * 0.6, 1)

        th = math.radians(self.cam_yaw)
        fx_, fz_ = math.sin(th), math.cos(th)
        px, py, pz = P(pl["pos"])
        self.camera.setPos(px - fx_ * 13.0, py - fz_ * 13.0, pz + 7.5)
        self.camera.lookAt(px, py, pz + 1.3)
        self._hud()


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description="Dao Den Long - 3D client")
    ap.add_argument("--seed", type=int, default=None, help="fixed world seed (default: random each play)")
    a = ap.parse_args(argv)
    from panda3d.core import loadPrcFileData
    loadPrcFileData("", "window-title Dao Den Long\nwin-size 1280 720\nframebuffer-multisample 1\nmultisamples 4\n"
                        "sync-video 1\n")
    LanternGame(seed=a.seed).run()
