# Nhật ký dùng AI

**Công cụ:** Claude Code (VS Code). Harness: [AGENTS.md](../../AGENTS.md), skill `verify-game`, Stop hook chặn khi test đỏ, agent `reviewer` chỉ đọc.

**Cách dùng:** tôi đọc PRD-0/Test Contract, chốt tiêu chí nghiệm thu và giả định, chọn kiến trúc (logic thuần tách khỏi render) rồi giao từng bước nhỏ cho agent; AI hỗ trợ viết khung code, test và tài liệu. Tôi đọc diff, chạy test/scenario/ảnh và quyết định sửa.

## Phase 1

| Bước | Việc giao cho AI | Kết quả / tôi kiểm tra gì |
|---|---|---|
| 1 | Đọc PRD-0 + contract, tóm tắt các con số bắt buộc | Đối chiếu lại với lab board, tự viết bảng giả định |
| 2 | Viết `sim.py` theo thứ tự xử lý tick đã chốt (A13) | Đọc lại từng bước; chạy smoke 2 lần so file |
| 3 | Viết CLI headless + validate file | Thử file hỏng → exit 2 |
| 4 | Viết test theo bảng nghiệm thu | 2 test fail → test sai (xem dưới), sửa test có lý do |
| 5 | Scenario + `verify.py` | Phát hiện mô tả scenario 07 sai thực tế |
| 6 | Client Panda3D + tool chụp ảnh | Xem ảnh, phát hiện 3 lỗi hiển thị/kịch bản |

**Token ước tính Phase 1:** ~200k token (input + output, phần lớn là đọc lại file và output test). Cách tiết kiệm: đọc đề 1 lần và ghi ra `phase-1.md` để không phải đọc lại; sửa nhỏ bằng sed thay vì ghi lại cả file; chạy `verify.py --quick` (chỉ in 1 dòng) thay vì in toàn bộ log; không dùng subagent cho việc nhỏ.

## Lỗi của AI và cách phát hiện

| # | Lỗi | Phát hiện bằng | Chỉnh harness |
|---|---|---|---|
| 1 | Test kỳ vọng `mote_picked` ở tick 41, đúng ra là 40 (hiểu sai mô hình "bước k → tick k+1") | Chạy test, tính tay lại | Ghi rõ mô hình tick trong `phase-1.md` |
| 2 | So sánh bán kính dễ sai ở biên do cộng dồn số thực | Cùng lỗi trên (khoảng cách 0.99999… / 1.00000…1) | Thêm `within()` có epsilon, quy tắc trong AGENTS.md |
| 3 | Đặt method `restart()` trong lớp con `ShowBase` → ghi đè method có sẵn, crash khi khởi tạo | Chạy tool chụp ảnh | Quy tắc mới trong AGENTS.md |
| 4 | Kịch bản ảnh đặt người chơi cách đèn 3.5 m (> 2.5 m) nên không gửi được sáng | Điểm in ra = 0 thay vì 100 | Tool in `state/score` cho mỗi ảnh |
| 5 | Ghi mô tả scenario 07 "chạy hết 18000 tick" nhưng run kết thúc ở tick 726 | Đọc dòng `end` | Đổi mô tả, thêm scenario 08 chạy trọn đêm; quy tắc trong AGENTS.md |
| 6 | Bật `AntialiasAttrib` làm lộ viền trắng mọi tam giác | Xem ảnh chụp | Quy tắc "phải xem ảnh" trong AGENTS.md |

## Phase 2

| Bước | Việc giao cho AI | Tôi kiểm tra gì |
|---|---|---|
| 1 | Chép Ticket-02 vào repo, lập bảng "giả định Phase 1 bị thay" + tiêu chí cho Phần 3 | Đối chiếu từng dòng số chuẩn |
| 2 | Viết `config.py` (số chuẩn + 3 bản đồ), `world.py`, viết lại `sim.py` theo 12 bước | Đọc diff theo thứ tự 12 bước của ticket |
| 3 | Viết lại unit test theo số chuẩn | 9 test fail lần đầu: 2 lỗi code, 7 lỗi test (xem phase-2.md §6) |
| 4 | 20 scenario với kỳ vọng tính tay | 2 fail → 1 lỗi code (EPS), 1 lỗi scenario (gió) |
| 5 | Âm thanh tự tổng hợp, settings, campaign, client mới | Xem ảnh chụp từng màn, đo FPS |

## Phase 4

| Bước | Việc giao cho AI | Tôi kiểm tra gì |
|---|---|---|
| 1 | Lưu Ticket-04, bảng giả định E1–E17 + tiêu chí Q1–Q12 | Đối chiếu từng số đo/định nghĩa của ticket |
| 2 | Module thuần: `bench_scene` (công thức avg/1% low/p95), `soak`, `leaderboard`, `sysinfo` | Test tính tay công thức; chạy soak thật |
| 3 | Bench trong client | Bench đầu 77 FPS → cProfile → giảm draw call, cache màu → 117 FPS; kiểm tra output headless giống từng byte |
| 4 | Đổi phím, phụ đề, giảm chuyển động, chữ lớn, bảng xếp hạng | Xem ảnh: phát hiện mũi tên lệch (`setR`, lỗi từ Phase 2), màu tím vô hình, phụ đề lặp/sót |
| 5 | Đóng gói `build_apps`, video demo dựng offscreen | Bản build tải chậm → đổi nguồn wheel; xem video |

**Token ước tính Phase 4:** ~450k. Tiết kiệm: profile trước khi tối ưu (không đoán); dựng video bằng script thay vì nhiều vòng thử tay.

**Lỗi AI ghi nhận ở Phase 4**

| # | Lỗi | Phát hiện bằng | Xử lý |
|---|---|---|---|
| 1 | Mũi tên ngoài màn hình dùng `NodePath.setR` → quay quanh tâm màn hình, nằm sai chỗ từ Phase 2 | Debug vị trí node rồi dò pixel trong ảnh | `setRoll(-deg)`; quy tắc AGENTS.md |
| 2 | Mũi tên Bóng Mực màu tím gần như vô hình trên nền đêm | Ảnh chụp | Dùng màu cảnh báo |
| 3 | Phụ đề lặp khi 2 Bóng Mực sinh cùng tick; phụ đề Đêm trước sót sang Đêm sau | Ảnh chụp | Gộp phụ đề trùng; xoá khi tải Đêm |
| 4 | `buttonThrowers` là `None` ở cửa sổ offscreen → tool chụp ảnh crash | Traceback | Kiểm tra trước khi dùng |
| 5 | cProfile không ghi kết quả vì `userExit` gọi `sys.exit` | Không có file profile | Bắt `SystemExit` trong script profile |
| 6 | `platform.release()` báo "10" trên Windows 11 | Đọc `bench.json` | Dùng số build |
| 7 | `build_apps` treo 30 phút khi tải wheel tối ưu từ buildbot | Log không đổi | `use_optimized_wheels: False` |

## Phase 3

| Bước | Việc giao cho AI | Tôi kiểm tra gì |
|---|---|---|
| 1 | Lưu Ticket-03, viết ADR + bảng tác động **trước** khi code | Đối chiếu từng mục [THAY THẾ] với test cũ |
| 2 | Vá `config.py`/`sim.py` bằng script có `assert` từng đoạn thay | Xem diff; test cũ fail đúng 4 cái dự kiến |
| 3 | Test Fuel/Drain + scenario 21–26 với kỳ vọng tính tay | 1 kỳ vọng sai (quên phần hút) |
| 4 | Client: thanh dầu, mù màu, camera | Xem ảnh: phát hiện 3 lỗi hiển thị |

**Token ước tính Phase 3:** ~250k. Tiết kiệm: vá file bằng script có `assert` thay vì ghi lại cả file lớn; chỉ in dòng FAIL.

**Token ước tính Phase 2:** ~450k (đọc ticket dài, viết lại sim/client lớn). Tiết kiệm: lưu ticket vào file một lần; sinh scenario bằng một script thay vì từng file; chạy `verify.py` chỉ in dòng FAIL; chạy FPS/ảnh bằng tool thay vì mô tả bằng lời.
