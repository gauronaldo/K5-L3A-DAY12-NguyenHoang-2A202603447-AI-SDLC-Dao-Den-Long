"""Headless runner (Test Contract v1.0, section B). No window, no GPU, stdlib only."""
import argparse
import json
import sys

from .files import ContractError, load_inputs, load_scenario
from .sim import InputState, Simulation


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        sys.exit(2)


def _dump(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def run(seed, night, ticks, out_path, scenario=None, frames=None, snapshot_every=10):
    sim = Simulation(seed=seed, scenario=scenario, night=night)
    frames = frames or {}
    inp = InputState()
    lines = [_dump(sim.snapshot())]
    for k in range(ticks):
        ch = frames.get(k)
        if ch:
            for key, val in ch.items():
                setattr(inp, key, val)
        for ev in sim.step(inp):
            lines.append(_dump(ev))
        if sim.tick % snapshot_every == 0:
            lines.append(_dump(sim.snapshot()))
        if sim.state != "playing":
            break
    lines.append(_dump({"type": "end", "ticks": sim.tick, "state": sim.state, "score": sim.score}))
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    return sim


def main(argv=None):
    ap = _Parser(prog="headless", description="Dao Den Long headless mode (Test Contract v1.1)")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--night", type=int, required=True)
    ap.add_argument("--scenario")
    ap.add_argument("--inputs")
    ap.add_argument("--ticks", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--snapshot-every", type=int, default=10)
    a = ap.parse_args(argv)

    if a.night not in (1, 2, 3):
        sys.stderr.write("error: --night must be 1, 2 or 3\n")
        return 2
    if a.ticks < 0 or a.snapshot_every < 1:
        sys.stderr.write("error: --ticks must be >= 0 and --snapshot-every >= 1\n")
        return 2
    try:
        scenario = load_scenario(a.scenario) if a.scenario else None
        frames = load_inputs(a.inputs) if a.inputs else None
    except ContractError as e:
        sys.stderr.write("error: %s\n" % e)
        return 2
    try:
        run(a.seed, a.night, a.ticks, a.out, scenario, frames, a.snapshot_every)
    except OSError as e:
        sys.stderr.write("error: cannot write output: %s\n" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
