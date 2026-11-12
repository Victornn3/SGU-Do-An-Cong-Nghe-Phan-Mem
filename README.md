# Văn Miếu – Quốc Tử Giám: ứng dụng thuyết minh tự động theo vị trí

Ứng dụng web thuyết minh đa ngôn ngữ (Việt, Anh, Trung, Hàn) cho khu di tích Văn Miếu – Quốc Tử Giám.
Khách mở web bằng điện thoại (quét mã QR in trên vé), ứng dụng nhận biết vị trí (GPS thật hoặc giả lập)
và tự phát bài thuyết minh khi khách bước vào vùng của từng điểm tham quan (geofence). Ban quản lý
dùng trang quản trị để sinh vé, quản lý điểm tham quan, nội dung thuyết minh và xem thống kê.

## Chạy hệ thống

Yêu cầu: Docker Desktop. Chạy trong thư mục dự án:

```bash
cp .env.example .env        # đổi JWT_SECRET và ADMIN_PASSWORD trước khi triển khai thật
docker compose up -d --build
```

| Địa chỉ | Dành cho |
|---|---|
| `http://localhost` | Khách tham quan |
| `http://localhost/admin.html` | Quản trị: thống kê, vé, báo cáo |
| `http://localhost/admin.html#poi` | Quản trị: điểm tham quan và nội dung thuyết minh (tab "Quản lý POI & Audio"; link cũ `admin-content.html` tự chuyển về đây) |

Tài khoản quản trị mặc định: `admin` / `admin123` (đổi trong `.env`, biến `ADMIN_PASSWORD`).
Dừng hệ thống: `docker compose down`.

## Cho mọi điện thoại quét được mã QR

Mã QR trên vé chứa đường dẫn `USER_WEB_BASE_URL?ticket=<mã vé>`. Mặc định là `http://localhost/index.html`,
chỉ mở được trên chính máy chạy Docker; điện thoại quét sẽ báo không vào được trang.
Để **bất kỳ điện thoại nào, ở bất kỳ mạng nào** cũng mở được, web phải có địa chỉ công khai trên Internet.
Cách nhanh cho demo là dùng [ngrok](https://ngrok.com) (gói miễn phí có sẵn 1 tên miền cố định dạng `ten-cua-ban.ngrok-free.app`):

```bash
brew install ngrok                       # cài một lần
ngrok config add-authtoken <TOKEN>       # token lấy ở dashboard.ngrok.com sau khi đăng ký
ngrok http 80                            # để cửa sổ này chạy suốt buổi demo
```

Lấy địa chỉ `https://....ngrok-free.app` mà ngrok in ra, sửa trong `.env`:

```
USER_WEB_BASE_URL=https://ten-cua-ban.ngrok-free.app/index.html
```

rồi chạy lại ticket-service để nhận cấu hình mới: `docker compose up -d --force-recreate ticket-service`.
Từ đó mã QR trong tab "Quản lý Vé & Quét Mã" trỏ về địa chỉ công khai; điện thoại nào quét cũng mở được trang khách,
và vì là `https` nên điện thoại dùng được cả GPS thật. Tên miền dev của ngrok không đổi khi khởi động lại, nên vé đã in vẫn dùng được.

Lưu ý: máy chạy Docker và ngrok phải đang bật thì QR mới mở được. Gói miễn phí của ngrok hiện một trang cảnh báo
ở lần đầu mở (bấm "Visit Site" là vào, trình duyệt nhớ 7 ngày) và giới hạn 1 GB dữ liệu mỗi tháng.
Muốn chạy lâu dài thì triển khai lên máy chủ có tên miền riêng và đặt `USER_WEB_BASE_URL` theo tên miền đó.
Nếu `USER_WEB_BASE_URL` vẫn là localhost, tab Vé sẽ hiện cảnh báo màu vàng.

## Kiến trúc

Các dịch vụ chạy trong cùng mạng Docker, khách chỉ đi qua cổng 80 (Nginx) và API Gateway.
Mỗi dịch vụ có **database MongoDB riêng**; khi cần dữ liệu của dịch vụ khác thì gọi qua API,
không đọc thẳng database của nhau.

| Dịch vụ | Cổng | Database | Dữ liệu |
|---|---|---|---|
| `frontend` (Nginx) | 80 | – | giao diện khách và quản trị |
| `api-gateway` | 8000 | – | kiểm tra JWT, phân quyền, chuyển yêu cầu |
| `auth-service` | 8001 | `vm_auth` | tài khoản quản trị (mật khẩu bcrypt) |
| `poi-service` | 8002 | `vm_poi` | điểm tham quan, danh mục ngôn ngữ |
| `narration-service` | 8003 | `vm_narration` | bài thuyết minh, trạng thái audio |
| `ticket-service` | 8004 | `vm_ticket` | vé STANDARD / PRIORITY, lượt quét |
| `statistics-service` | 8005 | `vm_stats` | phiên online, lượt truy cập, lịch sử vào điểm |

Dữ liệu mẫu (11 điểm, 4 ngôn ngữ, 11 bài thuyết minh) nằm trong `data/seed/` và được dịch vụ
`seed-data` nạp vào đúng database của từng dịch vụ mỗi lần chạy `docker compose up` (nạp lặp lại an toàn).

## Sinh lại file âm thanh (MP3)

File MP3 **không nằm trong repo** (thư mục `data/audio/` bị `.gitignore` chặn vì được sinh tự động).
Đủ bộ gồm 44 file: 11 điểm × 4 ngôn ngữ, lưu dạng `data/audio/<ngôn ngữ>/<mã điểm>.mp3`
(ví dụ `data/audio/ko/P03.mp3`). Muốn có lại đủ bộ, hệ thống đang chạy và có Internet (dùng Google TTS):

```bash
# 1. Lấy token quản trị
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Yêu cầu sinh toàn bộ audio (chạy nền, mất khoảng 1–3 phút)
curl -s -X POST http://localhost:8000/api/narrations/generate-all \
  -H "Authorization: Bearer $TOKEN"

# 3. Kiểm tra: phải ra 44
find data/audio -name "*.mp3" | wc -l
```

Sửa một bài thuyết minh ở tab "Quản lý POI & Audio" của `admin.html` thì audio của bài đó tự được sinh lại.
Nếu thiếu audio, giao diện khách hiện thông báo dự phòng, không phát nhầm ngôn ngữ khác.

## Kiểm thử

```bash
pip install pytest bcrypt
python3 -m pytest tests/ -q      # kiểm thử tự động (CI cũng chạy lệnh này)
./tests/smoke_api.sh             # thử nhanh các API khi hệ thống đang chạy
```

Bộ kiểm thử tự động gồm: kiểm tra dữ liệu POI, dữ liệu thuyết minh và ngôn ngữ, Haversine và
geofence (nạp `frontend/js/gps.js` bằng Node, cần Node để chạy nhóm này), bảo mật và vé.

## Tài liệu

- `docs/api-noi-dung.md`: API ngôn ngữ, điểm tham quan, thuyết minh
- `docs/architecture.md`: kiến trúc hệ thống
- `docs/api-ve-bao-mat.md`: API vé và bảo mật
- `docs/prd-ppt-phan-cua-han.md`: nội dung PRD/PPT phần khách và nội dung
