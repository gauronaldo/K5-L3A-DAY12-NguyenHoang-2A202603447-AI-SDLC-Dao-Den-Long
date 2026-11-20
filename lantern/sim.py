"""Deterministic game simulation (no rendering), contract v1.1. Shared by the 3D client and headless mode.

Coordinates: metres, Y up. One call to step() = one tick of 1/60 s.
The body of step() follows the mandatory 12-step order of Ticket-02.
"""
import math
import random
import re

from . import config as C
from . import world

T = C.TUNING
EPS = 1e-9


def xz_dist(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def dist3(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def within(a, b, r):
    """Contract: "within radius r" means XZ distance <= r (tolerant to float rounding)."""
    return xz_dist(a, b) <= r + EPS


def id_key(s):
    """Natural order for ids: S2 < S10."""
    m = re.match(r"^(.*?)(\d+)$", s)
    return (m.group(1), int(m.group(2)), s) if m else (s, -1, s)


class InputState:
    """Held input for one tick. Buttons trigger on a false -> true change."""

    BUTTONS = ("jump", "interact", "pulse", "dash", "pause")
    __slots__ = ("move", "cam_yaw_deg") + BUTTONS

    def __init__(self):
        self.move = (0.0, 0.0)
        self.cam_yaw_deg = 0.0
        for b in self.BUTTONS:
            setattr(self, b, False)

    def copy(self):
        c = InputState()
        c.move, c.cam_yaw_deg = self.move, self.cam_yaw_deg
        for b in self.BUTTONS:
            setattr(c, b, getattr(self, b))
        return c


def world_move(move, yaw_deg):
    """Contract C: rotate [x, z] by camera yaw, normalise if longer than 1."""
    x, z = float(move[0]), float(move[1])
    th = math.radians(yaw_deg)
    wx = x * math.cos(th) + z * math.sin(th)
    wz = -x * math.sin(th) + z * math.cos(th)
    n = math.hypot(wx, wz)
    if n > 1.0:
        wx, wz = wx / n, wz / n
    return wx, wz


def _unit(dx, dz, default=(1.0, 0.0)):
    d = math.hypot(dx, dz)
    return (dx / d, dz / d) if d > 1e-9 else default


class Simulation:
    def __init__(self, seed=0, scenario=None, night=1):
        scenario = scenario or {}
        self.night = night
        self.N = C.NIGHTS[night]
        self.rng = random.Random(seed * 1009 + night)
        self.state = "playing"
        self.result_reason = None
        self.paused = False
        self.tick = 0
        self.sim_tick = 0
        self.score = 0
        self.events = []
        self._prev = InputState()
        self._started = False
        self._mote_n = 0
        self._shade_n = 0
        self._drifter_n = 0
        self.total_ticks = int(round(float(scenario.get("time_left_s", self.N["duration_s"])) * C.TICK_RATE))

        p = scenario.get("player", {})
        start = [float(v) for v in self.N["start"]]
        self.player = {
            "pos": [float(v) for v in p.get("pos", start)], "vel": [0.0, 0.0, 0.0], "grounded": True,
            "facing": (0.0, 1.0), "flames": int(p.get("flames", T["flames"])), "carried": int(p.get("carried", 0)),
            "invuln": int(p.get("invuln_ticks", 0)), "dash_cd": int(p.get("dash_cd_ticks", 0)), "dash_left": 0,
            "dash_dir": (0.0, 1.0), "pulse_cd": int(p.get("pulse_cd_ticks", 0)), "charm": int(p.get("charm_ticks", 0)),
            "launch": None, "dead_wait": 0, "respawn_due": False,
        }
        g = world.ground_height(night, self.player["pos"][0], self.player["pos"][2])
        self.player["grounded"] = g is not None and abs(self.player["pos"][1] - g) < 1e-6

        self.lanterns = [{"id": "L%d" % (i + 1), "pos": [float(v) for v in pos], "lit": False, "deposited": 0}
                         for i, pos in enumerate(self.N["lanterns"])]
        for upd in scenario.get("lanterns", []):
            lan = next((l for l in self.lanterns if l["id"] == upd["id"]), None)
            if lan is None:
                lan = {"id": upd["id"], "pos": [0.0, 0.0, 0.0], "lit": False, "deposited": 0}
                self.lanterns.append(lan)
            if "pos" in upd:
                lan["pos"] = [float(v) for v in upd["pos"]]
            if "deposited" in upd:
                lan["deposited"] = int(upd["deposited"])
            if "lit" in upd:
                lan["lit"] = bool(upd["lit"])
        self.lanterns.sort(key=lambda l: id_key(l["id"]))

        self.random_motes = bool(scenario.get("random_motes", True))
        self.random_shades = bool(scenario.get("random_shades", True))
        self.random_drifters = bool(scenario.get("random_drifters", self.N["drifters"]))
        self.wind_enabled = bool(scenario.get("wind_enabled", self.N["wind"]))
        self.wind = {"active": False, "dir_deg": 0.0, "warn": False}

        # fixed generation order: motes -> shades -> drifters -> charms
        self.motes = []
        if "motes" in scenario:
            for m in scenario["motes"]:
                if isinstance(m, (list, tuple)):
                    m = {"pos": m}
                self._add_mote(m["pos"], m.get("kind", "random"), m.get("ttl_ticks"))
        elif self.random_motes:
            pts = self.rng.sample(range(len(self.N["mote_points"])), min(C.MOTE_START, len(self.N["mote_points"])))
            for i in sorted(pts):
                self._add_mote(self.N["mote_points"][i], "random", None, point=i)

        self.shades = []
        for s in scenario.get("shades", []):
            sid = s.get("id") or self._new_id("S", self.shades)
            sh = self._make_shade(sid, [float(v) for v in s["pos"]], s.get("state", "wander"))
            sh["t"] = int(s.get("state_ticks_left", sh["t"]))
            if sh["state"] == "stunned":
                sh["push_left"] = 0
            self.shades.append(sh)

        self.drifters = []
        for d in scenario.get("drifters", []):
            did = d.get("id") or self._new_id("D", self.drifters)
            dr = self._make_drifter(did, [float(v) for v in d["pos"]])
            dr["state"] = d.get("state", "idle")
            dr["stolen"] = int(d.get("stolen", 0))
            if dr["state"] == "flee":
                dr["t"] = int(d.get("state_ticks_left", C.DRIFTER_FLEE_TICKS))
            self.drifters.append(dr)

        if "charms" in scenario:
            self.charms = []
            for i, c in enumerate(scenario["charms"]):
                pos = c.get("pos") or (self.N["charms"][i] if i < len(self.N["charms"]) else [0, 0, 0])
                self.charms.append({"id": c.get("id", "C%d" % (i + 1)), "pos": [float(v) for v in pos],
                                    "available": bool(c.get("available", True)),
                                    "respawn": int(c.get("respawn_ticks", 0))})
        else:
            self.charms = [{"id": "C%d" % (i + 1), "pos": [float(v) for v in pos], "available": True, "respawn": 0}
                           for i, pos in enumerate(self.N["charms"])]

    # ------------------------------------------------------------------ helpers
    def _new_id(self, prefix, existing):
        used = {e["id"] for e in existing}
        attr = {"S": "_shade_n", "D": "_drifter_n"}[prefix]
        while True:
            n = getattr(self, attr) + 1
            setattr(self, attr, n)
            if "%s%d" % (prefix, n) not in used:
                return "%s%d" % (prefix, n)

    def _add_mote(self, pos, kind, ttl, point=None):
        self._mote_n += 1
        g = world.ground_height(self.night, pos[0], pos[2])
        y = float(pos[1]) if len(pos) > 1 and pos[1] is not None else (g or 0.0)
        m = {"id": "M%d" % self._mote_n, "pos": [float(pos[0]), y, float(pos[2])], "kind": kind,
             "ttl": ttl if kind == "dropped" else None, "point": point}
        if kind == "dropped" and m["ttl"] is None:
            m["ttl"] = C.DROP_TTL
        self.motes.append(m)
        return m

    def _make_shade(self, sid, pos, state="spawning"):
        t = C.SHADE_SPAWNING_TICKS if state == "spawning" else (C.STUN_TICKS if state == "stunned" else
                                                               (C.RECOIL_TICKS if state == "recoil" else 0))
        return {"id": sid, "pos": pos, "state": state, "t": t, "push_left": 0, "push_dir": (1.0, 0.0),
                "recoil_dir": (1.0, 0.0), "evict": 0, "evict_lan": None}

    def _make_drifter(self, did, pos):
        return {"id": did, "pos": pos, "state": "idle", "stolen": 0, "t": 0, "target": None}

    def _emit(self, name, data):
        self.events.append({"type": "event", "tick": self.tick, "name": name, "data": data})

    def _shade_speed(self):
        return self.N["shade_speed"]

    def _lit(self):
        return [l for l in self.lanterns if l["lit"]]

    def _safe_lanterns(self):
        return self._lit()

    def _enforce_safe(self, s):
        r = T["safe_radius"] + C.SAFE_EPS
        for _ in range(2):
            for lan in self._safe_lanterns():
                dx, dz = s["pos"][0] - lan["pos"][0], s["pos"][2] - lan["pos"][2]
                d = math.hypot(dx, dz)
                if d < r:
                    ux, uz = _unit(dx, dz)
                    s["pos"][0] = lan["pos"][0] + ux * r
                    s["pos"][2] = lan["pos"][2] + uz * r

    def _hover(self, e, h):
        g = world.ground_height(self.night, e["pos"][0], e["pos"][2])
        if g is not None:
            e["pos"][1] = g + h

    def _step_toward(self, e, tx, tz, speed, stop=0.0):
        dx, dz = tx - e["pos"][0], tz - e["pos"][2]
        d = math.hypot(dx, dz)
        if d <= stop + 1e-9:
            return
        mv = min(speed * C.DT, d - stop)
        e["pos"][0] += dx / d * mv
        e["pos"][2] += dz / d * mv

    @property
    def time_left_s(self):
        return (self.total_ticks - self.sim_tick) / C.TICK_RATE

    @property
    def lit_count(self):
        return sum(1 for l in self.lanterns if l["lit"])

    def capacity(self):
        return T["carry_capacity"]

    def alive(self):
        return self.player["dead_wait"] == 0 and not self.player["respawn_due"]

    # --------------------------------------------------------------------- step
    def step(self, inp):
        """Advance one tick using held input `inp` (InputState). Returns this tick's events."""
        self.events = []
        if self.state != "playing":
            return self.events
        self.tick += 1
        prev, self._prev = self._prev, inp.copy()
        edge = {b: getattr(inp, b) and not getattr(prev, b) for b in InputState.BUTTONS}
        if not self._started:
            self._started = True
            self._emit("night_start", {"night": self.night})

        # 1. input: pause first
        if edge["pause"]:
            self.paused = not self.paused
            self._emit("paused" if self.paused else "resumed", {})
            if self.paused:
                return self.events
        elif self.paused:
            return self.events

        pl = self.player
        # 2. counters
        self.sim_tick += 1
        for k in ("invuln", "dash_cd", "pulse_cd", "charm"):
            if pl[k] > 0:
                pl[k] -= 1
        if pl["dead_wait"] > 0:
            pl["dead_wait"] -= 1
            if pl["dead_wait"] == 0:
                pl["respawn_due"] = True
        for s in self.shades:
            if s["state"] in ("spawning", "stunned", "recoil") and s["t"] > 0:
                s["t"] -= 1
                if s["t"] == 0:
                    self._shade_timer_done(s)
        for d in self.drifters:
            if d["state"] == "flee" and d["t"] > 0:
                d["t"] -= 1
                if d["t"] == 0:
                    d["state"] = "removed"
        keep = []
        for m in self.motes:
            if m["kind"] == "dropped":
                m["ttl"] -= 1
                if m["ttl"] <= 0:
                    continue
            keep.append(m)
        self.motes = keep
        for c in self.charms:
            if not c["available"] and c["respawn"] > 0:
                c["respawn"] -= 1
                if c["respawn"] == 0:
                    c["available"] = True
        self._update_wind()

        # 3. move Mây, then fall check
        self._move_player(inp, edge)

        # 4. pick up motes and charms
        if self.alive():
            kept = []
            for m in self.motes:
                if (pl["carried"] < self.capacity() and within(pl["pos"], m["pos"], T["pickup_radius"])
                        and abs(pl["pos"][1] - m["pos"][1]) <= C.PICKUP_DY + EPS):
                    pl["carried"] += 1
                    self._emit("mote_picked", {"carried": pl["carried"]})
                else:
                    kept.append(m)
            self.motes = kept
            for c in self.charms:
                if (c["available"] and within(pl["pos"], c["pos"], T["pickup_radius"])
                        and abs(pl["pos"][1] - c["pos"][1]) <= C.PICKUP_DY + EPS):
                    c["available"], c["respawn"] = False, C.CHARM_RESPAWN
                    pl["charm"] = C.CHARM_TICKS
                    pl["dash_cd"] = 0
                    self._emit("charm_picked", {"charm_id": c["id"], "charm_ticks": C.CHARM_TICKS})

        # 5. interact with lanterns
        newly_lit = []
        if edge["interact"] and self.alive() and pl["carried"] > 0:
            newly_lit = self._interact()

        # 6. safe zones
        self._update_safe(newly_lit)

        # 7. light pulse
        if edge["pulse"] and self.alive() and pl["pulse_cd"] == 0 and pl["carried"] >= T["pulse_cost"]:
            self._pulse()

        # 8. move shades and drifters
        for s in sorted(self.shades, key=lambda s: id_key(s["id"])):
            self._move_shade(s)
        for d in self.drifters:
            self._move_drifter(d)

        # 9. contacts: drifters steal first, then shades hit (ascending id)
        if self.alive():
            self._contacts()

        # 10. scheduled spawns
        self._spawns()

        # 11. win / lose
        self._check_end()
        return self.events

    # ------------------------------------------------------------------ pieces
    def _shade_timer_done(self, s):
        if s["state"] == "recoil":
            s["state"] = "chase" if (self.alive() and xz_dist(s["pos"], self.player["pos"]) <= C.SHADE_DETECT) else "wander"
        else:  # spawning / stunned
            s["state"] = "wander"
        s["push_left"] = 0

    def _update_wind(self):
        self.wind["active"] = False
        self.wind["warn"] = False
        if not self.wind_enabled:
            return
        t = self.sim_tick
        k = (t + C.WIND_WARN) // C.WIND_EVERY
        start = k * C.WIND_EVERY
        if k >= 1 and t == start - C.WIND_WARN:
            self.wind["dir_deg"] = round(self.rng.uniform(0.0, 360.0), 3)
        if k >= 1 and start - C.WIND_WARN <= t < start:
            self.wind["warn"] = True
        j = t // C.WIND_EVERY
        if j >= 1 and t - j * C.WIND_EVERY < C.WIND_TICKS:
            self.wind["active"] = True

    def _can_occupy(self, x, z, y):
        if world.blocked_xz(self.night, x, z):
            return False
        g = world.ground_height(self.night, x, z)
        return g is None or g <= y + C.STEP_UP

    def _move_player(self, inp, edge):
        pl = self.player
        if pl["respawn_due"]:
            pl["respawn_due"] = False
            pl["pos"] = [float(v) for v in self.N["start"]]
            pl["vel"] = [0.0, 0.0, 0.0]
            pl["grounded"], pl["launch"], pl["dash_left"] = True, None, 0
            pl["invuln"] = C.INVULN_TICKS
            return
        if pl["dead_wait"] > 0:
            pl["vel"] = [0.0, 0.0, 0.0]
            return
        wx, wz = world_move(inp.move, inp.cam_yaw_deg)
        moving = math.hypot(wx, wz) > 1e-9
        if moving:
            pl["facing"] = _unit(wx, wz)
        if edge["jump"] and pl["grounded"]:
            pl["vel"][1] = C.JUMP_SPEED
            pl["grounded"] = False
        if edge["dash"] and pl["dash_left"] == 0 and (pl["dash_cd"] == 0 or pl["charm"] > 0):
            pl["dash_left"] = C.DASH_TICKS
            pl["dash_dir"] = _unit(wx, wz) if moving else pl["facing"]
            pl["dash_cd"] = 0 if pl["charm"] > 0 else C.DASH_CD_TICKS
            self._emit("dash", {})

        dashing = pl["dash_left"] > 0
        if dashing:
            hx, hz = pl["dash_dir"][0] * T["dash_speed"], pl["dash_dir"][1] * T["dash_speed"]
            pl["vel"][1] = 0.0
            pl["dash_left"] -= 1
        elif pl["launch"] is not None:
            hx, hz = pl["launch"]
        else:
            sp = C.CHARM_SPEED if pl["charm"] > 0 else T["player_speed"]
            hx, hz = wx * sp, wz * sp
        if self.wind["active"]:
            a = math.radians(self.wind["dir_deg"])
            hx += math.cos(a) * C.WIND_SPEED
            hz += math.sin(a) * C.WIND_SPEED

        x, y, z = pl["pos"]
        nx, nz = x + hx * C.DT, z + hz * C.DT
        if self._can_occupy(nx, nz, y):
            x, z = nx, nz
        elif self._can_occupy(nx, z, y):
            x = nx
        elif self._can_occupy(x, nz, y):
            z = nz
        g = world.ground_height(self.night, x, z)
        if pl["grounded"]:
            if g is None or g < y - C.STEP_UP:
                pl["grounded"] = False
            else:
                y = g
        if not pl["grounded"]:
            if not dashing:
                pl["vel"][1] -= C.GRAVITY * C.DT
                y += pl["vel"][1] * C.DT
            if g is not None and y <= g and pl["vel"][1] <= 0:
                y, pl["vel"][1], pl["grounded"], pl["launch"] = g, 0.0, True, None
        pl["pos"] = [x, y, z]
        pl["vel"][0], pl["vel"][2] = hx, hz
        if pl["grounded"]:
            pl["vel"][1] = 0.0
            for pad in self.N["pads"]:
                if math.hypot(x - pad["pos"][0], z - pad["pos"][2]) <= 1.0 + EPS and abs(y - pad["pos"][1]) < 0.05:
                    if "dir" in pad:
                        ux, uz = pad["dir"]
                    else:
                        ux, uz = _unit(pad["toward"][0] - pad["pos"][0], pad["toward"][2] - pad["pos"][2])
                    pl["launch"] = (ux * pad["h"], uz * pad["h"])
                    pl["vel"][1] = pad["vy"]
                    pl["grounded"] = False
                    break

        if pl["pos"][1] < C.FALL_Y:
            lost = pl["carried"]
            pl["carried"] = 0
            pl["flames"] -= 1
            pl["dead_wait"] = C.FALL_WAIT
            pl["vel"], pl["launch"], pl["dash_left"] = [0.0, 0.0, 0.0], None, 0
            self._emit("player_hit", {"by": "fall", "flames": pl["flames"], "dropped": 0, "lost": lost})

    def _interact(self):
        pl = self.player
        cands = [l for l in self.lanterns if not l["lit"] and within(pl["pos"], l["pos"], T["interact_radius"])]
        if not cands:
            return []
        lan = min(cands, key=lambda l: (xz_dist(pl["pos"], l["pos"]), id_key(l["id"])))
        amount = min(pl["carried"], T["lantern_cost"] - lan["deposited"])
        if amount <= 0:
            return []
        pl["carried"] -= amount
        lan["deposited"] += amount
        self.score += C.SCORE["per_mote"] * amount
        self._emit("deposit", {"lantern_id": lan["id"], "amount": amount, "deposited": lan["deposited"]})
        if lan["deposited"] >= T["lantern_cost"]:
            lan["lit"] = True
            self.score += C.SCORE["per_lantern"]
            self._emit("lantern_lit", {"lantern_id": lan["id"]})
            return [lan]
        return []

    def _update_safe(self, newly):
        for lan in newly:
            for s in self.shades:
                if xz_dist(s["pos"], lan["pos"]) < T["safe_radius"] + C.SAFE_EPS:
                    s["evict"], s["evict_lan"] = C.EVICT_TICKS, lan["id"]

    def _pulse(self):
        pl = self.player
        pl["carried"] -= T["pulse_cost"]
        pl["pulse_cd"] = C.PULSE_CD_TICKS
        center = [pl["pos"][0], pl["pos"][1] + C.PULSE_CENTER_Y, pl["pos"][2]]
        stunned = []
        for s in sorted(self.shades, key=lambda s: id_key(s["id"])):
            if dist3(center, s["pos"]) <= T["pulse_radius"] + EPS:
                s["state"], s["t"] = "stunned", C.STUN_TICKS
                s["push_left"] = C.PUSH_TICKS
                s["push_dir"] = _unit(s["pos"][0] - pl["pos"][0], s["pos"][2] - pl["pos"][2])
                self.score += C.SCORE["per_stun"]
                stunned.append(s["id"])
        self._emit("pulse", {"stunned_ids": stunned})
        for d in self.drifters:
            if d["state"] in ("chase", "flee") and dist3(center, d["pos"]) <= T["pulse_radius"] + EPS:
                if d["state"] == "chase":
                    d["state"], d["t"] = "flee", C.DRIFTER_FLEE_TICKS
                elif d["stolen"] > 0:
                    amount, d["stolen"] = d["stolen"], 0
                    for _ in range(amount):
                        self._add_mote([d["pos"][0], None, d["pos"][2]], "dropped", C.DROP_TTL)
                    d["t"] = C.DRIFTER_DROP_VANISH
                    self._emit("drifter_drop", {"drifter_id": d["id"], "amount": amount})

    def _nearest_unlit(self, pos):
        unlit = [l for l in self.lanterns if not l["lit"]]
        if not unlit:
            return None
        return min(unlit, key=lambda l: (xz_dist(pos, l["pos"]), id_key(l["id"])))

    def _wander_target(self, s):
        return self._nearest_unlit(s["pos"])

    def _move_shade(self, s):
        pl = self.player
        if s["evict"] > 0:
            lan = next(l for l in self.lanterns if l["id"] == s["evict_lan"])
            dx, dz = s["pos"][0] - lan["pos"][0], s["pos"][2] - lan["pos"][2]
            d = math.hypot(dx, dz)
            ux, uz = _unit(dx, dz)
            target = T["safe_radius"] + C.SAFE_EPS
            if d < target:
                mv = (target - d) / s["evict"]
                s["pos"][0] += ux * mv
                s["pos"][2] += uz * mv
            s["evict"] -= 1
            if s["evict"] == 0:
                s["evict_lan"] = None
            self._hover(s, C.SHADE_HOVER)
            return
        st = s["state"]
        if st == "spawning":
            return
        if st == "stunned":
            if s["push_left"] > 0:
                step = T["pulse_push_m"] / C.PUSH_TICKS
                nx, nz = s["pos"][0] + s["push_dir"][0] * step, s["pos"][2] + s["push_dir"][1] * step
                if world.blocked_xz(self.night, nx, nz):
                    s["push_left"] = 0
                else:
                    s["pos"][0], s["pos"][2] = nx, nz
                    s["push_left"] -= 1
        elif st == "recoil":
            self._recoil_step(s)
        else:
            d = xz_dist(s["pos"], pl["pos"])
            if st == "wander" and self.alive() and d <= C.SHADE_DETECT + EPS:
                s["state"] = st = "chase"
            elif st == "chase" and (not self.alive() or d > C.SHADE_GIVEUP + EPS):
                s["state"] = st = "wander"
            if st == "chase":
                self._step_toward(s, pl["pos"][0], pl["pos"][2], self._shade_speed())
            else:
                self._wander_move(s)
        world.push_out_of_tower(self.night, s["pos"])
        self._enforce_safe(s)
        self._hover(s, C.SHADE_HOVER)

    def _recoil_step(self, s):
        step = C.RECOIL_DIST / C.RECOIL_TICKS
        nx, nz = s["pos"][0] + s["recoil_dir"][0] * step, s["pos"][2] + s["recoil_dir"][1] * step
        if not world.blocked_xz(self.night, nx, nz):
            s["pos"][0], s["pos"][2] = nx, nz

    def _wander_move(self, s):
        tgt = self._wander_target(s)
        if tgt is not None:
            self._step_toward(s, tgt["pos"][0], tgt["pos"][2], C.SHADE_WANDER_SPEED, stop=2.0)

    def _drifter_wants(self, d):
        pl = self.player
        return (self.alive() and pl["carried"] >= C.DRIFTER_CHASE_MIN_CARRY
                and xz_dist(d["pos"], pl["pos"]) <= C.DRIFTER_CHASE_DIST + EPS)

    def _move_drifter(self, d):
        pl = self.player
        st = d["state"]
        if st == "removed":
            return
        if st == "idle" and self._drifter_wants(d):
            d["state"] = st = "chase"
        elif st == "chase" and not self._drifter_wants(d):
            d["state"] = st = "idle"
        if st == "chase":
            self._step_toward(d, pl["pos"][0], pl["pos"][2], C.DRIFTER_SPEED)
        elif st == "flee":
            ux, uz = _unit(d["pos"][0] - pl["pos"][0], d["pos"][2] - pl["pos"][2])
            d["pos"][0] += ux * C.DRIFTER_SPEED * C.DT
            d["pos"][2] += uz * C.DRIFTER_SPEED * C.DT
        else:
            if d["target"] is None or xz_dist(d["pos"], d["target"]) < 0.5:
                d["target"] = list(self.rng.choice(self.N["mote_points"]))
            self._step_toward(d, d["target"][0], d["target"][2], C.DRIFTER_IDLE_SPEED)
        world.push_out_of_tower(self.night, d["pos"])
        self._hover(d, C.DRIFTER_HOVER)

    def _contacts(self):
        pl = self.player
        for d in sorted(self.drifters, key=lambda d: id_key(d["id"])):
            if d["state"] == "chase" and within(pl["pos"], d["pos"], C.DRIFTER_TOUCH):
                amount = min(C.DRIFTER_STEAL, pl["carried"])
                pl["carried"] -= amount
                d["stolen"] = amount
                d["state"], d["t"] = "flee", C.DRIFTER_FLEE_TICKS
                self._emit("drifter_steal", {"drifter_id": d["id"], "amount": amount, "carried": pl["carried"]})
        if pl["invuln"] > 0:
            return
        for s in sorted(self.shades, key=lambda s: id_key(s["id"])):
            if (s["state"] in ("wander", "chase") and s["evict"] == 0
                    and within(pl["pos"], s["pos"], T["shade_hit_radius"])
                    and abs(pl["pos"][1] - s["pos"][1]) <= C.SHADE_HIT_DY + EPS):
                self._hit_by_shade(s)
                break

    def _hit_by_shade(self, s):
        pl = self.player
        dropped = pl["carried"] // 2
        pl["carried"] -= dropped
        pl["flames"] -= 1
        pl["invuln"] = C.INVULN_TICKS
        for _ in range(dropped):
            a = self.rng.uniform(0.0, 2.0 * math.pi)
            r = self.rng.uniform(*C.DROP_RING)
            self._add_mote([pl["pos"][0] + r * math.cos(a), None, pl["pos"][2] + r * math.sin(a)], "dropped", C.DROP_TTL)
        s["state"], s["t"] = "recoil", C.RECOIL_TICKS
        s["recoil_dir"] = _unit(s["pos"][0] - pl["pos"][0], s["pos"][2] - pl["pos"][2])
        self._recoil_step(s)  # recoil covers 2 m over exactly 60 ticks, starting with the hit tick
        self._emit("player_hit", {"by": "shade", "flames": pl["flames"], "dropped": dropped})

    def _shade_point_ok(self, p):
        if xz_dist(p, self.player["pos"]) < C.SHADE_SPAWN_MIN_DIST:
            return False
        return all(xz_dist(p, l["pos"]) > T["safe_radius"] for l in self._safe_lanterns())

    def _spawn_shade(self, taken):
        if len(self.shades) >= self.N["shade_max"]:
            return
        pts = [i for i, p in enumerate(self.N["shade_points"]) if i not in taken and self._shade_point_ok(p)]
        if not pts:
            return
        i = self.rng.choice(pts)
        taken.add(i)
        s = self._make_shade(self._new_id("S", self.shades), [float(v) for v in self.N["shade_points"][i]])
        self.shades.append(s)
        self._emit("shade_spawned", {"id": s["id"]})

    def _spawns(self):
        t = self.sim_tick
        if self.random_motes and t % C.MOTE_SPAWN_EVERY == 0 and len(self.motes) < C.MOTE_CAP:
            used = {m["point"] for m in self.motes if m["kind"] == "random" and m["point"] is not None}
            free = [i for i in range(len(self.N["mote_points"])) if i not in used]
            if free:
                i = self.rng.choice(free)
                self._add_mote(self.N["mote_points"][i], "random", None, point=i)
        if self.random_shades:
            every = C.ticks(self.N["shade_every_s"])
            if t == C.SHADE_FIRST_SPAWN:
                taken = set()
                self._spawn_shade(taken)
                self._spawn_shade(taken)
            elif t > C.SHADE_FIRST_SPAWN and (t - C.SHADE_FIRST_SPAWN) % every == 0:
                self._spawn_shade(set())
        if self.random_drifters and t % C.DRIFTER_EVERY == 0:
            if sum(1 for d in self.drifters if d["state"] != "removed") < C.DRIFTER_MAX:
                p = self.rng.choice(self.N["shade_points"])
                d = self._make_drifter(self._new_id("D", self.drifters), [float(p[0]), C.DRIFTER_HOVER, float(p[2])])
                self.drifters.append(d)

    def _won_bonus(self):
        self.score += C.SCORE["per_second_left"] * int(math.floor(max(0.0, self.time_left_s) + 1e-9))
        self.score += C.SCORE["per_flame_left"] * self.player["flames"]

    def _check_end(self):
        if self.player["flames"] <= 0:
            self._end("lost", "no_flames")
        elif all(l["lit"] for l in self.lanterns):
            self._won_bonus()
            self._end("won", "all_lit")
        elif self.sim_tick >= self.total_ticks:
            self._end("lost", "dawn")

    def _end(self, result, reason):
        self.state, self.result_reason = result, reason
        self._emit("game_over", {"result": result, "reason": reason})

    # ----------------------------------------------------------------- snapshot
    def snapshot(self):
        def r3(v):
            x = round(float(v), 3)
            return 0.0 if x == 0 else x

        def v3(p):
            return [r3(c) for c in p]

        pl = self.player
        return {
            "type": "snapshot", "tick": self.tick, "sim_tick": self.sim_tick,
            "state": "paused" if (self.paused and self.state == "playing") else self.state,
            "night": self.night,
            "time_left_s": r3(max(0.0, self.time_left_s)),
            "score": self.score,
            "wind": {"active": self.wind["active"], "dir_deg": r3(self.wind["dir_deg"])},
            "player": {"pos": v3(pl["pos"]), "vel": v3(pl["vel"]), "grounded": pl["grounded"],
                       "invuln": pl["invuln"] > 0, "flames": pl["flames"], "carried": pl["carried"],
                       "dash_cd_s": r3(pl["dash_cd"] / C.TICK_RATE), "pulse_cd_s": r3(pl["pulse_cd"] / C.TICK_RATE),
                       "charm_s": r3(pl["charm"] / C.TICK_RATE)},
            "lanterns": [{"id": l["id"], "pos": v3(l["pos"]), "lit": l["lit"], "deposited": l["deposited"]}
                         for l in self.lanterns],
            "shades": [{"id": s["id"], "pos": v3(s["pos"]), "state": s["state"]} for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [{"id": m["id"], "pos": v3(m["pos"]), "kind": m["kind"],
                       "ttl_s": None if m["ttl"] is None else r3(m["ttl"] / C.TICK_RATE)} for m in self.motes],
            "drifters": [{"id": d["id"], "pos": v3(d["pos"]), "state": d["state"], "stolen": d["stolen"]}
                         for d in self.drifters],
            "charms": [{"id": c["id"], "available": c["available"], "respawn_s": r3(c["respawn"] / C.TICK_RATE)}
                       for c in self.charms],
        }
