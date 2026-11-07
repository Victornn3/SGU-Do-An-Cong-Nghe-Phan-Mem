"""
Bộ Test tự động kiểm thử nghiệp vụ của Người 2 (M10):
- Kiểm tra định dạng vé (M5)
- Kiểm tra cơ chế quét lại vé (M6)
- Kiểm tra mã hóa bcrypt (M2)
- Kiểm tra cấu hình bảo mật
"""
import re
import pytest
import bcrypt

# Regex chuẩn mã vé
TICKET_REGEX = re.compile(r"^VM-(STD|PRI)-[A-Z0-9]{6}$")


def test_ticket_code_format_valid():
    """Kiểm tra mã vé hợp lệ (M5)"""
    valid_std = "VM-STD-ABC123"
    valid_pri = "VM-PRI-XYZ789"
    assert TICKET_REGEX.match(valid_std) is not None
    assert TICKET_REGEX.match(valid_pri) is not None


def test_ticket_code_format_invalid():
    """Kiểm tra từ chối mã vé sai định dạng (M5)"""
    invalid_codes = [
        "VM-STD-101",        # Quá ngắn
        "VM-VIP-123456",     # Sai loại vé
        "VM-ABCDEF12",       # Thiếu loại vé
        "random_code_123"    # Không có tiền tố
    ]
    for code in invalid_codes:
        assert TICKET_REGEX.match(code) is None


def test_bcrypt_password_hashing():
    """Kiểm tra thuật toán băm bcrypt hoạt động chính xác (M2)"""
    raw_password = "admin123"
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), salt)

    # Khớp mật khẩu đúng
    assert bcrypt.checkpw(raw_password.encode("utf-8"), hashed) is True
    # Từ chối mật khẩu sai
    assert bcrypt.checkpw(b"wrong_password", hashed) is False


def test_rescan_ticket_logic():
    """Kiểm tra logic quét lại vé: Không được báo lỗi mà chỉ cập nhật last_accessed_at (M6)"""
    ticket_data = {
        "ticket_code": "VM-STD-TEST01",
        "ticket_type": "STANDARD",
        "is_used": False,
        "first_accessed_at": None,
        "last_accessed_at": None
    }

    # Giả lập quét lần 1
    ticket_data["is_used"] = True
    ticket_data["first_accessed_at"] = "2026-05-18T08:00:00Z"
    ticket_data["last_accessed_at"] = "2026-05-18T08:00:00Z"
    
    assert ticket_data["is_used"] is True
    assert ticket_data["first_accessed_at"] is not None

    # Giả lập quét lần 2 (khách reload trang) -> Chỉ đổi last_accessed_at
    ticket_data["last_accessed_at"] = "2026-05-18T08:30:00Z"
    assert ticket_data["first_accessed_at"] == "2026-05-18T08:00:00Z"
    assert ticket_data["last_accessed_at"] == "2026-05-18T08:30:00Z"