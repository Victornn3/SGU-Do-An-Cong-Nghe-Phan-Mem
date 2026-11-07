import os
import json
import time
import logging
import urllib.request
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pymongo import MongoClient
from gtts import gTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("narration-service")

app = FastAPI(title="Narration & Audio Service", version="1.0.0")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "vm_narration")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

AUDIO_BASE_DIR = Path(os.getenv("AUDIO_BASE_DIR", "/data/audio"))


class NarrationUpdate(BaseModel):
    """Nội dung thuyết minh theo mã ngôn ngữ, ví dụ {"vi": "...", "ko": "..."}."""
    poi_id: str
    title: str
    contents: dict[str, str]


# Danh mục ngôn ngữ thuộc poi-service (database vm_poi). Narration-service không đọc
# thẳng database của service khác mà hỏi qua API, rồi giữ bản nhớ tạm vài chục giây.
POI_SERVICE_URL = os.getenv("POI_SERVICE_URL", "http://poi-service:8002")
LANGUAGE_CACHE_SECONDS = 30
_language_cache = {"at": 0.0, "data": {}}


def _load_languages() -> dict:
    now = time.monotonic()
    if _language_cache["data"] and now - _language_cache["at"] < LANGUAGE_CACHE_SECONDS:
        return _language_cache["data"]
    try:
        with urllib.request.urlopen(f"{POI_SERVICE_URL}/api/languages", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        data = {item["code"]: item for item in payload.get("data", []) if item.get("code")}
        _language_cache["at"] = now
        _language_cache["data"] = data
        return data
    except Exception as e:
        logger.error(f"Không lấy được danh mục ngôn ngữ từ poi-service: {e}")
        return _language_cache["data"]  # dùng bản cũ nếu có


def get_language(code: str) -> dict | None:
    """Tra ngôn ngữ đang hoạt động (lấy từ poi-service qua API, không ghi cứng)."""
    if not code:
        return None
    return _load_languages().get(code)


def generate_tts_file(text: str, lang: str, poi_id: str) -> str | None:
    """Tạo file MP3 bằng Google Text-to-Speech; mã TTS lấy từ collection `languages`."""
    if not text or not text.strip():
        return None

    language = get_language(lang)
    if not language:
        logger.error(f"Ngôn ngữ '{lang}' không tồn tại hoặc đã tắt, bỏ qua sinh audio cho {poi_id}")
        return None
    target_lang = language.get("tts_locale") or lang

    folder_path = AUDIO_BASE_DIR / lang
    folder_path.mkdir(parents=True, exist_ok=True)

    file_path = folder_path / f"{poi_id}.mp3"

    try:
        tts = gTTS(text=text, lang=target_lang, slow=False)
        tts.save(str(file_path))

        if file_path.is_file() and file_path.stat().st_size > 0:
            logger.info(f"Đã tạo file âm thanh thành công: {file_path}")
            return f"/audio/{lang}/{poi_id}.mp3"
    except Exception as e:
        logger.error(f"Lỗi khi sinh file TTS cho {poi_id} ({lang}): {e}")

    return None


def process_tts_background(poi_id: str, contents: dict):
    """Tiến trình chạy nền: Tạo file MP3 thật cho các ngôn ngữ và cập nhật trạng thái vào DB."""
    update_fields = {}

    for lang, text in contents.items():
        if not text:
            continue

        audio_url = generate_tts_file(text=text, lang=lang, poi_id=poi_id)

        if audio_url:
            update_fields[f"audio_status.{lang}"] = "completed"
            update_fields[f"audio_paths.{lang}"] = audio_url
        else:
            update_fields[f"audio_status.{lang}"] = "failed"

    if update_fields:
        db.narrations.update_one(
            {"target_id": poi_id},
            {"$set": update_fields}
        )


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "narration-service"}


@app.get("/api/narrations/{poi_id}")
def get_narration(poi_id: str, lang: str = "vi"):
    """
    Lấy bài thuyết minh theo mã điểm và mã ngôn ngữ (lấy từ collection `languages`).
    Không tự đổi sang ngôn ngữ khác: nếu thiếu nội dung hoặc audio thì báo rõ để
    giao diện hiện thông báo dự phòng.
    """
    if not get_language(lang):
        raise HTTPException(status_code=404, detail=f"Ngôn ngữ không được hỗ trợ: {lang}")

    item = db.narrations.find_one({"target_id": poi_id})
    if not item:
        raise HTTPException(status_code=404, detail="Thuyết minh không tồn tại")

    content = (item.get("content", {}).get(lang) or "").strip()
    audio_path = item.get("audio_paths", {}).get(lang)
    audio_status = item.get("audio_status", {}).get(lang, "pending")

    # Audio "có" khi file MP3 thật sự tồn tại trong thư mục audio (không chỉ dựa vào DB).
    local_file = AUDIO_BASE_DIR / lang / f"{poi_id}.mp3"
    is_ready = local_file.is_file() and local_file.stat().st_size > 0
    audio_path = audio_path or f"/audio/{lang}/{poi_id}.mp3"

    return {
        "poi_id": poi_id,
        "title": item.get("title"),
        "lang": lang,
        "content": content or None,
        "content_available": bool(content),
        "audio_url": audio_path if is_ready else None,
        "audio_available": is_ready,
        "audio_status": "completed" if is_ready else audio_status,
    }


@app.post("/api/narrations")
def update_narration(data: NarrationUpdate, background_tasks: BackgroundTasks):
    """Cập nhật nội dung thuyết minh theo mã ngôn ngữ và xếp hàng tạo MP3 ở nền."""
    if not data.contents:
        raise HTTPException(status_code=422, detail="Cần ít nhất một ngôn ngữ trong contents")

    unknown = [code for code in data.contents if not get_language(code)]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Ngôn ngữ không được hỗ trợ: {', '.join(unknown)}",
        )

    update_payload = {"target_id": data.poi_id, "title": data.title}
    contents_to_process = {}
    for code, text in data.contents.items():
        update_payload[f"content.{code}"] = text
        update_payload[f"audio_status.{code}"] = "processing"
        contents_to_process[code] = text

    db.narrations.update_one(
        {"target_id": data.poi_id},
        {"$set": update_payload},
        upsert=True,
    )

    background_tasks.add_task(process_tts_background, data.poi_id, contents_to_process)

    return {
        "success": True,
        "message": "Đã lưu nội dung. File MP3 đang được tự động khởi tạo trong nền.",
    }


@app.post("/api/narrations/generate-all")
def trigger_generate_all_audio(background_tasks: BackgroundTasks):
    """
    Kích hoạt tiến trình nền đọc toàn bộ bản ghi trong MongoDB 
    và sinh file MP3 cho mọi điểm x mọi ngôn ngữ đang hoạt động.
    """
    narrations = list(db.narrations.find({}))
    if not narrations:
        raise HTTPException(
            status_code=400,
            detail="Chưa có dữ liệu thuyết minh trong MongoDB để sinh âm thanh."
        )

    def task_generate_all():
        logger.info(f"Bắt đầu tiến trình nền sinh âm thanh cho {len(narrations)} POI...")
        for item in narrations:
            poi_id = item.get("target_id")
            contents = item.get("content", {})
            if poi_id and contents:
                process_tts_background(poi_id, contents)
        logger.info("Hoàn tất tiến trình sinh toàn bộ file âm thanh!")

    background_tasks.add_task(task_generate_all)

    return {
        "success": True,
        "message": f"Đã xếp hàng tiến trình sinh âm thanh cho {len(narrations)} địa điểm.",
        "total_pois": len(narrations),
    }