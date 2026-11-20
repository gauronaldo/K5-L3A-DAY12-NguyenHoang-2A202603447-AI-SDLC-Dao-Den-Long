# Phase 1 — PRD-0 + Test Contract v1.0

## 1. Yêu cầu → tiêu chí nghiệm thu

| ID | Yêu cầu (PRD-0 / Contract) | Tiêu chí nghiệm thu (làm A thì thấy B) | Cách kiểm chứng |
|---|---|---|---|
| R1 | Di chuyển 3D, nhảy, camera | Giữ `move [0,1]` 60 tick (yaw 0) → player đi đúng `player_speed` m theo +Z; yaw xoay vector đúng công thức contract; nhấn jump → y > 1 m rồi về 0 | unit `Movement.*`, CLI `test_inputs_fields_persist`, chơi thật (ảnh) |
| R2 | Đêm 1 "Đảo Bến": đảo tròn, 5 đèn | Snapshot tick 0: 5 đèn L1..L5, player (0,0,0), 3 HP, 300 s | scenario `07_default_night_start`, unit `test_default_night_layout` |
| R3 | Nhặt đom đóm | Đom đóm trong `pickup_radius` (≤, XZ) bị nhặt, event `mote_picked`, không vượt `carry_capacity` | unit `Motes.*`, scenario `01` |
| R4 | Gửi ánh sáng vào đèn | Nhấn interact trong `interact_radius` của đèn chưa sáng → `deposit`; đủ `lantern_cost` → `lantern_lit` | unit `Lanterns.*`, scenario `01` |
| R5 | Bóng Mực đuổi; chạm mất HP; xung sáng đẩy lùi, tốn sáng; sợ đèn | Shade tiến về player `shade_speed` m/s; chạm (≤ `shade_hit_radius`) → `player_hit`, rơi `floor(carried·hit_drop_ratio)`, bất tử `invuln_s`; pulse tốn `pulse_cost`, choáng `pulse_stun_s`, đẩy `pulse_push_m`, hồi `pulse_cooldown_s`; shade không bao giờ vào `safe_radius` quanh đèn | unit `Shades.*`, scenario `03`, `04`, `05`, `08` |
| R6 | Thắng / thua | Thắp đủ đèn → `game_over won all_lit`; hết HP → `lost no_flames`; hết giờ → `lost dawn`; sau game over mô phỏng dừng | unit `Night.*`, `Lanterns.test_win_all_lit_and_bonus`, scenario `02`, `03`, `06`, `08` |
| R7 | Điểm | Theo bảng `score` trong `game.contract.json`; dựng scenario không cộng điểm | unit + scenario `01`, `02`, `04` |
| R8 | HUD + chơi lại | HUD hiện HP, sáng đang mang, đèn đã thắp, điểm, thời gian, hồi chiêu; R chơi lại sau thắng/thua | chạy game, ảnh chụp `docs/proof/phase-1/screenshots/` |
| C1 | `game.contract.json` | Giá trị tuning khớp code | `ContractFile.test_contract_matches_code` |
| C2 | Headless CLI, 60 tick/s, dừng ở `--ticks` hoặc khi kết thúc, exit 0 | Snapshot 0 trước input; event tick = k+1; `end` là dòng cuối | `test_headless.Cli.*` |
| C3 | File hỏng → exit 2 + stderr | JSON hỏng, tick không tăng, move ngoài [-1,1], kiểu sai → exit 2 | `test_malformed_files_exit_2` |
| C4 | Tất định | Cùng seed/scenario/inputs → output giống từng byte | `test_determinism_default_night`, `tools/verify.py` chạy mỗi scenario 2 lần |

## 2. Giả định (chỗ PRD-0 mơ hồ)

| # | Chỗ mơ hồ | Giả định của tôi |
|---|---|---|
| A1 | "Ánh sáng" mà xung sáng tiêu tốn | Là đom đóm đang mang: mỗi pulse tốn `pulse_cost = 1`. Không đủ → không phát xung, không có event |
| A2 | Pulse không trúng ai | Vẫn phát event `pulse` với `stunned_ids: []` (vẫn tốn sáng, vẫn hồi chiêu) |
| A3 | `safe_radius` áp cho đèn nào | **Mọi** đèn (đã sáng hay chưa) — contract ghi "quanh một đèn", không nói chỉ đèn sáng. Shade bị giữ ở `safe_radius + 0.001` |
| A4 | Rơi khỏi đảo | Không có: `fall_enabled = false`, player bị chặn ở mép đảo bán kính 32 m, không bao giờ ghi event `by: "fall"` |
| A5 | Đom đóm rơi khi bị đánh | `floor(carried × 0.5)` bị mất hẳn (bay vào sương), không rải lại trên đất |
| A6 | Gửi sáng | Nhấn interact gửi tối đa `lantern_cost − deposited`; chọn đèn chưa sáng gần nhất trong tầm; carried = 0 thì không có event |
| A7 | Điểm | +10 mỗi đom đóm nhặt, +100 mỗi đèn thắp, +5 mỗi shade bị choáng; **chỉ khi thắng**: +1 × floor(giây còn lại) +50 × HP còn lại. Thua không có thưởng |
| A8 | Bóng Mực mặc định | 2 shade lúc đầu ở vòng 14–30 m, cách player ≥ 12 m, ngoài vùng an toàn; cứ 45 s xuất hiện thêm 1 (event `shade_spawned`), tối đa 6. Shade luôn đuổi (state `chase`/`stunned`). Scenario `random_shades:false` → không spawn theo thời gian |
| A9 | Đom đóm mặc định | 40 con rải ngẫu nhiên (seed) ở vòng 4–30 m, không hồi sinh (cần 25 để thắng) |
| A10 | Vị trí đèn mặc định | Vòng tròn bán kính 25 m, L1 ở (0,0,25), mỗi đèn cách 72° |
| A11 | Nhảy | Vận tốc 7 m/s, trọng lực 20 m/s²; chỉ là di chuyển dọc, mọi khoảng cách gameplay đo XZ nên nhảy không né được shade |
| A12 | Snapshot cuối | Chỉ ghi snapshot ở tick chia hết cho `--snapshot-every` (đúng chữ contract); trạng thái cuối nằm ở dòng `end` |
| A13 | Thứ tự xử lý trong 1 tick | input → di chuyển → nhảy → nhặt → interact → pulse → shade → va chạm → spawn → đồng hồ |
| A14 | Bất tử sau khi bị đánh | 90 tick (1.5 s) không nhận đòn; shade bị choáng không gây sát thương |
| A15 | Nền tảng | Python 3.10+; headless chỉ dùng thư viện chuẩn; bản 3D dùng Panda3D (pip, chạy macOS/Linux/Windows) |

## 3. Thiết kế (1 dòng lý do mỗi quyết định)

- `lantern/sim.py` là logic thuần, bước cố định 1/60 s — dùng chung cho game 3D và headless, nên headless chính là game thật.
- RNG riêng `random.Random(seed)`, thứ tự sinh cố định (đom đóm → shade) → tất định.
- `game.contract.json` có test so khớp với `lantern/config.py` → không thể lệch số.
- Client 3D (`lantern/client.py`) chỉ đọc state của `Simulation` và gửi `InputState`; phần trang trí (sáng tạo) không chạm vào logic.
