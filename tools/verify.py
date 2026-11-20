#!/usr/bin/env python3
"""One-command verification: unit tests + headless scenarios + determinism + timing.

    python3 tools/verify.py            # full run, writes evidence to docs/proof/<phase>/
    python3 tools/verify.py --quick    # unit tests only (used by the agent Stop hook)

Exit code 0 only if everything passes.
"""
import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADLESS = [sys.executable, os.path.join(ROOT, "headless.py")]


def unit_tests():
    suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "tests"))
    res = unittest.TextTestRunner(verbosity=0, stream=sys.stderr).run(suite)
    return res.wasSuccessful(), res.testsRun, len(res.failures) + len(res.errors)


def get_path(obj, path):
    for part in path.split("."):
        if part == "length":
            obj = len(obj)
        elif isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


def check(lines, exp):
    events = [l for l in lines if l["type"] == "event"]
    snaps = {l["tick"]: l for l in lines if l["type"] == "snapshot"}
    end = lines[-1]
    c = exp["check"]
    if c == "event":
        hits = [e for e in events if e["name"] == exp["name"]
                and all(e["data"].get(k) == v for k, v in exp.get("data", {}).items())
                and ("tick" not in exp or e["tick"] == exp["tick"])]
        return bool(hits), "found %d matching" % len(hits)
    if c == "event_count":
        n = sum(1 for e in events if e["name"] == exp["name"])
        return n == exp["count"], "count=%d" % n
    if c == "no_event":
        n = sum(1 for e in events if e["name"] == exp["name"])
        return n == 0, "count=%d" % n
    if c == "snapshot":
        if exp["tick"] not in snaps:
            return False, "no snapshot at tick %d" % exp["tick"]
        got = get_path(snaps[exp["tick"]], exp["path"])
        return got == exp["equals"], "got %r" % (got,)
    if c == "min_shade_lantern_dist":
        m = math.inf
        for s in snaps.values():
            for sh in s["shades"]:
                for la in s["lanterns"]:
                    m = min(m, math.hypot(sh["pos"][0] - la["pos"][0], sh["pos"][2] - la["pos"][2]))
        return m >= exp["min"], "min=%.3f over %d snapshots" % (m, len(snaps))
    if c == "end":
        bad = {k: end.get(k) for k in ("state", "score", "ticks") if k in exp and end.get(k) != exp[k]}
        return not bad, "end=%s" % json.dumps(end)
    return False, "unknown check %s" % c


def run_headless(sdir, meta, out):
    cmd = HEADLESS + ["--seed", str(meta["seed"]), "--night", "1", "--ticks", str(meta["ticks"]),
                      "--out", out, "--snapshot-every", str(meta["snapshot_every"])]
    for fn, flag in (("scenario.json", "--scenario"), ("inputs.json", "--inputs")):
        if os.path.exists(os.path.join(sdir, fn)):
            cmd += [flag, os.path.join(sdir, fn)]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    with open(out, encoding="utf-8") as f:
        data = f.read()
    return proc.returncode, data, dt, cmd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--phase", default="phase-1")
    a = ap.parse_args()

    ok_unit, n_unit, n_bad = unit_tests()
    print("unit tests: %d run, %d failed" % (n_unit, n_bad))
    if a.quick:
        return 0 if ok_unit else 1

    proof = os.path.join(ROOT, "docs", "proof", a.phase)
    runs = os.path.join(proof, "runs")
    os.makedirs(runs, exist_ok=True)
    rows, all_ok = [], ok_unit
    for name in sorted(os.listdir(os.path.join(ROOT, "scenarios"))):
        sdir = os.path.join(ROOT, "scenarios", name)
        with open(os.path.join(sdir, "expect.json"), encoding="utf-8") as f:
            meta = json.load(f)
        out_a = os.path.join(runs, name + ".jsonl")
        rc, data_a, dt, cmd = run_headless(sdir, meta, out_a)
        rc_b, data_b, _, _ = run_headless(sdir, meta, out_a + ".rerun")
        os.remove(out_a + ".rerun")
        lines = [json.loads(l) for l in data_a.splitlines() if l.strip()]
        results = [(e, *check(lines, e)) for e in meta["expect"]]
        det = data_a == data_b
        ok = rc == 0 and rc_b == 0 and det and all(r[1] for r in results)
        all_ok &= ok
        rows.append((name, meta, ok, det, dt, results, hashlib.sha256(data_a.encode()).hexdigest()[:12], lines[-1]))
        print("%-28s %s  (%.2fs, deterministic=%s)" % (name, "PASS" if ok else "FAIL", dt, det))
        for e, passed, msg in results:
            if not passed:
                print("    FAIL %s -> %s" % (json.dumps(e), msg))

    with open(os.path.join(proof, "verify-report.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# Verify report (%s)\n\n" % a.phase)
        f.write("Generated by `python3 tools/verify.py` - do not edit by hand.\n\n")
        f.write("- Machine: %s, Python %s\n" % (platform.platform(), platform.python_version()))
        f.write("- Unit tests: %d run, %d failed -> **%s**\n\n" % (n_unit, n_bad, "PASS" if ok_unit else "FAIL"))
        f.write("| Scenario | Requirement | Result | Deterministic (2 runs) | Wall time | End line | sha256[:12] |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for name, meta, ok, det, dt, results, h, end in rows:
            f.write("| `%s` | %s | %s | %s | %.2fs | `%s` | `%s` |\n" % (
                name, meta["req"], "PASS" if ok else "FAIL", det, dt, json.dumps(end), h))
        f.write("\n## Checks\n")
        for name, meta, ok, det, dt, results, h, end in rows:
            f.write("\n### %s\n\n" % name)
            for e, passed, msg in results:
                f.write("- [%s] `%s` -> %s\n" % ("x" if passed else " ", json.dumps(e), msg))
        f.write("\n**Overall: %s**\n" % ("PASS" if all_ok else "FAIL"))
    print("overall:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
