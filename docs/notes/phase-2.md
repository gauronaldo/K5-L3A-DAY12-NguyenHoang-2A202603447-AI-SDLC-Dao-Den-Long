# Phase 2 — Ticket-02 "Ba hòn đảo" (Contract v1.1)

Đề gốc: [docs/lab/tickets/ticket-02.md](../lab/tickets/ticket-02.md).

## 1. Giả định Phase 1 bị ticket thay thế

| Phase 1 | Phase 2 (chuẩn) | Ảnh hưởng tới test cũ |
|---|---|---|
| A1 pulse tốn 1, bán kính 6, choáng 3 s, hồi 1 s, đẩy tức thì 4 m | tốn 3, bán kính 5 (3D, tâm chân+0.8), choáng 120 tick, đẩy 4 m rải trong 15 tick, hồi 3 s | sửa `test_pulse_*`, scenario `04` |
| A3 safe_radius 5 quanh **mọi** đèn | 6 m quanh đèn **đã sáng**; shade trong vùng lúc đèn vừa thắp bị đẩy ra trong ≤ 30 tick | sửa `test_safe_radius_*`, scenario `05` (dùng đèn đã sáng) |
| A4 không rơi, chặn ở mép | rơi khi Y < −10: −1 lửa, mất hết đom đóm, chờ 60 tick, hồi sinh | xoá `test_island_edge_clamp_no_fall`, thay bằng test rơi |
| A5 đom đóm rơi mất hẳn | rơi ra vành 1.5–2.5 m, TTL 480 tick, nhặt lại được | sửa `test_hit_drop_invuln` |
| A6 cost 5, interact 2.5 | cost 10, interact 2.0, chọn đèn gần nhất / id nhỏ | test dùng `T[...]` tự cập nhật; scenario `01` sửa số |
| A7 điểm +10 khi **nhặt** | +10 mỗi đom đóm **nạp**, thưởng thắng ×2 giây | sửa test điểm, scenario `01`, `02` |
| A8 2 shade lúc đầu, mỗi 45 s, luôn đuổi | 2 con ở tick 300 rồi mỗi 8/7/6 s; state `spawning/wander/chase/recoil/stunned`; phát hiện 12 m, bỏ 18 m | sửa `test_default_night_layout`, `test_shade_spawn_event_and_ids`, scenario `08` |
| A9 40 đom đóm, không hồi | 20 lúc đầu, +1 mỗi 240 tick tới trần 30, đặt trên điểm sinh chuẩn | sửa test bố cục |
| A10 đèn trên vòng 25 m tự tính | toạ độ chuẩn trong ticket | — |
| A12/A13 thứ tự tick | thứ tự 12 bước bắt buộc của ticket | thay hoàn toàn `step()` |
| Thắng ngay khi thắp đèn cuối | xét thắng/thua ở cuối tick, `no_flames` ưu tiên | sửa test thắng |

## 2. Giả định mới (chỗ ticket chưa nói rõ)

| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| B1 | Tăng tốc ≤ 0.1 s | Vận tốc ngang đặt ngay bằng hướng × tốc độ (0 s, thoả "≤ 0.1 s") |
| B2 | Chênh cao khi chạm Bóng Mực | So trực tiếp `player.pos.y` (chân) với `shade.pos.y` (tâm) như hai vị trí trong contract |
| B3 | Shade mới sinh | Trạng thái `spawning` 60 tick (không di chuyển, không gây sát thương), rồi `wander` |
| B4 | `wander` | Trôi 2 m/s tới đèn **chưa sáng** gần nhất (dừng khi cách ≤ 2 m); không còn đèn chưa sáng thì đứng yên. Ticket-03 sau này gọi đây là "đi về đèn tắt gần nhất như trước" |
| B5 | Shade trong scenario không ghi `state` | `wander` (rồi tự sang `chase` nếu Mây ≤ 12 m) |
| B6 | Vị trí Y của shade | Bay ở độ cao mặt đất + 1.0 m tại vị trí XZ; trên biển giữ Y cũ. Shade bay qua vách tầng; chỉ tháp chuông (r = 2) là vật cản |
| B7 | recoil | Lùi 2 m ra xa Mây đều trong 60 tick, rồi `chase` nếu ≤ 12 m, ngược lại `wander` |
| B8 | Điểm sinh shade hợp lệ | Cách Mây ≥ 15 m (XZ) và không nằm trong vùng an toàn của đèn đã sáng; chọn ngẫu nhiên theo seed |
| B9 | `invuln` trong snapshot | Kiểu boolean (đang bất tử hay không); số tick còn lại đặt qua scenario `invuln_ticks` |
| B10 | `night_start` | Ghi ở tick 1 (bước đầu tiên của Đêm), không ghi lúc dựng scenario |
| B11 | Điểm xuất phát Đêm 2 / 3 | Đêm 2: (0,0,0) đảo A. Đêm 3: (0,0,0) nằm trong tháp chuông nên dùng **(0,0,−25)** tầng 0, quay mặt +Z |
| B12 | Bậc đi lên | Đi bộ lên được chênh ≤ 0.35 m/tick (đủ cho dốc 3 m / 6 m); cao hơn là vách chặn |
| B13 | Chạm bục nhảy | Đang đứng trên mặt đất và XZ ≤ 1 m tới tâm bục |
| B14 | Gió Đêm 3 | Cơn gió bắt đầu ở sim_tick 1800k (k ≥ 1), kéo dài 300 tick; hướng chọn ngẫu nhiên (seed) lúc báo trước (120 tick trước); `wind_enabled=false` tắt hẳn |
| B15 | Gió Lạc `idle` | Lượn 2 m/s tới một điểm sinh đom đóm ngẫu nhiên, tới nơi thì chọn điểm khác; bay cao mặt đất + 1.5 m |
| B16 | "Tối đa 2" Gió Lạc | Tính số con chưa `removed`. Con `removed` vẫn có trong mảng snapshot |
| B17 | Đếm "dưới 30" đom đóm | Tính mọi đom đóm đang có (cả loại rơi); điểm trống = điểm sinh chưa có đom đóm `random` |
| B18 | id đom đóm | `M1, M2, …` theo thứ tự tạo (cả loại rơi); `ttl_s` của loại `random` là `null` |
| B19 | Điểm trong headless | Dòng `end` ghi điểm của Đêm đang chạy |
| B20 | Khi chờ hồi sinh | Mây đứng yên ở chỗ rơi, không nhận input |

## 3. Tiêu chí nghiệm thu (Phần 1–4)

| ID | Tiêu chí | Kiểm chứng |
|---|---|---|
| S1 | Chạy 6 m/s; nhảy 7 m/s, g −20, chỉ khi chạm đất | unit `Movement` |
| S2 | Lướt 14 m/s × 12 tick, hồi 90 tick từ lúc bắt đầu, theo hướng di chuyển hoặc hướng mặt; trên không giữ độ cao; event `dash` | unit + scenario `10_dash` |
| S3 | Nhặt khi XZ ≤ 1 và chênh cao ≤ 1.5; 20 đom đóm lúc đầu, +1 mỗi 240 tick tới 30 | unit + scenario `07` |
| S4 | Đèn cost 10, nạp nhiều lần, chọn gần nhất/id nhỏ, +10/đom đóm nạp, +100/đèn | scenario `01` |
| S5 | Vùng an toàn 6 m cho đèn sáng; đẩy shade ra trong ≤ 30 tick và không gây sát thương | scenario `05`, `12_safe_evict` |
| S6 | Tỏa Sáng: tốn 3, 5 m 3D, choáng 120, đẩy 4 m trong 15 tick, +5/con | scenario `04` |
| S7 | Shade: spawning→wander→chase (12/18 m)→recoil 60 tick; tối đa 1 hit/tick; lịch sinh tick 300 + k·khoảng | unit + scenario `03`, `08` |
| S8 | Bị đánh: rơi floor(n/2) ra vành 1.5–2.5 m, TTL 480, bất tử 90 | unit `test_hit_drop_ring` |
| S9 | Rơi khỏi đảo: 1 lần, −1 lửa, `lost`, chờ 60, hồi sinh, bất tử 90 | scenario `09_fall` |
| S10 | Thắng/thua xét cuối tick; `no_flames` ưu tiên; thắng cả ở tick hết giờ | unit `Night` |
| S11 | Bản đồ 3 Đêm đúng toạ độ (đèn, điểm sinh, cầu, tầng, dốc, tháp, bục) | unit `Maps`, scenario `13_night2_pad`, `14_night3_ramp_pad` |
| S12 | Pause: tick tăng, sim_tick/thời gian đứng; `paused`/`resumed` | scenario `11_pause` |
| C1 | Contract v1.1: tuning, snapshot, scenario, input, event mới | `test_headless`, `ContractFile` |
| C2 | Một Đêm 21 600 tick ≤ 30 s | scenario `08` + đo thời gian trong `verify-report` |

## 4. Tiêu chí nghiệm thu Phần 3 (tính năng mới)

| ID | Tính năng | Làm A thì thấy B | Kiểm chứng |
|---|---|---|---|
| F1 | Gió Lạc | Mây mang ≥ 5 và ≤ 15 m → `chase`; chạm ≤ 1.2 m → `drifter_steal` min(3, mang), `flee` 240 tick → `removed`; pulse lúc chase → `flee` không cướp; pulse lúc flee có đồ → `drifter_drop`, đom đóm rơi tại chỗ, biến mất sau 120 tick; không mất lửa, không bị vùng an toàn chặn; sinh ở tick 1200, 2400 (tối đa 2) | scenario `15_drifter_steal`, `16_drifter_pulse`, unit |
| F2 | Bùa Gió | Nhặt → `charm_picked {charm_ticks: 600}`; tốc độ 7.2; lướt không hồi chiêu (nhấn lại vẫn cần); xuất hiện lại sau 2700 tick | scenario `17_charm` |
| F3 | Chuỗi 3 Đêm | Menu → giới thiệu (tên đảo + lời Ông Đăng) → chơi → kết quả → Đêm kế; thắng Đêm 3 → Bình Minh + tổng điểm; thua → chơi lại Đêm | ảnh chụp từng màn + unit `Campaign` |
| F4 | Tạm dừng | Esc/P dừng logic hoàn toàn; menu Tiếp tục / Chơi lại Đêm / Cài đặt / Về menu | scenario `11_pause` + ảnh |
| F5 | Cài đặt | Âm lượng, độ nhạy chuột; lưu file JSON và đọc lại khi mở game | unit `test_settings_roundtrip` + ảnh |
| F6 | Âm thanh | Nhạc nền + 10 hiệu ứng (nhặt, thắp, tỏa sáng, bị đánh, nhảy, lướt, thắng, thua, Bóng Mực xuất hiện, đếm ngược 10 s) | `tools/gen_sounds.py` tạo file; unit kiểm tra đủ file + ánh xạ event→âm thanh |
| F7 | HUD | Lửa trên trái; mm:ss trên giữa đỏ + nhấp nháy khi ≤ 30 s; đèn k/n + điểm trên phải; 10 ô đom đóm dưới giữa; hồi chiêu Lướt/Tỏa Sáng dưới phải; "E — Nạp ánh sáng (x/10)" gần đèn; mũi tên mép màn hình tới đèn chưa sáng khi nó ở ngoài màn hình | ảnh chụp |
| F8 | Bảng màu | Các màu liệt kê dùng đúng hex (sai ≤ 10%); ánh sáng môi trường = 0.15 + 0.55 × sáng/tổng | unit `test_palette` + ảnh |
| F9 | Hiệu năng | ≥ 30 FPS trung bình ở 1280×720 | `tools/fps_probe.py` |

## 5. Đánh giá Phase 2

- **Đạt:** S1–S12, C1–C2, F1–F9 (chi tiết: [bằng chứng](../proof/phase-2/README.md)). 68 unit test + 20 scenario, tất định 2/2.
- **Phase 1 có hỏng không:** test Phase 1 còn hiệu lực vẫn đạt; test bị số chuẩn thay đã sửa/xoá theo bảng §1. Phần sáng tạo Phase 1 (vòng an toàn, la bàn, đèn tay sáng dần) giữ lại, vòng an toàn đổi thành 6 m và chỉ hiện ở đèn đã sáng cho khớp luật mới.
- **Rủi ro:** các giả định B2 (chênh cao so tâm shade), B3 (spawning 60 tick), B4 (wander tới đèn chưa sáng), B11 (xuất phát Đêm 3) có thể khác test ẩn.
- **Cần chỉnh:** `step()` dài — nếu Phase 3 thêm trạng thái đèn thì tách phần đèn ra hàm riêng.

## 6. AI sai / lỗi phát hiện trong Phase 2

| # | Lỗi | Phát hiện bằng | Xử lý |
|---|---|---|---|
| 1 | Recoil chỉ đi 59/60 bước (bước đầu rơi vào tick sau) | unit test tính tay khoảng cách 2 m | Đi bước recoil đầu ngay trong tick bị đánh |
| 2 | `Simulation` chỉ nhận đom đóm dạng dict, scenario v1.0 dùng mảng `[x,y,z]` | unit test lỗi `TypeError` | Nhận cả hai dạng |
| 3 | Cộng dồn 0.1 m làm x = 40.0000000001 → rời đảo sớm 1 tick | scenario `09_fall_respawn` lệch tick 69/70 | EPS cho mép bản đồ (`world.py`) |
| 4 | Viết test sai: nhấn lướt khi đang lướt, quên bật gió, nhấn nhảy lặp lại sau khi chạm đất, vách tầng ở r=24 không phải 26, shade bị đặt lại độ cao | chạy test, đọc lại luật | Sửa test, ghi lý do trong commit |
| 5 | Test "no_flames thắng all_lit" dựng shade cạnh đèn vừa thắp — luật mới làm shade vô hại nên test không thể đúng | đọc lại luật vùng an toàn | Dựng lại: mọi đèn đã sáng sẵn, shade xa đèn |
| 6 | Scenario cả Đêm 3 quên gió → Mây bị thổi ra khỏi vùng an toàn rồi rơi | dòng `end` ticks = 5871 thay vì 21600 | Tắt gió trong scenario đó (gió có scenario 19 riêng), thêm quy tắc vào AGENTS.md |
| 7 | Ghi `Write` client mới thất bại vì chưa đọc file | thông báo công cụ | Đọc rồi ghi lại |
| 8 | Ký tự `✕` không có trong font Arial | cảnh báo Panda3D khi chạy FPS probe | Dùng `×`; ghi vào AGENTS.md |
| 9 | Trong bảng bằng chứng đã lỡ ghi "nghe thử bằng tai" dù chưa nghe | tự rà soát trước khi commit | Sửa thành "chưa nghe kiểm tra" |
