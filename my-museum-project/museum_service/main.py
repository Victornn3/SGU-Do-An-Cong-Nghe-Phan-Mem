import os
import json
import redis
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from utils.geo import haversine_distance
from bson import ObjectId

app = FastAPI(title="Museum & GPS Service", version="1.0")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["museum_db"]
poi_collection = db["POI"]

redis_client = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

TRIGGER_RADIUS_METERS = 30.0

class GeofenceRequest(BaseModel):
    user_lat: float
    user_lng: float
    preferred_lang: str = "vi"

class POICreateSchema(BaseModel):
    id: str
    name: str
    description_vi: str
    lat: float
    lng: float
    trigger_radius_meters: float = 30.0
    qr_code: str
    image: str = ""

@app.get("/")
async def root():
    return {"service": "Museum & GPS Service", "port": 8002, "status": "running"}

@app.get("/pois")
async def get_all_pois():
    pois = await poi_collection.find({}, {"_id": 0}).to_list(length=100)
    return pois

@app.get("/pois/{poi_id}")
async def get_poi_detail(poi_id: str):
    poi = await poi_collection.find_one({"id": poi_id}, {"_id": 0})
    if not poi:
        raise HTTPException(status_code=404, detail="Không tìm thấy bảo tàng")
    return poi

@app.get("/pois/qr/{qr_code}")
async def get_poi_by_qr(qr_code: str):
    poi = await poi_collection.find_one({"qr_code": qr_code}, {"_id": 0})
    if poi:
        return {"type": "museum", "data": poi}
    
    poi_artifact = await poi_collection.find_one(
        {"artifacts.qr_code": qr_code},
        {"_id": 0, "id": 1, "name": 1, "artifacts.$": 1}
    )
    if poi_artifact:
        return {"type": "artifact", "data": poi_artifact}
        
    raise HTTPException(status_code=404, detail="Mã QR không hợp lệ")

@app.post("/pois/geofence")
async def check_geofence(req: GeofenceRequest):
    pois = await poi_collection.find({}, {"_id": 0}).to_list(length=100)
    
    for poi in pois:
        poi_lat = poi["location"]["lat"]
        poi_lng = poi["location"]["lng"]
        dist = haversine_distance(req.user_lat, req.user_lng, poi_lat, poi_lng)
        
        radius = poi.get("trigger_radius_meters", TRIGGER_RADIUS_METERS)
        
        if dist <= radius:
            lang = req.preferred_lang
            audio_url = f"http://localhost:8000/audio/files/{poi['id']}_{lang}.mp3"
            
            return {
                "inside_geofence": True,
                "poi_id": poi["id"],
                "poi_name": poi["name"],
                "distance_meters": round(dist, 1),
                "audio_url": audio_url,
                "transcript": poi["description_vi"]
            }
            
    return {
        "inside_geofence": False,
        "poi_id": None,
        "distance_meters": None,
        "message": "Không nằm trong vùng bảo tàng nào"
    }

@app.post("/pois/admin/add")
async def add_poi(poi_data: POICreateSchema):
    new_poi = {
        "id": poi_data.id,
        "name": poi_data.name,
        "description_vi": poi_data.description_vi,
        "location": {"lat": poi_data.lat, "lng": poi_data.lng},
        "trigger_radius_meters": poi_data.trigger_radius_meters,
        "qr_code": poi_data.qr_code,
        "image": poi_data.image,
        "artifacts": []
    }
    
    await poi_collection.update_one({"id": poi_data.id}, {"$set": new_poi}, upsert=True)
    
    event_payload = {
        "event": "POI_CREATED",
        "poi_id": poi_data.id,
        "text_vi": poi_data.description_vi,
        "target_languages": ["en", "zh"]
    }
    try:
        redis_client.publish("poi_events", json.dumps(event_payload))
    except Exception as e:
        print(f"Lỗi Redis: {e}")
        
    return {"success": True, "message": "Thêm bảo tàng thành công", "poi_id": poi_data.id}


@app.delete("/pois/admin/delete/{poi_id}")
async def delete_poi(poi_id: str):
    # 1. Thử xóa theo trường id thông thường ("hist_vn", "war_remnants",...)
    result = await poi_collection.delete_one({"id": poi_id})
    
    # 2. Nếu chưa xóa được, thử tìm xóa theo _id ObjectId hoặc chuỗi
    if result.deleted_count == 0:
        try:
            result = await poi_collection.delete_one({"_id": ObjectId(poi_id)})
        except Exception:
            pass

    if result.deleted_count == 0:
        result = await poi_collection.delete_one({"_id": poi_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy bảo tàng có id '{poi_id}' trong MongoDB")
        
    return {"success": True, "message": "Đã xóa bảo tàng thành công", "poi_id": poi_id}