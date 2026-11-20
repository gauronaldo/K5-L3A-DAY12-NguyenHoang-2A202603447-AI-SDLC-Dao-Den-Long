# Phase 4 — Ticket-04 "Bình minh: phát hành v1.0.0" (Contract v1.3)

Đề gốc: [ticket-04](../lab/tickets/ticket-04.md).

## 1. Giả định

| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| E1 | "Rải đều trên đảo (seed 42)" | Vị trí ngẫu nhiên đều theo diện tích trong bán kính 38 m (`r = 38·√u`), tránh tâm 3 m và tránh vùng 6 m quanh đèn sáng; 100 đom đóm cũng rải đều như vậy |
| E2 | "Luật wander bình thường" | Bóng Mực ở `wander` đi 2 m/s tới đèn tắt gần nhất (L4/L5) như Phase 2–3; trong bench tắt chuyển sang `chase` (Mây đứng yên, không có sát thương) để mọi con giữ trạng thái wander như đề yêu cầu |
| E3 | Góc camera | Góc tính từ +X, ngược chiều kim đồng hồ nhìn từ trên (cùng quy ước Ticket-02): vị trí (30·cos θ, 15, 30·sin θ), θ = 2π·t/15 với t tính từ khung đầu tiên của cảnh |
| E4 | `load_ms` | Từ thời điểm hệ điều hành tạo tiến trình (Windows `GetProcessTimes`, Linux `/proc/self/stat`; macOS: lúc Python bắt đầu chạy `main.py`) tới khung đầu tiên của cảnh bench |
| E5 | `frame_ms_p95` | Phân vị 95 theo nearest-rank trên dt (ms) |
| E6 | `peak_mem_mb` | RSS lấy mẫu mỗi khung trong 30 s đo (Windows `GetProcessMemoryInfo`, Linux `/proc/self/statm`, macOS `ps`) |
| E7 | Sáng tạo trong bench | Tắt la bàn, vòng an toàn, lá gió, chớp màn hình; giữ ánh sáng/hiệu ứng chuẩn của game |
| E8 | Soak "Đêm thứ i dùng seed 7 + i" | i đếm từ 1 → seed 8…17; Đêm thứ i là Đêm ((i−1) mod 3) + 1 |
| E9 | Soak input | Một `random.Random(seed)` riêng cho input mỗi Đêm; nút được nhấn = true ở tick đó (cạnh lên khi tick trước false) |
| E10 | `mem_end_mb` "sau khi reset xong Đêm cuối" | Sau khi Đêm 10 kết thúc, huỷ Simulation và chạy `gc.collect()` rồi đo |
| E11 | Tên bảng xếp hạng | Chấp nhận 3–12 ký tự chữ (kể cả tiếng Việt có dấu), số, `_`; khoảng trắng hai đầu bị cắt |
| E12 | "Ai đạt trước đứng trên" | So `achieved_at`; nếu trùng thì theo thứ tự thêm vào |
| E13 | Điểm lưu khi thua | `score` = tổng điểm các Đêm đã thắng trước đó (có thể 0), `nights_won` tương ứng |
| E14 | Phím Esc | Esc luôn mở tạm dừng/quay lại (không đổi được) để không bị kẹt; phím Tạm dừng đổi được (mặc định P) |
| E15 | "Rung camera" | Game có rung camera 0.3 s khi bị đánh; "Giảm chuyển động" tắt rung + chớp màn hình |
| E16 | 18 px | Chữ dùng scale ≥ 0.05 trong aspect2d (720 px / 2 = 360 px mỗi đơn vị → ≥ 18 px); chữ lớn nhân 1.25 |
| E17 | Bản phát hành | `build_apps` của Panda3D tạo file thực thi Windows / Linux / macOS; kèm `.zip` mã nguồn chạy bằng 3 lệnh |

## 2. Tiêu chí nghiệm thu

| ID | Tiêu chí | Kiểm chứng |
|---|---|---|
| Q1 | `bench_cmd --seed 42 --duration 30 --out bench.json` mở 1280×720, vsync off, cảnh đúng (200 shade wander, 100 mote, L1–L3 fuel 100), camera bay vòng, khởi động 3 s, đo đúng 30 s, thoát 0, JSON đúng trường + công thức | `tests/test_bench.py` (công thức số liệu, dựng cảnh, quỹ đạo camera), `docs/proof/phase-4/bench.json` |
| Q2 | Ngưỡng tham khảo trên máy mình: avg ≥ 60, p1 low ≥ 30, load ≤ 10 s | `bench.json` |
| Q3 | `soak_cmd --seed 7 --nights 10 --out soak.json`: 10 Đêm 1→2→3 xoay vòng, input theo xác suất, crashes 0, mem_end ≤ 1.2·mem_start | `soak.json`, `tests/test_soak.py` (chạy rút gọn) |
| Q4 | Bảng xếp hạng: tên hợp lệ, top 10, sắp xếp, lưu đĩa, export đúng thứ tự, màn hình từ menu, nhập tên sau Bình Minh / thua | `tests/test_leaderboard.py`, export thật, ảnh |
| Q5 | Đổi phím 9 hành động, báo trùng, khôi phục mặc định, lưu | `test_app.Keybinds`, ảnh |
| Q6 | Phụ đề/chỉ báo: Bóng Mực xuất hiện (+ mũi tên mép), gió, 10 s cuối, fuel < 30 | ảnh |
| Q7 | Giảm chuyển động tắt rung + chớp | code + ảnh cài đặt |
| Q8 | Cỡ chữ ≥ 18 px; chữ lớn ×1.25 | `test_app.TextSize` (quét scale trong code), ảnh |
| Q9 | README đủ mục; CHANGELOG 4 phase; CREDITS; LICENSE; clone sạch 3 lệnh | kiểm tra clone sạch |
| Q10 | Contract v1.3 (`bench_cmd`, `soak_cmd`); v1.0–v1.2 giữ nguyên | `ContractFile`, toàn bộ scenario cũ |
| Q11 | Release v1.0.0 có bản chạy được; tag phase-4 | trang Release |
| Q12 | Retro 1–2 trang; video < 5 phút | `docs/notes/retro.md`, `docs/demo/` |

## 3. Đánh giá Phase 4

- **Đạt:** Q1–Q12 ([bằng chứng](../proof/phase-4/README.md)). 99 unit test + 25 scenario; bench 103 FPS / 1% low 68.8 / load 2.1 s; soak 0 crash, RSS +0.7 MB.
- **Phase trước có hỏng không:** không — mọi `runs/*.jsonl` Phase 3 giống từng byte sau khi thêm chế độ bench và tối ưu; scenario 01–26 vẫn đạt.
- **Sửa lỗi cũ:** mũi tên ngoài màn hình (lỗi từ Phase 2) được phát hiện nhờ ảnh chụp Phase 4.
- **Rủi ro:** số bench phụ thuộc máy (lần đo khi GPU bị chia sẻ nặng từng tụt 1% low xuống 14); bản macOS/Linux chỉ kiểm bằng workflow `release-smoke`; video là autopilot.
