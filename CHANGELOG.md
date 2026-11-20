# Changelog

## phase-1 — Đêm 1: Đảo Bến

- Logic mô phỏng tất định 60 tick/s dùng chung cho game 3D và headless.
- Headless CLI theo Test Contract v1.0 + `game.contract.json`.
- Client 3D Panda3D: di chuyển, nhảy, camera, nhặt đom đóm, gửi sáng, Bóng Mực, xung sáng, HUD, thắng/thua, chơi lại.
- 31 unit test, 8 scenario headless, `tools/verify.py`, `tools/screenshot.py`, CI Ubuntu + macOS.
- Harness: AGENTS.md, skill `verify-game`, Stop hook, agent `reviewer`.
