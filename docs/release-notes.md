## Đảo Đèn Lồng v1.0.0 — Bình minh

Game 3D: Mây gom đom đóm, thắp và châm dầu cho Đèn Lồng Lớn trên 3 hòn đảo, giữ đảo sáng tới bình minh, né Bóng Mực và Gió Lạc.

### Tải về
- **`DaoDenLong-1.0.0-windows-x64.zip`** — Windows 10/11 x64, không cần cài Python. Giải nén → chạy `DaoDenLong.exe`.
  Kèm `DaoDenLong-headless.exe` (Test Contract v1.3) và `DaoDenLong-soak.exe`. Lần đầu chạy, SmartScreen có thể hỏi xác nhận (file chưa ký số).
- **`demo.mp4`** — video demo 2:33 (render từ client thật, phần chơi do autopilot điều khiển).
- macOS / Linux: chạy từ mã nguồn bằng 3 lệnh trong README.

### Lệnh chính
```
DaoDenLong.exe                                                  # chơi
DaoDenLong.exe --bench --seed 42 --duration 30 --out bench.json # benchmark
DaoDenLong-soak.exe --seed 7 --nights 10 --out soak.json        # soak test
DaoDenLong-headless.exe --seed 1 --night 1 --ticks 600 --out out.jsonl
```

### Số đo (RTX 4060, Windows 11)
- Bench: 103.0 FPS trung bình · 68.8 FPS 1% low · tải 2.1 s (`docs/proof/phase-4/bench.json`)
- Soak 10 Đêm: 0 crash · RAM 25.3 → 26.0 MB
- 99 unit test + 25 scenario headless đạt, tất định

Chi tiết thay đổi: `CHANGELOG.md`. Bằng chứng từng phase: `docs/proof/`.
