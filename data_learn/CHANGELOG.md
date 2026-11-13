## 1.6.0

- Lịch hẹn nhắc nhở theo từng nhóm: POST /reminder (lưu lịch), GET /reminders/due (các lịch đã đến giờ, mọi nhóm), POST /reminder/sent (đánh dấu đã gửi), GET /reminders?group_id= (lịch đang chờ của nhóm), DELETE /reminder?id=&group_id= (hủy lịch).
- Bảng reminders mới tự tạo khi nâng cấp, không đụng dữ liệu cũ.

## 1.5.0

- Mã lỗi + nhật ký + tên bot + ghi nhớ tách THEO TỪNG NHÓM (group_id): mỗi nhóm độc lập.
- learned: khóa chính (code, group_id) — tự migrate DB cũ, lookup ưu tiên đúng nhóm rồi tới dòng dùng chung (group_id rỗng).
- /logs lọc theo group_id (kèm dòng dùng chung); xóa nhật ký theo ngày cũng theo nhóm.
- Máy trong nhật ký để dạng tự do (Máy in 2...), chỉ chuẩn hoá DC/Dây chuyền kèm số bất kỳ (DC12).
- Tên bot theo từng nhóm: GET/POST /bot-names nhận group_id, nhóm chưa đặt thì dùng danh sách chung/mặc định.
- Ghi nhớ hội thoại: GET /memory-epoch, POST /memory-epoch/bump — tăng epoch = xóa ghi nhớ của nhóm.

## 1.4.0

- Thêm kho tên bot: GET /bot-names, POST /bot-names/replace|add|remove (bảng settings). Tên mặc định: Lyly, Ly Ly, Ly Ky.

# Changelog

## 1.3.0

- Đổi tên thành Learn Data Server, slug mới `data_learn` (add-on mới hoàn toàn — chuyển dữ liệu cũ bằng file xuất /list + /logs.csv và script migration đi kèm).
- Thêm sửa nhật ký: `POST /log/update` (sửa từng phần theo id).
- Tra nhật ký `/logs?q=` giờ tìm cả theo loại máy (DC1–DC4).

## 1.2.0

- Thêm xóa nhật ký: `DELETE /log?id=` và `DELETE /logs?date=dd/mm/yyyy`.

## 1.1.0

- Thêm nhật ký sửa chữa: `POST /log`, `GET /logs`, `GET /logs.csv`.
- Bảng `repair_logs` tự tạo trong DB cũ, dữ liệu mã đã học giữ nguyên.

## 1.0.0

- Bản đầu: server học/tra/xóa mã lỗi (SQLite + lịch sử ghi), API cổng 8765.
