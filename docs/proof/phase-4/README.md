# Bằng chứng Phase 4 (tag `phase-4`, Release `v1.0.0`, contract v1.3)

Cách tái lập:

| Lệnh | Tạo ra |
|---|---|
| `python3 tools/verify.py --phase phase-4` | 99 unit test và 25 scenario → [verify-report.md](verify-report.md) |
| `python3 main.py --bench --seed 42 --duration 30 --out bench.json` | [bench.json](bench.json) |
| `python3 soak.py --seed 7 --nights 10 --out soak.json` | [soak.json](soak.json) |
| `python3 tools/screenshot.py --phase phase-4` | `screenshots/` |
| `python setup.py build_apps && python3 tools/package_release.py` | `dist/*.zip` (đính kèm vào Release) |

Đề gốc: [ticket-04](../../lab/tickets/ticket-04.md). Giả định và tiêu chí nghiệm thu: [phase-4.md](../../notes/phase-4.md).

Máy đo: Windows 11 (build 26200), AMD Ryzen 5 7500F, NVIDIA RTX 4060 (driver 580.88), RAM 32 GB, Python 3.11.9, Panda3D 1.10.14.

## Truy vết

| ID | Tiêu chí | Bằng chứng | Kết quả |
|---|---|---|---|
| Q1 | Bench: 1280×720, vsync tắt, 200 Bóng Mực ở wander, 100 đom đóm, L1–L3 đầy dầu, camera bay vòng r = 30 / y = 15 / 15 s, khởi động 3 s, đo 30 s, exit 0, JSON đúng các trường và công thức | `test_phase4.BenchStats` (công thức tính tay), `BenchScene` (nội dung cảnh, luật bị đóng băng, quỹ đạo camera), [bench.json](bench.json) (`frames` 3091 trong 30 s) | Đạt |
| Q2 | Ngưỡng (tham khảo trên máy mình): avg ≥ 60, 1% low ≥ 30, load ≤ 10 000 ms | [bench.json](bench.json): **103.0 / 68.8 / 2080 ms**, RSS đỉnh 157 MB | Đạt. Lần đo này máy đang chạy song song một game 3D khác (xem lịch sử đo bên dưới) |
| Q3 | Soak 10 Đêm (1→2→3 xoay vòng, seed 8…17), không crash, mem_end ≤ 1.2 × mem_start | [soak.json](soak.json): 0 crash, 25.3 → 26.0 MB; `test_phase4.Soak` (xác suất input 5/3/2/10 %, đổi hướng mỗi 30 tick) | Đạt |
| Q4 | Bảng xếp hạng: tên hợp lệ (hỗ trợ cả tiếng Việt có dấu), top 10, sắp theo điểm giảm dần (bằng điểm thì ai đạt trước đứng trên), lưu ra đĩa, export đúng thứ tự, có màn hình riêng, nhập tên sau Bình Minh hoặc khi thua | `test_phase4.LeaderboardTest`; ảnh [17 nhập tên](screenshots/17_name_entry.png), [18 bảng](screenshots/18_leaderboard.png) | Đạt |
| Q5 | Đổi phím cho 9 hành động, báo phím trùng, khôi phục mặc định, có lưu | `test_phase4.Keybinds`; ảnh [19](screenshots/19_keys_conflict.png) (báo trùng phím `e`) | Đạt |
| Q6 | Phụ đề và mũi tên ở mép màn hình khi Bóng Mực xuất hiện; báo gió, 10 s cuối, đèn dưới 30 dầu | ảnh [16](screenshots/16_subtitle_spawn_arrow.png) (phụ đề và mũi tên đỏ chỉ về Bóng Mực mới sinh), [13 Phase 3](../phase-3/screenshots/13_colorblind.png) (cảnh báo dầu); code `subtitle(...)` | Đạt (phụ đề 10 s cuối và gió chỉ kiểm qua code, chưa chụp ảnh) |
| Q7 | Giảm chuyển động: tắt rung camera và chớp màn hình | ảnh [20](screenshots/20_settings_accessibility.png); trong code, `player_hit` chỉ đặt `flash` và `shake` khi tắt chế độ này | Đạt (kiểm qua code và ảnh cài đặt) |
| Q8 | Chữ UI ≥ 18 px ở 720p; tùy chọn chữ lớn ×1.25 | `test_phase4.TextSize` (quét mọi `scale=` trong client, không có giá trị < 0.05); ảnh [21](screenshots/21_large_text_hud.png) | Đạt |
| Q9 | README đủ mục; CHANGELOG có 4 phase; có CREDITS và LICENSE; clone sạch rồi chạy được trong 3 lệnh | [README](../../../README.md), [CHANGELOG](../../../CHANGELOG.md); CI chạy trên Ubuntu và macOS | Đạt |
| Q10 | Contract v1.3 có `bench_cmd` và `soak_cmd`; luật v1.0–v1.2 giữ nguyên | `ContractFile.test_contract_matches_code`; 25 scenario Phase 1–3 vẫn đạt; mọi `runs/*.jsonl` Phase 3 giống từng byte sau khi tối ưu hiệu năng | Đạt |
| Q11 | Release v1.0.0 có bản chạy được | 3 file zip (Windows / Linux / macOS) tạo bằng `build_apps`. Bản Windows: đã chạy thử trên máy này, output headless giống từng byte với bản chạy từ mã nguồn, exit 2 với `--night 9`, soak đạt, game 200 FPS. Bản Linux và macOS: workflow [release-smoke](../../../.github/workflows/release-smoke.yml) chạy chính các file zip trên runner thật | Đạt (xem kết quả workflow ở tab Actions) |
| Q12 | Retro 1–2 trang; video demo dưới 5 phút | [retro.md](../../notes/retro.md); [demo.mp4](../../demo/demo.mp4) dài 2:33 | Đạt. Video được render từ client thật nhưng do autopilot chơi, không phải quay người chơi trực tiếp |

## Lịch sử đo bench (cùng code và cùng lệnh, chỉ khác tải nền của máy)

| Lần | Tình trạng máy | avg_fps | p1_low_fps | p95 (ms) | Ghi chú |
|---|---|---|---|---|---|
| 1 | rảnh, code chưa tối ưu | 76.9 | 58.8 | 15.1 | 5 s, trước khi giảm số draw call |
| 2 | rảnh | 117.6 | 77.1 | 10.7 | 30 s; file bị ghi đè ở lần sau, số lấy từ log console |
| 3 | VALORANT đang chạy | 62.9 | 14.1 | 24.2 | 30 s: lần này **không đạt** ngưỡng 1% low |
| 4–5 | VALORANT đang chạy | 72.4 / 72.0 | 45.2 / 41.3 | ~16.5 | 15 s, đo lặp để xem độ dao động |
| 6 (**bench.json**) | VALORANT đang chạy | **103.0** | **68.8** | 12.0 | 30 s, bản commit |

Kết luận: số đo trên máy cá nhân dao động mạnh theo tải nền. Lần 3 cho thấy nếu GPU bị chia sẻ nặng thì chỉ số 1% low có thể tụt dưới 30. Số chính thức sẽ đo trên máy chấm của giảng viên.

## Giới hạn

- Video demo là autopilot render offscreen, nên không có âm thanh và không phải cảnh người chơi trực tiếp. Nên quay thêm một đoạn chơi tay nếu cần.
- Bản macOS là x86_64 (trên Apple Silicon chạy qua Rosetta 2) và chưa ký số, nên lần đầu mở cần chuột phải chọn Open.
- Âm thanh chưa được nghe kiểm tra thủ công (giống Phase 2).
