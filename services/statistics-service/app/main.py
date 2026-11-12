import os
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import MongoClient, UpdateOne

app = FastAPI(title="Statistics Service", version="2.0.0")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "vm_stats")
TICKET_SERVICE_URL = os.getenv("TICKET_SERVICE_URL", "http://ticket-service:8004")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

SESSION_TIMEOUT_SECONDS = 25  # Quá 25 giây không có heartbeat thì coi như đã rời web
ALL_POIS = ["P00", "P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10"]


@app.on_event("startup")
def setup_indexes():
    """
    [M9] Tạo TTL Index trong MongoDB để lưu phiên bền vững.
    MongoDB sẽ tự động dọn các bản ghi hết hạn mà không làm nghẽn RAM ứng dụng.
    """
    try:
        db.active_sessions.create_index("last_seen", expireAfterSeconds=SESSION_TIMEOUT_SECONDS)
        db.active_sessions.create_index("session_id", unique=True)
        db.poi_history.create_index([("session_id", 1), ("poi_id", 1)])
    except Exception as e:
        print(f"Lưu ý tạo Index: {e}")


class VisitRecordRequest(BaseModel):
    session_id: str = Field(..., min_length=3, max_length=64)
    initial_mode: Optional[str] = "unknown"
    access_type: str = Field(..., max_length=32)
    is_real_visit: bool = False
    timestamp: Optional[str] = None


class SessionLocationPayload(BaseModel):
    session_id: str = Field(..., min_length=3, max_length=64)
    gps_mode: str = Field(default="SIMULATED", max_length=20)
    poi_id: Optional[str] = Field(None, max_length=10)
    inside_geofence: bool = False
    status: Optional[str] = Field(default="ACTIVE", max_length=10)
    timestamp: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "statistics-service"}


@app.post("/api/stats/session-location")
def update_session_location(data: SessionLocationPayload):
    """
    [M9] Cập nhật vị trí phiên online vào MongoDB (Bền vững, không mất khi restart server).
    """
    now_utc = datetime.now(timezone.utc)
    
    if data.status == "OFFLINE":
        # Khách chủ động tắt web hoặc thoát
        db.active_sessions.delete_one({"session_id": data.session_id})
        return {"success": True, "session_id": data.session_id, "status": "OFFLINE"}

    valid_poi = data.poi_id if (data.inside_geofence and data.poi_id in ALL_POIS) else None

    # Mỗi khách (session_id gắn với mã vé, xem getOrCreateSessionId ở frontend) chỉ được tính
    # MỘT lượt ghé cho mỗi điểm, dù ra vào lại, mở lại trang, quét lại vé hay dùng máy khác. Kiểm tra trong lịch sử (bền vững) chứ không
    # dựa vào active_sessions, vì bản ghi đó tự xóa sau 25 giây không có heartbeat.
    already_visited = bool(valid_poi) and db.poi_history.find_one(
        {"session_id": data.session_id, "poi_id": valid_poi}, {"_id": 1}
    ) is not None

    # Lưu / Cập nhật phiên trực tiếp vào MongoDB
    db.active_sessions.update_one(
        {"session_id": data.session_id},
        {
            "$set": {
                "session_id": data.session_id,
                "poi_id": valid_poi,
                "gps_mode": data.gps_mode,
                "inside_geofence": data.inside_geofence,
                "last_seen": now_utc,
            }
        },
        upsert=True
    )

    # Ghi nhận lượt ghé lần đầu khách này tới điểm này
    if valid_poi and not already_visited:
        db.poi_history.insert_one({
            "session_id": data.session_id,
            "poi_id": valid_poi,
            "created_at": now_utc
        })

    return {
        "success": True,
        "session_id": data.session_id,
        "current_poi": valid_poi,
    }


@app.get("/api/stats/poi-occupancy")
def get_poi_occupancy():
    """
    [M9] Đếm số khách thời gian thực tại từng POI từ MongoDB.
    Chỉ lấy các phiên có last_seen trong vòng 20 giây trở lại đây.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=SESSION_TIMEOUT_SECONDS)
    
    # Lấy danh sách phiên còn sống trong MongoDB
    active_docs = list(db.active_sessions.find({"last_seen": {"$gte": cutoff}}))
    
    counts = {poi: 0 for poi in ALL_POIS}
    for doc in active_docs:
        p_id = doc.get("poi_id")
        if p_id in counts:
            counts[p_id] += 1

    return counts


@app.post("/api/stats/visit")
def record_visit(data: VisitRecordRequest):
    """Ghi nhận lượt truy cập (Chống trùng session_id)"""
    existing_session = db.visits.find_one({"session_id": data.session_id})
    if existing_session:
        return {"success": True, "message": "Phiên đã tồn tại.", "updated": False}

    visit_doc = {
        "session_id": data.session_id,
        "initial_mode": data.initial_mode or "unknown",
        "access_type": data.access_type,
        "is_real_visit": data.is_real_visit,
        "created_at": datetime.now(timezone.utc),
    }
    db.visits.insert_one(visit_doc)
    return {"success": True, "session_id": data.session_id}


def fetch_ticket_summary(start=None, end=None) -> dict:
    """
    Lấy số liệu vé từ ticket-service qua API (bảng tickets thuộc database của ticket-service,
    statistics-service không đọc thẳng). Lỗi kết nối thì trả 0 và ghi log, không làm hỏng dashboard.
    """
    url = f"{TICKET_SERVICE_URL}/api/tickets/summary"
    if start and end:
        url += "?" + urllib.parse.urlencode({"start": start.isoformat(), "end": end.isoformat()})
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Không lấy được số liệu vé từ ticket-service: {e}")
        return {"total_created": 0, "total_scanned": 0, "standard_scanned": 0,
                "priority_scanned": 0, "scanned_in_range": 0}


@app.get("/api/stats/tickets")
def get_ticket_stats():
    """
    [M9] Thống kê vé duy nhất: Phân loại theo STANDARD và PRIORITY
    """
    summary = fetch_ticket_summary()
    total_created = summary["total_created"]
    total_scanned = summary["total_scanned"]
    standard_scanned = summary["standard_scanned"]
    priority_scanned = summary["priority_scanned"]

    scan_rate = round((total_scanned / total_created * 100), 2) if total_created > 0 else 0.0

    return {
        "total_tickets_created": total_created,
        "total_tickets_scanned": total_scanned,
        "standard_scanned": standard_scanned,
        "priority_scanned": priority_scanned,
        "scan_rate_percentage": scan_rate,
    }


@app.get("/api/stats/dashboard")
@app.get("/api/stats/overview")
def get_overview_dashboard(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    [M9] Cung cấp số liệu tổng hợp cho Dashboard và Báo cáo lịch sử
    """
    ticket_stats = get_ticket_stats()
    occupancy_stats = get_poi_occupancy()

    # Tính số khách online thời gian thực từ MongoDB
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=SESSION_TIMEOUT_SECONDS)
    online_visitors_count = db.active_sessions.count_documents({"last_seen": {"$gte": cutoff}})

    visit_filter = {}
    poi_history_filter = {}
    range_start = range_end = None

    if start_date and end_date:
        try:
            vn_tz = timezone(timedelta(hours=7))
            start_local = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=vn_tz)
            end_local = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=vn_tz)
            if start_local > end_local:
                raise ValueError("start_date phải trước hoặc cùng ngày với end_date")
            
            date_range = {"$gte": start_local.astimezone(timezone.utc), "$lte": end_local.astimezone(timezone.utc)}
            visit_filter["created_at"] = date_range
            # Số vé quét trong khoảng ngày do ticket-service tính (lọc first_accessed_at / scanned_at)
            range_start, range_end = date_range["$gte"], date_range["$lte"]
            poi_history_filter["created_at"] = date_range
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Khoảng ngày không hợp lệ: {exc}")

    # Thống kê lịch sử POI
    historical_poi_visits = {}
    for poi in ALL_POIS:
        f = {"poi_id": poi, **poi_history_filter}
        historical_poi_visits[poi] = db.poi_history.count_documents(f)

    total_historical_visits = db.visits.count_documents(visit_filter)
    ticket_summary = fetch_ticket_summary(range_start, range_end)
    total_tickets_scanned = ticket_summary["scanned_in_range"]
    total_tickets_created = ticket_summary["total_created"]
    scan_rate = round(total_tickets_scanned / total_tickets_created * 100, 2) if total_tickets_created else 0.0

    return {
        "success": True,
        "online_visitors": online_visitors_count,
        "total_tickets_created": total_tickets_created,
        "total_tickets_scanned": total_tickets_scanned,
        "standard_scanned": ticket_stats.get("standard_scanned", 0),
        "priority_scanned": ticket_stats.get("priority_scanned", 0),
        "scan_rate_percentage": scan_rate,
        "poi_occupancy": occupancy_stats,
        "historical_poi_visits": historical_poi_visits,
        "total_historical_visits": total_historical_visits,
        "tickets": ticket_stats,
    }