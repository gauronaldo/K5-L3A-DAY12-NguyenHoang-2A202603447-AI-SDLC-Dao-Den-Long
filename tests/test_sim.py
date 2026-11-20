"""Unit tests for game rules (PRD-0 + Test Contract v1.0). Run: python3 -m unittest discover -s tests"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lantern import config as C  # noqa: E402
from lantern.sim import InputState, Simulation, world_move, xz_dist  # noqa: E402

T = C.TUNING
EMPTY = {"random_motes": False, "random_shades": False, "motes": [], "shades": []}


def scen(**kw):
    d = dict(EMPTY)
    d.update(kw)
    return d


def run(sim, n, **fields):
    inp = InputState()
    for k, v in fields.items():
        setattr(inp, k, v)
    evs = []
    for _ in range(n):
        evs += sim.step(inp)
    return evs


def press(sim, button):
    """One tick with button down, one tick released (rising edge once)."""
    inp = InputState()
    setattr(inp, button, True)
    evs = sim.step(inp)
    evs += sim.step(InputState())
    return evs


def names(evs):
    return [e["name"] for e in evs]


class Movement(unittest.TestCase):
    def test_speed_one_second_forward(self):
        sim = Simulation(0, scen())
        run(sim, 60, move=(0.0, 1.0))
        self.assertAlmostEqual(sim.player["pos"][2], T["player_speed"], places=6)
        self.assertAlmostEqual(sim.player["pos"][0], 0.0, places=6)

    def test_yaw_rotation_matches_contract(self):
        # theta=90: x' = z*sin(90) = 1 for move [0,1]
        wx, wz = world_move((0, 1), 90)
        self.assertAlmostEqual(wx, 1.0)
        self.assertAlmostEqual(wz, 0.0)
        wx, wz = world_move((1, 0), 90)  # x' = cos90 = 0, z' = -sin90 = -1
        self.assertAlmostEqual(wx, 0.0)
        self.assertAlmostEqual(wz, -1.0)

    def test_diagonal_normalised(self):
        wx, wz = world_move((1, 1), 0)
        self.assertAlmostEqual(math.hypot(wx, wz), 1.0)

    def test_island_edge_clamp_no_fall(self):
        sim = Simulation(0, scen())
        evs = run(sim, 60 * 10, move=(1.0, 0.0))
        self.assertAlmostEqual(sim.player["pos"][0], C.ISLAND_RADIUS, places=6)
        self.assertNotIn("player_hit", names(evs))

    def test_jump_goes_up_and_lands(self):
        sim = Simulation(0, scen())
        sim.step(_inp(jump=True))
        peak = 0.0
        for _ in range(120):
            sim.step(_inp(jump=True))  # held: must not re-trigger
            peak = max(peak, sim.player["pos"][1])
        self.assertGreater(peak, 1.0)
        self.assertEqual(sim.player["pos"][1], 0.0)


def _inp(**kw):
    i = InputState()
    for k, v in kw.items():
        setattr(i, k, v)
    return i


class Motes(unittest.TestCase):
    def test_pickup_radius_inclusive(self):
        sim = Simulation(0, scen(motes=[[T["pickup_radius"], 0, 0], [T["pickup_radius"] + 0.01, 0, 0]]))
        evs = sim.step(InputState())
        self.assertEqual(names(evs), ["mote_picked"])
        self.assertEqual(sim.player["carried"], 1)
        self.assertEqual(sim.score, C.SCORE["per_mote"])
        self.assertEqual(evs[0]["tick"], 1)

    def test_capacity(self):
        sim = Simulation(0, scen(player={"carried": T["carry_capacity"] - 1}, motes=[[0, 0, 0], [0, 0, 0.5]]))
        evs = sim.step(InputState())
        self.assertEqual(len(evs), 1)
        self.assertEqual(sim.player["carried"], T["carry_capacity"])
        self.assertEqual(len(sim.motes), 1)


class Lanterns(unittest.TestCase):
    def test_deposit_partial_then_light(self):
        lan = [{"id": "L1", "pos": [0, 0, 2], "deposited": 0}]
        sim = Simulation(0, scen(player={"carried": 3}, lanterns=lan))
        evs = press(sim, "interact")
        self.assertEqual(evs[0]["data"], {"lantern_id": "L1", "amount": 3, "deposited": 3})
        self.assertFalse(sim.lanterns[0]["lit"])
        sim.player["carried"] = 4
        evs = press(sim, "interact")
        self.assertEqual(names(evs), ["deposit", "lantern_lit"])
        self.assertEqual(evs[0]["data"]["amount"], T["lantern_cost"] - 3)
        self.assertEqual(sim.player["carried"], 4 - (T["lantern_cost"] - 3))
        self.assertTrue(sim.lanterns[0]["lit"])
        self.assertEqual(sim.score, C.SCORE["per_lantern"])

    def test_interact_out_of_range(self):
        lan = [{"id": "L1", "pos": [0, 0, T["interact_radius"] + 0.01]}]
        sim = Simulation(0, scen(player={"carried": 5}, lanterns=lan))
        self.assertEqual(press(sim, "interact"), [])

    def test_interact_needs_rising_edge(self):
        lan = [{"id": "L1", "pos": [0, 0, 1]}]
        sim = Simulation(0, scen(player={"carried": 2}, lanterns=lan))
        evs = run(sim, 10, interact=True)
        self.assertEqual(names(evs), ["deposit"])

    def test_win_all_lit_and_bonus(self):
        lans = [{"id": "L%d" % i, "lit": True} for i in range(2, 6)] + [{"id": "L1", "pos": [0, 0, 1], "deposited": 4}]
        sim = Simulation(0, scen(player={"carried": 1}, lanterns=lans, time_left_s=100))
        self.assertEqual(sim.score, 0)  # scenario lit lanterns give no score
        evs = press(sim, "interact")
        self.assertEqual(names(evs), ["deposit", "lantern_lit", "game_over"])
        self.assertEqual(evs[-1]["data"], {"result": "won", "reason": "all_lit"})
        self.assertEqual(sim.state, "won")
        expect = C.SCORE["per_lantern"] + C.SCORE["per_second_left"] * 99 + C.SCORE["per_flame_left"] * T["flames"]
        self.assertEqual(sim.score, expect)


class Shades(unittest.TestCase):
    def test_chase_speed(self):
        sim = Simulation(0, scen(shades=[{"pos": [20, 1, 0]}]))
        run(sim, 60)
        self.assertAlmostEqual(sim.shades[0]["pos"][0], 20 - T["shade_speed"], places=6)
        self.assertEqual(sim.shades[0]["state"], "chase")

    def test_hit_drop_invuln(self):
        sim = Simulation(0, scen(player={"carried": 5}, shades=[{"id": "A", "pos": [0.5, 1, 0]}]))
        evs = sim.step(InputState())
        self.assertEqual(evs[0]["name"], "player_hit")
        self.assertEqual(evs[0]["data"], {"by": "shade", "flames": T["flames"] - 1,
                                          "dropped": int(5 * T["hit_drop_ratio"])})
        # no second hit during invulnerability
        evs = run(sim, int(T["invuln_s"] * 60) - 1)
        self.assertNotIn("player_hit", names(evs))
        evs = run(sim, 3)
        self.assertIn("player_hit", names(evs))

    def test_lose_no_flames(self):
        sim = Simulation(0, scen(player={"flames": 1}, shades=[{"pos": [0, 1, 0]}]))
        evs = sim.step(InputState())
        self.assertEqual(names(evs), ["player_hit", "game_over"])
        self.assertEqual(evs[1]["data"], {"result": "lost", "reason": "no_flames"})
        self.assertEqual(sim.step(InputState()), [])  # frozen after game over

    def test_safe_radius_never_entered(self):
        lan = [{"id": "L1", "pos": [0, 0, 0]}]
        sim = Simulation(0, scen(lanterns=lan, shades=[{"pos": [15, 1, 0]}, {"pos": [0, 1, -12]}]))
        hits = []
        for _ in range(600):
            hits += [e for e in sim.step(InputState()) if e["name"] == "player_hit"]
            for s in sim.shades:
                self.assertGreaterEqual(xz_dist(s["pos"], lan[0]["pos"]), T["safe_radius"])
        self.assertEqual(hits, [])  # player standing at a lantern is safe

    def test_pulse_stun_push_cost_score(self):
        sim = Simulation(0, scen(player={"carried": 2}, shades=[{"id": "N", "pos": [3, 1, 0]},
                                                                  {"id": "F", "pos": [T["pulse_radius"] + 1, 1, 0]}]))
        evs = press(sim, "pulse")
        self.assertEqual(evs[0]["name"], "pulse")
        self.assertEqual(evs[0]["data"], {"stunned_ids": ["N"]})
        self.assertEqual(sim.player["carried"], 2 - T["pulse_cost"])
        self.assertEqual(sim.score, C.SCORE["per_stun"])
        n = sim.shades[0]
        self.assertEqual(n["state"], "stunned")
        self.assertAlmostEqual(n["pos"][0], 3 + T["pulse_push_m"], places=6)
        run(sim, int(T["pulse_stun_s"] * 60) + 1)
        self.assertEqual(n["state"], "chase")

    def test_pulse_needs_light_and_cooldown(self):
        sim = Simulation(0, scen(player={"carried": 0}))
        self.assertEqual(press(sim, "pulse"), [])
        sim = Simulation(0, scen(player={"carried": 5}))
        self.assertEqual(names(press(sim, "pulse")), ["pulse"])
        self.assertEqual(press(sim, "pulse"), [])  # still cooling down
        run(sim, int(T["pulse_cooldown_s"] * 60))
        self.assertEqual(names(press(sim, "pulse")), ["pulse"])


class Night(unittest.TestCase):
    def test_dawn_loses(self):
        sim = Simulation(0, scen(time_left_s=1.0))
        evs = run(sim, 100)
        self.assertEqual(sim.steps, 60)
        self.assertEqual(evs[-1]["data"], {"result": "lost", "reason": "dawn"})
        self.assertEqual(evs[-1]["tick"], 60)

    def test_default_night_layout(self):
        sim = Simulation(7)
        self.assertEqual(len(sim.lanterns), T["lantern_count_night1"])
        self.assertEqual(sim.player["pos"], [0.0, 0.0, 0.0])
        self.assertEqual(sim.player["flames"], T["flames"])
        self.assertEqual(sim.time_left_s, T["night1_duration_s"])
        self.assertGreaterEqual(len(sim.motes), T["lantern_count_night1"] * T["lantern_cost"])
        for s in sim.shades:
            for l in sim.lanterns:
                self.assertGreater(xz_dist(s["pos"], l["pos"]), T["safe_radius"])

    def test_shade_spawn_event_and_ids(self):
        sim = Simulation(3, {"random_motes": False})
        evs = []
        for _ in range(int(C.SHADE_SPAWN_EVERY_S * 60)):
            evs += sim.step(InputState())
            if sim.state != "playing":
                break
        sp = [e for e in evs if e["name"] == "shade_spawned"]
        if sim.state == "playing":
            self.assertEqual([e["data"]["id"] for e in sp], ["S3"])

    def test_same_seed_same_world(self):
        a, b = Simulation(42), Simulation(42)
        self.assertEqual(a.snapshot(), b.snapshot())
        self.assertNotEqual(a.snapshot()["motes"], Simulation(43).snapshot()["motes"])


if __name__ == "__main__":
    unittest.main()
