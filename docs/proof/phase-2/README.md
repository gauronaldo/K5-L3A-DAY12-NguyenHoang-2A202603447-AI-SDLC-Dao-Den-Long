# Bằng chứng Phase 2 (tag `phase-2`, contract v1.1)

Tái lập:
- `python3 tools/verify.py --phase phase-2`: 68 unit test và 20 scenario, mỗi scenario chạy 2 lần để so tất định. Kết quả ghi vào [verify-report.md](verify-report.md) và `runs/`.
- `python3 tools/screenshot.py --phase phase-2`: chụp `screenshots/`.
- `python3 main.py --fps-probe 10 --night N`: đo FPS, kết quả lưu ở [fps.jsonl](fps.jsonl).

Yêu cầu và giả định: [docs/notes/phase-2.md](../../notes/phase-2.md). Đề gốc: [ticket-02](../../lab/tickets/ticket-02.md).

Máy đo: Windows 11, AMD Ryzen 5 7500F, NVIDIA RTX 4060, RAM 32 GB, Python 3.11.9, Panda3D 1.10.14.

## Phần 1, 2, 4: số chuẩn, bản đồ, contract

| ID | Tiêu chí | Bằng chứng | Kết quả |
|---|---|---|---|
| S1 | Chạy 6 m/s, dừng ≤ 0.1 s, nhảy 7 m/s / g 20 chỉ khi chạm đất | `test_sim.Movement` (speed, stops, jump) | Đạt |
| S2 | Lướt 14 m/s × 12 tick, hồi chiêu 90 tick tính từ lúc bắt đầu lướt, trên không giữ độ cao | scenario `10_dash`, `test_dash_*` | Đạt |
| S3 | Nhặt khi XZ ≤ 1 và chênh cao ≤ 1.5; 20 đom đóm ở điểm chuẩn; +1 ở tick 240 | `07_default_night1`, `test_pickup_xz_and_height`, `test_default_twenty…` | Đạt |
| S4 | Cost 10, nạp nhiều lần, chọn đèn gần nhất (bằng nhau thì id nhỏ), +10 mỗi đom đóm nạp, +100 mỗi đèn | `01_pickup_deposit_light` (điểm 200), `test_choose_nearest_then_lower_id` | Đạt |
| S5 | Vùng 6 m quanh đèn **đã sáng**; Bóng Mực bị đẩy ra trong ≤ 30 tick và không gây sát thương | `05_safe_radius` (snapshot mỗi tick), `12_safe_evict`, `SafeZone.*` | Đạt |
| S6 | Tỏa Sáng: tốn 3, bán kính 5 m tính 3D, choáng 120 tick, đẩy 4 m trong 15 tick, +5 mỗi con (kể cả trúng lại) | `04_pulse_stun_push`, `Pulse.*` | Đạt |
| S7 | Trạng thái spawning → wander → chase (12/18 m) → recoil; tối đa 1 hit mỗi tick, id nhỏ trước; lịch sinh 300 + 480k | `03`, `07`, `08`, `test_spawn_schedule_night1`, `test_one_hit_per_tick_lowest_id` | Đạt |
| S8 | Bị đánh: rơi floor(n/2) đom đóm ra vành 1.5–2.5 m, TTL đúng 480 tick, bất tử 90 tick, recoil 2 m trong 60 tick | `test_hit_drop_ring_invuln_recoil` | Đạt |
| S9 | Rơi khỏi đảo: 1 lần, có trường `lost`, chờ 60 tick, hồi sinh có bất tử; hết lửa thì thua ngay | `09_fall_respawn` (rơi ở tick 70, hồi sinh tick 130, khớp tính tay), `test_fall_*` | Đạt |
| S10 | Xét thắng/thua cuối tick; `no_flames` được ưu tiên; thắng cả ở đúng tick hết giờ; thưởng ×2 giây | `02_win_all_lit` (458), `06_dawn`, `Night.*` | Đạt |
| S11 | Bản đồ 3 Đêm: đèn, điểm sinh, cầu, bục Đêm 2 (bay ~1.4 s, đáp ở đảo B), dốc / vách / tháp / bục Đêm 3, gió 30 s / 5 s / 2 m/s | `13`, `14`, `15`, `19`, `Maps.*`; ảnh [05](screenshots/05_night2_pad_drifter_charm.png), [06](screenshots/06_night3_tiers_wind.png) | Đạt |
| S12 | Pause: tick tăng nhưng sim_tick và logic đứng yên; event `paused` / `resumed`; state `paused` | `11_pause`, `test_pause_freezes_logic`, `test_pause_input` | Đạt |
| C1 | Contract v1.1: `--night 1..3`, đủ trường snapshot / scenario / input / event mới, tên trạng thái shade | `test_headless.*` (`test_snapshot_schema_v1_1`, `test_bad_night_exit_2`…), `ContractFile` | Đạt |
| C2 | Một Đêm 21 600 tick chạy ≤ 30 s | `08_full_night1_dawn`, `20_full_night3_dawn` (kiểm tra `max_wall_s` trong report: khoảng 1–1.6 s), `test_full_night_under_30s` | Đạt |
| R | Regression Phase 1 theo số chuẩn | Test Phase 1 vẫn còn hiệu lực đều chạy lại; test bị luật mới thay đã sửa hoặc xoá kèm lý do ([phase-2.md §1](../../notes/phase-2.md)) | Đạt |

## Phần 3: tính năng mới

| ID | Tính năng | Bằng chứng | Kết quả |
|---|---|---|---|
| F1 | Gió Lạc | `16_drifter_steal` (cướp ở tick 33, bị removed ở tick 273), `17_drifter_pulse`, `Drifters.*` (không bị vùng an toàn chặn, bất tử không ngăn bị cướp, lịch sinh tick 1200) | Đạt |
| F2 | Bùa Gió | `18_charm` (z = 7.18 khớp tính tay, lướt không hồi chiêu, xuất hiện lại ở tick 2701), `Charm.*` | Đạt |
| F3 | Chuỗi 3 Đêm | `test_app.CampaignTest`; ảnh [01 menu](screenshots/01_menu.png), [02 giới thiệu + lời Ông Đăng](screenshots/02_intro_night1.png), [10 kết quả](screenshots/10_result_lost.png), [11 Bình Minh](screenshots/11_dawn.png) | Đạt |
| F4 | Tạm dừng (Esc/P) có menu 4 nút | ảnh [08](screenshots/08_pause_menu.png); client ngừng gọi `sim.step()` khi ở chế độ `paused` | Đạt |
| F5 | Cài đặt âm lượng và độ nhạy chuột, lưu giữa các lần mở | `test_app.SettingsTest` (đọc/ghi + chặn giá trị), ảnh [09](screenshots/09_settings.png) | Đạt |
| F6 | Nhạc nền và 10 hiệu ứng âm thanh | `test_app.AudioAssets` (đủ file WAV hợp lệ, client có ánh xạ) | Đạt một phần: đã kiểm tra đủ file và ánh xạ sự kiện; **chưa nghe kiểm tra** chất lượng âm |
| F7 | HUD đầy đủ | ảnh [03](screenshots/03_night1_pulse_hud.png) (lửa, giờ, đèn/điểm, 10 ô đom đóm, hồi chiêu), [04](screenshots/04_lantern_prompt.png) (nhắc "E — Nạp ánh sáng"), [05](screenshots/05_night2_pad_drifter_charm.png) / [07](screenshots/07_offscreen_arrow.png) (mũi tên ở mép màn hình), [06](screenshots/06_night3_tiers_wind.png) (cảnh báo gió) | Đạt. Giờ đỏ và nhấp nháy khi ≤ 30 s: có code, chưa chụp ảnh |
| F8 | Bảng màu và ánh sáng môi trường | `test_palette_and_ambient`, `test_app.Palette` | Đạt với vật tự phát sáng (đèn, đom đóm, viền). Vật chịu chiếu sáng dùng đúng màu gốc, nhưng màu hiển thị thay đổi theo ánh sáng đêm |
| F9 | ≥ 30 FPS ở 1280×720 | [fps.jsonl](fps.jsonl): khoảng 480–540 FPS trung bình, p95 < 3.1 ms trên cả 3 Đêm (autopilot, tắt vsync) | Đạt (trên máy đo ở trên) |

## Chưa đạt / giới hạn

- Chưa quay video chơi tay; video sẽ làm ở Phase 4.
- Âm thanh mới kiểm tra tồn tại file và ánh xạ sự kiện, chưa nghe kiểm tra thủ công.
- Màu của vật chịu chiếu sáng không thể giữ đúng hex trong khung hình vì ánh sáng đêm thay đổi.
