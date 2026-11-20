# Phase 3 — Ticket-03 "Đèn cạn dầu" (Contract v1.2)

Đề gốc: [ticket-03](../lab/tickets/ticket-03.md). Quyết định thiết kế: [ADR 0001](../adr/0001-lantern-fuel-and-dawn-win.md).

## 1. Luật cũ bị thay → test/scenario bị ảnh hưởng

| Luật cũ [THAY THẾ] | Test / scenario cũ | Xử lý |
|---|---|---|
| Thắng ngay khi mọi đèn sáng (`all_lit`) | `Night.test_win_on_dawn_tick_and_bonus`, `test_win_bonus_seconds_x2`, scenario `02_win_all_lit`, CLI không bị ảnh hưởng | **Xoá** (luật không còn); thay bằng `test_dawn_survived_*`, `test_no_early_win`, scenario `02_dawn_survived`, `21_dawn_below_threshold` |
| Điểm +10/đom đóm nạp, thưởng ×2 giây | `test_partial_deposit_and_light_scoring`, scenario `01` (200 → 150) | **Sửa** số theo bảng điểm mới |
| Đèn sáng không nhận đom đóm | (chưa có test riêng) | Thêm `Fuel.test_refuel_*` |
| Vùng an toàn luôn có ở đèn sáng | `SafeZone.*`, scenario `05`, `12` | **Giữ** — đèn sáng từ scenario có fuel 100 ≥ 30; thêm `test_low_fuel_loses_zone` |
| Thời lượng 300/330/360 s | `test_night_start_event_and_flames_per_night` (đọc từ config), scenario `07` (time_left 300 → 240), `08` (18000 → 14400), `20` (21600 → 18000) | **Sửa** số; `20` đổi vị trí đứng vì L6 tắt sau 100 s (xem §4) |
| `no_flames` thắng `all_lit` | `test_no_flames_beats_all_lit_and_dawn` | **Sửa** thành `no_flames` thắng `dawn_survived` ở tick bình minh |
| Sức chứa cố định 10 | `test_capacity` | **Giữ** (successful_lights = 0 → 10); thêm `test_capacity_grows` |

## 2. Giả định

| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| D1 | "Đầy dầu" | `fuel_u == 6000` đúng tuyệt đối; `used = min(mang, ceil((6000 − fuel_u)/600))` |
| D2 | Scenario `lit: true` không ghi `ever_lit` | `ever_lit = true` (đèn đang sáng thì đã từng sáng); `fuel` mặc định 100 |
| D3 | Tốc độ đi tới đèn yếu | Tốc độ wander 2 m/s như Phase 2 (B4) |
| D4 | Wander gặp Mây trong 12 m | Vẫn chuyển `chase` như Phase 2 (ticket chỉ thêm luật drain → chase 6 m) |
| D5 | Thời điểm hút | Bóng Mực ở trạng thái `drain` lúc đầu tick bị trừ 5 đơn vị ở bước 2 tick đó |
| D6 | `fuel_drain` mỗi 60 tick | Mỗi con đếm số tick đã hút liên tục; ghi event khi bộ đếm chia hết cho 60 (lần đầu sau 60 tick hút) |
| D7 | Bật lại vùng an toàn | Khi đèn vừa thắp, hoặc châm từ < 30 lên ≥ 30 → mọi Bóng Mực trong 6 m (kể cả đang drain) bị đẩy ra ≤ 30 tick, vô hại |
| D8 | successful_lights | Tăng 1 với mỗi `lantern_lit` (lần đầu hay thắp lại); scenario đặt sẵn được |
| D9 | Bóng Mực mục tiêu scenario | `target_lantern_id` đặt mục tiêu ban đầu cho `wander/drain`; mục tiêu được tính lại mỗi tick theo luật |
| D10 | Tỏa Sáng +15 | Tổng 15 (không cộng thêm 5) nếu trạng thái ngay trước khi trúng là `drain` |
| D11 | Phạm vi mù màu | Chỉ ảnh hưởng client; lưu trong settings (`colorblind`) |

## 3. Tiêu chí nghiệm thu

| ID | Tiêu chí | Kiểm chứng |
|---|---|---|
| P1 | Dầu: thắp → 100; hao 1/s; hết → `lantern_out`, deposited 0, ever_lit | `Fuel.*`, scenario `22_fuel_out_relight` |
| P2 | Châm dầu đúng công thức; đèn đầy không được chọn; +5/đom đóm; `refuel` | `test_refuel_*`, scenario `23_refuel` |
| P3 | Thắp lại cần 5; `lantern_lit relight:true`; +40; relit_count | scenario `22` |
| P4 | fuel < 30 mất vùng; đúng 30 còn; wander nhắm đèn yếu → `drain` ≤ 2 m, hút 5/s cộng dồn; `fuel_drain` mỗi 60 tick | scenario `24_drain`, `Drain.*` |
| P5 | Drain → chase ≤ 6 m / stunned (+15) / wander (đèn tắt, châm ≥ 30, > 2 m); châm ≥ 30 đẩy Bóng Mực ra ≤ 30 tick | `Drain.*`, scenario `25_drain_refuel_evict` |
| P6 | Thời lượng 240/270/300; không thắng sớm; thắng `dawn_survived` khi đèn sáng ≥ ceil(0.6·n); `no_flames` ưu tiên | scenario `02_dawn_survived`, `21_dawn_below_threshold`, `Night.*` |
| P7 | Điểm bình minh: mỗi đèn sáng 50 + floor(fuel), mỗi lửa 50 | scenario `02` (tính tay) |
| P8 | Sức chứa 10 + 2·successful_lights, tối đa 20; snapshot `capacity` | `test_capacity_grows` |
| P9 | Contract v1.2: tuning, snapshot (fuel 1 chữ số, đèn tắt 0), scenario, event | `test_headless`, `ContractFile` |
| P10 | Mù màu: viền/mắt #00B3FF, cảnh báo #FFFFFF + ⚠, đèn tắt xẹp 20% + rách, sắp hết dầu nhấp nháy; được lưu | ảnh chụp + `test_app.SettingsTest` |
| P11 | Thanh dầu trên đèn sáng; < 30 nhấp nháy 1 Hz | ảnh chụp |
