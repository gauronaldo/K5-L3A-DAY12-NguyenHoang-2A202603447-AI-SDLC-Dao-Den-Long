# Changelog

## phase-3 — Đèn cạn dầu (contract v1.2)

### Breaking changes
- **Luật thắng:** bỏ thắng sớm `all_lit`; chỉ xét ở bình minh: `dawn_survived` nếu đèn sáng ≥ ceil(0.6 × tổng), ngược lại `dawn`.
- **Thời lượng Đêm:** 300/330/360 s → 240/270/300 s.
- **Điểm:** thay toàn bộ — +5/đom đóm nạp (cả châm dầu), +100 thắp lần đầu, +40 thắp lại, +5/+15 trúng Tỏa Sáng, bình minh 50 + floor(fuel) mỗi đèn sáng + 50 mỗi lửa; bỏ thưởng thời gian.
- **Đèn:** có thể tắt khi hết dầu; tương tác với đèn sáng chưa đầy = châm dầu (trước đây bị bỏ qua).
- **Vùng an toàn:** chỉ khi đèn sáng và fuel ≥ 30 (trước: mọi đèn sáng).
- **Bóng Mực:** thêm trạng thái `drain`; wander ưu tiên đèn yếu.
- **Snapshot:** đèn thêm `fuel`, `ever_lit`, `relit_count`; player thêm `capacity`. Sự kiện `lantern_lit` thêm `relight`; mới `refuel`, `lantern_out`, `fuel_drain`.
- **Sức chứa:** 10 + 2 × số lần thắp thành công (tối đa 20).

### Thêm
- ADR 0001; thanh dầu + nhấp nháy 1 Hz; chế độ mù màu (lưu); scenario 21–26; camera FOV 70°.

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
