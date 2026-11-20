---
name: verify-game
description: Run the full verification of Dao Den Long (unit tests, headless scenarios twice for determinism) and refresh the evidence in docs/proof/<phase>/. Use after changing game logic, before tagging a phase, or when asked to prove a requirement works.
---

# Verify game and save evidence

1. Run `python3 tools/verify.py --phase phase-N` (N = current phase). Exit 0 = all green.
2. If a scenario fails: read the FAIL line, compare with `docs/notes/phase-N.md`. Fix the code if it breaks a requirement; fix the scenario only if the expectation was wrong, and note why in the phase notes.
3. New requirement → add `scenarios/<NN_name>/` with:
   - `scenario.json` / `inputs.json` (Test Contract format, optional)
   - `expect.json`: `{"req": "...", "seed": 1, "ticks": N, "snapshot_every": 10, "expect": [...]}`
   - check types: `event` (name, data subset, tick?), `event_count`, `no_event`,
     `snapshot` (tick, path like `shades.0.state` / `lanterns.length`, equals),
     `min_shade_lantern_dist`, `end` (state/score/ticks).
4. Screenshot of the 3D client (needs panda3d): `python3 tools/screenshot.py` → `docs/proof/phase-N/screenshots/`.
5. Never edit files in `docs/proof/` by hand. Commit the regenerated report with the code it verifies.
