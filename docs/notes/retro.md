# Đánh giá & Retro

## Phase 1 — đánh giá

- **Đạt:** toàn bộ R1–R8 và C1–C4 (xem [bảng bằng chứng](../proof/phase-1/README.md)). 31 unit test + 8 scenario đạt, tất định 2/2 lần.
- **Hỏng phase trước:** không áp dụng (phase đầu).
- **Chưa đạt / rủi ro:** chưa có video chơi tay; CI macOS/Linux mới cấu hình, chưa thấy kết quả trước khi push; một số giả định (A1 pulse tốn đom đóm, A3 safe_radius cho mọi đèn, A7 thưởng chỉ khi thắng) có thể bị ticket sau thay đổi — các số đều ở `config.py` + `game.contract.json` nên đổi nhanh.
- **Cần chỉnh:** giữ thứ tự xử lý tick (A13) trong một chỗ duy nhất để phase sau dễ đổi luật; scenario mới nên viết trước khi code.
- **Harness:** AGENTS.md thêm 3 quy tắc từ lỗi thật; Stop hook đã thử chặn được khi test đỏ.

## Phase 2 — đánh giá

- **Đạt:** toàn bộ số chuẩn, 3 bản đồ, contract v1.1, 9 tính năng Phần 3 ([bằng chứng](../proof/phase-2/README.md)); FPS ~500 ở 1280×720.
- **Hỏng phase trước:** không; test Phase 1 bị số chuẩn thay đã sửa/xoá có lý do.
- **Chưa đạt / rủi ro:** âm thanh chưa nghe kiểm tra; giả định B2/B3/B4/B11 có thể khác test ẩn.
- **Harness:** AGENTS.md thêm quy tắc đếm tick, EPS, "kỳ vọng phải tính tay", nhớ cơ chế nền; skill thêm `why`, check mới, FPS.

## Phase 3 — đánh giá

- **Đạt:** P1–P11 ([bằng chứng](../proof/phase-3/README.md)); ADR 0001; CHANGELOG có mục Breaking changes.
- **Hỏng phase trước:** không; 3 test xoá + 6 test sửa đều có lý do trong [phase-3.md §1](phase-3.md).
- **Bài học:** lập bảng tác động trước khi code giúp test cũ fail đúng như dự đoán, không bất ngờ.

## Retro toàn dự án

Sẽ hoàn thiện ở Phase 4 (số liệu token, bài học, nếu làm lại thì đổi gì).

Ghi chú sớm:
- Tách `sim.py` thuần + headless ngay từ đầu giúp mọi kiểm chứng chạy < 3 s, không cần GPU.
- Tool chụp ảnh offscreen biến phần "chỉ nhìn mới thấy" thành bằng chứng tái lập được.
