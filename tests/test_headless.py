"""End-to-end tests of the headless CLI (Test Contract v1.0 sections B-E)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADLESS = [sys.executable, os.path.join(ROOT, "headless.py")]


def run_cli(*args, files=None):
    tmp = tempfile.mkdtemp()
    paths = {}
    for name, content in (files or {}).items():
        p = os.path.join(tmp, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else json.dumps(content))
        paths[name] = p
    out = os.path.join(tmp, "out.jsonl")
    argv = [a.format(out=out, **paths) for a in args]
    proc = subprocess.run(HEADLESS + argv, capture_output=True, text=True)
    lines = []
    if os.path.exists(out):
        with open(out, encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
    return proc, lines


BASE = ["--seed", "1", "--night", "1", "--out", "{out}"]


class Cli(unittest.TestCase):
    def test_tick_model_and_end_line(self):
        proc, lines = run_cli(*BASE, "--ticks", "25", "--snapshot-every", "10",
                              "--scenario", "{s}", files={"s": {"random_shades": False}})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        snaps = [l for l in lines if l["type"] == "snapshot"]
        self.assertEqual([s["tick"] for s in snaps], [0, 10, 20])
        self.assertTrue(all(s["sim_tick"] == s["tick"] for s in snaps))
        self.assertEqual(snaps[0]["time_left_s"], 240.0)   # Ticket-03: Night 1 lasts 240 s
        self.assertAlmostEqual(snaps[1]["time_left_s"], 240 - 10 / 60, places=3)
        self.assertEqual(lines[-1], {"type": "end", "ticks": 25, "state": "playing", "score": snaps[-1]["score"]})

    def test_snapshot0_is_before_input(self):
        proc, lines = run_cli(*BASE, "--ticks", "1", "--snapshot-every", "1", "--inputs", "{i}",
                              files={"i": {"frames": [{"tick": 0, "move": [0, 1]}]}})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        snaps = [l for l in lines if l["type"] == "snapshot"]
        self.assertEqual(snaps[0]["player"]["pos"], [0.0, 0.0, 0.0])
        self.assertEqual(snaps[1]["player"]["pos"], [0.0, 0.0, 0.1])

    def test_inputs_fields_persist(self):
        frames = {"frames": [{"tick": 0, "move": [1, 0], "cam_yaw_deg": 90}, {"tick": 30, "interact": False}]}
        proc, lines = run_cli(*BASE, "--ticks", "60", "--snapshot-every", "60", "--inputs", "{i}",
                              "--scenario", "{s}", files={"i": frames, "s": {"random_shades": False}})
        p = lines[-2]["player"]["pos"]
        self.assertEqual(p, [0.0, 0.0, -6.0])

    def test_scenario_example_from_contract(self):
        sc = {"player": {"pos": [0, 0, 0], "carried": 0, "flames": 3}, "random_motes": False,
              "random_shades": False, "motes": [[0, 0, 5]], "shades": [{"pos": [10, 0, 0]}],
              "lanterns": [{"id": "L1", "pos": [0, 0, 25], "deposited": 0}], "time_left_s": 300}
        inputs = {"frames": [{"tick": 0, "move": [0, 1], "cam_yaw_deg": 0}]}
        proc, lines = run_cli(*BASE, "--ticks", "60", "--scenario", "{s}", "--inputs", "{i}",
                              files={"s": sc, "i": inputs})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ev = [l for l in lines if l["type"] == "event" and l["name"] != "night_start"]
        self.assertEqual(ev[0]["name"], "mote_picked")
        self.assertEqual(ev[0]["tick"], 40)  # step k=39 -> state 40: z=4.0, distance to mote = 1.0 <= pickup_radius
        snap0 = lines[0]
        self.assertEqual(snap0["shades"][0]["id"], "S1")
        self.assertEqual(snap0["motes_active"], 1)
        self.assertEqual(len(snap0["lanterns"]), 5)

    def test_game_over_stops_early_exit0(self):
        sc = {"random_motes": False, "random_shades": False, "time_left_s": 0.5}
        proc, lines = run_cli(*BASE, "--ticks", "1000", "--scenario", "{s}", files={"s": sc})
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(lines[-1], {"type": "end", "ticks": 30, "state": "lost", "score": 0})
        over = [l for l in lines if l.get("name") == "game_over"]
        self.assertEqual(over, [{"type": "event", "tick": 30, "name": "game_over",
                                 "data": {"result": "lost", "reason": "dawn"}}])

    def test_determinism_default_night(self):
        inputs = {"frames": [{"tick": 0, "move": [0.3, 1]}, {"tick": 50, "pulse": True}, {"tick": 51, "pulse": False},
                             {"tick": 90, "move": [-1, 0], "jump": True}, {"tick": 91, "jump": False}]}
        outs = []
        for _ in range(2):
            proc, lines = run_cli("--seed", "99", "--night", "3", "--out", "{out}", "--ticks", "3000",
                                  "--inputs", "{i}", files={"i": inputs})
            self.assertEqual(proc.returncode, 0)
            outs.append(lines)
        self.assertEqual(outs[0], outs[1])

    def test_malformed_files_exit_2(self):
        bad_inputs = [
            "{not json",
            {"frames": [{"tick": 5}, {"tick": 5}]},
            {"frames": [{"tick": 5}, {"tick": 3}]},
            {"frames": [{"tick": 0, "move": [2, 0]}]},
            {"frames": [{"tick": 0, "pulse": "yes"}]},
            {"nope": []},
        ]
        for bad in bad_inputs:
            proc, _ = run_cli(*BASE, "--ticks", "10", "--inputs", "{i}", files={"i": bad})
            self.assertEqual(proc.returncode, 2, bad)
            self.assertTrue(proc.stderr.strip())
        for bad in ["[]", {"player": {"pos": [0, 0]}}, {"motes": "x"}, {"random_shades": 1}]:
            proc, _ = run_cli(*BASE, "--ticks", "10", "--scenario", "{s}", files={"s": bad})
            self.assertEqual(proc.returncode, 2, bad)

    def test_bad_cli_nonzero(self):
        proc, _ = run_cli("--seed", "1", "--night", "1", "--ticks", "10")  # missing --out
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(proc.stderr.strip())

    # Phase 1 test "events_dont_include_fall" removed: Ticket-02 enables falling (fall_enabled = true).
    def test_fall_event_has_lost_field(self):
        proc, lines = run_cli(*BASE, "--ticks", "900", "--inputs", "{i}",
                              files={"i": {"frames": [{"tick": 0, "move": [1, 0]}]}})
        falls = [l for l in lines if l.get("name") == "player_hit" and l["data"]["by"] == "fall"]
        self.assertTrue(falls)
        self.assertEqual(set(falls[0]["data"]), {"by", "flames", "dropped", "lost"})

    def test_snapshot_schema_v1_1(self):
        for night in ("1", "2", "3"):
            proc, lines = run_cli("--seed", "4", "--night", night, "--out", "{out}", "--ticks", "1500")
            self.assertEqual(proc.returncode, 0, proc.stderr)
            snap = [l for l in lines if l["type"] == "snapshot"][-1]
            self.assertEqual(snap["night"], int(night))
            self.assertEqual(set(snap["wind"]), {"active", "dir_deg"})
            self.assertTrue({"pos", "vel", "grounded", "invuln", "flames", "carried", "dash_cd_s", "pulse_cd_s",
                             "charm_s"} <= set(snap["player"]))
            self.assertIsInstance(snap["player"]["invuln"], bool)
            for m in snap["motes"]:
                self.assertEqual(set(m), {"id", "pos", "kind", "ttl_s"})
            for d in snap["drifters"]:
                self.assertEqual(set(d), {"id", "pos", "state", "stolen"})
            for c in snap["charms"]:
                self.assertEqual(set(c), {"id", "available", "respawn_s"})
            for sh in snap["shades"]:
                self.assertIn(sh["state"], ("spawning", "wander", "chase", "recoil", "stunned"))
            self.assertEqual(lines[1]["name"], "night_start")

    def test_pause_input(self):
        frames = {"frames": [{"tick": 5, "pause": True}, {"tick": 6, "pause": False},
                             {"tick": 20, "pause": True}, {"tick": 21, "pause": False}]}
        proc, lines = run_cli(*BASE, "--ticks", "30", "--snapshot-every", "10", "--inputs", "{i}", files={"i": frames})
        snaps = {l["tick"]: l for l in lines if l["type"] == "snapshot"}
        self.assertEqual((snaps[10]["state"], snaps[10]["sim_tick"]), ("paused", 5))
        self.assertEqual((snaps[30]["state"], snaps[30]["sim_tick"]), ("playing", 15))
        self.assertEqual([l["name"] for l in lines if l.get("name") in ("paused", "resumed")], ["paused", "resumed"])

    def test_snapshot_schema_v1_2(self):
        sc = {"lanterns": [{"id": "L1", "lit": True}, {"id": "L2", "lit": True, "fuel": 12.34, "ever_lit": True}],
              "player": {"successful_lights": 2}}
        proc, lines = run_cli(*BASE, "--ticks", "1", "--snapshot-every", "1", "--scenario", "{s}", files={"s": sc})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        snap = [l for l in lines if l["type"] == "snapshot"][0]
        self.assertEqual(snap["lanterns"][0]["fuel"], 100.0)   # lit without fuel -> 100
        self.assertEqual(snap["lanterns"][1]["fuel"], 12.3)    # one decimal
        self.assertEqual(snap["lanterns"][2]["fuel"], 0.0)     # unlit -> 0
        self.assertEqual(set(snap["lanterns"][0]), {"id", "pos", "lit", "deposited", "fuel", "ever_lit", "relit_count"})
        self.assertEqual(snap["player"]["capacity"], 14)

    def test_bad_night_exit_2(self):
        proc, _ = run_cli("--seed", "1", "--night", "4", "--ticks", "10", "--out", "{out}")
        self.assertEqual(proc.returncode, 2)

    def test_full_night_under_30s(self):
        import time
        t0 = time.perf_counter()
        proc, lines = run_cli("--seed", "9", "--night", "3", "--ticks", "21600", "--out", "{out}")
        self.assertEqual(proc.returncode, 0)
        self.assertLess(time.perf_counter() - t0, 30.0)


class ContractFile(unittest.TestCase):
    def test_contract_matches_code(self):
        sys.path.insert(0, ROOT)
        from lantern import config as C
        with open(os.path.join(ROOT, "game.contract.json"), encoding="utf-8") as f:
            gc = json.load(f)
        self.assertEqual(gc["contract_version"], C.CONTRACT_VERSION)
        for k, v in C.TUNING.items():
            self.assertEqual(gc["tuning"][k], v, k)
        self.assertEqual(set(gc["tuning"]), set(C.TUNING))
        self.assertEqual(gc["score"], C.SCORE)
        self.assertEqual(gc["fall_enabled"], C.FALL_ENABLED)
        self.assertTrue(gc["bench_cmd"] and gc["soak_cmd"])   # contract v1.3


if __name__ == "__main__":
    unittest.main()
