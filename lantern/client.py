"""Panda3D client: menus, three nights, HUD, audio. Renders a Simulation and feeds it input at a fixed 60 Hz.

Presentation only - gameplay lives in lantern/sim.py, so nothing here changes headless output.
"""
import json
import math
import os
import random
import time
import unicodedata

from direct.gui.DirectGui import DGG, DirectButton, DirectEntry, DirectFrame, DirectSlider
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (AmbientLight, ButtonRegistry, CullFaceAttrib, DirectionalLight, Filename, Fog, KeyboardButton,
                          MouseButton, Point2, Point3, PointLight, TextNode, TransparencyAttrib)

from . import config as C
from . import meshes
from . import bench_scene, sysinfo
from .campaign import Campaign
from .leaderboard import Leaderboard, valid_name
from .settings import ACTION_LABELS, ACTIONS, DEFAULT_KEYS, Settings, key_conflicts
from .sim import InputState, Simulation, xz_dist
from .world import ground_height

T = C.TUNING
PAL = {k: C.hex_rgb(v) for k, v in C.PALETTE.items()}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUND_DIR = os.path.join(ROOT, "assets", "sounds")
SFX = ("pickup", "lantern_lit", "pulse", "hit", "jump", "dash", "win", "lose", "shade_spawn", "countdown", "wind")
EVENT_SFX = {"mote_picked": "pickup", "lantern_lit": "lantern_lit", "pulse": "pulse", "player_hit": "hit",
             "dash": "dash", "shade_spawned": "shade_spawn"}
FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
]
SYMBOL_FONTS = [   # fonts that really contain U+26A0 (Arial does not)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Apple Symbols.ttf",
    "/Library/Fonts/Arial Unicode.ttf", "C:/Windows/Fonts/seguisym.ttf", "C:/Windows/Fonts/seguiemj.ttf",
]
TEXT = PAL["ui_text"]
GOLD = PAL["gold"]
DANGER = PAL["ui_danger"]
CB_RIM = C.hex_rgb("#00B3FF")      # Ticket-03 colour-blind palette
CB_DANGER = C.hex_rgb("#FFFFFF")


def P(v, lift=0.0):
    """Simulation (x, y-up, z) -> Panda3D (x, y, z-up)."""
    return (v[0], v[2], v[1] + lift)


def ascii_vi(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


class Autopilot:
    """Deterministic bot used by the FPS probe, screenshots and the demo: collect, deposit, pulse."""

    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.t = 0

    def __call__(self, sim):
        i = InputState()
        pl = sim.player
        self.t += 1
        unlit = [l for l in sim.lanterns if not l["lit"]]
        go_lantern = unlit and (pl["carried"] >= sim.capacity() or (not sim.motes and pl["carried"] > 0))
        if go_lantern:
            tgt = min(unlit, key=lambda l: xz_dist(l["pos"], pl["pos"]))["pos"]
        elif sim.motes:
            tgt = min(sim.motes, key=lambda m: xz_dist(m["pos"], pl["pos"]))["pos"]
        else:
            tgt = None
        if tgt is not None:
            dx, dz = tgt[0] - pl["pos"][0], tgt[2] - pl["pos"][2]
            d = math.hypot(dx, dz)
            if d > 0.3:
                i.move = (dx / d, dz / d)
        i.interact = self.t % 20 < 10
        near = any(xz_dist(s["pos"], pl["pos"]) < 4 and s["state"] in ("chase", "wander") for s in sim.shades)
        i.pulse = near and self.t % 30 < 15
        i.jump = self.rng.random() < 0.01
        return i


class Game(ShowBase):
    def __init__(self, seed=None, autoplay=False, bench=False):
        ShowBase.__init__(self)
        self.bench = bench
        self._texts = []          # (node, base scale) for the large-text option
        self.subs = []            # subtitles: [text, seconds left]
        self.shake = 0.0
        self.capture_action = None
        self.disableMouse()
        self.camLens.setFov(70)   # wide enough to keep lantern tops and fuel bars in view
        self.camLens.setNear(0.3)
        self.setBackgroundColor(*PAL["sky"])
        self.render.setShaderAuto()
        self.fixed_seed = seed
        self.autoplay = Autopilot(seed or 0) if autoplay else None
        self.settings = Settings.load()
        self.campaign = Campaign()
        self.leaderboard = Leaderboard()
        self.font = None
        for f in FONTS:
            if os.path.exists(f):
                font = self.loader.loadFont(Filename.fromOsSpecific(f).getFullpath())
                if font and font.isValid():
                    self.font = font
                    break
        self.sym_font = None
        for f in SYMBOL_FONTS:
            if os.path.exists(f):
                font = self.loader.loadFont(Filename.fromOsSpecific(f).getFullpath())
                if font and font.isValid():
                    self.sym_font = font
                    break
        self.sim = None
        self.world_np = None
        self.dyn = None
        self.mode = "menu"
        self.cam_yaw = 0.0
        self.attempt = 0
        self.end_timer = None
        self.last_mouse_x = None
        self.frame_hook = None
        self.flash = 0.0
        self.settings_back = "menu"
        self.current_panel = None
        self._setup_lights()
        self._setup_audio()
        self._build_hud()
        self._build_panels()
        self.accept("escape", self._on_escape)
        self._pause_key = None
        self._bind_pause_key()
        self.accept("enter", self._on_enter)
        if self.buttonThrowers:   # None for off-screen windows (screenshot tool)
            self.buttonThrowers[0].node().setButtonDownEvent("any-button")
        self.accept("any-button", self._on_any_button)
        self.apply_text_scale()
        self.taskMgr.add(self._update, "update")
        self.show_panel("menu")

    # ------------------------------------------------------------ helpers
    def tr(self, s):
        return s if self.font else ascii_vi(s)

    def text(self, s, **kw):
        if self.font:
            kw.setdefault("font", self.font)
        kw.setdefault("fg", TEXT)
        kw.setdefault("shadow", (0, 0, 0, 0.8))
        node = OnscreenText(text=self.tr(s), mayChange=True, **kw)
        self._texts.append((node, kw.get("scale", 0.07)))
        return node

    def set_text(self, node, s):
        node.setText(self.tr(s))

    def cb(self):
        return bool(self.settings.get("colorblind"))

    def keys(self):
        return self.settings["keys"]

    def _bind_pause_key(self):
        if self._pause_key:
            self.ignore(self._pause_key)
        self._pause_key = self.keys()["pause"]
        if self._pause_key != "escape":
            self.accept(self._pause_key, self.toggle_pause)

    def _on_escape(self):
        if self.capture_action:
            self.capture_action = None
            self._refresh_keys_panel()
        elif self.mode in ("play", "paused"):
            self.toggle_pause()

    def _on_any_button(self, name):
        if not self.capture_action or name.startswith("mouse") or name in ("escape", "wheel_up", "wheel_down"):
            return
        self.keys()[self.capture_action] = name
        self.capture_action = None
        self._refresh_keys_panel()

    def _down(self, action):
        name = self.keys()[action]
        handle = ButtonRegistry.ptr().findButton(name)
        return bool(handle) and self.mouseWatcherNode.is_button_down(handle)

    def danger(self):
        return CB_DANGER if self.cb() else DANGER

    def warn(self, s):
        """Text part of a danger message (the ⚠ icon is a separate node, see _place_icon)."""
        return s

    def _icon(self):
        kw = {"font": self.sym_font} if self.sym_font else {}
        return OnscreenText(text="⚠" if self.sym_font else "(!)", mayChange=True, fg=CB_DANGER,
                            shadow=(0, 0, 0, 0.8), scale=0.07, **kw)

    def _place_icon(self, icon, node):
        """Colour-blind mode: show ⚠ to the left of a non-empty danger text."""
        txt = node.getText()
        if not self.cb() or not txt or node.isHidden():
            icon.hide()
            return
        width = node.textNode.getWidth() * node.getScale()[0]
        x, y = node.getPos()
        icon.reparentTo(node.getParent())
        icon.setPos(x - width / 2 - 0.06, y)
        icon.show()

    def text_mult(self):
        return 1.25 if self.settings.get("large_text") else 1.0

    def apply_text_scale(self):
        m = self.text_mult()
        for node, base in self._texts:
            sc = base if isinstance(base, (int, float)) else base[0]
            node.setScale(sc * m)

    def _btn(self, parent, label, cmd, pos, scale=0.065, width=9):
        return DirectButton(parent=parent, text=self.tr(label), command=cmd, pos=pos, scale=scale,
                            text_font=self.font, text_fg=TEXT, frameColor=(0.16, 0.2, 0.38, 0.95),
                            frameSize=(-width / 2, width / 2, -0.55, 1.05), relief=DGG.FLAT,
                            text_shadow=(0, 0, 0, 0.6))

    # ------------------------------------------------------------ audio
    def _setup_audio(self):
        self.sfx = {}
        for name in SFX:
            path = os.path.join(SOUND_DIR, name + ".wav")
            if os.path.exists(path):
                self.sfx[name] = self.loader.loadSfx(Filename.fromOsSpecific(path).getFullpath())
        path = os.path.join(SOUND_DIR, "music.wav")
        self.music = self.loader.loadMusic(Filename.fromOsSpecific(path).getFullpath()) if os.path.exists(path) else None
        if self.music:
            self.music.setLoop(True)
            self.music.play()
        self.apply_volume()

    def apply_volume(self):
        v = self.settings["volume"]
        for m in self.sfxManagerList:
            m.setVolume(v)
        if self.musicManager:
            self.musicManager.setVolume(v * 0.6)

    def play(self, name):
        s = self.sfx.get(name)
        if s:
            s.play()

    # ------------------------------------------------------------ lights
    def _setup_lights(self):
        r = self.render
        self.amb = AmbientLight("amb")
        r.setLight(r.attachNewNode(self.amb))
        moon = DirectionalLight("moon")
        moon.setColor((0.42, 0.46, 0.68, 1))
        mnp = r.attachNewNode(moon)
        mnp.setHpr(30, -55, 0)
        r.setLight(mnp)
        fog = Fog("fog")
        fog.setColor(*PAL["fog"][:3])
        fog.setExpDensity(0.012)
        r.setFog(fog)
        self.set_ambient(0, 1)

    def set_ambient(self, lit, total):
        i = C.ambient_intensity(lit, total)
        self.amb.setColor((i, i, i, 1))
        self.ambient_value = i

    # ------------------------------------------------------------ world building
    def _island(self, parent, center, radius, top=0.0):
        g = meshes.cylinder(radius, 3.0, 72)
        g.reparentTo(parent)
        g.setPos(center[0], center[1], top - 3.0)
        g.setColor(*PAL["grass"])
        sand = meshes.ring(radius - 1.8, radius, 72)
        sand.reparentTo(parent)
        sand.setPos(center[0], center[1], top + 0.02)
        sand.setColor(*PAL["sand"])
        under = meshes.cone(radius, radius * 0.45, 48)
        under.reparentTo(parent)
        under.setP(180)
        under.setPos(center[0], center[1], top - 3.0)
        under.setColor(0.2, 0.17, 0.24, 1)

    def _build_world(self, night):
        if self.world_np:
            self.world_np.removeNode()
        w = self.world_np = self.render.attachNewNode("world")
        sea = meshes.cylinder(500, 0.1, 64)
        sea.reparentTo(w)
        sea.setZ(-14)
        sea.setColor(*PAL["cloud_sea"])
        if night == 1:
            self._island(w, (0, 0), C.N1_RADIUS)
        elif night == 2:
            for c in C.N2_ISLANDS:
                self._island(w, c, C.N2_RADIUS)
            x0, x1, z0, z1 = C.N2_BRIDGE
            bridge = meshes.box(x0, x1, z0, z1, -0.4, 0.0)
            bridge.reparentTo(w)
            bridge.setColor(*PAL["wood"])
            for i in range(10):
                plank = meshes.box(x0 + i * 1.8, x0 + i * 1.8 + 0.12, z0, z1, 0.0, 0.04)
                plank.reparentTo(w)
                plank.setColor(0.32, 0.22, 0.14, 1)
        else:
            self._island(w, (0, 0), C.N3_RADIUS)
            t_in, t_out, t_h = C.N3_TIER1
            tier1 = meshes.annulus_sector(t_in, t_out, 0, 180, t_h, 36)
            tier1.reparentTo(w)
            tier1.setColor(0.26, 0.5, 0.43, 1)
            tier2 = meshes.cylinder(C.N3_TIER2[0], C.N3_TIER2[1], 48)
            tier2.reparentTo(w)
            tier2.setColor(0.3, 0.55, 0.47, 1)
            top, foot, width = C.N3_RAMP
            hw = width / 2
            for deg in C.N3_RAMPS:
                a = math.radians(deg)
                ux, uy, vx, vy = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
                ramp = meshes.wedge((foot * ux - hw * vx, foot * uy - hw * vy), (foot * ux + hw * vx, foot * uy + hw * vy),
                                    (top * ux - hw * vx, top * uy - hw * vy), (top * ux + hw * vx, top * uy + hw * vy),
                                    t_h)
                ramp.reparentTo(w)
                ramp.setColor(*PAL["wood"])
            tower = meshes.cylinder(C.N3_TOWER_R, C.N3_TOWER_H, 24)
            tower.reparentTo(w)
            tower.setZ(C.N3_TIER2[1])
            tower.setColor(0.55, 0.45, 0.35, 1)
            roof = meshes.cone(2.8, 2.2, 24)
            roof.reparentTo(w)
            roof.setZ(C.N3_TIER2[1] + C.N3_TOWER_H)
            roof.setColor(0.5, 0.16, 0.14, 1)
            bell = meshes.cone(1.0, 1.2, 16)
            bell.reparentTo(w)
            bell.setZ(C.N3_TIER2[1] + C.N3_TOWER_H - 1.0)
            bell.setColor(*GOLD)
        for pad in C.NIGHTS[night]["pads"]:
            d = meshes.cylinder(1.0, 0.12, 24)
            d.reparentTo(w)
            d.setPos(*P(pad["pos"]))
            d.setColor(*GOLD)
            d.setLightOff()
        rng = random.Random(1234 + night)   # decoration only, independent of the game seed
        nd = C.NIGHTS[night]
        for _ in range(40):
            base = rng.choice(nd["mote_points"])
            p = [base[0] + rng.uniform(-6, 6), 0, base[2] + rng.uniform(-6, 6)]
            if ground_height(night, p[0], p[2]) != 0.0:
                continue
            if any(xz_dist(p, l) < 7 for l in nd["lanterns"]) or any(xz_dist(p, m) < 2 for m in nd["mote_points"]) \
                    or any(xz_dist(p, pd["pos"]) < 3 for pd in nd["pads"]) or abs(p[2]) < 3 and 20 < p[0] < 50:
                continue
            tree = w.attachNewNode("tree")
            trunk = meshes.cylinder(0.18, 1.0, 8)
            trunk.reparentTo(tree)
            trunk.setColor(*PAL["wood"])
            crown = meshes.cone(rng.uniform(0.9, 1.4), rng.uniform(2.0, 3.2), 10)
            crown.reparentTo(tree)
            crown.setZ(0.9)
            crown.setColor(0.12, 0.3, 0.25, 1)
            tree.setPos(*P(p))
        w.flattenStrong()

    def _build_dynamic(self):
        if self.dyn:
            for l in self.lan_lights:
                self.render.clearLight(l)
            self.render.clearLight(self.player_light_np)
            self.dyn.removeNode()
        self.dyn = self.render.attachNewNode("dynamic")
        sim = self.sim
        self.lan_nodes, self.lan_lights = {}, []
        for lan in sim.lanterns:
            root = self.dyn.attachNewNode("lantern-" + lan["id"])
            root.setPos(*P(lan["pos"]))
            pole = meshes.cylinder(0.12, 3.0, 10)
            pole.reparentTo(root)
            pole.setColor(*PAL["wood"])
            roof = meshes.cone(0.85, 0.6, 12)
            roof.reparentTo(root)
            roof.setZ(3.75)
            roof.setColor(0.45, 0.18, 0.15, 1)
            body = meshes.sphere(0.65, 14, 10)
            body.reparentTo(root)
            body.setZ(3.3)
            body.setScale(1, 1, 1.15)
            core = meshes.sphere(0.35, 10, 8)
            core.reparentTo(root)
            core.setZ(3.3)
            core.setColor(*PAL["lantern_core"])
            core.setLightOff()
            notch = meshes.box(-0.08, 0.08, -0.7, -0.6, -0.35, 0.3)   # "torn paper" mark for colour-blind mode
            notch.reparentTo(body)
            notch.setColor(0.05, 0.04, 0.06, 1)
            bar = root.attachNewNode("fuel-bar")
            bar.setZ(4.6)
            bar.setBillboardPointEye()
            bg = meshes.box(-0.8, 0.8, -0.02, 0.02, -0.09, 0.09)
            bg.reparentTo(bar)
            bg.setColor(0.08, 0.08, 0.12, 1)
            fill = meshes.box(0.0, 1.6, -0.04, 0.0, -0.07, 0.07)
            fill.reparentTo(bar)
            fill.setX(-0.8)
            fill.setColor(*GOLD)
            bar.setLightOff()
            safe = meshes.ring(T["safe_radius"] - 0.15, T["safe_radius"], 72)
            safe.reparentTo(root)
            safe.setZ(0.04)
            safe.setTwoSided(True)
            safe.setLightOff()
            safe.setTransparency(TransparencyAttrib.MAlpha)
            safe.setColor(1.0, 0.72, 0.3, 0.5)
            pl = PointLight("pl-" + lan["id"])
            pl.setColor((1.6, 1.0, 0.45, 1))
            pl.setAttenuation((1, 0, 0.012))
            plnp = root.attachNewNode(pl)
            plnp.setZ(3.3)
            self.lan_lights.append(plnp)
            self.lan_nodes[lan["id"]] = {"root": root, "body": body, "core": core, "safe": safe, "light": plnp,
                                         "state": None, "bar": bar, "fill": fill, "notch": notch}

        self.player_np = self.dyn.attachNewNode("may")
        body = meshes.cone(0.5, 1.25, 16)
        body.reparentTo(self.player_np)
        body.setColor(*PAL["may_cloak"])
        scarf = meshes.cylinder(0.3, 0.14, 14)
        scarf.reparentTo(self.player_np)
        scarf.setZ(1.05)
        scarf.setColor(*PAL["may_scarf"])
        head = meshes.sphere(0.28, 12, 8)
        head.reparentTo(self.player_np)
        head.setZ(1.38)
        head.setColor(0.95, 0.8, 0.65, 1)
        hat = meshes.cone(0.78, 0.5, 18)
        hat.reparentTo(self.player_np)
        hat.setZ(1.55)
        hat.setColor(0.62, 0.66, 0.36, 1)
        self.hand_lantern = meshes.sphere(0.14, 10, 6)
        self.hand_lantern.reparentTo(self.player_np)
        self.hand_lantern.setPos(0.45, 0.15, 0.62)
        self.hand_lantern.setLightOff()
        plight = PointLight("may-light")
        plight.setAttenuation((1, 0, 0.08))
        self.player_light = plight
        self.player_light_np = self.hand_lantern.attachNewNode(plight)
        self.render.setLight(self.player_light_np)
        self.compass = meshes.cone(0.18, 0.6, 8)
        self.compass.reparentTo(self.dyn)
        self.compass.setLightOff()
        self.compass.setColor(*GOLD)

        self.mote_nodes, self.shade_nodes, self.drifter_nodes, self.charm_nodes = {}, {}, {}, {}
        for c in sim.charms:
            root = self.dyn.attachNewNode("charm-" + c["id"])
            rim = meshes.box(-0.32, 0.32, -0.03, 0.03, -0.45, 0.45)
            rim.reparentTo(root)
            rim.setColor(*GOLD)
            paper = meshes.box(-0.26, 0.26, -0.05, 0.05, -0.39, 0.39)
            paper.reparentTo(root)
            paper.setColor(*PAL["charm"])
            root.setLightOff()
            self.charm_nodes[c["id"]] = root
        deco = random.Random(99)
        self.leaves = []
        for _ in range(24):
            leaf = meshes.box(-0.12, 0.12, -0.02, 0.02, -0.06, 0.06)
            leaf.reparentTo(self.dyn)
            leaf.setColor(0.5, 0.7, 0.3, 1)
            leaf.hide()
            self.leaves.append([leaf, deco.uniform(0, 6.28), deco.uniform(3, 9), deco.uniform(0.5, 3)])
        self.effects = []
        self._sync_entities(0.0)

    def _add_mote(self, m):
        # one geom per firefly (perf: Ticket-04 bench has 100 of them); glow colour on a slightly larger core
        root = meshes.sphere(0.15, 8, 6)
        root.reparentTo(self.dyn)
        root.setColor(*PAL["mote_core"])
        root.setLightOff()
        root.setPythonTag("phase", (m["pos"][0] * 0.37 + m["pos"][2] * 0.71) % 6.28)
        self.mote_nodes[m["id"]] = root

    def _add_shade(self, s):
        # 2 geoms per shade (perf): lit body + unlit rim outline that also carries the eyes
        root = self.dyn.attachNewNode("shade-" + s["id"])
        rim = root.attachNewNode("rim")
        shell = meshes.sphere(0.95, 12, 8)
        shell.reparentTo(rim)
        shell.setScale(1, 1, 1.25)
        for dx in (-0.28, 0.28):
            eye = meshes.sphere(0.11, 6, 4)
            eye.reparentTo(rim)
            eye.setPos(dx, 0.80, 0.25)
        rim.flattenStrong()
        rim.setAttrib(CullFaceAttrib.makeReverse())
        rim.setLightOff()
        blob = meshes.sphere(0.85, 12, 8)
        blob.reparentTo(root)
        blob.setScale(1, 1, 1.25)
        blob.flattenStrong()
        root.setShaderOff(1)   # shades use fixed-function lighting everywhere (play == bench); far fewer state switches
        self.shade_nodes[s["id"]] = [root, blob, rim, None]

    def _add_drifter(self, d):
        root = self.dyn.attachNewNode("drifter-" + d["id"])
        segs = []
        for _ in range(5):
            seg = meshes.box(-0.25, 0.25, -0.03, 0.03, -0.12, 0.12)
            seg.reparentTo(root)
            seg.setColor(PAL["drifter"][0], PAL["drifter"][1], PAL["drifter"][2], 0.85)
            seg.setTransparency(TransparencyAttrib.MAlpha)
            segs.append(seg)
        root.setLightOff()
        self.drifter_nodes[d["id"]] = (root, segs)

    # ------------------------------------------------------------ HUD
    def _build_hud(self):
        tl, tr, tc = self.a2dTopLeft, self.a2dTopRight, self.a2dTopCenter
        self.h_flames = self.text("", parent=tl, pos=(0.06, -0.11), scale=0.07, fg=DANGER, align=TextNode.ALeft)
        self.h_timer = self.text("", parent=tc, pos=(0, -0.12), scale=0.085, fg=TEXT)
        self.h_right = self.text("", parent=tr, pos=(-0.06, -0.1), scale=0.06, fg=GOLD, align=TextNode.ARight)
        self.h_prompt = self.text("", parent=self.aspect2d, pos=(0, -0.55), scale=0.06, fg=TEXT)
        self.h_warn = self.text("", parent=self.aspect2d, pos=(0, 0.62), scale=0.06, fg=DANGER)
        self.h_warn_icon = self._icon()
        self.h_timer_icon = self._icon()
        self.h_cells = []
        for i in range(T["capacity_max"]):
            cell = DirectFrame(parent=self.a2dBottomCenter, frameColor=(0.15, 0.15, 0.22, 0.85),
                               frameSize=(-0.032, 0.032, -0.032, 0.032), pos=(-0.405 + i * 0.09, 0, 0.12))
            self.h_cells.append(cell)
        self.h_carry = self.text("", parent=self.a2dBottomCenter, pos=(0, 0.19), scale=0.05, fg=PAL["mote_glow"])
        self.h_cd = {}
        for i, (key, label) in enumerate((("dash", "Lướt"), ("pulse", "Tỏa Sáng"))):
            box = DirectFrame(parent=self.a2dBottomRight, frameColor=(0.15, 0.2, 0.38, 0.9),
                              frameSize=(-0.09, 0.09, -0.09, 0.09), pos=(-0.42 + i * 0.22, 0, 0.22))
            fill = DirectFrame(parent=box, frameColor=(0.05, 0.05, 0.08, 0.75), frameSize=(-0.09, 0.09, -0.09, -0.09))
            lab = self.text(label, parent=box, pos=(0, -0.15), scale=0.05)
            sec = self.text("", parent=box, pos=(0, -0.015), scale=0.06)
            self.h_cd[key] = (box, fill, lab, sec)
        self.h_arrow = self.text("▲", parent=self.aspect2d, scale=0.09, fg=GOLD)
        self.h_spawn_arrow = self.text("▲", parent=self.aspect2d, scale=0.13, fg=DANGER, shadow=(0, 0, 0, 1))
        self.h_sub = self.text("", parent=self.a2dBottomCenter, pos=(0, 0.3), scale=0.06, fg=TEXT,
                               bg=(0, 0, 0, 0.55))
        self.spawn_arrow = None
        self.h_hint = self.text("WASD di chuyển · ←/→, chuột phải: camera · Space nhảy · Shift lướt · "
                                "E nạp sáng · Q tỏa sáng · Esc/P tạm dừng",
                                parent=self.a2dBottomLeft, pos=(0.05, 0.03), scale=0.05, align=TextNode.ALeft,
                                fg=(0.85, 0.82, 0.9, 0.85))
        self.hud_nodes = [self.h_flames, self.h_timer, self.h_right, self.h_prompt, self.h_warn, self.h_carry,
                          self.h_arrow, self.h_hint, self.h_sub, self.h_spawn_arrow] + self.h_cells + [v[0] for v in self.h_cd.values()]
        self.show_hud(False)

    def show_hud(self, on):
        for n in self.hud_nodes:
            n.show() if on else n.hide()
        if not on:
            self.h_warn_icon.hide()
            self.h_timer_icon.hide()

    def _hud(self, now):
        sim, pl = self.sim, self.sim.player
        self.h_flames.setFg(self.danger())
        self.set_text(self.h_flames, "♥ " * pl["flames"] if self.font else "Lua: %d" % pl["flames"])
        t = max(0.0, sim.time_left_s)
        secs = int(math.ceil(t - 1e-9))
        self.set_text(self.h_timer, "%02d:%02d" % (secs // 60, secs % 60))
        if t <= 30:
            self.h_timer.setFg(self.danger())
            self._place_icon(self.h_timer_icon, self.h_timer)
            self.h_timer.setAlphaScale(1.0 if int(now * 3) % 2 == 0 else 0.25)
        else:
            self.h_timer.setFg(TEXT)
            self.h_timer.setAlphaScale(1.0)
            self.h_timer_icon.hide()
        self.set_text(self.h_right, "Đèn %d/%d\nĐiểm %d" % (sim.lit_count, len(sim.lanterns),
                                                           self.campaign.total + sim.score))
        cap = sim.capacity()
        for i, cell in enumerate(self.h_cells):
            if i >= cap:
                cell.hide()
                continue
            cell.show()
            cell.setPos((i - (cap - 1) / 2.0) * 0.075, 0, 0.12)
            g = PAL["mote_glow"]
            cell["frameColor"] = (g[0], g[1], g[2], 1) if i < pl["carried"] else (0.15, 0.15, 0.22, 0.85)
        self.set_text(self.h_carry, "Đom đóm %d/%d" % (pl["carried"], sim.capacity()))
        for key, total, cur in (("dash", C.DASH_CD_TICKS, pl["dash_cd"]), ("pulse", C.PULSE_CD_TICKS, pl["pulse_cd"])):
            box, fill, _, sec = self.h_cd[key]
            frac = 0.0 if (key == "dash" and pl["charm"] > 0) else cur / float(total)
            fill["frameSize"] = (-0.09, 0.09, -0.09, -0.09 + 0.18 * frac)
            need = key == "pulse" and pl["carried"] < T["pulse_cost"]
            self.set_text(sec, "%.1f" % (cur / 60.0) if frac > 0 else ("×" if need else ""))
        near = [l for l in sim.lanterns if sim._accepts(l) and xz_dist(l["pos"], pl["pos"]) <= T["interact_radius"]]
        if near and sim.alive():
            lan = min(near, key=lambda l: xz_dist(l["pos"], pl["pos"]))
            if lan["lit"]:
                self.set_text(self.h_prompt, "E — Châm dầu (%d/100)" % (lan["fuel_u"] // C.FUEL_U))
            else:
                cost = T["relight_cost"] if lan["ever_lit"] else T["lantern_cost"]
                self.set_text(self.h_prompt, "E — Nạp ánh sáng (%d/%d)" % (lan["deposited"], cost))
        else:
            self.set_text(self.h_prompt, "")
        low = [l for l in sim.lanterns if l["lit"] and l["fuel_u"] < C.LOW_FUEL_U]
        msg = "Gió sắp thổi!" if sim.wind["warn"] else ("Gió mạnh!" if sim.wind["active"] else "")
        if not msg and low:
            msg = "Đèn %s sắp hết dầu!" % ", ".join(l["id"] for l in low)
        self.h_warn.setFg(self.danger())
        self.set_text(self.h_warn, self.warn(msg))
        self._place_icon(self.h_warn_icon, self.h_warn)
        self._update_subtitles(globalClock.getDt())  # noqa: F821
        self._spawn_indicator(globalClock.getDt())  # noqa: F821
        self._offscreen_arrow()

    def subtitle(self, text, seconds):
        for sub_ in self.subs:          # same message again (e.g. two shades in one tick): refresh, don't repeat
            if sub_[0] == text:
                sub_[1] = max(sub_[1], seconds)
                return
        self.subs.append([text, seconds])

    def _update_subtitles(self, dt):
        for sub_ in self.subs:
            sub_[1] -= dt
        self.subs = [x for x in self.subs if x[1] > 0]
        self.set_text(self.h_sub, "  ·  ".join(x[0] for x in self.subs[-2:]))

    def _edge_point(self, world_pt):
        """Screen position on the edge pointing at world_pt, or None when it is on screen."""
        p = self.cam.getRelativePoint(self.render, Point3(*world_pt))
        p2 = Point2()
        if p.y > 0 and self.camLens.project(p, p2) and abs(p2.x) < 0.98 and abs(p2.y) < 0.98:
            return None
        dx, dy = p.x, p.z
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            dy = -1.0
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        ar = self.getAspectRatio()
        k = min((ar - 0.12) / max(abs(dx), 1e-6), 0.82 / max(abs(dy), 1e-6))
        return dx * k, dy * k, math.degrees(math.atan2(dx, dy))

    def _spawn_indicator(self, dt):
        sa = self.spawn_arrow
        shade = next((s for s in self.sim.shades if sa and s["id"] == sa[0]), None)
        if not sa or shade is None:
            self.h_spawn_arrow.hide()
            return
        sa[1] -= dt
        if sa[1] <= 0:
            self.spawn_arrow = None
            self.h_spawn_arrow.hide()
            return
        e = self._edge_point(P(shade["pos"]))
        if e is None:
            self.h_spawn_arrow.hide()
        else:
            self.h_spawn_arrow.setFg(self.danger())
            self.h_spawn_arrow.setPos(e[0], e[1])
            self.h_spawn_arrow.setRoll(-e[2])   # OnscreenText roll is counter-clockwise
            self.h_spawn_arrow.show()

    def _offscreen_arrow(self):
        sim, pl = self.sim, self.sim.player
        unlit = [l for l in sim.lanterns if not l["lit"]]
        if not unlit:
            self.h_arrow.hide()
            return
        tgt = min(unlit, key=lambda l: xz_dist(l["pos"], pl["pos"]))
        p = self.cam.getRelativePoint(self.render, Point3(*P(tgt["pos"], 3.3)))
        p2 = Point2()
        if p.y > 0 and self.camLens.project(p, p2) and abs(p2.x) < 0.98 and abs(p2.y) < 0.98:
            self.h_arrow.hide()
            return
        dx, dy = p.x, p.z
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            dy = -1.0
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        ar = self.getAspectRatio()
        k = min((ar - 0.12) / max(abs(dx), 1e-6), 0.82 / max(abs(dy), 1e-6))
        self.h_arrow.setPos(dx * k, dy * k)
        self.h_arrow.setRoll(-math.degrees(math.atan2(dx, dy)))   # setRoll: rotate in place (setR spins around screen centre)
        self.h_arrow.show()

    # ------------------------------------------------------------ panels
    def _panel(self, title):
        f = DirectFrame(parent=self.aspect2d, frameColor=(0.05, 0.07, 0.16, 0.92), frameSize=(-1.0, 1.0, -0.75, 0.75))
        f.title = self.text(title, parent=f, pos=(0, 0.55), scale=0.11, fg=GOLD)
        f.hide()
        return f

    def _build_panels(self):
        self.panels = {}
        p = self.panels["menu"] = self._panel("Đảo Đèn Lồng")
        self.text("Gom đom đóm · thắp Đèn Lồng Lớn · né Bóng Mực", parent=p, pos=(0, 0.4), scale=0.055)
        self._btn(p, "Bắt đầu", self.new_campaign, (0, 0, 0.18))
        self._btn(p, "Bảng xếp hạng", self.show_leaderboard, (0, 0, 0.02))
        self._btn(p, "Cài đặt", lambda: self.show_panel("settings", back="menu"), (0, 0, -0.14))
        self._btn(p, "Thoát", self.userExit, (0, 0, -0.30))

        p = self.panels["intro"] = self._panel("")
        p.body = self.text("", parent=p, pos=(0, 0.3), scale=0.055, wordwrap=30)
        self._btn(p, "Vào Đêm (Enter)", self.start_night, (0, 0, -0.5))

        p = self.panels["result"] = self._panel("")
        p.body = self.text("", parent=p, pos=(0, 0.3), scale=0.065)
        p.next = self._btn(p, "Đêm kế tiếp", self.next_night, (0, 0, -0.18))
        p.retry = self._btn(p, "Chơi lại Đêm", self.retry_night, (0, 0, -0.18))
        p.save = self._btn(p, "Lưu điểm", lambda: self.show_name_entry("result"), (0, 0, -0.02))
        self._btn(p, "Về menu", self.to_menu, (0, 0, -0.36))

        p = self.panels["dawn"] = self._panel("Bình Minh")
        p.body = self.text("", parent=p, pos=(0, 0.3), scale=0.065)
        self._btn(p, "Lưu điểm", lambda: self.show_name_entry("dawn"), (0, 0, -0.18))
        self._btn(p, "Về menu", self.to_menu, (0, 0, -0.36))

        p = self.panels["name"] = self._panel("Lưu điểm")
        p.info = self.text("", parent=p, pos=(0, 0.38), scale=0.06)
        self.text("Tên (3–12 ký tự: chữ, số, _)", parent=p, pos=(0, 0.2), scale=0.05)
        p.entry = DirectEntry(parent=p, scale=0.07, pos=(-0.45, 0, 0.05), width=13, numLines=1, focus=0,
                              entryFont=self.font, initialText="", command=lambda t: self.save_score())
        p.msg = self.text("", parent=p, pos=(0, -0.1), scale=0.05, fg=DANGER)
        self._btn(p, "Lưu", self.save_score, (0, 0, -0.3))
        self._btn(p, "Bỏ qua", lambda: self.show_panel(self.name_back), (0, 0, -0.46))

        p = self.panels["leaderboard"] = self._panel("Bảng xếp hạng")
        p.rows = self.text("", parent=p, pos=(0, 0.4), scale=0.05, align=TextNode.ACenter)
        self._btn(p, "Về menu", self.to_menu, (0, 0, -0.6))

        p = self.panels["pause"] = self._panel("Tạm dừng")
        self._btn(p, "Tiếp tục", self.toggle_pause, (0, 0, 0.3))
        self._btn(p, "Chơi lại Đêm", self.retry_night, (0, 0, 0.14))
        self._btn(p, "Cài đặt", lambda: self.show_panel("settings", back="pause"), (0, 0, -0.02))
        self._btn(p, "Về menu", self.to_menu, (0, 0, -0.18))

        p = self.panels["settings"] = self._panel("Cài đặt")
        self.text("Âm lượng", parent=p, pos=(-0.45, 0.28), scale=0.06, align=TextNode.ARight)
        p.vol = DirectSlider(parent=p, range=(0, 1), value=self.settings["volume"], pageSize=0.1, scale=0.4,
                             pos=(0.1, 0, 0.3), command=self._on_settings)
        self.text("Độ nhạy chuột", parent=p, pos=(-0.45, 0.08), scale=0.06, align=TextNode.ARight)
        p.sens = DirectSlider(parent=p, range=(0.2, 3.0), value=self.settings["mouse_sensitivity"], pageSize=0.2,
                              scale=0.4, pos=(0.1, 0, 0.1), command=self._on_settings)
        p.vals = self.text("", parent=p, pos=(0, -0.1), scale=0.05)
        p.cb = self._btn(p, "", self._toggle_cb, (0, 0, -0.2), width=14)
        p.rm = self._btn(p, "", lambda: self._toggle("reduce_motion"), (0, 0, -0.31), width=14)
        p.lt = self._btn(p, "", lambda: self._toggle("large_text"), (0, 0, -0.42), width=14)
        self._btn(p, "Phím điều khiển", lambda: self.show_panel("keys"), (0, 0, -0.53), width=14)
        self._btn(p, "Lưu và quay lại", self._settings_back, (0, 0, -0.66), width=14)

        p = self.panels["keys"] = self._panel("Phím điều khiển")
        p.rows = {}
        for i, a in enumerate(ACTIONS):
            y = 0.4 - i * 0.095
            self.text(ACTION_LABELS[a], parent=p, pos=(-0.15, y), scale=0.05, align=TextNode.ARight)
            p.rows[a] = self._btn(p, "", lambda a=a: self._start_capture(a), (0.25, 0, y), scale=0.05, width=9)
        p.msg = self.text("", parent=p, pos=(0, -0.48), scale=0.05, fg=DANGER)
        self._btn(p, "Khôi phục mặc định", self._reset_keys, (-0.45, 0, -0.62), scale=0.05, width=12)
        self._btn(p, "Lưu và quay lại", self._keys_back, (0.45, 0, -0.62), scale=0.05, width=12)
        self._on_settings()
        self._refresh_keys_panel()

    def _on_settings(self):
        p = self.panels.get("settings")
        if not p or not hasattr(p, "sens"):
            return
        self.settings["volume"] = round(float(p.vol["value"]), 2)
        self.settings["mouse_sensitivity"] = round(float(p.sens["value"]), 2)
        self.apply_volume()
        self.set_text(p.vals, "Âm lượng %d%% · Độ nhạy %.2f" % (self.settings["volume"] * 100,
                                                                self.settings["mouse_sensitivity"]))
        if hasattr(p, "cb"):
            on = lambda k: "BẬT" if self.settings.get(k) else "TẮT"  # noqa: E731
            p.cb["text"] = self.tr("Bảng màu dễ phân biệt: %s" % on("colorblind"))
        if hasattr(p, "lt"):
            p.rm["text"] = self.tr("Giảm chuyển động: %s" % on("reduce_motion"))
            p.lt["text"] = self.tr("Chữ lớn (×1.25): %s" % on("large_text"))

    def _toggle(self, key):
        self.settings[key] = not self.settings.get(key)
        if key == "large_text":
            self.apply_text_scale()
        self._on_settings()

    def _start_capture(self, action):
        self.capture_action = action
        self._refresh_keys_panel()

    def _reset_keys(self):
        self.settings["keys"] = dict(DEFAULT_KEYS)
        self.capture_action = None
        self._refresh_keys_panel()

    def _refresh_keys_panel(self):
        p = self.panels.get("keys")
        if not p:
            return
        conflicts = key_conflicts(self.keys())
        bad = {a for acts in conflicts.values() for a in acts}
        for a, btn in p.rows.items():
            label = "Nhấn phím…" if self.capture_action == a else self.keys()[a]
            btn["text"] = self.tr(label)
            btn["frameColor"] = (0.55, 0.12, 0.15, 0.95) if a in bad else (0.16, 0.2, 0.38, 0.95)
        if conflicts:
            msg = "Trùng phím: " + "; ".join("%s → %s" % (k, ", ".join(ACTION_LABELS[x] for x in v))
                                            for k, v in conflicts.items())
            p.msg.setFg(self.danger())
        else:
            msg = "Bấm vào một ô rồi nhấn phím mới (Esc để huỷ)"
            p.msg.setFg(TEXT)
        self.set_text(p.msg, msg)

    def _keys_back(self):
        if key_conflicts(self.keys()):
            self.set_text(self.panels["keys"].msg, "Còn phím trùng — hãy sửa trước khi lưu")
            return
        self.settings.save()
        self._bind_pause_key()
        self.show_panel("settings", back=self.settings_back)

    # ---------------------------------------------------------- leaderboard
    def show_leaderboard(self):
        p = self.panels["leaderboard"]
        rows = ["%2d. %-12s %6d điểm  %d đêm  %s" % (i + 1, e["name"], e["score"], e["nights_won"], e["achieved_at"][:10])
                for i, e in enumerate(self.leaderboard.public())]
        self.set_text(p.rows, "\n".join(rows) if rows else "Chưa có điểm nào.")
        self.show_panel("leaderboard")

    def show_name_entry(self, back):
        self.name_back = back
        p = self.panels["name"]
        self.set_text(p.info, "Điểm: %d · Đêm đã thắng: %d" % (self.campaign.total, self.campaign.nights_won))
        self.set_text(p.msg, "")
        p.entry.enterText("")
        p.entry["focus"] = 1
        self.show_panel("name")

    def save_score(self):
        p = self.panels["name"]
        name = p.entry.get().strip()
        if not valid_name(name):
            self.set_text(p.msg, "Tên không hợp lệ (3–12 ký tự: chữ, số, _)")
            return
        seed = self.fixed_seed if self.fixed_seed is not None else self._seed() // 10
        self.leaderboard.add(name, self.campaign.total, self.campaign.nights_won, seed)
        p.entry["focus"] = 0
        self.show_leaderboard()

    def _toggle_cb(self):
        self.settings["colorblind"] = not self.cb()
        self._on_settings()

    def _settings_back(self):
        self.settings.save()
        self.show_panel(self.settings_back or "menu")

    def show_panel(self, name, back=None):
        if name == "settings":
            self.settings_back = back
        for k, p in self.panels.items():
            p.show() if k == name else p.hide()
        self.current_panel = name

    # ------------------------------------------------------------ flow
    def _seed(self):
        base = self.fixed_seed if self.fixed_seed is not None else int(time.time()) & 0xFFFF
        return base * 10 + self.campaign.night + self.attempt * 100

    def new_campaign(self):
        self.campaign.reset()
        self.attempt = 0
        self.show_intro()

    def show_intro(self):
        name, line = self.campaign.intro()
        p = self.panels["intro"]
        self.set_text(p.title, "Đêm %d — %s" % (self.campaign.night, name))
        self.set_text(p.body, line)
        self.mode = "intro"
        self.show_hud(False)
        self.show_panel("intro")
        self.load_night(self.campaign.night)

    def load_night(self, night):
        self.sim = Simulation(self._seed(), night=night)
        self.inp = InputState()
        self.acc = 0.0
        self.cam_yaw = 0.0
        self.end_timer = None
        self.flash = 0.0
        self.last_count = None
        self.subs, self.spawn_arrow = [], None
        self._build_world(night)
        self._build_dynamic()
        self.set_ambient(self.sim.lit_count, len(self.sim.lanterns))

    def start_night(self):
        self.show_panel(None)
        self.show_hud(True)
        self.mode = "play"

    def retry_night(self):
        self.attempt += 1
        self.show_intro()

    def next_night(self):
        self.campaign.advance()
        self.attempt = 0
        self.show_intro()

    def to_menu(self):
        self.mode = "menu"
        self.show_hud(False)
        self.show_panel("menu")

    def toggle_pause(self):
        if self.mode == "play":
            self.mode = "paused"
            self.show_panel("pause")
        elif self.mode == "paused" and self.current_panel == "pause":
            self.mode = "play"
            self.show_panel(None)

    def _on_enter(self):
        if self.mode == "intro":
            self.start_night()

    def _night_finished(self):
        sim = self.sim
        outcome = self.campaign.night_over(sim.state, sim.score)
        self.show_hud(False)
        if outcome == "dawn":
            p = self.panels["dawn"]
            self.set_text(p.body, "Ba hòn đảo đã sáng lại!\nTổng điểm: %d" % self.campaign.total)
            self.mode = "dawn"
            self.show_panel("dawn")
            return
        p = self.panels["result"]
        won = sim.state == "won"
        reason = {"all_lit": "Mọi Đèn Lồng Lớn đã sáng", "dawn": "Trời sáng mà đảo vẫn chìm trong sương",
                  "no_flames": "Ngọn lửa của Mây đã tắt", "dawn_survived": "Giữ được đảo sáng tới bình minh"}
        self.set_text(p.title, "Đêm %d — %s" % (self.campaign.night, "Thắng" if won else "Thua"))
        self.set_text(p.body, "%s\nĐiểm Đêm: %d\nTổng điểm: %d" % (reason.get(sim.result_reason, ""), sim.score,
                                                                  self.campaign.total))
        p.next.show() if won else p.next.hide()
        p.retry.hide() if won else p.retry.show()
        p.save.hide() if won else p.save.show()
        self.mode = "result"
        self.show_panel("result")

    # ------------------------------------------------------------ main loop
    def _read_input(self, dt):
        down = self.mouseWatcherNode.is_button_down
        sens = self.settings["mouse_sensitivity"]
        turn = (1 if down(KeyboardButton.right()) else 0) - (1 if down(KeyboardButton.left()) else 0)
        self.cam_yaw += turn * 110.0 * dt * sens
        if self.mouseWatcherNode.hasMouse() and down(MouseButton.three()):
            mx = self.mouseWatcherNode.getMouseX()
            if self.last_mouse_x is not None:
                self.cam_yaw += (mx - self.last_mouse_x) * 180.0 * sens
            self.last_mouse_x = mx
        else:
            self.last_mouse_x = None
        i = InputState()
        b = self._down
        x = (1 if b("right") else 0) - (1 if b("left") else 0)
        z = (1 if b("up") else 0) - (1 if b("down") else 0)
        i.move = (float(x), float(z))
        i.cam_yaw_deg = self.cam_yaw % 360.0
        i.jump = b("jump")
        i.dash = b("dash")
        i.interact = b("interact")
        i.pulse = b("pulse") or down(MouseButton.one())
        return i

    def feed(self, inp):
        """Advance one fixed tick (also used by tools)."""
        pl = self.sim.player
        was_grounded = pl["grounded"]
        evs = self.sim.step(inp)
        if was_grounded and not pl["grounded"] and pl["vel"][1] > 0:
            self.play("jump")
        for ev in evs:
            self._on_event(ev)
        t = self.sim.time_left_s
        if 0 < t <= 10 and int(math.ceil(t)) != self.last_count:
            self.last_count = int(math.ceil(t))
            self.play("countdown")
            if self.last_count == 10:
                self.subtitle("Còn 10 giây tới bình minh!", 3.0)
        if self.sim.wind["warn"] and self.sim.sim_tick % C.WIND_EVERY == C.WIND_EVERY - C.WIND_WARN:
            self.play("wind")
            self.subtitle("Gió sắp thổi!", 2.0)
        return evs

    def _on_event(self, ev):
        name = ev["name"]
        if name in EVENT_SFX:
            self.play(EVENT_SFX[name])
        if name == "pulse":
            fx = meshes.ring(0.47, 0.55, 64)
            fx.reparentTo(self.dyn)
            fx.setPos(*P(self.sim.player["pos"], 0.8))
            fx.setLightOff()
            fx.setTwoSided(True)
            fx.setTransparency(TransparencyAttrib.MAlpha)
            self.effects.append([fx, 0.0, "pulse"])
        elif name == "player_hit":
            if not self.settings.get("reduce_motion"):
                self.flash = 0.35
                self.shake = 0.3
        elif name == "shade_spawned":
            self.subtitle("Bóng Mực xuất hiện!", 3.0)
            self.spawn_arrow = [ev["data"]["id"], 4.0]
        elif name == "lantern_lit":
            node = self.lan_nodes[ev["data"]["lantern_id"]]
            fx = meshes.sphere(0.7, 16, 10)
            fx.reparentTo(node["root"])
            fx.setZ(3.3)
            fx.setLightOff()
            fx.setTransparency(TransparencyAttrib.MAlpha)
            self.effects.append([fx, 0.0, "burst"])
        elif name == "game_over":
            self.play("win" if ev["data"]["result"] == "won" else "lose")
            self.end_timer = 1.5

    def _update(self, task):
        dt = min(globalClock.getDt(), 0.25)  # noqa: F821 (Panda3D builtin)
        if self.frame_hook:
            self.frame_hook(dt)
        if self.sim is None:
            return task.cont
        if self.mode == "play":
            if self.sim.state == "playing":
                self.acc += dt
                if self.autoplay is None:
                    self.inp = self._read_input(dt)
                while self.acc >= C.DT and self.sim.state == "playing":
                    if self.autoplay is not None:
                        self.inp = self.autoplay(self.sim)
                    self.feed(self.inp)
                    self.acc -= C.DT
            elif self.end_timer is not None:
                self.end_timer -= dt
                if self.end_timer <= 0:
                    self.end_timer = None
                    self._night_finished()
        self._sync(dt)
        return task.cont

    def _sync_entities(self, now):
        sim = self.sim
        for m in sim.motes:
            if m["id"] not in self.mote_nodes:
                self._add_mote(m)
        alive = {m["id"] for m in sim.motes}
        for key in list(self.mote_nodes):
            if key not in alive:
                self.mote_nodes.pop(key).removeNode()
        for m in sim.motes:
            n = self.mote_nodes[m["id"]]
            ph = n.getPythonTag("phase")
            n.setPos(*P(m["pos"], 0.55 + 0.2 * math.sin(now * 2.2 + ph)))
            if m["kind"] == "dropped" and m["ttl"] < 120:
                n.setAlphaScale(0.4 + 0.6 * (int(now * 8) % 2))
        for s in sim.shades:
            if s["id"] not in self.shade_nodes:
                self._add_shade(s)
            entry = self.shade_nodes[s["id"]]
            root, blob, rim, look = entry
            root.setPos(*P(s["pos"], 0.12 * math.sin(now * 3 + len(s["id"]))))
            root.lookAt(*P(sim.player["pos"], s["pos"][1]))
            st = s["state"]
            look_now = (st == "stunned", self.cb())
            if look != look_now:             # only touch colours when they change (perf)
                entry[3] = look_now
                rim.setColor(*(CB_RIM if look_now[1] else PAL["shade_rim"]))
                blob.setColor(*(PAL["shade_stunned"] if look_now[0] else PAL["shade_body"]))
            if st == "spawning":
                root.setScale(0.35 + 0.65 * (1 - s["t"] / float(C.SHADE_SPAWNING_TICKS)))
            else:
                root.setScale(0.8 if st == "stunned" else 1.0)
        for d in sim.drifters:
            if d["id"] not in self.drifter_nodes:
                self._add_drifter(d)
            root, segs = self.drifter_nodes[d["id"]]
            if d["state"] == "removed":
                root.hide()
                continue
            root.setPos(*P(d["pos"]))
            for i, seg in enumerate(segs):
                seg.setPos(-i * 0.45, 0, 0.35 * math.sin(now * 6 - i * 0.9))
                seg.setR(20 * math.sin(now * 6 - i * 0.9))
            root.setH(now * 90 % 360)
        for c in sim.charms:
            n = self.charm_nodes[c["id"]]
            if c["available"]:
                n.show()
                n.setPos(*P(c["pos"], 1.0 + 0.15 * math.sin(now * 2)))
                n.setH(now * 60 % 360)
            else:
                n.hide()

    def _sync(self, dt):
        if self.sim is None or self.dyn is None:
            return
        sim, pl = self.sim, self.sim.player
        now = globalClock.getFrameTime()  # noqa: F821
        self.player_np.setPos(*P(pl["pos"]))
        fx_, fz_ = pl["facing"]
        self.player_np.setH(-math.degrees(math.atan2(fx_, fz_)))
        glow = 0.35 + 0.65 * min(1.0, pl["carried"] / 10.0)
        self.hand_lantern.setColor(1.0, 0.65 + 0.3 * glow, 0.3 * glow, 1)
        self.hand_lantern.setScale(0.8 + 0.6 * glow)
        self.player_light.setColor((1.2 * glow, 0.8 * glow, 0.35 * glow, 1))
        if pl["dead_wait"] > 0:
            self.player_np.hide()
        else:
            self.player_np.show()
            self.player_np.setAlphaScale(0.45 if pl["invuln"] > 0 and int(now * 12) % 2 else 1.0)

        changed = False
        for lan in sim.lanterns:
            node = self.lan_nodes[lan["id"]]
            state = (lan["lit"], lan["deposited"])
            if node["state"] != state:
                node["state"] = state
                changed = True
                if lan["lit"]:
                    node["body"].setColor(*PAL["lantern_lit"])
                    node["body"].setLightOff()
                    node["core"].show()
                    node["safe"].show()
                    self.render.setLight(node["light"])
                else:
                    f = lan["deposited"] / float(T["lantern_cost"])
                    off = PAL["lantern_off"]
                    node["body"].setColor(off[0] + 0.3 * f, off[1] + 0.2 * f, off[2], 1)
                    node["body"].clearLight()
                    node["core"].hide()
                    node["safe"].hide()
                    self.render.clearLight(node["light"])
        blink_on = int(now * 2) % 2 == 0          # 1 Hz: on 0.5 s, off 0.5 s
        for lan in sim.lanterns:
            node = self.lan_nodes[lan["id"]]
            low = lan["lit"] and lan["fuel_u"] < C.LOW_FUEL_U
            if lan["lit"]:
                node["bar"].show()
                node["fill"].setSx(max(0.001, lan["fuel_u"] / float(C.FUEL_MAX_U)))
                node["fill"].setColor(*(self.danger() if low else GOLD))
            else:
                node["bar"].hide()
            alpha = 0.25 if (low and not blink_on) else 1.0
            node["bar"].setAlphaScale(alpha)
            node["body"].setAlphaScale(alpha)
            if alpha < 1:
                node["body"].setTransparency(TransparencyAttrib.MAlpha)
            node["safe"].show() if (sim._safe(lan) and not self.bench) else node["safe"].hide()   # fuel < 30: no zone
            squash = self.cb() and not lan["lit"]
            node["body"].setScale(1, 1, 1.15 * (0.8 if squash else 1.0))
            node["notch"].show() if squash else node["notch"].hide()
        if changed:
            self.set_ambient(sim.lit_count, len(sim.lanterns))
        self._sync_entities(now)

        unlit = [l for l in sim.lanterns if not l["lit"]]
        if unlit and sim.state == "playing" and pl["dead_wait"] == 0 and not self.bench:
            tgt = min(unlit, key=lambda l: xz_dist(l["pos"], pl["pos"]))
            self.compass.show()
            self.compass.setPos(*P(pl["pos"], 2.45))
            ang = math.degrees(math.atan2(tgt["pos"][0] - pl["pos"][0], tgt["pos"][2] - pl["pos"][2]))
            self.compass.setHpr(-ang, -90, 0)
        else:
            self.compass.hide()

        windy = sim.wind["warn"] or sim.wind["active"]
        a = math.radians(sim.wind["dir_deg"])
        for leaf in self.leaves:
            node, ph, r, h = leaf
            if windy:
                along = (now * 6 + r * 3) % 16 - 8
                node.show()
                node.setPos(pl["pos"][0] + math.cos(a) * along - math.sin(a) * (r - 6) * 0.6,
                            pl["pos"][2] + math.sin(a) * along + math.cos(a) * (r - 6) * 0.6,
                            pl["pos"][1] + h + 0.3 * math.sin(now * 4 + ph))
                node.setHpr(now * 200 + ph * 50, now * 150, 0)
            else:
                node.hide()

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
        sky = PAL["sky"]
        self.setBackgroundColor(sky[0] + self.flash, sky[1], sky[2] + self.flash * 0.6, 1)

        th = math.radians(self.cam_yaw)
        fxc, fzc = math.sin(th), math.cos(th)
        px, py, pz = P(pl["pos"])
        if self.bench:
            cp = bench_scene.camera_pose(self.bench_t)
            self.camera.setPos(*P(cp))
            self.camera.lookAt(0, 0, 0)
        else:
            self.camera.setPos(px - fxc * 12.0, py - fzc * 12.0, pz + 6.0)
            self.camera.lookAt(px, py, pz + 2.0)
            if self.shake > 0:
                self.shake = max(0.0, self.shake - dt)
                amp = 0.25 * self.shake / 0.3
                self.camera.setPos(self.camera, math.sin(now * 90) * amp, 0, math.cos(now * 77) * amp)
        if self.mode in ("play", "paused"):
            self._hud(now)


def run_bench(seed, duration, out_path):
    """Ticket-04 benchmark: fixed scene, orbiting camera, 3 s warm-up, then exactly `duration` s measured."""
    from panda3d.core import loadPrcFileData
    started = sysinfo.process_start_epoch()
    loadPrcFileData("", "window-title Dao Den Long (bench)\nwin-size 1280 720\nfullscreen 0\nsync-video 0\n"
                        "audio-library-name null\n")
    g = Game(seed=seed, bench=True)
    g.sim = bench_scene.bench_sim(seed)
    g.inp = InputState()
    g.acc, g.end_timer, g.last_count = 0.0, None, None
    g._build_world(1)
    g._build_dynamic()
    g.set_ambient(g.sim.lit_count, len(g.sim.lanterns))
    g.show_panel(None)
    g.show_hud(True)
    g.mode = "play"
    g.bench_t = 0.0
    st = {"first": None, "last": None, "dts": [], "mem": 0.0, "measured": 0.0}

    def hook(_dt):
        now = time.perf_counter()
        if st["first"] is None:                       # first frame of the bench scene
            st["first"] = st["last"] = now
            st["load_ms"] = int(round((time.time() - started) * 1000))
            return
        dt = now - st["last"]
        st["last"] = now
        g.bench_t = now - st["first"]
        if g.bench_t <= bench_scene.WARMUP_S:
            return
        st["dts"].append(dt * 1000.0)
        st["measured"] += dt
        st["mem"] = max(st["mem"], sysinfo.rss_mb())
        if st["measured"] >= duration:
            gsg = g.win.getGsg()
            out = {"contract_version": C.CONTRACT_VERSION}
            out.update(bench_scene.frame_stats(st["dts"]))
            out.update({"load_ms": st["load_ms"], "peak_mem_mb": round(st["mem"], 1), "vsync_off": True,
                        "renderer": "Panda3D %s, %s (%s %s)" % (__import__("panda3d").__version__,
                                                               gsg.getDriverRenderer(), gsg.getDriverVendor(),
                                                               gsg.getDriverVersion()),
                        "os": sysinfo.os_description(),
                        "scene": {"shades": len(g.sim.shades), "motes": len(g.sim.motes),
                                  "lit": [l["id"] for l in g.sim.lanterns if l["lit"]], "seed": seed,
                                  "duration_s": duration, "warmup_s": bench_scene.WARMUP_S}})
            with open(out_path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)
            print(json.dumps(out))
            g.frame_hook = None
            g.userExit()
    g.frame_hook = hook
    g.run()


def fps_probe(night, seconds, seed=3):
    """Run the real client with the autopilot and report frame statistics as JSON."""
    from panda3d.core import loadPrcFileData
    loadPrcFileData("", "window-title Dao Den Long (fps probe)\nwin-size 1280 720\nsync-video 0\n")
    g = Game(seed=seed, autoplay=True)
    g.campaign.night = night
    g.show_intro()
    g.start_night()
    frames, state = [], {"t": 0.0}

    def hook(dt):
        state["t"] += dt
        if state["t"] > 2.0:
            frames.append(dt)
        if state["t"] > 2.0 + seconds:
            n = len(frames)
            out = {"night": night, "frames": n, "avg_fps": round(n / sum(frames), 1),
                   "frame_ms_p95": round(sorted(frames)[int(0.95 * (n - 1))] * 1000, 2),
                   "resolution": "1280x720", "vsync": False}
            print(json.dumps(out))
            g.frame_hook = None
            g.userExit()
    g.frame_hook = hook
    g.run()


def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description="Dao Den Long - 3D client")
    ap.add_argument("--seed", type=int, default=None, help="fixed world seed (default: random each play)")
    ap.add_argument("--fps-probe", type=float, metavar="SECONDS", help="measure FPS with the autopilot and exit")
    ap.add_argument("--night", type=int, default=1, choices=(1, 2, 3))
    ap.add_argument("--bench", action="store_true", help="Ticket-04 benchmark scene (use with --duration --out)")
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--out", default="bench.json")
    ap.add_argument("--export-leaderboard", metavar="FILE", help="write the local leaderboard as JSON and exit")
    a = ap.parse_args(argv)
    if a.export_leaderboard:
        Leaderboard().export(a.export_leaderboard)
        return
    if a.bench:
        run_bench(a.seed if a.seed is not None else 42, a.duration, a.out)
        return
    if a.fps_probe:
        fps_probe(a.night, a.fps_probe)
        return
    from panda3d.core import loadPrcFileData
    loadPrcFileData("", "window-title Dao Den Long\nwin-size 1280 720\nframebuffer-multisample 1\nmultisamples 4\n")
    Game(seed=a.seed).run()
