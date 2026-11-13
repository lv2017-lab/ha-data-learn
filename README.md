# Learn Data Server — kho add-on Home Assistant

Add-on server dữ liệu (SQLite + API cổng 8765) cho **Zalo Learn Data Bot**:

- Tự động học / xóa mã lỗi máy in qua nhóm Zalo
- Bot nhớ nội dung trò chuyện theo nhóm
- Gọi đúng tên bot là bot trả lời (không cần tag), phong cách dạ/vâng, ngắn gọn
- Nhật ký sửa chữa / thay thế phụ tùng: thêm, sửa, xóa, tra theo ngày tháng năm và loại máy (DC1–DC4), xuất Excel CSV
- Phân tích ảnh gửi vào nhóm bằng Gemini (AI Task)

## Cài đặt

1. Add-on Store → ⋮ → Repositories → thêm URL repo này
2. Cài **Learn Data Server** → Start
3. Kiểm tra `http://<IP-HA>:8765/health` → `{"ok": true}`

Chi tiết wiring (rest_command, automation) xem tài liệu đi kèm bot.
