import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

MUSEUMS_DATA = [
    {
        "id": "museum_01",
        "name": "Bảo tàng Lịch sử TP.HCM",
        "description_vi": "Bảo tàng trưng bày hơn 40.000 hiện vật lịch sử Việt Nam từ thời tiền sử đến năm 1945.",
        "location": {"lat": 10.7878, "lng": 106.7051},
        "trigger_radius_meters": 30,
        "qr_code": "QR_MUSEUM_01",
        "artifacts": [
            {
                "artifact_id": "art_01",
                "name_vi": "Trống đồng Đông Sơn",
                "qr_code": "QR_ART_01",
                "description_vi": "Trống đồng cổ thuộc văn hóa Đông Sơn niên đại khoảng thế kỷ 3-2 TCN."
            }
        ]
    },
    {
        "id": "museum_02",
        "name": "Bảo tàng Mỹ thuật TP.HCM",
        "description_vi": "Bảo tàng lưu giữ nhiều tác phẩm hội họa, điêu khắc và mỹ thuật cổ truyền quý giá.",
        "location": {"lat": 10.7698, "lng": 106.6989},
        "trigger_radius_meters": 30,
        "qr_code": "QR_MUSEUM_02",
        "artifacts": []
    },
    {
        "id": "museum_03",
        "name": "Bảo tàng Thành phố Hồ Chí Minh",
        "description_vi": "Nơi trưng bày các thời kỳ phát triển lịch sử, văn hóa và thương mại của Sài Gòn - TP.HCM.",
        "location": {"lat": 10.7760, "lng": 106.6995},
        "trigger_radius_meters": 30,
        "qr_code": "QR_MUSEUM_03",
        "artifacts": []
    },
    {
        "id": "museum_04",
        "name": "Dinh Độc Lập",
        "description_vi": "Di tích lịch sử quốc gia đặc biệt, đánh dấu sự kiện giải phóng miền Nam thống nhất đất nước.",
        "location": {"lat": 10.7770, "lng": 106.6953},
        "trigger_radius_meters": 30,
        "qr_code": "QR_MUSEUM_04",
        "artifacts": []
    },
    {
        "id": "museum_05",
        "name": "Bảo tàng Địa chất",
        "description_vi": "Nơi lưu giữ và trưng bày hàng nghìn mẫu đá, khoáng vật và hóa thạch tại Việt Nam.",
        "location": {"lat": 10.7865, "lng": 106.7032},
        "trigger_radius_meters": 30,
        "qr_code": "QR_MUSEUM_05",
        "artifacts": []
    },
    {
        "id": "museum_06",
        "name": "Bảo tàng Chứng tích Chiến tranh",
        "description_vi": "Bảo tàng trưng bày tư liệu, hiện vật về hậu quả và di chứng của các cuộc chiến tranh.",
        "location": {"lat": 10.7792, "lng": 106.6921},
        "trigger_radius_meters": 30,
        "qr_code": "QR_MUSEUM_06",
        "artifacts": []
    },
    {
        "id": "museum_07",
        "name": "Bảo tàng Bến Nhà Rồng (Bảo tàng Hồ Chí Minh)",
        "description_vi": "Di tích lịch sử nơi Bác Hồ ra đi tìm đường cứu nước năm 1911.",
        "location": {"lat": 10.7681, "lng": 106.7068},
        "trigger_radius_meters": 30,
        "qr_code": "QR_MUSEUM_07",
        "artifacts": []
    }
]

async def init_database():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["museum_db"]
    collection = db["POI"]
    
    for museum in MUSEUMS_DATA:
        await collection.update_one(
            {"id": museum["id"]},
            {"$set": museum},
            upsert=True
        )
    print("✅ Đã nạp thành công 7 Bảo tàng TP.HCM vào MongoDB!")

if __name__ == "__main__":
    asyncio.run(init_database())
