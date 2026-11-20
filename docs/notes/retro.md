# Đánh giá & Retro

## Phase 1 — đánh giá

- **Đạt:** toàn bộ R1–R8 và C1–C4 (xem [bảng bằng chứng](../proof/phase-1/README.md)). 31 unit test + 8 scenario đạt, tất định 2/2 lần.
- **Hỏng phase trước:** không áp dụng (phase đầu).
- **Chưa đạt / rủi ro:** chưa có video chơi tay; CI macOS/Linux mới cấu hình, chưa thấy kết quả trước khi push; một số giả định (A1 pulse tốn đom đóm, A3 safe_radius cho mọi đèn, A7 thưởng chỉ khi thắng) có thể bị ticket sau thay đổi — các số đều ở `config.py` + `game.contract.json` nên đổi nhanh.
- **Cần chỉnh:** giữ thứ tự xử lý tick (A13) trong một chỗ duy nhất để phase sau dễ đổi luật; scenario mới nên viết trước khi code.
- **Harness:** AGENTS.md thêm 3 quy tắc từ lỗi thật; Stop hook đã thử chặn được khi test đỏ.

## Retro toàn dự án

Sẽ hoàn thiện ở Phase 4 (số liệu token, bài học, nếu làm lại thì đổi gì).

Ghi chú sớm:
- Tách `sim.py` thuần + headless ngay từ đầu giúp mọi kiểm chứng chạy < 3 s, không cần GPU.
- Tool chụp ảnh offscreen biến phần "chỉ nhìn mới thấy" thành bằng chứng tái lập được.
