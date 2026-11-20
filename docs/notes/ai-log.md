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

**Token ước tính Phase 2:** ~450k (đọc ticket dài, viết lại sim/client lớn). Tiết kiệm: lưu ticket vào file một lần; sinh scenario bằng một script thay vì từng file; chạy `verify.py` chỉ in dòng FAIL; chạy FPS/ảnh bằng tool thay vì mô tả bằng lời.
