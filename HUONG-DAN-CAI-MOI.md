# HƯỚNG DẪN CÀI MỚI HOÀN TOÀN — Learn Data Server 1.5.0 + Learn Data Bot V7

Cài từ trắng, không chuyển dữ liệu cũ. Bộ gói gồm:

```
learn-data-server/
├── repository.yaml          → đẩy lên GitHub
├── README.md                → đẩy lên GitHub
├── data_learn/              → đẩy lên GitHub (add-on, slug data_learn, v1.5.0)
├── automation/
│   └── learn-data-bot-v7.yaml   → dán vào Home Assistant
├── rest_command.yaml        → tạo trong /config của HA (IP đã điền 192.168.1.31)
└── HUONG-DAN-CAI-MOI.md     → file này
```

## BƯỚC 1 — GitHub

1. Tạo repo **Public** tên `learn-data-server` (không tick tạo README)
2. Upload `repository.yaml`, `README.md` và thư mục `data_learn/`
3. Mở `repository.yaml`, sửa `<TEN-GITHUB-CUA-BAN>` thành tên GitHub của bạn

## BƯỚC 2 — Cài add-on trên Home Assistant

1. Settings → Apps (Add-ons) → Add-on Store → ⋮ → **Repositories**
   → thêm `https://github.com/<tên-của-bạn>/learn-data-server`
2. Tìm **Learn Data Server** → **Install** → **Start**
3. Kiểm tra: tab Log có `print-learn-server listening on :8765`,
   mở `http://192.168.1.31:8765/health` → `{"ok": true}`

## BƯỚC 3 — rest_command (File Editor)

1. Mở `configuration.yaml`: kiểm tra CHƯA có khóa `rest_command:` nào,
   rồi thêm 1 dòng: `rest_command: !include rest_command.yaml`
2. Tạo file mới tên đúng `rest_command.yaml` (cùng thư mục configuration.yaml),
   dán toàn bộ nội dung file `rest_command.yaml` trong gói (đã điền sẵn IP 192.168.1.31)
3. Developer Tools → YAML → **Check configuration** → **Reload RESTful Commands**
4. Developer Tools → Actions: phải thấy đủ **14 lệnh**:
   `print_learn_save`, `print_learn_lookup`, `print_learn_delete`,
   `print_log_save`, `print_log_query`, `print_log_update`,
   `print_log_delete_id`, `print_log_delete_date`,
   `bot_names_get`, `bot_names_replace`, `bot_names_add`, `bot_names_remove`,
   `memory_epoch_get`, `memory_epoch_bump`
   Nếu chưa thấy đủ 14 lệnh → **Restart hẳn Home Assistant** rồi kiểm tra lại.

## BƯỚC 4 — Automation

Settings → Automations → mở bot Print đang chạy (hoặc tạo mới) → ⋮ →
**Edit in YAML** → Ctrl+A → dán toàn bộ `learn-data-bot-v7.yaml` → Save.
Chỉ giữ 1 automation bot này trên webhook; tắt/xóa các bản Print cũ.

- Đổi tên bot: bot đọc danh sách tên từ add-on mỗi tin nhắn — đổi tên ngay trong nhóm (xem BƯỚC 6), không cần sửa file.
- `local_only: false` phải giữ nguyên trên automation webhook này (Zalo gọi từ xa).

## BƯỚC 5 — Điều kiện cho tính năng ẢNH (ảnh mới ghi đè ảnh cũ)

1. Settings → Devices & services → Add integration → **Downloader**
   → thư mục tải: `/config/www`
2. `configuration.yaml` thêm (gộp vào khóa `homeassistant:` nếu đã có):

```yaml
homeassistant:
  media_dirs:
    zalo: /config/www/zalo_images
```

3. Restart HA 1 lần. Ảnh gửi vào nhóm sẽ tải về đúng 1 file
   `/config/www/zalo_images/image_latest.jpg`, ảnh mới **ghi đè** ảnh cũ.

## BƯỚC 6 — Test (database đang trắng)

1. `E18` → ra nội dung gốc (194 mã tĩnh)
2. `Lyly ơi, cho hỏi lỗi E18 là gì?` (không tag) → bot trả lời bắt đầu bằng "Dạ"
3. Học mã theo format chuẩn:
   `Lyly học E999: Nội dung lỗi test - Kiểm tra nguồn` → ✅;
   gửi `E999` → ra đúng mẫu `❌ Mã lỗi E999: Nội dung lỗi test` / `🔧 Hướng xử lý: Kiểm tra nguồn`;
   `Lyly sửa mã E999: Nội dung đã sửa - Cách xử lý mới` → ✅;
   `Lyly xóa học E999` → gửi lại `E999` → im lặng (hoặc chỉ còn mã tĩnh nếu trùng)
4. Nhật ký theo format chuẩn:
   `Lyly nhật ký: Máy DC4 - Thay Bơm Vaccum - Kênh 4 - 12/11/2026` → ✅;
   `Lyly tra nhật ký DC4` → thấy dòng vừa ghi;
   `Lyly xóa nhật ký ngày 12/11/2026` → 🗑️ Đã xóa … dòng
   (Cú pháp cũ bằng dấu `|` vẫn chạy song song.)
5. Xóa ghi nhớ (bắt buộc add-on đã lên 1.5.0):
   `Lyly xóa ghi nhớ` → bot xác nhận đã xóa toàn bộ ghi nhớ của nhóm.
   Nếu nhận thông báo "Xóa ghi nhớ thất bại" → add-on chưa lên 1.5.0.
6. Đổi tên bot trong nhóm (tên lưu riêng theo từng nhóm):
   `Lyly đổi tên thành Na Na, Ly Ly`, `Lyly thêm tên X`, `Lyly xóa tên X`
   → bot xác nhận lại danh sách tên đang dùng.
7. Gửi 1 ảnh vào nhóm → bot phân tích; ảnh có mã lỗi trùng kho → bot gửi luôn nội dung mã đó nối tiếp phần phân tích. Ảnh bài toán → mỗi phép tính một dòng dạng `số <dấu> số = kết quả đúng — Đúng/Sai`.

---

## Cập nhật từ 1.4.0 / V6.6 lên 1.5.0 / V7

1. Đẩy lại toàn bộ thư mục này lên GitHub → vào Add-on Store → add-on
   **Learn Data Server** → **Update** lên **1.5.0** → Start, xem log chạy bình thường.
2. Thay file `/config/rest_command.yaml` bằng file trong gói này (14 lệnh) →
   **Restart hẳn Home Assistant** → Developer Tools → Actions phải thấy
   `memory_epoch_get` và `memory_epoch_bump`.
3. Thay automation bằng `automation/learn-data-bot-v7.yaml` (tắt/xóa bản V6.6,
   chỉ để đúng 1 bản chạy).
4. Test nhanh theo BƯỚC 6, mục 3 → 5.

## Dùng chung mọi thiết bị, tối đa 4 nhóm độc lập

- **Mã lỗi chuẩn:** `Lyly học <MÃ>: <nội dung lỗi> - <hướng xử lý>`,
  sửa bằng `Lyly sửa mã <MÃ>: ...`, xóa bằng `Lyly xóa học <MÃ>`.
  Mã dạng chữ+số bất kỳ (E336, A12...) đều được, không bó vào máy in.
- **Nhật ký chuẩn:** `Lyly nhật ký: Máy <tên máy> - Thay thiết bị <Y> - Vị trí - Ngày`
  (ngày trống = hôm nay). Tên máy tự do (Máy in 2, DC12...).
- **Ghi nhớ:** bot nhớ theo từng nhóm; xóa bằng `Lyly xóa ghi nhớ`
  (cũng nhận `xóa trí nhớ` / `quên hết`).
- **Thêm nhóm:** mở automation → mục `conditions:` → trong danh sách `allowed`
  thay `GROUP_ID_2`, `GROUP_ID_3`, `GROUP_ID_4` bằng ID thật của các nhóm mới.
  Mỗi nhóm độc lập hoàn toàn: kho mã đã học, nhật ký, tên bot và ghi nhớ
  đều tách riêng; chỉ kho 194 mã gốc là dùng chung.

## Xử lý sự cố đổi tên

Bộ tách tên trong V7 cắt tới chữ “thành” cuối cùng, nên nhắn
`Lyly đổi tên cho tôi thành Nabu` vẫn lưu đúng một tên “Nabu”.
Nếu đang lỡ lưu sai tên cũ, ra lệnh bằng tag (không phụ thuộc danh sách tên):
`@Aibot đổi tên thành Nabu` → bot xác nhận lại đúng “Nabu” là xong.


---

## Cập nhật 1.6.0 / V8 — Lịch hẹn nhắc nhở trong nhóm

Có gì mới: gọi tên bot + "nhắc ..." là bot đặt lịch, đúng giờ bot tự gửi tin
nhắc vào đúng nhóm đã đặt. Lịch tách theo từng nhóm như mã lỗi/nhật ký.

1. Đẩy repo lên GitHub → Add-on **Learn Data Server** → **Update** lên
   **1.6.0** → Start (bảng reminders tự tạo, không mất dữ liệu cũ).
2. Thay file `/config/rest_command.yaml` bằng file trong gói này
   (**19 lệnh** — thêm reminder_save, reminders_due_get, reminder_sent,
   reminders_list, reminder_delete) → **Restart hẳn Home Assistant** →
   Developer Tools → Actions phải thấy đủ 5 lệnh reminder_* / reminders_*.
3. Thay automation bot bằng `automation/learn-data-bot-v8.yaml`
   (tắt/xóa bản V7, chỉ để MỘT bản bot chạy trên webhook).
4. Tạo THÊM một automation mới, dán `automation/learn-data-bot-reminder-sender.yaml`
   — automation này chạy mỗi phút, tới giờ là gửi tin nhắc vào nhóm.

Cách dùng trong nhóm:

- `Lyly nhắc tôi 9h uống nước` → 9:00 hôm nay (giờ đã qua thì tự sang ngày mai)
- `Lyly nhắc tôi 9h30 đi họp` · `Lyly nhắc tôi sau 30 phút kiểm tra máy in`
- `Lyly ngày mai có 1 cuộc họp lúc 10 giờ, nhớ nhắc tôi`
- `Lyly nhắc tôi ngày 20/11 lúc 8h họp phụ huynh`
- `Lyly lịch hẹn` → xem các lịch đang chờ (có mã #)
- `Lyly hủy lịch #3` → hủy lịch số 3

Test nhanh: nhắn `Lyly nhắc tôi sau 1 phút uống nước` — khoảng 1 phút sau
bot gửi "⏰ Nhắc anh: uống nước" vào nhóm là đạt.

Bản V8.1 (thay file automation ở bước 3 bằng learn-data-bot-v8-1.yaml): hiểu thêm cách nói "2 phút sau", "5 phút nữa", "uống nước sau 2 phút" — trước đó chỉ hiểu "sau 2 phút".
