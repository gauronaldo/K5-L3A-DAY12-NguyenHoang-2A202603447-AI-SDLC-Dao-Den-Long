"""Unit tests for game rules (Ticket-02 standard numbers, contract v1.1).

Run: python3 -m unittest discover -s tests
Phase 1 tests replaced by Ticket-02 rules are listed with reasons in docs/notes/phase-2.md section 1.
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lantern import config as C  # noqa: E402
from lantern import world  # noqa: E402
from lantern.sim import InputState, Simulation, world_move, xz_dist  # noqa: E402

T = C.TUNING
EMPTY = {"random_motes": False, "random_shades": False, "random_drifters": False, "wind_enabled": False,
         "motes": [], "shades": [], "drifters": [], "charms": []}


def scen(**kw):
    d = dict(EMPTY)
    d.update(kw)
    return d


def inp(**kw):
    i = InputState()
    for k, v in kw.items():
        setattr(i, k, v)
    return i


def run(sim, n, **fields):
    i = inp(**fields)
    evs = []
    for _ in range(n):
        evs += sim.step(i)
    return evs


def press(sim, button, **fields):
    """One tick with the button down, one tick released."""
    evs = sim.step(inp(**dict(fields, **{button: True})))
    evs += sim.step(inp(**fields))
    return evs


def names(evs):
    return [e["name"] for e in evs if e["name"] != "night_start"]


class Movement(unittest.TestCase):
    def test_speed_one_second(self):
        sim = Simulation(0, scen())
        run(sim, 60, move=(0.0, 1.0))
        self.assertAlmostEqual(sim.player["pos"][2], 6.0, places=6)
        self.assertEqual(sim.player["vel"], [0.0, 0.0, 6.0])

    def test_stops_within_0_1s(self):
        sim = Simulation(0, scen())
        run(sim, 30, move=(0.0, 1.0))
        z = sim.player["pos"][2]
        run(sim, 6)
        self.assertAlmostEqual(sim.player["pos"][2], z, places=6)

    def test_yaw_rotation_matches_contract(self):
        wx, wz = world_move((0, 1), 90)
        self.assertAlmostEqual(wx, 1.0)
        self.assertAlmostEqual(wz, 0.0)
        wx, wz = world_move((1, 1), 0)
        self.assertAlmostEqual(math.hypot(wx, wz), 1.0)

    def test_jump_height_and_ground_only(self):
        sim = Simulation(0, scen())
        sim.step(inp(jump=True))
        peak = 0.0
        for k in range(80):
            sim.step(inp(jump=(k % 2 == 1 and k < 30)))  # presses mid-air must not re-jump
            peak = max(peak, sim.player["pos"][1])
        self.assertAlmostEqual(peak, 7.0 ** 2 / (2 * 20.0), delta=0.12)
        self.assertEqual(sim.player["pos"][1], 0.0)
        self.assertTrue(sim.player["grounded"])

    def test_dash_distance_direction_cooldown(self):
        sim = Simulation(0, scen())
        evs = press(sim, "dash")  # standing still: facing +Z
        self.assertEqual(names(evs), ["dash"])
        run(sim, 20)
        self.assertAlmostEqual(sim.player["pos"][2], T["dash_speed"] * T["dash_duration_s"], places=6)
        self.assertEqual(names(press(sim, "dash")), [])  # cooldown 90 ticks from dash start (22 ticks elapsed)
        run(sim, C.DASH_CD_TICKS - 24)
        self.assertEqual(names(press(sim, "dash")), ["dash"])

    def test_dash_follows_move_and_keeps_height_in_air(self):
        sim = Simulation(0, scen())
        sim.step(inp(jump=True))
        run(sim, 10)
        y0 = sim.player["pos"][1]
        sim.step(inp(dash=True, move=(1.0, 0.0)))
        self.assertEqual(sim.player["pos"][1], y0)
        run(sim, 11, move=(1.0, 0.0))
        self.assertEqual(sim.player["pos"][1], y0)
        self.assertAlmostEqual(sim.player["pos"][0], 2.8, places=6)

    def test_fall_off_island(self):
        sim = Simulation(0, scen(player={"pos": [39.5, 0, 0], "carried": 4}))
        evs = []
        for _ in range(200):
            evs += sim.step(inp(move=(1.0, 0.0)))
            if "player_hit" in names(evs):
                break
        hit = [e for e in evs if e["name"] == "player_hit"][0]
        self.assertEqual(hit["data"], {"by": "fall", "flames": 2, "dropped": 0, "lost": 4})
        self.assertLess(sim.player["pos"][1], C.FALL_Y)
        self.assertEqual(sim.player["carried"], 0)
        run(sim, C.FALL_WAIT - 1, move=(1.0, 0.0))
        self.assertLess(sim.player["pos"][1], 0)  # still waiting
        sim.step(inp())
        self.assertEqual(sim.player["pos"], [0.0, 0.0, 0.0])
        self.assertEqual(sim.player["invuln"], C.INVULN_TICKS)

    def test_fall_ignores_invulnerability_and_can_lose(self):
        sim = Simulation(0, scen(player={"pos": [39.9, 0, 0], "flames": 1, "invuln_ticks": 500}))
        evs = run(sim, 120, move=(1.0, 0.0))
        self.assertEqual(names(evs)[-2:], ["player_hit", "game_over"])
        self.assertEqual(evs[-1]["data"], {"result": "lost", "reason": "no_flames"})


class Motes(unittest.TestCase):
    def test_pickup_xz_and_height(self):
        sim = Simulation(0, scen(motes=[[1.0, 0, 0], [1.01, 0, 0], [0, 1.6, 0.5]]))
        evs = sim.step(inp())
        self.assertEqual(names(evs), ["mote_picked"])
        self.assertEqual(sim.score, 0)  # Ticket-02: points come from depositing, not picking

    def test_default_twenty_on_distinct_points_and_respawn(self):
        sim = Simulation(5)
        self.assertEqual(len(sim.motes), C.MOTE_START)
        self.assertEqual(len({tuple(m["pos"]) for m in sim.motes}), C.MOTE_START)
        pts = {tuple(p) for p in C.NIGHTS[1]["mote_points"]}
        self.assertTrue(all(tuple(m["pos"]) in pts for m in sim.motes))
        sim.player["pos"] = [0.0, 0.0, 7.0]   # away from every mote point
        run(sim, 239)
        self.assertEqual(len(sim.motes), 20)
        sim.step(inp())
        self.assertEqual(len(sim.motes), 21)

    def test_capacity(self):
        sim = Simulation(0, scen(player={"carried": 9}, motes=[[0, 0, 0], [0, 0, 0.5]]))
        sim.step(inp())
        self.assertEqual(sim.player["carried"], 10)
        self.assertEqual(len(sim.motes), 1)


class Lanterns(unittest.TestCase):
    def test_partial_deposit_and_light_scoring(self):
        lan = [{"id": "L1", "pos": [0, 0, 1.5]}]
        sim = Simulation(0, scen(player={"carried": 6}, lanterns=lan))
        evs = press(sim, "interact")
        self.assertEqual(evs[1]["data"], {"lantern_id": "L1", "amount": 6, "deposited": 6})
        sim.player["carried"] = 9
        evs = press(sim, "interact")
        self.assertEqual(names(evs), ["deposit", "lantern_lit"])
        self.assertEqual(sim.player["carried"], 5)
        self.assertEqual(sim.score, 10 * 10 + 100)

    def test_choose_nearest_then_lower_id(self):
        lans = [{"id": "L2", "pos": [1, 0, 0]}, {"id": "L1", "pos": [-1, 0, 0]}, {"id": "L3", "pos": [0, 0, 0.5]}]
        sim = Simulation(0, scen(player={"carried": 1}, lanterns=lans))
        self.assertEqual(press(sim, "interact")[1]["data"]["lantern_id"], "L3")
        sim = Simulation(0, scen(player={"carried": 1}, lanterns=lans[:2]))
        self.assertEqual(press(sim, "interact")[1]["data"]["lantern_id"], "L1")

    def test_interact_radius_2(self):
        sim = Simulation(0, scen(player={"carried": 3}, lanterns=[{"id": "L1", "pos": [0, 0, 2.01]}]))
        self.assertEqual(names(press(sim, "interact")), [])


class SafeZone(unittest.TestCase):
    def test_only_lit_lanterns_block(self):
        lans = [{"id": "L1", "pos": [10, 0, 0], "lit": True}, {"id": "L2", "pos": [-10, 0, 0]}]
        sim = Simulation(0, scen(player={"pos": [10, 0, 0]}, lanterns=lans,
                                 shades=[{"pos": [10, 1, 11]}, {"pos": [-10, 1, 3]}]))
        run(sim, 300)
        self.assertGreaterEqual(xz_dist(sim.shades[0]["pos"], lans[0]["pos"]), T["safe_radius"])
        self.assertLess(xz_dist(sim.shades[1]["pos"], lans[1]["pos"]), 2.0 + 1e-6)  # wanders into unlit lantern zone

    def test_evicted_within_30_ticks_and_harmless(self):
        lan = [{"id": "L1", "pos": [0, 0, 1], "deposited": 9}]
        sim = Simulation(0, scen(player={"carried": 1}, lanterns=lan, shades=[{"id": "S1", "pos": [0, 1, 0.5]}]))
        evs = press(sim, "interact")
        self.assertIn("lantern_lit", names(evs))
        evs = run(sim, 28)
        self.assertNotIn("player_hit", names(evs))
        self.assertGreaterEqual(xz_dist(sim.shades[0]["pos"], [0, 0, 1]), T["safe_radius"])


class Pulse(unittest.TestCase):
    def test_cost_radius_3d_stun_push(self):
        shades = [{"id": "A", "pos": [4.9, 1.0, 0]}, {"id": "B", "pos": [0, 4.0, 3.9]}, {"id": "C", "pos": [0, 1, -5.2]}]
        sim = Simulation(0, scen(player={"carried": 5}, shades=shades))
        evs = sim.step(inp(pulse=True))
        self.assertEqual(evs[-1]["data"], {"stunned_ids": ["A"]})   # B: 3D 5.05 m, C: 5.2 m
        self.assertEqual(sim.player["carried"], 2)
        self.assertEqual(sim.score, 5)
        a = sim.shades[0]
        run(sim, 14)
        self.assertAlmostEqual(a["pos"][0], 4.9 + 4.0, places=6)
        run(sim, 30)
        self.assertAlmostEqual(a["pos"][0], 8.9, places=6)
        self.assertEqual(a["state"], "stunned")
        run(sim, C.STUN_TICKS - 45)
        self.assertEqual(a["state"], "stunned")
        sim.step(inp())
        self.assertNotEqual(a["state"], "stunned")

    def test_needs_three_and_cooldown(self):
        sim = Simulation(0, scen(player={"carried": 2}))
        self.assertEqual(names(press(sim, "pulse")), [])
        sim = Simulation(0, scen(player={"carried": 9}))
        self.assertEqual(names(press(sim, "pulse")), ["pulse"])
        run(sim, C.PULSE_CD_TICKS - 3)
        self.assertEqual(names(press(sim, "pulse")), [])
        self.assertEqual(names(press(sim, "pulse")), ["pulse"])

    def test_restun_scores_again(self):
        sim = Simulation(0, scen(player={"carried": 9, "pos": [0, 0, 0]}, shades=[{"pos": [1, 1, 0]}]))
        press(sim, "pulse")
        run(sim, C.PULSE_CD_TICKS)
        press(sim, "pulse")
        self.assertEqual(sim.score, 10)


class Shades(unittest.TestCase):
    def test_detect_12_giveup_18(self):
        sim = Simulation(0, scen(shades=[{"pos": [11.9, 1, 0]}, {"pos": [-12.5, 1, 0]}]))
        sim.step(inp())
        self.assertEqual([s["state"] for s in sim.shades], ["chase", "wander"])
        sim = Simulation(0, scen(shades=[{"pos": [17, 1, 0], "state": "chase"}]))
        run(sim, 60, move=(-1.0, 0.0))  # player runs 6 m/s, shade 4 m/s -> gap grows past 18 m
        self.assertEqual(sim.shades[0]["state"], "wander")

    def test_chase_speed(self):
        sim = Simulation(0, scen(shades=[{"pos": [10, 1, 0]}]))
        run(sim, 60)
        self.assertAlmostEqual(sim.shades[0]["pos"][0], 6.0, places=6)

    def test_hit_drop_ring_invuln_recoil(self):
        sim = Simulation(0, scen(player={"carried": 7}, shades=[{"id": "S1", "pos": [0.5, 1, 0]}]))
        evs = sim.step(inp())
        self.assertEqual(evs[-1]["data"], {"by": "shade", "flames": 2, "dropped": 3})
        drops = [m for m in sim.motes if m["kind"] == "dropped"]
        self.assertEqual(len(drops), 3)
        for m in drops:
            self.assertTrue(1.5 - 1e-9 <= xz_dist(m["pos"], [0, 0, 0]) <= 2.5 + 1e-9)
            self.assertEqual(m["ttl"], C.DROP_TTL)
        self.assertEqual(sim.shades[0]["state"], "recoil")
        run(sim, C.RECOIL_TICKS - 1)
        # the shade first chased 4/60 m this tick, then recoiled 2 m over 60 ticks
        self.assertAlmostEqual(xz_dist(sim.shades[0]["pos"], [0, 0, 0]), 0.5 - 4 / 60 + 2.0, places=6)
        self.assertEqual(sim.shades[0]["state"], "recoil")
        evs = run(sim, C.INVULN_TICKS - C.RECOIL_TICKS - 1)
        self.assertNotIn("player_hit", names(evs))
        first = {m["id"] for m in drops}
        sim.shades.clear()   # otherwise the shade keeps hitting and the night ends (no_flames) at tick 181
        run(sim, C.DROP_TTL - sim.tick)                           # dropped at tick 1 -> present up to tick 480
        self.assertTrue(first <= {m["id"] for m in sim.motes})
        run(sim, 1)                                               # gone at tick 481 (480 ticks alive)
        self.assertFalse(first & {m["id"] for m in sim.motes})

    def test_one_hit_per_tick_lowest_id(self):
        sim = Simulation(0, scen(shades=[{"id": "S10", "pos": [0.2, 1, 0]}, {"id": "S2", "pos": [-0.2, 1, 0]}]))
        evs = sim.step(inp())
        self.assertEqual(names(evs), ["player_hit"])
        self.assertEqual({s["id"]: s["state"] for s in sim.shades}, {"S10": "chase", "S2": "recoil"})

    def test_height_difference(self):
        # shades hover at ground + 1 m (B6); a player 3 m up is out of reach (dy > 1.5) until landing
        sim = Simulation(0, scen(player={"pos": [0, 3.0, 0]}, shades=[{"pos": [0.2, 1, 0]}]))
        self.assertEqual(names(sim.step(inp())), [])
        evs = run(sim, 40)
        self.assertIn("player_hit", names(evs))

    def test_spawn_schedule_night1(self):
        sim = Simulation(3, {"random_motes": False})
        evs = run(sim, 300 + 480 * 5 + 1)
        sp = [(e["tick"], e["data"]["id"]) for e in evs if e["name"] == "shade_spawned"]
        self.assertEqual(sp, [(300, "S1"), (300, "S2"), (780, "S3"), (1260, "S4"), (1740, "S5"), (2220, "S6")])
        for p in C.NIGHTS[1]["shade_points"]:
            self.assertAlmostEqual(math.hypot(p[0], p[2]), 37.0, places=4)

    def test_spawning_state_then_wander(self):
        sim = Simulation(3, {"random_motes": False})
        run(sim, 300)
        self.assertEqual({s["state"] for s in sim.shades}, {"spawning"})
        run(sim, C.SHADE_SPAWNING_TICKS)
        self.assertTrue(all(s["state"] in ("wander", "chase") for s in sim.shades))


class Night(unittest.TestCase):
    def test_dawn(self):
        sim = Simulation(0, scen(time_left_s=1.0))
        evs = run(sim, 100)
        self.assertEqual(evs[-1]["data"], {"result": "lost", "reason": "dawn"})
        self.assertEqual(evs[-1]["tick"], 60)

    def test_win_on_dawn_tick_and_bonus(self):
        lans = [{"id": "L%d" % i, "lit": True} for i in range(2, 6)] + [{"id": "L1", "pos": [0, 0, 1], "deposited": 9}]
        sim = Simulation(0, scen(player={"carried": 1}, lanterns=lans, time_left_s=1 / 60))
        evs = sim.step(inp(interact=True))
        self.assertEqual(evs[-1]["data"], {"result": "won", "reason": "all_lit"})
        self.assertEqual(sim.score, 10 + 100 + 0 * 2 + 50 * 3)

    def test_win_bonus_seconds_x2(self):
        lans = [{"id": "L%d" % i, "lit": True} for i in range(2, 6)] + [{"id": "L1", "pos": [0, 0, 1], "deposited": 9}]
        sim = Simulation(0, scen(player={"carried": 1}, lanterns=lans, time_left_s=100))
        sim.step(inp(interact=True))
        self.assertEqual(sim.score, 10 + 100 + 99 * 2 + 150)

    def test_no_flames_beats_all_lit_and_dawn(self):
        # a shade next to a lantern that is being lit is evicted and harmless, so the "all lit + lethal hit"
        # case is built with every lantern already lit and the shade far from all of them
        lans = [{"id": "L%d" % i, "lit": True} for i in range(1, 6)]
        sim = Simulation(0, scen(player={"flames": 1}, lanterns=lans, shades=[{"pos": [0.5, 1, 0]}],
                                 time_left_s=1 / 60))
        evs = sim.step(inp())
        self.assertEqual(evs[-1]["data"], {"result": "lost", "reason": "no_flames"})

    def test_pause_freezes_logic(self):
        sim = Simulation(0, scen(shades=[{"pos": [10, 1, 0]}]))
        run(sim, 10)
        evs = sim.step(inp(pause=True))
        self.assertEqual(names(evs), ["paused"])
        pos = list(sim.shades[0]["pos"])
        run(sim, 50, pause=True)
        self.assertEqual((sim.tick, sim.sim_tick), (61, 10))
        self.assertEqual(sim.shades[0]["pos"], pos)
        self.assertEqual(sim.snapshot()["state"], "paused")
        sim.step(inp())
        evs = sim.step(inp(pause=True))
        self.assertEqual(names(evs), ["resumed"])
        self.assertEqual(sim.sim_tick, 11)

    def test_night_start_event_and_flames_per_night(self):
        for n in (1, 2, 3):
            sim = Simulation(1, night=n)
            evs = sim.step(inp())
            self.assertEqual(evs[0]["data"], {"night": n})
            self.assertEqual(sim.player["flames"], 3)
            self.assertEqual(sim.total_ticks, int(C.NIGHTS[n]["duration_s"] * 60))


class Drifters(unittest.TestCase):
    def test_chase_steal_flee_removed(self):
        sim = Simulation(0, scen(player={"carried": 6}, drifters=[{"id": "D1", "pos": [5, 1.5, 0]}]), night=2)
        sim.step(inp())
        self.assertEqual(sim.drifters[0]["state"], "chase")
        evs = run(sim, 60)
        st = [e for e in evs if e["name"] == "drifter_steal"]
        self.assertEqual(st[0]["data"], {"drifter_id": "D1", "amount": 3, "carried": 3})
        self.assertEqual(sim.drifters[0]["state"], "flee")
        run(sim, C.DRIFTER_FLEE_TICKS)
        self.assertEqual(sim.drifters[0]["state"], "removed")
        self.assertEqual(sim.player["flames"], 3)

    def test_idle_when_carry_below_5(self):
        sim = Simulation(0, scen(player={"carried": 4}, drifters=[{"pos": [3, 1.5, 0]}]), night=2)
        run(sim, 30)
        self.assertEqual(sim.drifters[0]["state"], "idle")

    def test_pulse_chase_flees_without_steal(self):
        sim = Simulation(0, scen(player={"carried": 8}, drifters=[{"id": "D1", "pos": [4, 1.5, 0]}]), night=2)
        sim.step(inp())
        sim.step(inp(pulse=True))
        self.assertEqual(sim.drifters[0]["state"], "flee")
        self.assertEqual(sim.drifters[0]["stolen"], 0)

    def test_pulse_flee_with_loot_drops(self):
        sim = Simulation(0, scen(player={"carried": 8}, drifters=[{"id": "D1", "pos": [3, 1.5, 0], "state": "flee",
                                                                  "stolen": 3}]), night=2)
        evs = sim.step(inp(pulse=True))
        self.assertIn({"drifter_id": "D1", "amount": 3}, [e["data"] for e in evs if e["name"] == "drifter_drop"])
        self.assertEqual(len([m for m in sim.motes if m["kind"] == "dropped"]), 3)
        run(sim, 120)
        self.assertEqual(sim.drifters[0]["state"], "removed")

    def test_not_blocked_by_safe_zone_and_ignores_invuln(self):
        sim = Simulation(0, scen(player={"carried": 6, "invuln_ticks": 300},
                                 lanterns=[{"id": "L1", "pos": [0, 0, 0], "lit": True}],
                                 drifters=[{"pos": [5, 1.5, 0]}]), night=2)
        evs = run(sim, 60)
        self.assertIn("drifter_steal", names(evs))

    def test_spawn_schedule(self):
        sim = Simulation(4, {"random_motes": False, "random_shades": False}, night=2)
        sim.player["pos"] = [0.0, 0.0, -24.0]
        run(sim, 1199)
        self.assertEqual(sim.drifters, [])
        sim.step(inp())
        self.assertEqual([d["id"] for d in sim.drifters], ["D1"])
        self.assertEqual(Simulation(4, night=1).random_drifters, False)


class Charm(unittest.TestCase):
    def test_pick_speed_dash_respawn(self):
        sim = Simulation(0, scen(charms=[{"id": "C1", "pos": [0, 0, 0.5]}]), night=2)
        evs = sim.step(inp())
        self.assertEqual(evs[-1]["data"], {"charm_id": "C1", "charm_ticks": 600})
        z0 = sim.player["pos"][2]
        run(sim, 60, move=(0.0, 1.0))
        self.assertAlmostEqual(sim.player["pos"][2] - z0, 7.2, places=6)
        self.assertEqual(names(press(sim, "dash")), ["dash"])
        self.assertEqual(names(press(sim, "dash")), [])          # pressing while dashing is ignored
        run(sim, 12)
        self.assertEqual(names(press(sim, "dash")), ["dash"])   # no cooldown, still needs a new press
        run(sim, 12)
        self.assertEqual(names(run(sim, 30, dash=True)), ["dash"])  # holding = one dash
        self.assertFalse(sim.charms[0]["available"])
        run(sim, C.CHARM_RESPAWN)
        self.assertTrue(sim.charms[0]["available"])

    def test_default_positions(self):
        self.assertEqual([c["pos"] for c in Simulation(0, night=2).charms], [[35.0, 0.0, 0.0]])
        self.assertEqual(len(Simulation(0, night=3).charms), 2)
        self.assertEqual(Simulation(0, night=1).charms, [])


class Maps(unittest.TestCase):
    def test_lantern_positions(self):
        self.assertEqual([l["pos"] for l in Simulation(0, night=1).lanterns][1], [23.8, 0.0, 7.7])
        self.assertEqual(len(Simulation(0, night=2).lanterns), 6)
        self.assertEqual(Simulation(0, night=3).lanterns[0]["pos"], [0.0, 6.0, 6.0])

    def test_night2_bridge_and_gap(self):
        self.assertEqual(world.ground_height(2, 35, 1.9), 0.0)
        self.assertIsNone(world.ground_height(2, 35, 2.1))
        self.assertIsNone(world.ground_height(2, 35, 10))

    def test_night2_pad_lands_on_island_b(self):
        sim = Simulation(0, scen(player={"pos": [20, 0, 18]}), night=2)
        sim.step(inp())
        self.assertFalse(sim.player["grounded"])
        n = 0
        while not sim.player["grounded"] and n < 200:
            sim.step(inp(move=(-1.0, 0.0)))  # input must not override launch
            n += 1
        self.assertAlmostEqual(n / 60, 1.4, delta=0.05)
        self.assertLessEqual(xz_dist(sim.player["pos"], [70, 0, 0]), C.N2_RADIUS)

    def test_night3_tiers_ramp_tower(self):
        self.assertEqual(world.ground_height(3, 0, 18), 3.0)       # tier 1 (z > 0)
        self.assertEqual(world.ground_height(3, 0, -18), 0.0)      # no tier 1 for z < 0
        self.assertEqual(world.ground_height(3, 0, 5), 6.0)        # tier 2
        a = math.radians(30)
        self.assertAlmostEqual(world.ground_height(3, 27 * math.cos(a), 27 * math.sin(a)), 1.5)
        self.assertTrue(world.blocked_xz(3, 0, 1.0))
        # wall: walking from tier 0 straight into tier 1 is blocked
        sim = Simulation(0, scen(player={"pos": [0, 0, 26]}), night=3)
        run(sim, 60, move=(0.0, -1.0))
        self.assertGreater(sim.player["pos"][2], 24.0)   # stopped at the tier-1 wall (r = 24)
        self.assertLess(sim.player["pos"][2], 24.2)
        self.assertEqual(sim.player["pos"][1], 0.0)
        # ramp: walking up the 30 deg ramp reaches tier 1
        foot = [29.5 * math.cos(a), 0, 29.5 * math.sin(a)]
        sim = Simulation(0, scen(player={"pos": foot}), night=3)
        ux, uz = -math.cos(a), -math.sin(a)
        run(sim, 120, move=(ux, uz))
        self.assertEqual(sim.player["pos"][1], 3.0)

    def test_night3_pad_reaches_tier2(self):
        sim = Simulation(0, scen(player={"pos": [0, 3, 13]}), night=3)
        for _ in range(150):
            sim.step(inp())
            if sim.player["grounded"] and sim.tick > 5:
                break
        self.assertEqual(sim.player["pos"][1], 6.0)
        self.assertLessEqual(math.hypot(sim.player["pos"][0], sim.player["pos"][2]), 8.0)

    def test_wind_night3(self):
        sim = Simulation(2, scen(wind_enabled=True), night=3)
        run(sim, 1799)
        self.assertFalse(sim.wind["active"])
        x0 = list(sim.player["pos"])
        evs = run(sim, 60)
        self.assertTrue(sim.wind["active"])
        moved = xz_dist(sim.player["pos"], x0)
        self.assertAlmostEqual(moved, 2.0, delta=0.05)
        run(sim, 300)
        self.assertFalse(sim.wind["active"])

    def test_palette_and_ambient(self):
        self.assertEqual(C.PALETTE["lantern_lit"], "#FFB347")
        self.assertAlmostEqual(C.ambient_intensity(0, 5), 0.15)
        self.assertAlmostEqual(C.ambient_intensity(5, 5), 0.70)


class Determinism(unittest.TestCase):
    def test_same_seed_same_world(self):
        for n in (1, 2, 3):
            a, b = Simulation(42, night=n), Simulation(42, night=n)
            for _ in range(2000):
                a.step(inp(move=(0.3, 1.0)))
                b.step(inp(move=(0.3, 1.0)))
            self.assertEqual(a.snapshot(), b.snapshot())


if __name__ == "__main__":
    unittest.main()
