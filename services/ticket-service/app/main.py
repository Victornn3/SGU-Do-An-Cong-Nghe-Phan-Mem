import os
import re
import uuid
from urllib.parse import quote
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import MongoClient, ReturnDocument

app = FastAPI(title="Ticket Service", version="2.0.0")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "van_mieu")
USER_WEB_BASE_URL = os.getenv("USER_WEB_BASE_URL", "http://localhost/index.html")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

# Regex kiểm tra định dạng vé chuẩn: VM-STD-xxxxxx hoặc VM-PRI-xxxxxx (6 ký tự chữ/số)
TICKET_CODE_REGEX = re.compile(r"^VM-(STD|PRI)-[A-Z0-9]{6}$")

# Map loại vé sang tiền tố
TICKET_PREFIX_MAP = {
    "STANDARD": "STD",
    "PRIORITY": "PRI"
}


class CreateTicketRequest(BaseModel):
    ticket_type: str = Field(default="STANDARD", description="Loại vé: STANDARD hoặc PRIORITY")


def generate_qr_url(ticket_code: str) -> str:
    """Tạo link ảnh QR code chứa đường dẫn mở thẳng trang web User kèm mã vé."""
    target_link = f"{USER_WEB_BASE_URL}?ticket={ticket_code}"
    encoded_data = quote(target_link, safe="")
    return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded_data}"


def format_ticket(ticket: dict) -> dict:
    """Định dạng bản ghi vé an toàn để trả về qua JSON."""
    if not ticket:
        return {}
    formatted = {**ticket}
    if "_id" in formatted:
        formatted["_id"] = str(formatted["_id"])
    
    # Định dạng các trường thời gian
    for time_col in ["created_at", "first_accessed_at", "last_accessed_at"]:
        if isinstance(formatted.get(time_col), datetime):
            formatted[time_col] = formatted[time_col].isoformat()

    code = formatted.get("ticket_code", "")
    if code:
        formatted["qr_url"] = generate_qr_url(code)

    return formatted


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ticket-service"}


@app.get("/api/tickets")
def get_tickets(limit: int = 50):
    """Lấy danh sách các vé gần nhất."""
    raw_tickets = list(db.tickets.find().sort("created_at", -1).limit(limit))
    return {
        "success": True,
        "total": len(raw_tickets),
        "data": [format_ticket(t) for t in raw_tickets],
    }


@app.post("/api/tickets/create")
def create_ticket(payload: Optional[CreateTicketRequest] = None):
    """
    [M5] Tạo mã vé theo chuẩn VM-STD-xxxxxx hoặc VM-PRI-xxxxxx
    """
    ticket_type = (payload.ticket_type if payload else "STANDARD").upper().strip()
    if ticket_type not in TICKET_PREFIX_MAP:
        raise HTTPException(
            status_code=400, 
            detail=f"Loại vé '{ticket_type}' không hợp lệ. Chỉ chấp nhận STANDARD hoặc PRIORITY."
        )

    prefix = TICKET_PREFIX_MAP[ticket_type]
    random_str = uuid.uuid4().hex[:6].upper()
    ticket_code = f"VM-{prefix}-{random_str}"
    
    now_utc = datetime.now(timezone.utc)

    ticket_doc = {
        "ticket_code": ticket_code,
        "ticket_type": ticket_type,
        "is_used": False,
        "first_accessed_at": None,
        "last_accessed_at": None,
        "created_at": now_utc,
    }

    db.tickets.insert_one(ticket_doc)

    return {
        "success": True,
        "ticket_code": ticket_code,
        "ticket_type": ticket_type,
        "qr_url": generate_qr_url(ticket_code),
        "data": format_ticket(ticket_doc),
    }


@app.post("/api/tickets/scan/{ticket_code}")
def scan_ticket(ticket_code: str):
    """
    [M5 & M6] Xác thực và quét vé:
    - Kiểm tra đúng định dạng VM-STD-... hoặc VM-PRI-...
    - Lần đầu: ghi nhận first_accessed_at và last_accessed_at.
    - Quét lại: CHỈ cập nhật last_accessed_at, vẫn cho phép vào (không báo lỗi).
    """
    clean_code = ticket_code.strip().upper()

    # 1. Kiểm tra định dạng mã vé
    if not TICKET_CODE_REGEX.match(clean_code):
        return {
            "success": False,
            "status": "invalid_format",
            "message": f"Mã vé '{clean_code}' sai định dạng (Chuẩn: VM-STD-xxxxxx hoặc VM-PRI-xxxxxx)!",
        }

    now_utc = datetime.now(timezone.utc)

    # 2. Tìm vé trong cơ sở dữ liệu
    ticket = db.tickets.find_one({"ticket_code": clean_code})
    if not ticket:
        return {
            "success": False,
            "status": "not_found",
            "message": f"Mã vé '{clean_code}' không tồn tại trên hệ thống!",
        }

    # 3. Xử lý quét lần đầu vs quét lại (M6)
    if not ticket.get("is_used"):
        # Lần đầu tiên vào cổng
        updated_ticket = db.tickets.find_one_and_update(
            {"ticket_code": clean_code},
            {
                "$set": {
                    "is_used": True,
                    "first_accessed_at": now_utc,
                    "last_accessed_at": now_utc,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return {
            "success": True,
            "status": "first_access",
            "message": f"Chào mừng bạn lần đầu đến Văn Miếu ({ticket.get('ticket_type', 'STANDARD')})!",
            "ticket": format_ticket(updated_ticket),
        }
    else:
        # Khách quét lại hoặc refresh trang web
        updated_ticket = db.tickets.find_one_and_update(
            {"ticket_code": clean_code},
            {
                "$set": {
                    "last_accessed_at": now_utc,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        return {
            "success": True,
            "status": "re_access",
            "message": f"Chào mừng bạn quay trở lại ({ticket.get('ticket_type', 'STANDARD')})!",
            "ticket": format_ticket(updated_ticket),
        }