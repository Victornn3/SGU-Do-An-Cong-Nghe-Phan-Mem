import os
import uuid
from urllib.parse import quote
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient, ReturnDocument

app = FastAPI(title="Ticket Service", version="1.0.0")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "van_mieu")

# Địa chỉ trang User (Mặc định mở index.html)
# Khi test trên cùng máy tính hoặc qua Docker, để đường dẫn tương đối hoặc cổng web User
USER_WEB_BASE_URL = os.getenv("USER_WEB_BASE_URL", "http://localhost/index.html")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]


def generate_qr_url(ticket_code: str) -> str:
    """Tạo link ảnh QR code chứa đường dẫn mở thẳng trang web User kèm mã vé."""
    target_link = f"{USER_WEB_BASE_URL}?ticket={ticket_code}"
    # Mã hóa URL để đưa vào api qrserver an toàn
    encoded_data = quote(target_link, safe="")
    return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded_data}"


def format_ticket(ticket: dict) -> dict:
    """Định dạng bản ghi vé, chuyển ObjectId và datetime sang kiểu chuỗi an toàn và bổ sung qr_url."""
    if not ticket:
        return {}
    formatted = {**ticket}
    if "_id" in formatted:
        formatted["_id"] = str(formatted["_id"])
    if isinstance(formatted.get("created_at"), datetime):
        formatted["created_at"] = formatted["created_at"].isoformat()
    if isinstance(formatted.get("scanned_at"), datetime):
        formatted["scanned_at"] = formatted["scanned_at"].isoformat()

    # Luôn gắn qr_url chứa link User vào để Frontend hiển thị trực tiếp
    code = formatted.get("ticket_code") or formatted.get("code") or ""
    if code:
        formatted["qr_url"] = generate_qr_url(code)

    return formatted


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ticket-service"}


@app.get("/api/tickets")
def get_tickets(limit: int = 50):
    """Lấy danh sách các vé đã phát hành gần nhất để hiển thị trên Dashboard Admin."""
    raw_tickets = list(db.tickets.find().sort("created_at", -1).limit(limit))
    return {
        "success": True,
        "total": len(raw_tickets),
        "data": [format_ticket(t) for t in raw_tickets],
    }


@app.post("/api/tickets/create")
def create_ticket():
    """Tạo một mã vé mới duy nhất, lưu vào MongoDB và sinh URL mã QR chứa link web User."""
    ticket_code = f"VM-{uuid.uuid4().hex[:8].upper()}"
    now_utc = datetime.now(timezone.utc)

    ticket_doc = {
        "ticket_code": ticket_code,
        "is_used": False,
        "scanned_at": None,
        "created_at": now_utc,
    }

    db.tickets.insert_one(ticket_doc)

    return {
        "success": True,
        "ticket_code": ticket_code,
        "qr_url": generate_qr_url(ticket_code),
        "data": format_ticket(ticket_doc),
    }


@app.post("/api/tickets/scan/{ticket_code}")
def scan_ticket(ticket_code: str):
    """
    Xác minh và cập nhật trạng thái vé.
    Chỉ cho phép quét 1 lần đối với vé chưa sử dụng (Chống đếm trùng nguyên tử).
    """
    clean_code = ticket_code.strip().upper()
    now_utc = datetime.now(timezone.utc)

    result = db.tickets.find_one_and_update(
        {"ticket_code": clean_code, "is_used": False},
        {
            "$set": {
                "is_used": True,
                "scanned_at": now_utc,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    if not result:
        existing = db.tickets.find_one({"ticket_code": clean_code})
        if existing:
            return {
                "success": False,
                "message": f"Vé {clean_code} đã được quét trước đó vào lúc {existing.get('scanned_at')}!",
                "status": "already_used",
            }
        return {
            "success": False,
            "message": f"Mã vé {clean_code} không tồn tại trên hệ thống!",
            "status": "not_found",
        }

    return {
        "success": True,
        "message": "Quét vé hợp lệ. Xác nhận vào cổng thành công!",
        "status": "scanned_success",
        "ticket": format_ticket(result),
    }