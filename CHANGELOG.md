# Changelog

## phase-2 — Ba hòn đảo (contract v1.1)

### Breaking
- Toàn bộ tuning theo số chuẩn Ticket-02 (cost 10, interact 2 m, pulse 3/5 m/3 s, safe 6 m chỉ cho đèn sáng, shade 4 m/s…).
- Điểm +10 khi **nạp** (không còn khi nhặt); thưởng thắng ×2 giây còn lại.
- `fall_enabled: true` — rơi khỏi đảo có phạt; scenario v1.0 vẫn đọc được.
- Snapshot thêm `night`, `wind`, trạng thái người chơi và mảng `motes/drifters/charms` dạng object.

### Thêm
- Đêm 2 Đảo Cau, Đêm 3 Đảo Chuông; lướt, bục nhảy, tầng/dốc/tháp, gió.
- Gió Lạc, Bùa Gió, tạm dừng, chuỗi 3 Đêm, cài đặt lưu file, âm thanh, HUD đầy đủ, bảng màu chuẩn.
- 20 scenario, test settings/campaign/âm thanh, `--fps-probe`.

## phase-1 — Đêm 1: Đảo Bến

- Logic mô phỏng tất định 60 tick/s dùng chung cho game 3D và headless.
- Headless CLI theo Test Contract v1.0 + `game.contract.json`.
- Client 3D Panda3D: di chuyển, nhảy, camera, nhặt đom đóm, gửi sáng, Bóng Mực, xung sáng, HUD, thắng/thua, chơi lại.
- 31 unit test, 8 scenario headless, `tools/verify.py`, `tools/screenshot.py`, CI Ubuntu + macOS.
- Harness: AGENTS.md, skill `verify-game`, Stop hook, agent `reviewer`.
