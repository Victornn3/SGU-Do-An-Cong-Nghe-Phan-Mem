import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI(title="Statistics Service", version="1.0.0")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "van_mieu")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

# Lưu phiên đang online thực tế: { "session_id": { "poi_id": "P00", "last_seen": timestamp } }
active_sessions: Dict[str, dict] = {}
SESSION_TIMEOUT_SECONDS = 20  # Quá 20 giây không có heartbeat thì coi như đã rời web


def clean_dead_sessions():
    """Tự động loại bỏ các phiên đã tắt trình duyệt hoặc rời trang"""
    now = time.time()
    dead = [s_id for s_id, info in active_sessions.items() if now - info.get("last_seen", 0) > SESSION_TIMEOUT_SECONDS]
    for s_id in dead:
        active_sessions.pop(s_id, None)


class VisitRecordRequest(BaseModel):
    session_id: str
    initial_mode: str | None = None
    access_type: str
    is_real_visit: bool = False
    timestamp: str | None = None


class SessionLocationPayload(BaseModel):
    session_id: str
    gps_mode: str
    poi_id: Optional[str] = None
    inside_geofence: bool
    status: Optional[str] = "ACTIVE"
    timestamp: Optional[str] = None


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "statistics-service"}


@app.post("/api/stats/session-location")
def update_session_location(data: SessionLocationPayload):
    """Cập nhật vị trí thời gian thực và chống đếm trùng lượt nghe tự động POI"""
    clean_dead_sessions()
    
    if data.status == "OFFLINE":
        active_sessions.pop(data.session_id, None)
    else:
        old_info = active_sessions.get(data.session_id, {})
        previous_poi = old_info.get("poi_id")
        valid_poi = data.poi_id if data.inside_geofence and data.poi_id else None

        # Mỗi session_id chỉ có một POI hiện tại. Nếu yêu cầu cũ đến trễ, bỏ qua để không ghi đè vị trí mới hơn.
        received_at = time.time()
        client_timestamp = data.timestamp
        if client_timestamp:
            try:
                parsed = datetime.fromisoformat(client_timestamp.replace("Z", "+00:00"))
                received_at = parsed.timestamp()
            except (ValueError, TypeError):
                pass

        if old_info.get("last_client_timestamp", 0) > received_at:
            old_info["last_seen"] = time.time()
            active_sessions[data.session_id] = old_info
            return {
                "success": True,
                "session_id": data.session_id,
                "current_poi": old_info.get("poi_id"),
                "ignored_stale_update": True,
            }

        # Cập nhật phiên hiện tại
        active_sessions[data.session_id] = {
            "poi_id": valid_poi,
            "last_seen": time.time(),
            "last_client_timestamp": received_at,
            "gps_mode": data.gps_mode,
        }

        # Chỉ ghi nhận vào poi_history khi phiên đi vào POI hợp lệ và đổi sang POI khác
        if valid_poi and valid_poi != previous_poi:
            db.poi_history.insert_one({
                "session_id": data.session_id,
                "poi_id": valid_poi,
                "created_at": datetime.now(timezone.utc)
            })

    return {
        "success": True,
        "session_id": data.session_id,
        "current_poi": active_sessions.get(data.session_id, {}).get("poi_id"),
    }


@app.get("/api/stats/poi-occupancy")
def get_poi_occupancy():
    """Trả về số người đang online thực tế tại từng POI (phục vụ Tab 1 thời gian thực)"""
    clean_dead_sessions()
    all_pois = ["P00", "P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10"]
    counts = {poi: 0 for poi in all_pois}

    for info in active_sessions.values():
        p_id = info.get("poi_id")
        if p_id in counts:
            counts[p_id] += 1

    return counts


@app.post("/api/stats/visit")
def record_visit(data: VisitRecordRequest):
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


@app.get("/api/stats/visits")
def get_visit_stats():
    total_visits = db.visits.count_documents({})
    demo_simulation = db.visits.count_documents({"access_type": "demo_simulation"})
    return {
        "success": True,
        "total_sessions": total_visits,
        "demo_simulation_visits": demo_simulation,
    }


@app.get("/api/stats/tickets")
def get_ticket_stats():
    total_created = db.tickets.count_documents({})
    total_scanned = db.tickets.count_documents({"is_used": True})
    scan_rate = round((total_scanned / total_created * 100), 2) if total_created > 0 else 0
    return {
        "total_tickets_created": total_created,
        "total_tickets_scanned": total_scanned,
        "scan_rate_percentage": scan_rate,
    }


@app.get("/api/stats/dashboard")
@app.get("/api/stats/overview")
def get_overview_dashboard(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """
    Cung cấp số liệu thời gian thực (Tab 1) và số liệu tích lũy, lọc theo ngày (Tab 4)
    """
    clean_dead_sessions()
    ticket_stats = get_ticket_stats()
    occupancy_stats = get_poi_occupancy()

    visit_filter = {}
    scanned_ticket_filter = {"is_used": True}
    poi_history_filter = {}
    if start_date and end_date:
        try:
            vn_tz = timezone(timedelta(hours=7))
            start_local = datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=vn_tz)
            end_local = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=vn_tz)
            if start_local > end_local:
                raise ValueError("start_date must be on or before end_date")
            date_range = {"$gte": start_local.astimezone(timezone.utc), "$lte": end_local.astimezone(timezone.utc)}
            visit_filter["created_at"] = date_range
            scanned_ticket_filter["scanned_at"] = date_range
            poi_history_filter["created_at"] = date_range
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Khoảng ngày không hợp lệ: {exc}")

    # Thống kê lịch sử ghé thăm tích lũy từng POI từ bảng poi_history
    historical_poi_visits = {}
    all_pois = ["P00", "P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10"]
    for poi in all_pois:
        f = {"poi_id": poi, **poi_history_filter}
        historical_poi_visits[poi] = db.poi_history.count_documents(f)

    total_historical_visits = db.visits.count_documents(visit_filter if visit_filter else {})
    total_tickets_scanned = db.tickets.count_documents(scanned_ticket_filter)
    total_tickets_created = db.tickets.count_documents({})
    scan_rate = round(total_tickets_scanned / total_tickets_created * 100, 2) if total_tickets_created else 0
    online_visitors_count = len(active_sessions)

    return {
        "success": True,
        "online_visitors": online_visitors_count,  # Dành cho Tab 1 (nhảy số tức thì, thoát về 0)
        "total_tickets_created": total_tickets_created,
        "total_tickets_scanned": total_tickets_scanned,
        "scan_rate_percentage": scan_rate,
        "poi_occupancy": occupancy_stats,
        "historical_poi_visits": historical_poi_visits,  # Dành cho Tab 4 (lịch sử POI)
        "total_historical_visits": total_historical_visits, # Dành cho Tab 4 (tổng khách tích lũy)
        "tickets": ticket_stats,
    }