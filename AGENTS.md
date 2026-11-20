# AGENTS.md — Đảo Đèn Lồng

Game 3D (Panda3D) 3 Đêm + headless theo Test Contract **v1.1**. Python 3.10+.

## Lệnh
- Test nhanh: `python3 tools/verify.py --quick` (unit test, không cần panda3d)
- Kiểm chứng đầy đủ + bằng chứng: `python3 tools/verify.py --phase phase-N` → `docs/proof/phase-N/`
- Headless: `python3 headless.py --seed 1 --night {1,2,3} --ticks 600 --out out.jsonl [--scenario f] [--inputs f]`
- Game: `python3 main.py` · FPS: `python3 main.py --fps-probe 10 --night 3` · Ảnh: `python3 tools/screenshot.py --phase phase-N`
- Âm thanh sinh lại: `python3 tools/gen_sounds.py`

## Cấu trúc
- `lantern/sim.py` logic thuần (KHÔNG import panda3d). `step()` đi đúng **12 bước** của Ticket-02 — giữ comment đánh số.
- `lantern/config.py` số chuẩn + 3 bản đồ + bảng màu. `lantern/world.py` mặt đất/vật cản theo Đêm.
- `lantern/files.py` đọc/kiểm tra inputs & scenario (lỗi → exit 2). `lantern/headless.py` CLI.
- `lantern/client.py` render + HUD + menu, chỉ đọc state sim. `campaign.py`, `settings.py` thuần Python.
- `scenarios/<NN_name>/` = scenario + inputs + expect (có `why` giải thích con số kỳ vọng).

## Quy tắc
- Yêu cầu ở `docs/lab/tickets/` + `docs/notes/phase-N.md`; KHÔNG tự bịa luật. Chỗ mơ hồ → bảng giả định.
- Số chuẩn của ticket là bắt buộc: sửa `config.py` VÀ `game.contract.json` (test so khớp).
- Khoảng cách gameplay là XZ (trừ Tỏa Sáng: 3D), "trong bán kính r" là `<= r + EPS`; mép bản đồ cũng có EPS.
- Bộ đếm: đặt N ở tick k, giảm ở bước 2 các tick sau → hết ở tick k+N. Kiểm tra lệch-một-tick bằng tính tay.
- Tất định: chỉ dùng `sim.rng`; client chỉ dùng `random.Random(hằng số)` cho trang trí.
- Kỳ vọng trong scenario phải **tính tay** (ghi vào `why`), không chép từ output.
- Phần trang trí/sáng tạo chỉ ở client, không đổi output headless.
- Không sửa tay `docs/proof/`; sinh lại bằng tool.
- Test cũ sai vì luật mới: sửa/xoá kèm lý do trong `docs/notes/phase-N.md`, không skip âm thầm.
- Không xong khi test đỏ (Stop hook chặn).
- `ShowBase` đã có `restart`, `run`, `start`… — không đặt trùng tên. Font Arial thiếu một số ký tự (✕): dùng ký tự Latin-1.
- Đổi client → chạy `tools/screenshot.py` và XEM ảnh.
- Mô tả scenario (`req`) phải khớp điều thực sự kiểm tra; nhớ các cơ chế nền (gió Đêm 3, spawn mặc định) khi dựng scenario.
