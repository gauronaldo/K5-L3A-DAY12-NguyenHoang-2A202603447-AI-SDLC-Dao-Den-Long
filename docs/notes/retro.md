# Đánh giá & Retro — Đảo Đèn Lồng

## 1. Đánh giá từng phase

| Phase | Kết quả | Hỏng phase trước? | Chưa đạt / rủi ro | Chỉnh sau phase |
|---|---|---|---|---|
| 1 — PRD-0 | R1–R8, C1–C4 đạt; 31 test + 8 scenario ([bằng chứng](../proof/phase-1/README.md)) | — | Mũi tên chỉ đèn ngoài màn hình có lỗi vị trí (`setR`), chỉ phát hiện ở Phase 4 | AGENTS.md +3 quy tắc từ lỗi thật |
| 2 — Ba hòn đảo | Số chuẩn, 3 bản đồ, contract v1.1, 9 tính năng; 68 test + 20 scenario; ~500 FPS ([bằng chứng](../proof/phase-2/README.md)) | Không; test bị số chuẩn thay đã sửa/xoá có lý do | Âm thanh chưa nghe kiểm tra thủ công; giả định B2/B3/B4/B11 | Quy tắc đếm tick, EPS, "kỳ vọng phải tính tay" |
| 3 — Đèn cạn dầu | P1–P11 đạt; ADR 0001; 86 test + 25 scenario ([bằng chứng](../proof/phase-3/README.md)) | Không; 3 test xoá + 6 sửa có lý do | Giả định D2/D5/D6 | Lập bảng tác động trước khi code; vá file bằng script có `assert` |
| 4 — v1.0.0 | Bench, soak, bảng xếp hạng, đổi phím, phụ đề, giảm chuyển động, chữ lớn; 99 test ([bằng chứng](../proof/phase-4/README.md)) | Không; mọi `runs/*.jsonl` Phase 3 giống từng byte sau tối ưu | Số bench đo khi máy đang chạy một game 3D khác (xem bằng chứng); video là autopilot | Quy tắc UI (setRoll, tương phản), hiệu năng, ghi hoàn cảnh đo |

## 2. Số liệu toàn dự án

- **Code:** logic `lantern/sim.py` ~700 dòng, client ~1200 dòng; 99 unit test, 25 scenario headless, 21 ảnh bằng chứng, 3 bản đồ.
- **Headless:** một Đêm 21 600 tick chạy 1–3 s (ngưỡng 30 s). Soak 10 Đêm: 0 crash, RSS 25 → 26 MB.
- **Bench (RTX 4060):** 117.6 FPS trung bình / 77 FPS 1% low khi máy rảnh; 63–72 / 14–45 khi một game 3D khác chạy song song ([bench.json](../proof/phase-4/bench.json) là lần đo cuối, có ghi chú).
- **Git:** ~70 commit nhỏ (feat/fix/test/docs/chore), 4 tag phase, CI Ubuntu + macOS xanh ở mọi tag.

## 3. Điều hiệu quả / không hiệu quả khi làm với AI

**Hiệu quả**
- **Tách `sim.py` thuần + headless từ đầu:** mọi luật kiểm chứng được trong vài giây, không cần GPU; client chỉ đọc state. Ba lần đổi luật lớn không phải đụng vào renderer.
- **Kỳ vọng tính tay trong `why` của scenario:** bắt được 4 lỗi thật (EPS mép đảo, recoil 59/60 bước, quên phần hút dầu, quên gió) mà nếu chép số từ output thì sẽ "đạt" một cách sai.
- **Xem ảnh chụp thay vì tin log:** 9 lỗi hiển thị chỉ thấy được qua ảnh (viền tam giác, ⚠ thành ô vuông, camera che đầu đèn, vòng an toàn sai luật, mũi tên lệch…).
- **Bảng tác động trước change request (Phase 3):** test cũ fail đúng như dự đoán, không bất ngờ.

**Không hiệu quả**
- Viết test cùng lúc với code làm AI mắc lỗi ở *test* nhiều hơn ở code (Phase 2: 7/9 test fail là test sai). Lẽ ra nên viết test từ tiêu chí trước, chạy đỏ, rồi mới code.
- Heredoc bash có ký tự `\` bị công cụ cắt — mất 3 lượt trước khi chuyển sang ghi script ra file.
- Đo hiệu năng trên máy cá nhân đang chạy ứng dụng khác cho số dao động mạnh.

## 4. Những lần AI sai và cách phát hiện (tổng hợp)

| Loại | Ví dụ | Phát hiện bằng |
|---|---|---|
| Lệch một tick / số thực | `mote_picked` tick 41 vs 40; x = 40.0000000001 rời đảo sớm; recoil 59/60 | Tính tay trong test/scenario |
| Test sai, không phải code sai | nhấn lướt khi đang lướt, quên `night_start`, quên gió/hút dầu | Đọc lại luật khi test đỏ |
| Ghi nhận không trung thực | Mô tả scenario "chạy hết đêm" khi dừng ở tick 726; "nghe thử bằng tai" khi chưa nghe | Đọc dòng `end`; tự rà soát bảng bằng chứng |
| API engine | `restart()` trùng `ShowBase`; `setR` của `OnscreenText`; glyph thiếu trong font | Chạy tool chụp ảnh, xem ảnh |
| Hiệu năng | 1000 draw call / khung → 77 FPS | cProfile, bench |

Mỗi loại đều thành một dòng trong [AGENTS.md](../../AGENTS.md) để không lặp lại.

## 5. Harness nào giúp nhiều nhất

1. **`tools/verify.py` + skill `verify-game`** — một lệnh chạy unit test, 25 scenario × 2 lần (tất định), sinh báo cáo truy vết. Dùng sau mỗi thay đổi; CI chạy cùng lệnh trên Ubuntu/macOS.
2. **`tools/screenshot.py`** — biến phần "chỉ nhìn mới thấy" thành bằng chứng tái lập; là nơi phát hiện phần lớn lỗi client.
3. **AGENTS.md** — khoảng 40 dòng quy tắc, mỗi dòng sinh ra từ một lỗi thật; ngắn để không tốn ngữ cảnh.
4. **Stop hook** — chặn kết thúc khi unit test đỏ (đã thử bằng cách cố ý làm hỏng một hằng số).
5. Agent `reviewer` có sẵn nhưng ít dùng; việc review chủ yếu do tôi đọc diff và đối chiếu ticket.

## 6. Token / chi phí AI

| Phase | Ước tính | Tiết kiệm bằng cách |
|---|---|---|
| 1 | ~200k | Ghi PRD ra `phase-1.md` một lần; `verify.py --quick` in 1 dòng |
| 2 | ~450k | Lưu ticket vào repo; sinh 20 scenario bằng 1 script; chỉ in dòng FAIL |
| 3 | ~250k | Vá file bằng script có `assert` thay vì ghi lại cả file |
| 4 | ~450k | Profile trước khi tối ưu; ảnh/bench/soak qua tool thay vì mô tả bằng lời |
| **Tổng** | **~1.35M token** (ước tính theo độ dài phiên, không có số đo chính xác) | |

## 7. Nếu làm lại

- Viết test/scenario từ bảng tiêu chí **trước** (đỏ) rồi mới cho AI viết code (xanh) — giảm lỗi test sai.
- Dựng `tools/screenshot.py` và một bench đơn giản ngay từ Phase 1 để bắt lỗi UI/hiệu năng sớm (lỗi `setR` sống qua 2 phase).
- Đo hiệu năng trên máy rảnh, lặp 3 lần, báo trung vị.
- Dùng agent reviewer độc lập ở cuối mỗi phase thay vì chỉ tự review.
