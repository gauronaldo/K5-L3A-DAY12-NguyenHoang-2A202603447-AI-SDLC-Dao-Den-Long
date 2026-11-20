# Bằng chứng Phase 3 (tag `phase-3`, contract v1.2)

Cách tái lập:
- `python3 tools/verify.py --phase phase-3`: chạy 86 unit test và 25 scenario, mỗi scenario chạy 2 lần để so tính tất định. Kết quả ghi vào [verify-report.md](verify-report.md).
- `python3 tools/screenshot.py --phase phase-3`: chụp ảnh màn hình.
- [fps.jsonl](fps.jsonl): kết quả đo FPS.

Tài liệu liên quan:
- Thiết kế: [ADR 0001](../../adr/0001-lantern-fuel-and-dawn-win.md)
- Phân tích tác động và giả định: [phase-3.md](../../notes/phase-3.md)
- Đề gốc: [ticket-03](../../lab/tickets/ticket-03.md)

Máy đo: Windows 11, AMD Ryzen 5 7500F, RTX 4060, RAM 32 GB.

| ID | Tiêu chí | Bằng chứng | Kết quả |
|---|---|---|---|
| P1 | Thắp đèn thì dầu đầy 100, hao 1/s. Hết dầu thì phát `lantern_out`, deposited về 0, `ever_lit` = true | `22_fuel_out_relight` (tắt đúng tick 60), `Fuel.test_decay_and_out` | Đạt |
| P2 | Châm dầu: used = min(mang, ceil((100−fuel)/10)), dầu tối đa 100, +5 mỗi đom đóm, đèn đầy không được chọn | `23_refuel` (dầu 84.0), `test_refuel_formula`, `test_refuel_caps_at_100`, `test_full_lantern_not_selected` | Đạt |
| P3 | Thắp lại cần 5, phát `relight: true`, +40, tăng `relit_count` | `22` (điểm 65, dầu 99.7 ở tick 90), `test_relight_costs_5_scores_40` | Đạt |
| P4 | Dầu < 30 thì mất vùng an toàn, dầu đúng 30 vẫn còn. Bóng Mực wander nhắm đèn yếu; trong 2 m thì chuyển `drain`, hút 5/s, nhiều con cộng dồn; `fuel_drain` mỗi 60 tick | `24_drain` (vào drain ở tick 180, `fuel_drain` 11.0 ở tick 240, đèn tắt ở tick 350, đều khớp tính tay), `Drain.*`, `test_low_fuel_loses_zone_exact_30_keeps_it` | Đạt |
| P5 | Từ drain: Mây trong 6 m thì sang chase, trúng Tỏa Sáng thì sang stunned (+15), đèn tắt hoặc được châm ≥ 30 thì về wander. Châm lên ≥ 30 thì Bóng Mực bị đẩy ra trong ≤ 30 tick | `25_drain_refuel_evict`, `test_drain_to_*`, `test_pulse_draining_scores_15`, `test_refuel_above_30_evicts` | Đạt |
| P6 | Thời lượng 240/270/300 s; không thắng sớm; thắng `dawn_survived` khi số đèn sáng ≥ ceil(0.6n); hết lửa (`no_flames`) luôn được xét trước | `02_dawn_survived`, `21_dawn_below_threshold`, `08`/`20` (hết Đêm ở tick 14400 / 18000), `test_no_early_win`, `test_thresholds_per_night` (3/4/5), `test_no_flames_beats_all_lit_and_dawn` | Đạt |
| P7 | Điểm bình minh: mỗi đèn sáng 50 + floor(fuel), mỗi lửa 50, không còn thưởng thời gian | `02` (474), `test_dawn_survived_threshold_and_bonus`; ảnh [15](screenshots/15_result_dawn_survived.png) (567, khớp tính tay) | Đạt |
| P8 | Sức chứa = 10 + 2 × số lần thắp, tối đa 20; snapshot có `capacity` | `26_capacity` (nhặt 12 con, còn lại 1), `test_capacity_grows` | Đạt |
| P9 | Contract v1.2: các khoá tuning mới, fuel làm tròn 1 chữ số, đèn tắt có fuel 0, sự kiện mới | `test_snapshot_schema_v1_2`, `ContractFile.test_contract_matches_code` | Đạt |
| P10 | Chế độ mù màu được lưu: viền và mắt Bóng Mực #00B3FF, cảnh báo màu trắng kèm ⚠, đèn tắt xẹp 20% và có vết rách | ảnh [13](screenshots/13_colorblind.png) so với ảnh thường [12](screenshots/12_fuel_bars_drain.png), [14](screenshots/14_settings_colorblind.png); `test_colorblind_persisted` | Đạt |
| P11 | Thanh dầu trên đèn đang sáng; dầu < 30 thì đèn và thanh nhấp nháy 1 Hz | ảnh [12](screenshots/12_fuel_bars_drain.png) chụp lúc L1 đang ở nhịp tắt (mờ), [13](screenshots/13_colorblind.png) | Đạt (chỉ chứng minh bằng ảnh tĩnh; nhịp 1 Hz xác nhận qua code `int(now*2) % 2`) |
| R | Không hỏng test Phase 1–2 còn hiệu lực | Toàn bộ scenario 03–19 vẫn đạt mà không phải sửa; các test bị luật mới thay thế đã được xử lý theo bảng §1 | Đạt |

Hiệu năng sau khi thêm thanh dầu và camera 70°: khoảng 270–280 FPS trung bình ([fps.jsonl](fps.jsonl)).
