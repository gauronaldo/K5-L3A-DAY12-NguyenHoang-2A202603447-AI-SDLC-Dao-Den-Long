# AGENTS.md — Đảo Đèn Lồng

Game 3D (Panda3D) + headless theo Test Contract. Python 3.10+.

## Lệnh
- Test nhanh: `python3 tools/verify.py --quick` (unit test)
- Kiểm chứng đầy đủ + ghi bằng chứng: `python3 tools/verify.py` → `docs/proof/phase-N/`
- Headless: `python3 headless.py --seed 1 --night 1 --ticks 600 --out out.jsonl [--scenario f] [--inputs f]`
- Game: `python3 main.py` (cần `pip install -r requirements.txt`)

## Cấu trúc
- `lantern/sim.py` logic thuần (KHÔNG import panda3d). `lantern/config.py` mọi con số tuning.
- `lantern/files.py` đọc/kiểm tra inputs & scenario (lỗi → exit 2). `lantern/headless.py` CLI.
- `lantern/client.py` render + HUD, chỉ đọc state sim. `scenarios/<name>/` = scenario + inputs + expect.

## Quy tắc
- Yêu cầu phase nằm trong `docs/notes/phase-N.md`; KHÔNG tự bịa luật. Chỗ mơ hồ → thêm vào bảng giả định.
- Đổi tuning: sửa `config.py` VÀ `game.contract.json` (test so khớp).
- Mọi khoảng cách gameplay là XZ, "trong bán kính r" là `<= r` (dùng `within()`).
- Tính tất định: chỉ dùng `sim.rng`, không dùng `random` toàn cục, thời gian thực hay thứ tự set/dict không ổn định.
- Phần trang trí/sáng tạo chỉ ở client, không đổi output headless.
- Không sửa tay file trong `docs/proof/`; sinh lại bằng `tools/verify.py`.
- Test cũ sai vì luật mới: sửa hoặc xoá kèm lý do trong `docs/notes/`, không skip âm thầm.
- Không xong khi test đỏ (Stop hook sẽ chặn).
