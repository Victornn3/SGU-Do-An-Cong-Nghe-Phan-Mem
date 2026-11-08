# Tài liệu Kiến trúc Hệ thống (Architecture Document) - TV2

## 1. Mô hình tổng thể (Microservices Architecture)
Hệ thống Thuyết minh Văn Miếu được thiết kế theo kiến trúc Microservices phân tán gồm các dịch vụ độc lập, giao tiếp thông qua mạng nội bộ Docker:

- Frontend (Nginx - Port 80): Phục vụ giao diện tĩnh cho khách (index.html) và ban quản lý (admin.html), định tuyến proxy /api vào API Gateway.
- API Gateway (FastAPI - Port 8000): Cửa ngõ duy nhất tiếp nhận request, chịu trách nhiệm xác thực JWT và kiểm soát phân quyền (Reverse Proxy).
- Auth Service (Port 8001): Quản lý định danh quản trị viên, băm mật khẩu chuẩn bcrypt và cấp phát JWT token.
- POI Service (Port 8002): Quản lý tọa độ, bán kính Geofence và danh mục 11 điểm di tích.
- Narration Service (Port 8003): Quản lý bài thuyết minh đa ngôn ngữ và tệp âm thanh audio.
- Ticket Service (Port 8004): Phát hành vé định danh VM-STD- / VM-PRI-, tạo mã QR và kiểm soát quét vé vào cổng.
- Statistics Service (Port 8005): Giám sát lưu lượng khách thời gian thực, lưu trữ phiên trực tuyến bền vững vào MongoDB (TTL Index).
- MongoDB (Port 27017): Cơ sở dữ liệu chính, đã đóng cổng ra ngoài mạng Internet để đảm bảo an toàn.

## 2. Luồng bảo mật & Phân quyền (Security Workflow)
- API Công khai (Public): Khách tham quan được phép truy cập tự do các API đọc (/api/pois, /api/narrations), quét mã vé (/api/tickets/scan/*), và gửi tọa độ GPS (/api/stats/*).
- API Quản trị (Protected): Mọi API thay đổi dữ liệu (/api/tickets/create, thêm sửa điểm, xem báo cáo) bắt buộc phải có Header:
  Authorization: Bearer <JWT_TOKEN>
  Nếu thiếu hoặc sai Token, API Gateway sẽ từ chối ngay với mã lỗi 401 Unauthorized.