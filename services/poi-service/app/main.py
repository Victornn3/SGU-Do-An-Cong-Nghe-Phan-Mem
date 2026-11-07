import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

from .validation import ValidationError, build_poi_fields, validate_status

app = FastAPI(title="POI & GPS Service", version="1.1.0")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "van_mieu")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]


def format_poi(doc: dict) -> dict:
    """Chuyển đổi _id sang chuỗi string an toàn cho JSON serialization."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "poi-service"}


@app.get("/api/languages")
def get_languages(include_inactive: bool = False):
    """
    Danh mục ngôn ngữ (dữ liệu cấu hình). Giao diện khách đọc danh sách này để
    dựng ô chọn ngôn ngữ và chuỗi giao diện, nên thêm ngôn ngữ mới chỉ cần
    thêm một bản ghi vào collection `languages`, không phải sửa code.
    """
    query = {} if include_inactive else {"is_active": True}
    languages = list(db.languages.find(query).sort("display_order", 1))
    for lang in languages:
        lang.pop("_id", None)
    return {"success": True, "data": languages}


PUBLIC_FILTER = {"status": "PUBLISHED"}


def active_language_codes() -> set:
    return {l["code"] for l in db.languages.find({"is_active": True}, {"code": 1})}


def sync_active_flag(fields: dict) -> dict:
    """Giữ is_active tương thích dữ liệu cũ: chỉ PUBLISHED mới là true."""
    if "status" in fields:
        fields["is_active"] = fields["status"] == "PUBLISHED"
    return fields


class PoiPayload(BaseModel):
    """Chỉ để FastAPI sinh tài liệu /docs; việc kiểm tra thật nằm ở validation.py."""
    poi_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    geofence_radius: Optional[float] = None
    translations: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    display_order: Optional[int] = None
    image_url: Optional[str] = None


class StatusPayload(BaseModel):
    status: str


# ---------------- API công khai (khách) ----------------

@app.get("/api/pois")
def get_pois():
    """Danh sách POI đã xuất bản (PUBLISHED), theo display_order."""
    raw = list(db.pois.find(PUBLIC_FILTER).sort("display_order", 1))
    return {"success": True, "data": [format_poi(p) for p in raw]}


# ---------------- API quản trị (cần token, do gateway kiểm tra) ----------------
# Lưu ý: các route /api/pois/admin/... phải khai báo TRƯỚC /api/pois/{poi_id}.

@app.get("/api/pois/admin/all")
def admin_list_pois():
    """Tất cả POI, mọi trạng thái (DRAFT/PUBLISHED/HIDDEN)."""
    raw = list(db.pois.find({}).sort("display_order", 1))
    return {"success": True, "data": [format_poi(p) for p in raw]}


@app.post("/api/pois", status_code=201)
def create_poi(payload: PoiPayload):
    """Tạo POI mới. Luôn ở trạng thái DRAFT cho tới khi admin xuất bản."""
    data = payload.model_dump(exclude_none=True)
    code = str(data.get("poi_code", "")).strip()
    if not code:
        raise HTTPException(status_code=422, detail="Thiếu poi_code")
    if db.pois.find_one({"_id": code}):
        raise HTTPException(status_code=409, detail="poi_code đã tồn tại: " + code)
    try:
        fields = build_poi_fields(data, active_language_codes())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    now = datetime.now(timezone.utc)
    doc = {
        "_id": code,
        "poi_code": code,
        "display_order": data.get("display_order", db.pois.count_documents({})),
        "image_url": data.get("image_url", ""),
        "coordinate_status": "pending_field_verification",
        **fields,
        "status": "DRAFT",
        "is_active": False,
        "created_at": now,
        "updated_at": now,
    }
    db.pois.insert_one(doc)
    return {"success": True, "data": format_poi(doc)}


@app.put("/api/pois/{poi_id}")
def update_poi(poi_id: str, payload: PoiPayload):
    """Cập nhật nội dung/tọa độ/bán kính. Không đổi poi_code."""
    data = payload.model_dump(exclude_none=True)
    data.pop("poi_code", None)
    if not db.pois.find_one({"_id": poi_id}):
        raise HTTPException(status_code=404, detail="Không tìm thấy POI: " + poi_id)
    try:
        fields = build_poi_fields(data, active_language_codes(), partial=True)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    fields["updated_at"] = datetime.now(timezone.utc)
    db.pois.update_one({"_id": poi_id}, {"$set": sync_active_flag(fields)})
    return {"success": True, "data": format_poi(db.pois.find_one({"_id": poi_id}))}


@app.patch("/api/pois/{poi_id}/status")
def change_poi_status(poi_id: str, payload: StatusPayload):
    """Xuất bản / ẩn / đưa về nháp. POI HIDDEN biến mất khỏi /api/pois ngay."""
    try:
        status = validate_status(payload.status)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    fields = sync_active_flag(
        {"status": status, "updated_at": datetime.now(timezone.utc)}
    )
    result = db.pois.update_one({"_id": poi_id}, {"$set": fields})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy POI: " + poi_id)
    return {"success": True, "data": format_poi(db.pois.find_one({"_id": poi_id}))}


@app.delete("/api/pois/{poi_id}")
def hide_poi(poi_id: str):
    """Xóa mềm: chuyển POI sang HIDDEN (không xóa dữ liệu khỏi DB)."""
    return change_poi_status(poi_id, StatusPayload(status="HIDDEN"))


@app.get("/api/pois/{poi_id}")
def get_poi_detail(poi_id: str):
    """Chi tiết 1 POI đã xuất bản, tìm theo poi_code (vd P00)."""
    poi = db.pois.find_one({"_id": poi_id, **PUBLIC_FILTER})
    if not poi:
        raise HTTPException(
            status_code=404, detail="Không tìm thấy POI với mã: " + poi_id
        )
    return {"success": True, "data": format_poi(poi)}
