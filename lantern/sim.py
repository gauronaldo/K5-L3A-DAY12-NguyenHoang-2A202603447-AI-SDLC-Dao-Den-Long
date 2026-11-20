"""Deterministic game simulation (no rendering). Shared by the 3D client and headless mode.

Coordinates: metres, Y up, ground at Y=0. All gameplay distances are horizontal (XZ).
One call to step() = one tick of 1/60 s.
"""
import math
import random

from . import config as C

T = C.TUNING


EPS = 1e-9


def xz_dist(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def within(a, b, r):
    """Contract: "within radius r" means XZ distance <= r (tolerant to float rounding)."""
    return xz_dist(a, b) <= r + EPS


class InputState:
    """Held input for one tick. Buttons trigger on a false -> true change."""

    __slots__ = ("move", "cam_yaw_deg", "jump", "interact", "pulse", "dash")

    def __init__(self):
        self.move = (0.0, 0.0)
        self.cam_yaw_deg = 0.0
        self.jump = False
        self.interact = False
        self.pulse = False
        self.dash = False

    def copy(self):
        c = InputState()
        c.move, c.cam_yaw_deg = self.move, self.cam_yaw_deg
        c.jump, c.interact, c.pulse, c.dash = self.jump, self.interact, self.pulse, self.dash
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


def default_lantern_positions():
    out = []
    for i in range(T["lantern_count_night1"]):
        a = math.radians(72.0 * i)
        out.append([round(C.LANTERN_RING_RADIUS * math.sin(a), 3), 0.0,
                    round(C.LANTERN_RING_RADIUS * math.cos(a), 3)])
    return out


class Simulation:
    def __init__(self, seed=0, scenario=None):
        self.rng = random.Random(seed)
        scenario = scenario or {}
        self.state = "playing"
        self.result_reason = None
        self.steps = 0
        self.score = 0
        self.events = []          # events produced by the last step()
        self._prev = InputState()

        p = scenario.get("player", {})
        self.player = {
            "pos": [float(v) for v in p.get("pos", [0.0, 0.0, 0.0])],
            "vy": 0.0,
            "flames": int(p.get("flames", T["flames"])),
            "carried": int(p.get("carried", 0)),
            "invuln_t": 0.0,
            "pulse_cd": 0.0,
        }

        self.lanterns = [{"id": "L%d" % (i + 1), "pos": pos, "lit": False, "deposited": 0}
                         for i, pos in enumerate(default_lantern_positions())]
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

        self.random_shades = bool(scenario.get("random_shades", True))
        random_motes = bool(scenario.get("random_motes", True))

        # Generation order is fixed (motes, then shades) so IDs/positions are seed-deterministic.
        if "motes" in scenario:
            self.motes = [[float(m[0]), 0.0, float(m[2])] for m in scenario["motes"]]
        elif random_motes:
            self.motes = [self._random_ground_point(*C.MOTE_RING) for _ in range(C.RANDOM_MOTES)]
        else:
            self.motes = []

        self.shades = []
        self._next_shade = 1
        if "shades" in scenario:
            for s in scenario["shades"]:
                sid = s.get("id") or self._new_shade_id()
                self.shades.append(self._make_shade(sid, [float(v) for v in s["pos"]]))
        elif self.random_shades:
            for _ in range(C.INITIAL_SHADES):
                self.shades.append(self._make_shade(self._new_shade_id(), self._shade_spawn_point()))

        self.total_ticks = int(round(float(scenario.get("time_left_s", T["night1_duration_s"])) * C.TICK_RATE))
        self.spawn_timer = 0

    # ------------------------------------------------------------------ helpers
    def _random_ground_point(self, rmin, rmax):
        a = self.rng.uniform(0.0, 2.0 * math.pi)
        r = math.sqrt(self.rng.uniform(rmin * rmin, rmax * rmax))
        return [round(r * math.sin(a), 3), 0.0, round(r * math.cos(a), 3)]

    def _new_shade_id(self):
        used = {s["id"] for s in self.shades}
        while "S%d" % self._next_shade in used:
            self._next_shade += 1
        sid = "S%d" % self._next_shade
        self._next_shade += 1
        return sid

    def _make_shade(self, sid, pos):
        return {"id": sid, "pos": pos, "state": "chase", "stun_t": 0.0}

    def _shade_spawn_point(self):
        for _ in range(50):
            p = self._random_ground_point(*C.SHADE_SPAWN_RING)
            p[1] = C.SHADE_HEIGHT
            if xz_dist(p, self.player["pos"]) < C.SHADE_SPAWN_MIN_DIST_PLAYER:
                continue
            if any(xz_dist(p, l["pos"]) <= T["safe_radius"] for l in self.lanterns):
                continue
            return p
        return p

    def _enforce_safe(self, shade):
        r = T["safe_radius"] + C.SAFE_EPS
        for _ in range(2):
            for lan in self.lanterns:
                dx = shade["pos"][0] - lan["pos"][0]
                dz = shade["pos"][2] - lan["pos"][2]
                d = math.hypot(dx, dz)
                if d < r:
                    if d < 1e-9:
                        dx, dz, d = 1.0, 0.0, 1.0
                    shade["pos"][0] = lan["pos"][0] + dx / d * r
                    shade["pos"][2] = lan["pos"][2] + dz / d * r

    def _emit(self, name, data):
        self.events.append({"type": "event", "tick": self.steps + 1, "name": name, "data": data})

    def _end(self, result, reason):
        if result == "won":
            time_left = max(0.0, (self.total_ticks - (self.steps + 1)) / C.TICK_RATE)
            self.score += C.SCORE["per_second_left"] * int(math.floor(time_left + 1e-9))
            self.score += C.SCORE["per_flame_left"] * self.player["flames"]
        self.state = result
        self.result_reason = reason
        self._emit("game_over", {"result": result, "reason": reason})

    @property
    def time_left_s(self):
        return (self.total_ticks - self.steps) / C.TICK_RATE

    @property
    def lit_count(self):
        return sum(1 for l in self.lanterns if l["lit"])

    # --------------------------------------------------------------------- step
    def step(self, inp):
        """Advance one tick using held input `inp` (InputState)."""
        self.events = []
        if self.state != "playing":
            return self.events
        prev, self._prev = self._prev, inp.copy()
        pl = self.player

        # 1. movement (horizontal) + island edge clamp (fall_enabled = false)
        wx, wz = world_move(inp.move, inp.cam_yaw_deg)
        step_len = T["player_speed"] * C.DT
        pl["pos"][0] += wx * step_len
        pl["pos"][2] += wz * step_len
        r = math.hypot(pl["pos"][0], pl["pos"][2])
        if r > C.ISLAND_RADIUS:
            pl["pos"][0] *= C.ISLAND_RADIUS / r
            pl["pos"][2] *= C.ISLAND_RADIUS / r

        # 2. jump (vertical only; cosmetic for gameplay distances which are XZ)
        if inp.jump and not prev.jump and pl["pos"][1] <= 0.0:
            pl["vy"] = C.JUMP_SPEED
        if pl["pos"][1] > 0.0 or pl["vy"] > 0.0:
            pl["vy"] -= C.GRAVITY * C.DT
            pl["pos"][1] += pl["vy"] * C.DT
            if pl["pos"][1] <= 0.0:
                pl["pos"][1], pl["vy"] = 0.0, 0.0

        # 3. pick up motes (list order) until full
        kept = []
        for m in self.motes:
            if pl["carried"] < T["carry_capacity"] and within(pl["pos"], m, T["pickup_radius"]):
                pl["carried"] += 1
                self.score += C.SCORE["per_mote"]
                self._emit("mote_picked", {"carried": pl["carried"]})
            else:
                kept.append(m)
        self.motes = kept

        # 4. interact: deposit into nearest unlit lantern in range
        if inp.interact and not prev.interact and pl["carried"] > 0:
            cands = [(xz_dist(pl["pos"], l["pos"]), i) for i, l in enumerate(self.lanterns)
                     if not l["lit"] and within(pl["pos"], l["pos"], T["interact_radius"])]
            if cands:
                lan = self.lanterns[min(cands)[1]]
                amount = min(pl["carried"], T["lantern_cost"] - lan["deposited"])
                if amount > 0:
                    pl["carried"] -= amount
                    lan["deposited"] += amount
                    self._emit("deposit", {"lantern_id": lan["id"], "amount": amount,
                                           "deposited": lan["deposited"]})
                if lan["deposited"] >= T["lantern_cost"]:
                    lan["lit"] = True
                    self.score += C.SCORE["per_lantern"]
                    self._emit("lantern_lit", {"lantern_id": lan["id"]})
                    if all(l["lit"] for l in self.lanterns):
                        self._end("won", "all_lit")
                        self.steps += 1
                        return self.events

        # 5. light pulse
        if inp.pulse and not prev.pulse and pl["pulse_cd"] <= 1e-9 and pl["carried"] >= T["pulse_cost"]:
            pl["carried"] -= T["pulse_cost"]
            pl["pulse_cd"] = T["pulse_cooldown_s"]
            stunned = []
            for s in self.shades:
                d = xz_dist(pl["pos"], s["pos"])
                if d <= T["pulse_radius"] + EPS:
                    if d < 1e-9:
                        dx, dz = 1.0, 0.0
                    else:
                        dx, dz = (s["pos"][0] - pl["pos"][0]) / d, (s["pos"][2] - pl["pos"][2]) / d
                    s["pos"][0] += dx * T["pulse_push_m"]
                    s["pos"][2] += dz * T["pulse_push_m"]
                    s["state"], s["stun_t"] = "stunned", T["pulse_stun_s"]
                    self._enforce_safe(s)
                    self.score += C.SCORE["per_stun"]
                    stunned.append(s["id"])
            self._emit("pulse", {"stunned_ids": stunned})

        # 6. shades: stun timers, chase, keep out of lantern safe zones
        for s in self.shades:
            if s["state"] == "stunned":
                s["stun_t"] -= C.DT
                if s["stun_t"] <= 1e-9:
                    s["state"], s["stun_t"] = "chase", 0.0
                continue
            dx, dz = pl["pos"][0] - s["pos"][0], pl["pos"][2] - s["pos"][2]
            d = math.hypot(dx, dz)
            if d > 1e-9:
                mv = min(T["shade_speed"] * C.DT, d)
                s["pos"][0] += dx / d * mv
                s["pos"][2] += dz / d * mv
            self._enforce_safe(s)

        # 7. shade contact
        if pl["invuln_t"] <= 1e-9:
            for s in self.shades:
                if s["state"] != "stunned" and within(pl["pos"], s["pos"], T["shade_hit_radius"]):
                    dropped = int(math.floor(pl["carried"] * T["hit_drop_ratio"]))
                    pl["carried"] -= dropped
                    pl["flames"] -= 1
                    pl["invuln_t"] = T["invuln_s"]
                    self._emit("player_hit", {"by": "shade", "flames": pl["flames"], "dropped": dropped})
                    if pl["flames"] <= 0:
                        self._end("lost", "no_flames")
                        self.steps += 1
                        return self.events
                    break
        else:
            pl["invuln_t"] = max(0.0, pl["invuln_t"] - C.DT)
        pl["pulse_cd"] = max(0.0, pl["pulse_cd"] - C.DT)

        # 8. timed shade spawns (default night only)
        if self.random_shades:
            self.spawn_timer += 1
            if self.spawn_timer >= int(C.SHADE_SPAWN_EVERY_S * C.TICK_RATE):
                self.spawn_timer = 0
                if len(self.shades) < C.MAX_SHADES:
                    s = self._make_shade(self._new_shade_id(), self._shade_spawn_point())
                    self.shades.append(s)
                    self._emit("shade_spawned", {"id": s["id"]})

        # 9. clock / dawn
        if self.steps + 1 >= self.total_ticks:
            self._end("lost", "dawn")
        self.steps += 1
        return self.events

    # ----------------------------------------------------------------- snapshot
    def snapshot(self):
        def r3(v):
            x = round(float(v), 3)
            return 0.0 if x == 0 else x

        pl = self.player
        return {
            "type": "snapshot",
            "tick": self.steps,
            "sim_tick": self.steps,
            "state": self.state,
            "time_left_s": r3(max(0.0, self.time_left_s)),
            "score": self.score,
            "player": {"pos": [r3(v) for v in pl["pos"]], "flames": pl["flames"], "carried": pl["carried"]},
            "lanterns": [{"id": l["id"], "pos": [r3(v) for v in l["pos"]], "lit": l["lit"],
                          "deposited": l["deposited"]} for l in self.lanterns],
            "shades": [{"id": s["id"], "pos": [r3(v) for v in s["pos"]], "state": s["state"]}
                       for s in self.shades],
            "motes_active": len(self.motes),
            "motes": [[r3(m[0]), 0.0, r3(m[2])] for m in self.motes],
        }
