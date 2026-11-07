# Tài liệu API – phần nội dung và khách tham quan

Mọi API đi qua gateway (`http://localhost/api/...` khi chạy Docker). Dữ liệu trả về dạng JSON, tiếng Việt có dấu (UTF-8).

**Quy ước xác thực:** API **đọc** của khách không cần token. API **ghi** (POST/PUT/PATCH/DELETE) và `GET /api/pois/admin/all` cần header `Authorization: Bearer <token>`; việc kiểm tra token do gateway thực hiện (phần của Người 2). Trang quản trị lấy token từ `localStorage.admin_token` sau khi đăng nhập ở `admin.html`.

## 1. Ngôn ngữ

### GET `/api/languages`
Danh mục ngôn ngữ đang bật, dùng để dựng ô chọn ngôn ngữ và chuỗi giao diện. Thêm ngôn ngữ mới chỉ cần thêm một bản ghi vào `data/seed/languages.json` rồi chạy lại seed, không phải sửa code.

| Tham số | Kiểu | Mặc định | Ý nghĩa |
|---|---|---|---|
| `include_inactive` | bool | `false` | `true` để lấy cả ngôn ngữ đang tắt |

Phản hồi 200:
```json
{
  "success": true,
  "data": [
    {
      "code": "vi", "name": "Vietnamese", "native_name": "Tiếng Việt", "flag": "🇻🇳",
      "html_lang": "vi", "tts_locale": "vi", "display_order": 1, "is_active": true,
      "ui": { "status.insideGeofence": "Đã vào vùng Geofence: {code} - {poi} ({dist}m)", "...": "..." }
    }
  ]
}
```
`ui` chứa các chuỗi giao diện; `{radius}`, `{count}`, `{poi}`… là chỗ giữ chỗ để giao diện điền giá trị.

## 2. POI cho khách

### GET `/api/pois`
Chỉ trả POI có `status = PUBLISHED`, sắp theo `display_order`. POI `DRAFT` hoặc `HIDDEN` không xuất hiện.

Phản hồi 200 (rút gọn một phần tử):
```json
{
  "success": true,
  "data": [{
    "_id": "P00", "poi_code": "P00", "name": "Cổng Văn Miếu",
    "latitude": 21.027526, "longitude": 105.835622, "geofence_radius": 15,
    "status": "PUBLISHED", "coordinate_status": "verified",
    "display_order": 0, "image_url": "/images/poi_P00_cong_van_mieu.jpg",
    "translations": {
      "vi": { "name": "Cổng Văn Miếu", "description": "..." },
      "en": { "name": "Van Mieu Gate", "description": "..." },
      "zh": { "name": "文庙门", "description": "..." }
    }
  }]
}
```

### GET `/api/pois/{poi_code}`
Chi tiết một POI đã xuất bản, ví dụ `/api/pois/P00`.

| Mã | Khi nào |
|---|---|
| 200 | Có POI và đang PUBLISHED |
| 404 | Không có mã đó, hoặc POI đang DRAFT/HIDDEN |

## 3. Thuyết minh và audio

### GET `/api/narrations/{poi_code}?lang={mã_ngôn_ngữ}`
`lang` mặc định `vi`. Hệ thống **không tự đổi sang ngôn ngữ khác**: thiếu nội dung hoặc audio thì báo rõ để giao diện hiện thông báo.

Phản hồi 200:
```json
{
  "poi_id": "P00", "title": "Cổng Văn Miếu — ...", "lang": "en",
  "content": "Welcome to ...", "content_available": true,
  "audio_url": "/audio/en/P00.mp3", "audio_available": true,
  "audio_status": "completed"
}
```
Khi thiếu: `content` là `null` và `content_available` là `false`; `audio_url` là `null` và `audio_available` là `false`. Giao diện khi đó hiện "Nội dung đang cập nhật" hoặc "Chưa có audio cho ngôn ngữ này" và vô hiệu hóa nút phát.

| Mã | Khi nào |
|---|---|
| 200 | Thành công (kể cả khi thiếu nội dung/audio, xem cờ `*_available`) |
| 404 | Ngôn ngữ không có trong bảng `languages`, hoặc không có thuyết minh cho POI |

### POST `/api/narrations` (cần token)
Lưu nội dung thuyết minh theo ngôn ngữ và tạo MP3 ở nền (gTTS).
```json
{ "poi_id": "P00", "title": "Tiêu đề", "contents": { "vi": "Nội dung...", "en": "Content..." } }
```
| Mã | Khi nào |
|---|---|
| 200 | Đã lưu, MP3 đang được tạo |
| 400 | Có mã ngôn ngữ chưa khai báo |
| 422 | `contents` rỗng |

### POST `/api/narrations/generate-all` (cần token)
Tạo lại MP3 cho mọi POI và mọi ngôn ngữ đang bật. 400 nếu chưa có dữ liệu thuyết minh.

## 4. Quản lý POI (cho admin, cần token)

Trạng thái POI: `DRAFT` (nháp) → `PUBLISHED` (hiện cho khách) ↔ `HIDDEN` (ẩn).

### GET `/api/pois/admin/all`
Tất cả POI ở mọi trạng thái, cùng định dạng như `/api/pois`.

### POST `/api/pois`
Tạo POI mới, luôn ở trạng thái `DRAFT`.
```json
{
  "poi_code": "P11", "latitude": 21.0285, "longitude": 105.8359, "geofence_radius": 15,
  "translations": { "vi": { "name": "Tên", "description": "Mô tả" }, "en": { "name": "Name", "description": "Desc" } }
}
```
Quy tắc: `poi_code` duy nhất; `geofence_radius` từ 10 đến 25 m (mặc định 15); tọa độ nằm trong khu vực Hà Nội; `translations.vi.name` bắt buộc; chỉ nhận mã ngôn ngữ có trong bảng `languages`; thiếu bản dịch khác vẫn hợp lệ.

| Mã | Khi nào |
|---|---|
| 201 | Tạo thành công |
| 409 | `poi_code` đã tồn tại |
| 422 | Dữ liệu sai quy tắc (thông điệp nằm trong `detail`) |

### PUT `/api/pois/{poi_code}`
Cập nhật một phần: chỉ trường có gửi lên mới được kiểm tra và ghi. Không đổi được `poi_code`. Mã trả về: 200, 404, 422.

### PATCH `/api/pois/{poi_code}/status`
```json
{ "status": "PUBLISHED" }
```
Giá trị hợp lệ: `DRAFT`, `PUBLISHED`, `HIDDEN`. POI `HIDDEN` biến mất khỏi `/api/pois` ngay lập tức. Mã trả về: 200, 404, 422.

### DELETE `/api/pois/{poi_code}`
Xóa mềm: chuyển POI sang `HIDDEN`, **không** xóa dữ liệu khỏi cơ sở dữ liệu. Mã trả về: 200, 404.

## 5. API đã bỏ
`GET /api/zones` đã bị loại. Hệ thống dùng danh sách phẳng 11 POI, không còn khái niệm cụm.

## 6. Lưu ý vận hành
- Chạy lại `seed-data` sẽ **ghi đè** các POI có trong `pois.json` (kể cả trạng thái và nội dung đã sửa qua trang admin). POI tạo thêm qua admin không bị xóa.
- `coordinate_status = verified`: tọa độ đã được đối chiếu trên Google Maps (chưa đo GPS tại hiện trường). `pending_field_verification` là giá trị mặc định của điểm mới tạo qua API, chưa được đối chiếu.

## 7. Quyền truy cập tại gateway (do Người 2 cài, JWT)
- **Công khai (không cần token):** `GET /api/languages`, `GET /api/pois`, `GET /api/pois/{poi_code}`, `GET /api/narrations/{poi_code}`.
- **Cần token quản trị (`Authorization: Bearer <token>`):** `GET /api/pois/admin/all`, `POST/PUT/PATCH/DELETE /api/pois…`, `POST /api/narrations`, `POST /api/narrations/generate-all`.
- Lấy token: `POST /api/auth/login` (xem tài liệu của Người 2). Trang `admin-content.html` dùng token do `admin.html` lưu trong `localStorage` với khóa `admin_token`.
- Ví dụ sinh audio khi gateway đã bật JWT:
  `curl -X POST http://localhost:8000/api/narrations/generate-all -H "Authorization: Bearer <token>"`
- Giao diện khách gọi `VMTicketGate.verify()` (file `ticket-gate.js` của Người 2) trước khi nạp dữ liệu; vé không hợp lệ thì bị chặn, bấm "Chế độ Demo" thì vào thẳng.
