# ADR 0001 — Đèn có nhiên liệu và luật thắng "giữ sáng tới bình minh"

- **Trạng thái:** Chấp nhận (Phase 3, Ticket-03, contract v1.2)
- **Thay thế:** luật Phase 2 "đèn sáng là sáng mãi", "thắng ngay khi mọi đèn sáng", "Bóng Mực không bao giờ vào vùng an toàn"

## Bối cảnh

Ở Phase 2, đèn chỉ có hai trạng thái `lit: bool` và `deposited`. Đêm kết thúc ngay khi đèn cuối cùng sáng. Ticket-03 yêu cầu đèn tiêu hao dầu, có thể tắt rồi thắp lại, Bóng Mực có thể hút dầu, và chỉ xét thắng khi trời sáng.

## Quyết định

**1. Mô hình trạng thái đèn**

```
            nạp đủ cost (10 nếu chưa từng sáng, 5 nếu ever_lit)
  TẮT  ─────────────────────────────────────────────────►  SÁNG (fuel = 100)
 (deposited 0..cost)                                       │  fuel ≥ 30: có vùng an toàn 6 m
   ▲                                                       │  fuel < 30: mất vùng, Bóng Mực wander nhắm tới
   └────────────── fuel ≤ 0 (hao 1/s + hút 5/s mỗi Bóng Mực drain) ◄──┘
                   → lantern_out, deposited = 0, ever_lit = true
  SÁNG + chưa đầy ── Tương tác ──► châm dầu: used = min(mang, ceil((100−fuel)/10)), fuel += 10·used
```

- Dầu lưu bằng **số nguyên đơn vị 1/60** (`fuel_u`, tối đa 6000): mỗi tick hao 1, mỗi Bóng Mực đang hút trừ 5. Nhờ vậy không có sai số số thực. Chỉ khi xuất ra mới làm tròn 1 chữ số thập phân.
- Một đèn có các trường `lit`, `deposited`, `fuel_u`, `ever_lit`, `relit_count`. Hai hàm `_safe(lan)` (lit và fuel ≥ 30) và `_accepts(lan)` (chưa sáng, hoặc sáng nhưng chưa đầy) gom mọi luật về một chỗ.
- Bước 2 của tick (giảm bộ đếm) trừ dầu, rồi tắt ngay các đèn có fuel ≤ 0, đúng thứ tự Ticket-03 yêu cầu.
- Vùng an toàn bật lại khi đèn vừa thắp hoặc được châm lên ≥ 30 từ dưới 30. Lúc đó dùng chung cơ chế "đẩy ra trong ≤ 30 tick, không gây sát thương" của Phase 2.

**2. Bóng Mực thêm trạng thái `drain`**

- `wander` chọn mục tiêu: đèn sáng có fuel < 30 gần nhất (bằng nhau thì id nhỏ hơn). Nếu không có thì chọn đèn tắt gần nhất như Phase 2. Khi cách mục tiêu yếu ≤ 2 m thì chuyển `drain`.
- `drain` đứng yên. Chuyển sang `chase` nếu Mây ≤ 6 m; sang `stunned` nếu trúng Tỏa Sáng (+15 điểm); sang `wander` nếu đèn tắt, được châm lên ≥ 30, hoặc ra xa > 2 m.

**3. Luật thắng**

- Bỏ thắng sớm. Ở bước 11 (sau mọi cập nhật): hết lửa thì `no_flames`. Ngược lại, nếu `sim_tick ≥ thời lượng` thì thắng `dawn_survived` khi số đèn sáng ≥ ceil(0.6 × tổng), không thì thua `dawn`.
- Điểm bình minh chỉ cộng khi thắng: mỗi đèn sáng +50 + floor(fuel), mỗi lửa +50. Bỏ thưởng thời gian.

## Hệ quả

- Snapshot đèn thêm `fuel`, `ever_lit`, `relit_count`. Event mới: `refuel`, `lantern_out`, `fuel_drain`, `lantern_lit.relight`. `all_lit` không còn được phát.
- Test và scenario dựa trên "thắng khi mọi đèn sáng" hoặc điểm cũ phải sửa hay thay. Danh sách ở [phase-3.md §1](../notes/phase-3.md).
- Sức chứa trở thành hàm `capacity()` = min(20, 10 + 2 × successful_lights). Mọi chỗ nhặt đom đóm đều gọi hàm này.
- Phương án đã cân nhắc nhưng bỏ: lưu dầu bằng `float` rồi so với epsilon. Bỏ vì tick hết dầu có thể lệch 1 so với tính tay, trái với khuyến nghị của ticket.
