# Bằng chứng Phase 1 (tag `phase-1`)

Tái lập toàn bộ: `python3 tools/verify.py` (unit test + 8 scenario, mỗi scenario chạy 2 lần để so tính tất định) → sinh lại [verify-report.md](verify-report.md) và `runs/*.jsonl`. Ảnh: `python3 tools/screenshot.py` (cần panda3d).
Yêu cầu + giả định: [docs/notes/phase-1.md](../../notes/phase-1.md).

## Truy vết yêu cầu → bằng chứng

| ID | Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|---|
| R1 | Di chuyển 3D, nhảy, camera | Unit: tốc độ 6 m/s, công thức xoay yaw, chuẩn hoá vector chéo, nhảy lên > 1 m rồi chạm đất, chặn mép đảo. CLI: yaw 90 + move [1,0] trong 60 tick → (0,0,−6) | `tests/test_sim.py::Movement`, `tests/test_headless.py::test_inputs_fields_persist`, [ảnh 02](screenshots/02_gameplay_pulse.png) | Đạt |
| R2 | Đêm 1, đảo tròn, 5 đèn | Snapshot tick 0 có 5 đèn, player (0,0,0), 3 HP, 300 s | scenario `07_default_night_start`, unit `test_default_night_layout`, [ảnh 01](screenshots/01_title.png) | Đạt |
| R3 | Nhặt đom đóm | Bán kính tính `≤`, giới hạn sức mang, event `mote_picked` | scenario `01` (5 lần nhặt), unit `Motes.*` | Đạt |
| R4 | Gửi sáng, thắp đèn | Gửi một phần rồi đủ → `lantern_lit`; ngoài tầm/không nhấn lại → không có gì | scenario `01` (deposit 5 → lit ở tick 81), unit `Lanterns.*`, [ảnh 03](screenshots/03_deposit_lantern.png) | Đạt |
| R5a | Bóng Mực đuổi, chạm mất HP | Shade đi đúng 3.5 m/s; chạm → `player_hit`, rơi `floor(carried·0.5)`, bất tử 1.5 s | scenario `03` (trúng đòn đúng tick 35 theo tính tay: ⌈2 / (3.5/60)⌉), unit `test_hit_drop_invuln` | Đạt |
| R5b | Xung sáng đẩy lùi, tốn sáng | Pulse tốn 1 đom đóm, choáng 3 s, đẩy 4 m, hồi 1 s; shade ngoài 6 m không bị | scenario `04` (S1 từ x=4 → x=8, `stunned` ở tick 10, `chase` lại ở tick 190; FAR không bị), unit `test_pulse_*`, [ảnh 02](screenshots/02_gameplay_pulse.png) | Đạt |
| R5c | Bóng Mực sợ đèn | Khoảng cách shade–đèn nhỏ nhất qua mọi snapshot ≥ 5.0 | scenario `05` (snapshot mỗi tick, 1200 tick), `07`, `08`; unit `test_safe_radius_never_entered` | Đạt |
| R6 | Thắng/thua | won `all_lit`; lost `no_flames`; lost `dawn`; mô phỏng dừng sau game over | scenario `02`, `03`, `06`, `08`; [ảnh 04](screenshots/04_win.png), [ảnh 05](screenshots/05_lose_hit.png) | Đạt |
| R7 | Điểm | Đúng bảng `score`; dựng scenario không cộng điểm; thưởng thời gian + lửa chỉ khi thắng | scenario `01` (=150), `02` (=100+99+150), `04` (=5); unit `test_win_all_lit_and_bonus` | Đạt |
| R8 | HUD + chơi lại | HUD hiển thị lửa, đom đóm, đèn, hồi xung, điểm, giờ; phím R gọi `new_game()` | ảnh 01–05; `tools/screenshot.py` gọi chính `new_game()` giữa các ảnh | Đạt (chơi tay bằng phím R sẽ quay trong video Phase 4) |
| C1 | `game.contract.json` | Test so khớp từng giá trị với `lantern/config.py` | `test_contract_matches_code` | Đạt |
| C2 | Headless: 60 tick/s, snapshot 0 trước input, event tick = k+1, dừng sớm khi kết thúc, `end` cuối, exit 0 | CLI test | `test_tick_model_and_end_line`, `test_snapshot0_is_before_input`, `test_game_over_stops_early_exit0` | Đạt |
| C3 | File hỏng → exit 2 + stderr | 6 kiểu inputs hỏng + 4 kiểu scenario hỏng | `test_malformed_files_exit_2` | Đạt |
| C4 | Tất định | Chạy 2 lần so từng byte (mọi scenario + một đêm mặc định có input) | cột "Deterministic" trong [verify-report.md](verify-report.md), `test_determinism_default_night` | Đạt |
| C5 | Chạy trên macOS/Linux | GitHub Actions trên `ubuntu-latest` và `macos-latest` | `.github/workflows/verify.yml` | Cấu hình xong; máy làm bài là Windows nên chưa tự thấy CI chạy trước khi push |

## Số đo

- Trọn đêm 18000 tick (scenario `08`, 6 Bóng Mực): **~0.6 s** wall time trên Windows 11, Python 3.11.9 (≈ 30 000 tick/s, nhanh hơn thời gian thực ~500 lần).
- Toàn bộ `tools/verify.py`: ~3 s.

## Khớp tag (clone sạch)

`git clone` sang thư mục mới → chạy `headless_cmd` lấy từ `game.contract.json` (exit 0) → `python3 tools/verify.py`: PASS; mọi `runs/*.jsonl` giống từng byte với bản đã commit, trong `verify-report.md` chỉ cột wall time thay đổi.

## Harness tự kiểm chứng

- Stop hook (`tools/hooks/stop_gate.py`): thử đổi `player_speed` 6.0 → 5.0 → hook trả **exit 2** và in test lỗi; khôi phục → **exit 0**.
- Ảnh được chụp từ client thật (offscreen) bằng `tools/screenshot.py`; nhờ xem ảnh mới phát hiện lỗi viền tam giác do `AntialiasAttrib` (đã sửa).

## Chưa đạt / giới hạn

- Chưa có video chơi tay (theo lịch nộp ở Phase 4).
- Không có âm thanh.
- Chưa kiểm tra trực tiếp trên máy macOS/Linux thật ngoài CI.
