# Đảo Đèn Lồng — Day 12 AI SDLC

> 🎬 **Video demo:** sẽ đính kèm Release `v1.0.0` ở Phase 4.
> Nguyễn Hoàng · 2A202603447 · Đề bài gốc: [docs/lab/](docs/lab/README.md) · Ticket: [docs/lab/tickets/](docs/lab/tickets/)

Đảo Đèn Lồng là game 3D góc nhìn thứ ba. Người chơi điều khiển **Mây**, người giữ đèn nhỏ tuổi đội nón lá. Mây gom **đom đóm** để thắp lại các **Đèn Lồng Lớn** trên ba hòn đảo trong biển mây (Đảo Bến, Đảo Cau, Đảo Chuông), đồng thời né **Bóng Mực** và **Gió Lạc** trong sương đen.

![gameplay](docs/proof/phase-3/screenshots/12_fuel_bars_drain.png)

## Cài đặt và chạy (macOS / Linux, Python ≥ 3.10)

```bash
git clone https://github.com/gauronaldo/K5-L3A-DAY12-NguyenHoang-2A202603447-AI-SDLC-Dao-Den-Long.git && cd K5-L3A-DAY12-NguyenHoang-2A202603447-AI-SDLC-Dao-Den-Long
python3 -m pip install -r requirements.txt
python3 main.py
```

Chế độ headless và test chỉ cần Python, không phải cài thêm gì. Trên Windows, gõ `python` thay cho `python3`.

## Điều khiển

| Phím | Hành động |
|---|---|
| W A S D (hoặc ↑ ↓) | Di chuyển theo hướng camera |
| ← → hoặc giữ chuột phải và kéo | Xoay camera (độ nhạy chỉnh trong Cài đặt) |
| Space | Nhảy |
| Shift | Lướt |
| E (hoặc F) | Nạp đom đóm vào Đèn Lồng Lớn gần nhất (trong 2 m) |
| Q (hoặc chuột trái) | Tỏa Sáng: tốn 3 đom đóm, làm choáng và đẩy lùi Bóng Mực trong 5 m |
| Esc / P | Tạm dừng (Tiếp tục / Chơi lại Đêm / Cài đặt / Về menu) |

## Luật chơi (Ticket-02 + Ticket-03)

- Có 3 Đêm: Đảo Bến (5 đèn, 240 s), Đảo Cau (6 đèn, 270 s), Đảo Chuông (7 đèn, 300 s). Mục tiêu là **giữ đảo sáng tới bình minh**: lúc hết giờ phải còn ít nhất 3/5, 4/6 hoặc 5/7 đèn sáng thì mới thắng. Mất hết 3 Ngọn Lửa thì thua ngay.
- Đèn cần 10 đom đóm để thắp lần đầu, sau đó chỉ cần 5 để thắp lại. Đèn sáng hao 1 dầu mỗi giây. Đứng gần đèn đang sáng chưa đầy và bấm E để châm dầu (10 dầu cho mỗi đom đóm). Hết dầu thì đèn tắt.
- Đèn còn từ 30 dầu trở lên mới có vùng an toàn 6 m. Đèn yếu hơn sẽ bị Bóng Mực tới hút dầu (5 mỗi giây).
- Sức chứa đom đóm = 10 + 2 × số lần thắp thành công, tối đa 20.
- Bóng Mực phát hiện Mây trong 12 m và bỏ đuổi khi xa hơn 18 m. Bị chạm thì mất 1 lửa và rơi một nửa số đom đóm đang mang. Rơi khỏi đảo cũng mất 1 lửa và mất hết đom đóm. Gió Lạc cướp đom đóm, Bùa Gió giúp tăng tốc, Đêm 3 có gió mạnh.
- Điểm: mỗi đom đóm nạp vào đèn +5; thắp lần đầu +100; thắp lại +40; mỗi Bóng Mực trúng Tỏa Sáng +5 (+15 nếu nó đang hút dầu). Khi thắng Đêm, mỗi đèn còn sáng được +50 + số dầu còn lại, mỗi lửa còn lại +50.
- **Cài đặt:** âm lượng, độ nhạy chuột và *Bảng màu dễ phân biệt* (dành cho người mù màu).

Mọi con số nằm trong [lantern/config.py](lantern/config.py) và [game.contract.json](game.contract.json). Quyết định thiết kế ghi ở [ADR 0001](docs/adr/0001-lantern-fuel-and-dawn-win.md).

## Headless (Test Contract v1.2)

```bash
python3 headless.py --seed 1 --night 2 --ticks 1200 --out out.jsonl \
    [--scenario scenarios/16_drifter_steal/scenario.json] [--inputs file.json] [--snapshot-every 10]
```

- Chạy 60 tick/s, không mở cửa sổ. Lệnh dừng khi chạy đủ `--ticks` hoặc khi Đêm kết thúc (exit 0). Nếu file đầu vào sai định dạng hoặc `--night` không thuộc 1–3 thì exit 2 và ghi lỗi ra stderr.
- Một Đêm 21 600 tick chạy khoảng 1–3 giây.
- Phần tự diễn giải chỗ ticket chưa nói rõ: điểm xuất phát Đêm 3 là (0,0,−25), vì (0,0,0) nằm trong tháp chuông. `invuln` trong snapshot là boolean. Các giả định khác xem [phase-2.md §2](docs/notes/phase-2.md).

## Kiểm chứng

```bash
python3 tools/verify.py --phase phase-3       # unit test + 25 scenario (chạy 2 lần mỗi scenario) → docs/proof/phase-2/
python3 -m unittest discover -s tests          # chỉ unit test
python3 tools/screenshot.py --phase phase-3   # ảnh chụp từ client thật (offscreen)
python3 main.py --fps-probe 10 --night 3       # đo FPS ở 1280×720, có autopilot điều khiển
```

CI chạy `tools/verify.py` trên Ubuntu và macOS mỗi lần push. Bảng truy vết yêu cầu đến bằng chứng: [Phase 1](docs/proof/phase-1/README.md) · [Phase 2](docs/proof/phase-2/README.md) · [Phase 3](docs/proof/phase-3/README.md).

## Sáng tạo của tôi

Các phần dưới đây chỉ nằm trong client, không chạm tới `lantern/sim.py`. Vì vậy output headless không thay đổi; bằng chứng là 20 scenario vẫn đạt và tất định.

- **Vòng an toàn phát sáng** 6 m quanh đèn có vùng an toàn (tắt khi dầu < 30), giúp người chơi thấy rõ vùng Bóng Mực không vào được ([ảnh](docs/proof/phase-2/screenshots/03_night1_pulse_hud.png)).
- **Đèn tay của Mây sáng dần** theo số đom đóm đang mang.
- **La bàn** trên đầu Mây chỉ về đèn chưa sáng gần nhất.
- **Lời dẫn của Ông Đăng** riêng cho từng Đêm ([ảnh](docs/proof/phase-2/screenshots/02_intro_night1.png)).
- **Âm thanh tự tổng hợp** bằng code (nhạc nền ngũ cung và 11 hiệu ứng), không dùng asset ngoài.
- Hiệu ứng bùng sáng khi thắp đèn, vòng Tỏa Sáng lan rộng đúng 5 m, lá bay theo hướng gió.

## Cấu trúc

```text
lantern/sim.py        logic thuần, tất định, 12 bước/tick (dùng chung cho game và headless)
lantern/config.py     số chuẩn, 3 bản đồ, bảng màu   ·   lantern/world.py   mặt đất / vật cản
lantern/files.py      kiểm tra inputs/scenario         ·   lantern/headless.py CLI
lantern/client.py     client Panda3D, HUD, menu        ·   lantern/campaign.py, settings.py, meshes.py
assets/sounds/        âm thanh sinh bởi tools/gen_sounds.py
tests/, scenarios/    unit test + scenario headless (kỳ vọng tính tay)
tools/                verify.py, screenshot.py, gen_sounds.py, hooks/stop_gate.py
docs/notes/           giả định, nhật ký AI, retro    ·   docs/proof/  bằng chứng từng phase
AGENTS.md, CLAUDE.md, .claude/   harness AI (skill verify-game, Stop hook, agent reviewer)
```

## Tài liệu

[Phase 1](docs/notes/phase-1.md) · [Phase 2](docs/notes/phase-2.md) · [Phase 3](docs/notes/phase-3.md) · [ADR](docs/adr/) · [Nhật ký AI](docs/notes/ai-log.md) · [Đánh giá & retro](docs/notes/retro.md) · [CHANGELOG](CHANGELOG.md) · [CREDITS](CREDITS.md) · [LICENSE](LICENSE)
