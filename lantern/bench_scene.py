"""Benchmark scene (Ticket-04 section 1) and frame statistics. No rendering here, so it is unit-testable."""
import math
import random

from . import config as C
from .sim import Simulation, xz_dist

BENCH_SHADES = 200
BENCH_MOTES = 100
BENCH_RADIUS = 38.0           # E1: uniform over the island area, inside the 40 m edge
WARMUP_S = 3.0
CAM_RADIUS = 30.0
CAM_HEIGHT = 15.0
CAM_LAP_S = 15.0


def bench_scenario(seed=42):
    rng = random.Random(seed)
    lit = [{"id": "L%d" % i, "lit": True, "fuel": 100} for i in (1, 2, 3)]
    lit_pos = [C.NIGHTS[1]["lanterns"][i] for i in range(3)]

    def point(y):
        while True:
            a = rng.uniform(0.0, 2.0 * math.pi)
            r = BENCH_RADIUS * math.sqrt(rng.random())
            p = [round(r * math.cos(a), 3), y, round(r * math.sin(a), 3)]
            if r < 3.0 or any(xz_dist(p, l) <= C.TUNING["safe_radius"] for l in lit_pos):
                continue
            return p

    shades = [{"id": "S%d" % (i + 1), "pos": point(C.SHADE_HOVER), "state": "wander"} for i in range(BENCH_SHADES)]
    motes = [point(0.0) for _ in range(BENCH_MOTES)]
    return {"player": {"pos": [0, 0, 0]}, "random_motes": False, "random_shades": False, "random_drifters": False,
            "wind_enabled": False, "lanterns": lit, "shades": shades, "motes": motes}


def bench_sim(seed=42):
    sim = Simulation(seed, bench_scenario(seed), night=1)
    sim.bench = True      # no spawns, damage, pickup, fuel burn, end of night, or wander->chase
    return sim


def camera_pose(t):
    """Sim-space camera position at time t (s): circle r=30 at y=15, angle 0 at (30,15,0), CCW from above."""
    th = 2.0 * math.pi * t / CAM_LAP_S
    return [CAM_RADIUS * math.cos(th), CAM_HEIGHT, CAM_RADIUS * math.sin(th)]


def frame_stats(dts_ms):
    """Ticket-04 definitions. dts_ms: frame times in milliseconds inside the measured window."""
    n = len(dts_ms)
    total = sum(dts_ms)
    k = max(1, int(math.ceil(0.01 * n)))
    worst = sorted(dts_ms, reverse=True)[:k]
    s = sorted(dts_ms)
    p95 = s[max(0, int(math.ceil(0.95 * n)) - 1)]   # nearest-rank
    return {"frames": n, "avg_fps": round(1000.0 * n / total, 1), "p1_low_fps": round(1000.0 / (sum(worst) / k), 1),
            "frame_ms_p95": round(p95, 2)}
