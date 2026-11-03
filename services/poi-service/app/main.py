import os
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient

app = FastAPI(title="POI & GPS Service", version="1.0.0")

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


@app.get("/api/zones")
def get_zones():
    """Lấy danh sách các cụm/khu vực tham quan."""
    zones = list(db.zones.find({"is_active": True}).sort("display_order", 1))
    return {
        "success": True, 
        "data": [format_poi(z) for z in zones]
    }


@app.get("/api/pois")
def get_pois(group_id: str = None):
    """Lấy danh sách đầy đủ các POI đang hoạt động, sắp xếp theo display_order."""
    query = {"is_active": True}
    if group_id:
        query["group_id"] = group_id

    raw_pois = list(db.pois.find(query).sort("display_order", 1))
    pois = [format_poi(p) for p in raw_pois]

    return {
        "success": True, 
        "data": pois
    }


@app.get("/api/pois/{poi_id}")
def get_poi_detail(poi_id: str):
    """
    Lấy chi tiết 1 điểm tham quan.
    Hỗ trợ tìm kiếm theo cả 'poi_code' (ví dụ: P00, P01) hoặc '_id'.
    """
    poi = db.pois.find_one({
        "$or": [
            {"poi_code": poi_id},
            {"_id": poi_id}
        ],
        "is_active": True
    })

    if not poi:
        raise HTTPException(
            status_code=404, 
            detail=f"Không tìm thấy POI với mã: {poi_id}"
        )

    return {
        "success": True, 
        "data": format_poi(poi)
    }