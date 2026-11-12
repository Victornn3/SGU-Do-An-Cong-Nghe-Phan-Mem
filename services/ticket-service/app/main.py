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
MONGO_DB = os.getenv("MONGO_DATABASE", "vm_ticket")
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


CANCEL_REASONS = ("PRINT_ERROR", "LOST", "REFUNDED", "OTHER")


class CancelTicketRequest(BaseModel):
    reason: str = Field(default="OTHER", description="PRINT_ERROR | LOST | REFUNDED | OTHER")
    note: str = Field(default="", max_length=200, description="Ghi chú thêm (không bắt buộc)")


class CreateTicketRequest(BaseModel):
    ticket_type: str = Field(default="STANDARD", description="Loại vé: STANDARD hoặc PRIORITY")


def ticket_link(ticket_code: str) -> str:
    """Đường dẫn trang khách kèm mã vé, là nội dung nằm trong mã QR.
    Muốn điện thoại ở bất kỳ đâu quét được thì USER_WEB_BASE_URL phải là địa chỉ
    công khai (vd https://ten-cua-ban.ngrok-free.app/index.html), không phải localhost."""
    return f"{USER_WEB_BASE_URL}?ticket={quote(ticket_code, safe='')}"


def generate_qr_url(ticket_code: str) -> str:
    """Tạo link ảnh QR code chứa đường dẫn mở thẳng trang web User kèm mã vé."""
    encoded_data = quote(ticket_link(ticket_code), safe="")
    return f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded_data}"


def format_ticket(ticket: dict) -> dict:
    """Định dạng bản ghi vé an toàn để trả về qua JSON."""
    if not ticket:
        return {}
    formatted = {**ticket}
    if "_id" in formatted:
        formatted["_id"] = str(formatted["_id"])
    
    # Định dạng các trường thời gian
    for time_col in ["created_at", "first_accessed_at", "last_accessed_at", "cancelled_at"]:
        value = formatted.get(time_col)
        if isinstance(value, datetime):
            # MongoDB lưu giờ UTC nhưng pymongo trả về datetime không kèm múi giờ.
            # Gắn rõ UTC (+00:00) để trình duyệt đổi đúng sang giờ Việt Nam,
            # nếu không trình duyệt sẽ hiểu nhầm đó là giờ địa phương (lệch 7 tiếng).
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            formatted[time_col] = value.isoformat()

    code = formatted.get("ticket_code", "")
    if code:
        formatted["qr_url"] = generate_qr_url(code)
        formatted["ticket_link"] = ticket_link(code)

    return formatted


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ticket-service"}


def next_ticket_no() -> int:
    """Số thứ tự vé tăng dần (1, 2, 3...), lấy từ bộ đếm riêng nên không trùng kể cả khi xóa vé."""
    counter = db.counters.find_one_and_update(
        {"_id": "ticket_no"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return counter["seq"]


def backfill_ticket_numbers():
    """Vé tạo trước khi có số thứ tự: đánh số theo thời gian tạo, tiếp sau số lớn nhất hiện có."""
    last = db.tickets.find_one({"ticket_no": {"$exists": True}}, sort=[("ticket_no", -1)])
    current = (last or {}).get("ticket_no", 0)
    counter = db.counters.find_one({"_id": "ticket_no"}) or {}
    current = max(current, counter.get("seq", 0))
    for ticket in db.tickets.find({"ticket_no": {"$exists": False}}).sort("created_at", 1):
        current += 1
        db.tickets.update_one({"_id": ticket["_id"]}, {"$set": {"ticket_no": current}})
    db.counters.update_one({"_id": "ticket_no"}, {"$max": {"seq": current}}, upsert=True)


@app.on_event("startup")
def setup_indexes():
    """Bảng tickets thuộc ticket-service nên chỉ service này tạo chỉ mục."""
    try:
        db.tickets.create_index("ticket_code", unique=True)
        db.tickets.create_index("first_accessed_at")
        db.tickets.create_index("ticket_no")
        backfill_ticket_numbers()
    except Exception as e:
        print(f"Lưu ý tạo Index: {e}")


@app.get("/api/tickets/summary")
def get_ticket_summary(start: Optional[str] = None, end: Optional[str] = None):
    """
    Số liệu tổng hợp vé cho statistics-service (gọi qua API thay vì đọc thẳng bảng tickets).
    start/end (ISO 8601, có múi giờ) chỉ dùng để đếm số vé quét lần đầu trong khoảng đó.
    """
    # Vé đã hủy không tính là vé phát hành (tỷ lệ quét chỉ tính trên vé còn hiệu lực)
    total_cancelled = db.tickets.count_documents({"is_cancelled": True})
    total_created = db.tickets.count_documents({"is_cancelled": {"$ne": True}})
    total_scanned = db.tickets.count_documents({"is_used": True})
    standard_scanned = db.tickets.count_documents({"is_used": True, "ticket_type": "STANDARD"})
    priority_scanned = db.tickets.count_documents({"is_used": True, "ticket_type": "PRIORITY"})

    scanned_in_range = total_scanned
    if start and end:
        try:
            date_range = {"$gte": datetime.fromisoformat(start), "$lte": datetime.fromisoformat(end)}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Khoảng thời gian không hợp lệ: {exc}")
        scanned_in_range = db.tickets.count_documents({
            "is_used": True,
            "$or": [{"first_accessed_at": date_range}, {"scanned_at": date_range}],
        })

    return {
        "total_created": total_created,
        "total_cancelled": total_cancelled,
        "total_scanned": total_scanned,
        "standard_scanned": standard_scanned,
        "priority_scanned": priority_scanned,
        "scanned_in_range": scanned_in_range,
    }


@app.get("/api/tickets")
def get_tickets(limit: int = 50):
    """Lấy danh sách các vé gần nhất (vé mới tạo, số thứ tự lớn nằm trên)."""
    limit = max(1, min(limit, 1000))
    raw_tickets = list(db.tickets.find().sort([("ticket_no", -1), ("created_at", -1)]).limit(limit))
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
        "ticket_no": next_ticket_no(),
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

    # 3. Vé đã bị hủy (in lỗi, mất vé, khách trả vé...): không cho vào, hướng dẫn ra quầy
    if ticket.get("is_cancelled"):
        return {
            "success": False,
            "status": "cancelled",
            "message": f"Vé '{clean_code}' đã bị hủy. Vui lòng liên hệ quầy vé để được hỗ trợ.",
        }

    # 4. Xử lý quét lần đầu vs quét lại (M6)
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


def find_ticket_or_404(ticket_code: str) -> dict:
    clean_code = ticket_code.strip().upper()
    ticket = db.tickets.find_one({"ticket_code": clean_code})
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy vé {clean_code}")
    return ticket


@app.post("/api/tickets/{ticket_code}/cancel")
def cancel_ticket(ticket_code: str, payload: Optional[CancelTicketRequest] = None):
    """
    Hủy vé (không xóa): vé in lỗi, mất vé, khách trả vé... Bản ghi vẫn được giữ
    cùng thời gian và lý do để đối soát; quét vé đã hủy sẽ bị từ chối.
    Chỉ hủy được vé CHƯA QUÉT, để số liệu lượt khách không bị sai.
    """
    payload = payload or CancelTicketRequest()
    reason = payload.reason.strip().upper()
    if reason not in CANCEL_REASONS:
        raise HTTPException(status_code=400, detail="Lý do hủy phải là: " + ", ".join(CANCEL_REASONS))
    ticket = find_ticket_or_404(ticket_code)
    if ticket.get("is_used"):
        raise HTTPException(
            status_code=409,
            detail=f"Vé {ticket['ticket_code']} đã được quét nên không thể hủy (giữ để thống kê lượt khách đúng).",
        )
    if ticket.get("is_cancelled"):
        raise HTTPException(status_code=409, detail=f"Vé {ticket['ticket_code']} đã bị hủy trước đó.")
    updated = db.tickets.find_one_and_update(
        {"_id": ticket["_id"]},
        {"$set": {
            "is_cancelled": True,
            "cancelled_at": datetime.now(timezone.utc),
            "cancel_reason": reason,
            "cancel_note": payload.note.strip(),
        }},
        return_document=ReturnDocument.AFTER,
    )
    return {"success": True, "message": f"Đã hủy vé {ticket['ticket_code']}.", "data": format_ticket(updated)}


@app.post("/api/tickets/{ticket_code}/restore")
def restore_ticket(ticket_code: str):
    """Khôi phục vé đã hủy nhầm: vé dùng lại được như bình thường."""
    ticket = find_ticket_or_404(ticket_code)
    if not ticket.get("is_cancelled"):
        raise HTTPException(status_code=409, detail=f"Vé {ticket['ticket_code']} chưa bị hủy.")
    updated = db.tickets.find_one_and_update(
        {"_id": ticket["_id"]},
        {"$set": {"is_cancelled": False},
         "$unset": {"cancelled_at": "", "cancel_reason": "", "cancel_note": ""}},
        return_document=ReturnDocument.AFTER,
    )
    return {"success": True, "message": f"Đã khôi phục vé {ticket['ticket_code']}.", "data": format_ticket(updated)}
