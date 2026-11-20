# Credits

- **Nhân vật, bối cảnh, tên gọi** (Mây, Đảo Đèn Lồng, Đèn Lồng Lớn, Bóng Mực, đom đóm): bản gốc của lab Day 12.
- **Mô hình 3D:** tự dựng bằng code (`lantern/meshes.py`: hình trụ, nón, cầu, vòng). Không dùng asset bên ngoài.
- **Âm thanh:** tự tổng hợp bằng code (`tools/gen_sounds.py`, thư viện chuẩn Python), không dùng mẫu âm thanh bên ngoài.
- **Font chữ:** dùng font có sẵn của hệ điều hành lúc chạy (DejaVu Sans / Arial / Segoe UI), không đóng gói trong repo.
- **Engine:** [Panda3D](https://www.panda3d.org/) 1.10.14 — Modified BSD License.
- **Video demo:** render offscreen từ client bằng `tools/make_demo.py`, mã hoá bằng FFmpeg (gói `imageio-ffmpeg`, BSD-2 / FFmpeg LGPL) — chỉ dùng khi dựng video, không nằm trong game.
- **Đóng gói:** `build_apps` của Panda3D (Modified BSD).
- **Công cụ AI:** Claude Code (Anthropic) hỗ trợ viết code, test và tài liệu; xem [docs/notes/ai-log.md](docs/notes/ai-log.md).
