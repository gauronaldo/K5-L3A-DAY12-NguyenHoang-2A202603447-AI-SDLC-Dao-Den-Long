"""Soak test (Ticket-04 section 2): many nights in one process with seeded random input; checks crashes + memory."""
import argparse
import gc
import json
import math
import random
import sys
import time
import traceback

from . import sysinfo
from .sim import InputState, Simulation


def random_input(rng, tick, state):
    """Every 30 ticks pick a new move direction; per tick: 5% jump, 3% dash, 2% pulse, 10% interact."""
    if tick % 30 == 0:
        a = rng.uniform(0.0, 2.0 * math.pi)
        state["move"] = (math.cos(a), math.sin(a))
    i = InputState()
    i.move = state["move"]
    i.jump = rng.random() < 0.05
    i.dash = rng.random() < 0.03
    i.pulse = rng.random() < 0.02
    i.interact = rng.random() < 0.10
    return i


def run_night(seed, night):
    sim = Simulation(seed, night=night)
    rng = random.Random(seed)
    state = {"move": (0.0, 0.0)}
    k = 0
    while sim.state == "playing" and k < sim.total_ticks + 10:
        sim.step(random_input(rng, k, state))
        if k % 10 == 0:
            json.dumps(sim.snapshot())   # exercise serialisation like headless does
        k += 1
    return sim


def soak(seed, nights, progress=None):
    t0 = time.perf_counter()
    results, crashes, mem_start = [], 0, None
    for i in range(1, nights + 1):
        night = (i - 1) % 3 + 1
        try:
            if mem_start is None:
                probe = Simulation(seed + i, night=night)   # "after loading the first night"
                gc.collect()
                mem_start = sysinfo.rss_mb()
                del probe
            sim = run_night(seed + i, night)
            results.append(sim.state)
            del sim
        except Exception:
            crashes += 1
            results.append("crash")
            traceback.print_exc()
        if progress:
            progress(i, night, results[-1])
    gc.collect()     # "after the last night has been reset"
    mem_end = sysinfo.rss_mb()
    return {"nights": nights, "crashes": crashes, "results": results, "mem_start_mb": round(mem_start, 1),
            "mem_end_mb": round(mem_end, 1), "duration_s": round(time.perf_counter() - t0, 1),
            "seeds": [seed + i for i in range(1, nights + 1)], "os": sysinfo.os_description()}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="soak", description="Dao Den Long soak test (Ticket-04)")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--nights", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = soak(a.seed, a.nights, lambda i, n, r: sys.stderr.write("night %d/%d (Dem %d): %s\n" % (i, a.nights, n, r)))
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    ok = out["crashes"] == 0 and out["mem_end_mb"] <= 1.2 * out["mem_start_mb"]
    sys.stderr.write("soak %s: %s\n" % ("PASS" if ok else "FAIL", json.dumps(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
