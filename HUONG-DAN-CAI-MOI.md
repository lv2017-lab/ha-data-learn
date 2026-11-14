# HƯỚNG DẪN ĐẦY ĐỦ — Learn Data Server 1.6.0 + Learn Data Bot V8.2

Bản mới nhất. Bot Zalo đa năng theo nhóm: tra/học mã lỗi, nhật ký sửa chữa,
phân tích ảnh, trò chuyện AI, đổi tên bot, xóa ghi nhớ, lịch hẹn nhắc nhở.
Mỗi nhóm độc lập hoàn toàn (tối đa 4 nhóm), chỉ kho 194 mã gốc là dùng chung.

```
learn-data-server-full/
├── repository.yaml            → đẩy lên GitHub
├── README.md                  → đẩy lên GitHub
├── data_learn/                → đẩy lên GitHub (add-on, slug data_learn, v1.6.0)
├── automation/
│   ├── learn-data-bot-v8-2.yaml              → automation bot chính (dán vào HA)
│   └── learn-data-bot-reminder-sender.yaml   → automation gửi nhắc hẹn (dán vào HA)
├── rest_command.yaml          → tạo trong /config của HA (19 lệnh)
└── HUONG-DAN-CAI-MOI.md       → file này
```

> Về địa chỉ IP: file `rest_command.yaml` dùng sẵn chữ **IP-HASS**.
> Khi cài, thay toàn bộ **IP-HASS** bằng IP LAN của máy Home Assistant
> (IP bạn dùng mở HA trong mạng nội bộ, KHÔNG dùng tên miền/tunnel).

---

## PHẦN A — CÀI MỚI HOÀN TOÀN

### BƯỚC 1 — GitHub

1. Tạo repo **Public** tên `learn-data-server` (không tick tạo README).
2. Upload `repository.yaml`, `README.md` và thư mục `data_learn/`.
3. Mở `repository.yaml`, sửa `<TEN-GITHUB-CUA-BAN>` thành tên GitHub của bạn.

### BƯỚC 2 — Cài add-on trên Home Assistant

1. Settings → Add-ons → Add-on Store → ⋮ → **Repositories**
   → thêm `https://github.com/<tên-của-bạn>/learn-data-server`.
2. Tìm **Learn Data Server** → **Install** → **Start**.
3. Kiểm tra: tab Log có dòng `print-learn-server listening on :8765`;
   mở `http://IP-HASS:8765/health` (thay IP-HASS bằng IP máy HA) → `{"ok": true}`.

### BƯỚC 3 — rest_command (File Editor)

1. Mở `configuration.yaml`: kiểm tra CHƯA có khóa `rest_command:` nào,
   rồi thêm đúng 1 dòng: `rest_command: !include rest_command.yaml`
2. Tạo file mới tên đúng `rest_command.yaml` (cùng thư mục với
   configuration.yaml), dán toàn bộ file `rest_command.yaml` trong gói,
   rồi thay toàn bộ **IP-HASS** bằng IP LAN của máy HA.
3. **Restart hẳn Home Assistant** (rest_command chỉ nạp lúc khởi động,
   Reload YAML không ăn).
4. Developer Tools → Actions: phải thấy đủ **19 lệnh**:
   `print_learn_save`, `print_learn_lookup`, `print_learn_delete`,
   `print_log_save`, `print_log_query`, `print_log_update`,
   `print_log_delete_id`, `print_log_delete_date`,
   `bot_names_get`, `bot_names_replace`, `bot_names_add`, `bot_names_remove`,
   `memory_epoch_get`, `memory_epoch_bump`,
   `reminder_save`, `reminders_due_get`, `reminder_sent`,
   `reminders_list`, `reminder_delete`.
   Thiếu lệnh nào → file chưa đúng bản trong gói này, hoặc chưa Restart.

> Token (tùy chọn): nếu add-on có đặt `PRINT_BOT_TOKEN` thì trong file
> rest_command phải bỏ dấu `#` ở 2 dòng headers của **mọi** lệnh và điền
> đúng token. Thiếu ở lệnh nào thì lệnh đó bị 401 và bot "câm" phần đó.

### BƯỚC 4 — Hai automation

**Automation 1 (bot chính):** Settings → Automations → Create (hoặc mở bot
cũ) → ⋮ → **Edit in YAML** → Ctrl+A → dán `learn-data-bot-v8-2.yaml` → Save.

- Chỉ giữ **MỘT** automation bot trên webhook này; tắt/xóa mọi bản cũ
  (V7, V8, V8.1...) — chạy 2 bản là bot trả lời trùng / bay sang nhóm khác.
- Giữ nguyên `local_only: false` (Zalo gọi webhook từ xa).
- Thêm nhóm mới: trong `conditions:` của automation, thay `GROUP_ID_2`,
  `GROUP_ID_3`, `GROUP_ID_4` bằng ID thật của nhóm. Nhóm 1 đã có sẵn
  `5983799972549184973`.

**Automation 2 (gửi nhắc hẹn):** tạo thêm một automation mới, dán
`learn-data-bot-reminder-sender.yaml` → Save. Automation này chạy mỗi phút,
tới giờ hẹn là gửi tin nhắc vào đúng nhóm đã đặt lịch.

### BƯỚC 5 — Điều kiện cho tính năng ẢNH

1. Settings → Devices & services → Add integration → **Downloader**
   → thư mục tải: `/config/www`.
2. Trong `configuration.yaml`, gộp vào khóa `homeassistant:` sẵn có
   (KHÔNG tạo khóa `homeassistant:` thứ hai):

```yaml
homeassistant:
  media_dirs:
    zalo: /config/www/zalo_images
```

3. Restart HA 1 lần; mở Media phải thấy nguồn `zalo`.
   Ảnh gửi vào nhóm tải về đúng 1 file
   `/config/www/zalo_images/image_latest.jpg`, ảnh mới **ghi đè** ảnh cũ.

### BƯỚC 6 — Test nhanh

1. Gửi `E18` trong nhóm → ra nội dung gốc (kho 194 mã tĩnh).
2. `Lyly ơi, cho hỏi lỗi E18 là gì?` (không cần tag) → bot trả lời bắt đầu "Dạ".
3. Học mã: `Lyly học E999: Nội dung lỗi test - Kiểm tra nguồn` → ✅;
   gửi `E999` → ra mẫu chuẩn `❌ Mã lỗi E999: ...` / `🔧 Hướng xử lý: ...`;
   `Lyly sửa mã E999: Nội dung đã sửa - Cách xử lý mới` → ✅;
   `Lyly xóa học E999` → gửi lại `E999` → không còn bản đã học.
4. Nhật ký: `Lyly nhật ký: Máy DC4 - Thay Bơm Vaccum - Kênh 4 - 12/11/2026` → ✅;
   `Lyly tra nhật ký DC4` → thấy dòng vừa ghi.
5. Xóa ghi nhớ: `Lyly xóa ghi nhớ` → bot xác nhận đã xóa.
   (Nếu báo "Xóa ghi nhớ thất bại" → add-on chưa lên bản có memory-epoch.)
6. Đổi tên: `Lyly đổi tên thành Na Na, Ly Ly` → bot xác nhận danh sách tên.
7. Ảnh: gửi ảnh màn hình máy có mã lỗi → bot chỉ báo mã lỗi + nội dung lỗi,
   rồi gửi kèm nội dung mã trong kho nếu trùng. Ảnh bài toán → mỗi phép tính
   một dòng `số <dấu> số = kết quả đúng — Đúng/Sai`.
8. Lịch hẹn: `Lyly nhắc tôi sau 1 phút uống nước` → bot xác nhận đã đặt lịch,
   khoảng 1 phút sau bot gửi `⏰ Nhắc anh: uống nước` vào nhóm là đạt.

---

## PHẦN B — CÁCH DÙNG TRONG NHÓM

Gọi đúng tên bot (mặc định **Lyly**, hoặc tag @Aibot) rồi ra lệnh/hỏi.
Bot trả lời nhẹ nhàng, xưng em, gọi "anh", ngắn gọn đúng chủ đề.

- **Hỏi đáp:** `Lyly <câu hỏi bất kỳ>` — bot trả lời bằng AI, có nhớ ngữ
  cảnh trò chuyện của nhóm.
- **Tra mã lỗi:** gửi thẳng mã, ví dụ `E336`. Đã học thì ưu tiên bản đã học,
  không có mới tra kho 194 mã gốc.
- **Học / sửa mã (mọi thiết bị, mã chữ+số bất kỳ):**
  `Lyly học <MÃ>: <nội dung lỗi> - <hướng xử lý>` ·
  `Lyly sửa mã <MÃ>: <nội dung mới> - <hướng xử lý mới>` ·
  `Lyly xóa học <MÃ>`.
- **Nhật ký sửa chữa:** `Lyly nhật ký: Máy <tên máy> - Thay thiết bị <Y> -
  <Vị trí> - <Ngày dd/mm/yyyy>` (bỏ trống ngày = hôm nay; tên máy tự do:
  DC4, Dây chuyền 4, Máy in 2...). Cú pháp cũ bằng dấu `|` vẫn chạy.
  Tra cứu: `Lyly tra nhật ký <từ khóa>` / `Lyly lịch sử <thiết bị>`.
  Sửa: `Lyly sửa nhật ký #<id>: <phần cần sửa>`. Xóa: theo #id hoặc theo ngày.
- **Ảnh:** gửi ảnh vào nhóm, bot tự phân tích. Ảnh màn hình máy có báo lỗi:
  bot CHỈ báo mã lỗi + nội dung lỗi hiển thị (không mô tả nút bấm/biểu
  tượng/menu), trùng mã trong kho thì gửi kèm nội dung mã. Ảnh bài tập
  toán: bot chép phép tính, hệ thống tự chấm Đúng/Sai, mỗi dòng 1 phép tính.
- **Đổi tên bot (riêng từng nhóm):** `Lyly đổi tên thành A, B` ·
  `Lyly thêm tên X` · `Lyly xóa tên X`.
- **Xóa ghi nhớ trò chuyện:** `Lyly xóa ghi nhớ` (nhận cả `xóa trí nhớ`,
  `quên hết`) — bot quên toàn bộ ngữ cảnh cũ của nhóm.
- **Lịch hẹn nhắc nhở:** `Lyly nhắc tôi 9h uống nước` (giờ đã qua → tự sang
  ngày mai) · `9h30` · `sau 30 phút` · `2 phút sau` · `5 phút nữa` ·
  `ngày mai có 1 cuộc họp lúc 10 giờ, nhớ nhắc tôi` ·
  `ngày 20/11 lúc 8h họp phụ huynh`.
  Xem lịch: `Lyly lịch hẹn`. Hủy: `Lyly hủy lịch #<số>`.
  Tới giờ, automation sender gửi `⏰ Nhắc anh: <nội dung>` vào đúng nhóm.

Mỗi nhóm độc lập: kho mã đã học, nhật ký, tên bot, ghi nhớ và lịch hẹn
đều tách riêng theo nhóm; chỉ kho 194 mã gốc dùng chung.

---

## PHẦN C — CẬP NHẬT TỪ BẢN CŨ (giữ nguyên dữ liệu)

1. Đẩy lại thư mục gói này lên GitHub → Add-on **Learn Data Server** →
   **Update** lên **1.6.0** → Start (database tự nâng cấp, không mất dữ
   liệu học/nhật ký/tên/lịch đã có).
2. Thay `/config/rest_command.yaml` bằng file trong gói này (19 lệnh,
   nhớ thay IP-HASS) → **Restart hẳn Home Assistant** → kiểm tra đủ
   5 lệnh `reminder_*` / `reminders_*` trong Developer Tools → Actions.
3. Thay automation bot bằng `learn-data-bot-v8-2.yaml` (tắt/xóa bản cũ,
   chỉ để 1 bản chạy).
4. Nếu chưa có automation sender thì tạo thêm theo BƯỚC 4.
5. Test nhanh: mục 5, 6, 8 của BƯỚC 6.

Từ bản 1.4.0 / V6.6 trở về trước cũng làm đúng 5 bước trên (bản cũ dùng
file rest 12–14 lệnh nên bắt buộc thay file + Restart).

---

## PHẦN D — XỬ LÝ SỰ CỐ

- **Log báo `Action rest_command.<...> not found`** → HA chưa nạp file
  rest mới: thay đúng file `rest_command.yaml` trong gói này (nhớ thay
  IP-HASS) rồi **Restart hẳn HA**. Reload YAML không nạp được rest_command.
- **Bot báo "chưa lưu được / chưa đặt được lịch"** → mở Log của add-on:
  - `POST ... 400` → file rest_command sai bản (bản cũ từng lỗi mất ngoặc
    `{{ }}` ở payload) → dùng đúng file trong gói này.
  - `POST ... 401` → lệch token: kiểm tra headers X-Token ở mọi lệnh.
  - `POST ... 404` → add-on chưa lên 1.6.0 (endpoint chưa có) → Update add-on.
- **"Xóa ghi nhớ thất bại"** → add-on chưa lên ≥ 1.5.0, hoặc thiếu 2 lệnh
  `memory_epoch_*` (xem mục not found ở trên).
- **Đổi tên xong, gọi tên mới bot im lặng** → ra lệnh cứu bằng tag:
  `@Aibot đổi tên thành <tên đúng>` (tag không phụ thuộc danh sách tên).
- **Ảnh báo `Unknown source directory`** → thiếu `media_dirs: zalo:`
  (BƯỚC 5) → thêm rồi Restart HA.
- **Bot trả lời 2 lần, hoặc tin bay sang nhóm khác** → đang chạy 2 bản
  bot trên cùng webhook → chỉ giữ đúng 1 bản (V8.2).
- **Nhắc hẹn không tới** → kiểm tra automation sender có tồn tại và đang
  bật; xem Log add-on có dòng `GET /reminders/due 200` mỗi phút không.
