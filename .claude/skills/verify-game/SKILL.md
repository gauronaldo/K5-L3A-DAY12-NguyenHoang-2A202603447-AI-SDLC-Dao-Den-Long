---
name: verify-game
description: Run the full verification of Dao Den Long (unit tests, headless scenarios for nights 1-3 twice for determinism, screenshots, FPS) and refresh the evidence in docs/proof/<phase>/. Use after changing game logic or the client, before tagging a phase, or when asked to prove a requirement works.
---

# Verify game and save evidence

1. `python3 tools/verify.py --phase phase-N` (N = current phase). Exit 0 = all green.
2. A scenario fails → read the FAIL line, compare with `docs/notes/phase-N.md` and the ticket in `docs/lab/tickets/`.
   Fix the code if it breaks a requirement; fix the scenario only if the expectation was wrong, and write why
   in the phase notes (section "AI sai / lỗi phát hiện").
3. New requirement → add `scenarios/<NN_name>/`:
   - `scenario.json` / `inputs.json` (contract format; turn off unrelated systems: `random_motes`, `random_shades`,
     `random_drifters`, `wind_enabled`)
   - `expect.json`: `{"req", "why", "seed", "night", "ticks", "snapshot_every", "expect": [...], "max_wall_s"?}`
   - checks: `event` (name, data subset, tick?), `event_count`, `no_event`, `snapshot` (tick, path like
     `drifters.0.state` / `lanterns.length` / `player.pos.1`, equals), `same` (ticks, path), `player_near`,
     `player_moved`, `min_shade_lantern_dist` (lit lanterns, from_tick?), `end`.
   - `why` = hand calculation of every expected number. Never copy numbers from a run.
4. Client changed → `python3 tools/screenshot.py --phase phase-N`, then OPEN the PNGs and look.
5. Performance → `python3 main.py --fps-probe 10 --night 3` (save the JSON line to `docs/proof/phase-N/fps.jsonl`).
   Release benchmark → `python3 main.py --bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json`
   (thresholds avg >= 60, 1% low >= 30, load <= 10000 ms; note other heavy apps running).
   Soak → `python3 soak.py --seed 7 --nights 10 --out docs/proof/phase-4/soak.json` (crashes 0, mem_end <= 1.2 x start).
   Slow? profile first: run the bench under cProfile with SystemExit caught (userExit calls sys.exit).
6. Never edit `docs/proof/` by hand. Commit regenerated evidence with the code it verifies.
