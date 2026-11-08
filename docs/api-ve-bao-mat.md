# Đặc tả API Vé và Bảo mật (API Specification) - TV2

## 1. Authentication Service (/api/auth)

### 1.1 Đăng nhập quản trị viên
- Endpoint: POST /api/auth/login
- Body yêu cầu:
  {
    "username": "admin",
    "password": "admin123"
  }
- Cơ chế xác thực: So khớp mật khẩu băm bcrypt trong collection db.admins.
- Phản hồi thành công (HTTP 200):
  {
    "success": true,
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "username": "admin"
  }

---

## 2. Ticket Service (/api/tickets)

### 2.1 Phát hành vé mới (Yêu cầu quyền Admin)
- Endpoint: POST /api/tickets/create
- Header: Authorization: Bearer <token>
- Body yêu cầu:
  {
    "ticket_type": "STANDARD" // hoặc "PRIORITY"
  }
- Quy chuẩn mã vé:
  - Vé thường: VM-STD-xxxxxx (6 ký tự chữ/số ngẫu nhiên)
  - Vé ưu tiên: VM-PRI-xxxxxx (6 ký tự chữ/số ngẫu nhiên)
- Phản hồi: Trả về mã vé và qr_url để in lên phôi vé giấy.

### 2.2 Quét vé vào cổng (Khách quét mã QR)
- Endpoint: POST /api/tickets/scan/{ticket_code}
- Header: Không yêu cầu (Public)
- Cơ chế hoạt động:
  - Quét lần đầu: Ghi nhận is_used = true, lưu thời điểm first_accessed_at và last_accessed_at.
  - Quét lại (Reload trang): Cập nhật last_accessed_at, trả về status: re_access, cho phép tiếp tục sử dụng bình thường.
  - Mã sai định dạng: Chặn ngay bằng Regex và trả về lỗi invalid_format.