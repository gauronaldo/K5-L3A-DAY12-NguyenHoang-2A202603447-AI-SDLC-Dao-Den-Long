# AGENTS.md — Đảo Đèn Lồng

Game 3D (Panda3D) 3 Đêm + headless theo Test Contract **v1.3**. Python 3.10+.
Quyết định thiết kế lớn: `docs/adr/`.

## Lệnh
- Test nhanh: `python3 tools/verify.py --quick` (unit test, không cần panda3d)
- Kiểm chứng đầy đủ + bằng chứng: `python3 tools/verify.py --phase phase-N` → `docs/proof/phase-N/`
- Headless: `python3 headless.py --seed 1 --night {1,2,3} --ticks 600 --out out.jsonl [--scenario f] [--inputs f]`
- Game: `python3 main.py` · FPS: `python3 main.py --fps-probe 10 --night 3` · Ảnh: `python3 tools/screenshot.py --phase phase-N`
- Âm thanh sinh lại: `python3 tools/gen_sounds.py`
- Bench: `python3 main.py --bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json` (đóng app nặng khác trước khi đo)
- Soak: `python3 soak.py --seed 7 --nights 10 --out docs/proof/phase-4/soak.json`
- Bản phát hành: `python setup.py build_apps` · Video: `python3 tools/make_demo.py`

## Cấu trúc
- `lantern/sim.py` logic thuần (KHÔNG import panda3d). `step()` đi đúng **12 bước** của Ticket-02 — giữ comment đánh số.
- `lantern/config.py` số chuẩn + 3 bản đồ + bảng màu. `lantern/world.py` mặt đất/vật cản theo Đêm.
- `lantern/files.py` đọc/kiểm tra inputs & scenario (lỗi → exit 2). `lantern/headless.py` CLI.
- `lantern/client.py` render + HUD + menu, chỉ đọc state sim. `campaign.py`, `settings.py`, `leaderboard.py`,
  `bench_scene.py`, `soak.py`, `sysinfo.py` thuần Python (test được không cần GPU).
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
- Dầu đèn là **số nguyên** `fuel_u` (1/60 đơn vị); không đổi sang float. Luật đèn đi qua `_safe()` / `_accepts()`.
- Change request thay luật: liệt kê test/scenario bị ảnh hưởng TRƯỚC khi code (bảng §1 trong `phase-N.md`), xoá/sửa kèm lý do.
- Khi tính tay kỳ vọng, liệt kê mọi thứ trừ/cộng trong cùng tick (hao + hút + châm) — đã từng quên phần hút.
- Vá file lớn bằng script Python ghi ra file (có `assert` từng đoạn), không dùng heredoc chứa `\\` trong bash.
- `ShowBase` đã có `restart`, `run`, `start`… — không đặt trùng tên. Font Arial thiếu một số ký tự (✕): dùng ký tự Latin-1.
- Đổi client → chạy `tools/screenshot.py` và XEM ảnh.
- `OnscreenText`: xoay bằng `setRoll(-deg)` — `setR` quay quanh tâm màn hình (mũi tên Phase 2–3 từng nằm sai chỗ).
- Màu UI phải tương phản với nền đêm (tím #7A3CFF gần như vô hình trên #0E1430); dùng màu cảnh báo cho chỉ báo.
- Hiệu năng: mỗi thực thể ≤ 2 geom, chỉ đổi màu khi trạng thái đổi; đo bằng `--bench`/cProfile trước khi tối ưu.
- Chữ UI: scale ≥ 0.05 (18 px ở 720p) — `tests/test_phase4.py` quét code.
- Số đo hiệu năng phải ghi kèm máy và hoàn cảnh (app nặng khác đang chạy?) — không sửa tay `bench.json`.
- Mô tả scenario (`req`) phải khớp điều thực sự kiểm tra; nhớ các cơ chế nền (gió Đêm 3, spawn mặc định) khi dựng scenario.
