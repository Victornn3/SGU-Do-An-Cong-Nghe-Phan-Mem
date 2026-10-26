import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pymongo import MongoClient
from gtts import gTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("narration-service")

app = FastAPI(title="Narration & Audio Service", version="1.0.0")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "van_mieu")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

AUDIO_BASE_DIR = Path(os.getenv("AUDIO_BASE_DIR", "/data/audio"))


class NarrationUpdate(BaseModel):
    poi_id: str
    title: str
    vi_content: str
    en_content: str | None = None
    zh_content: str | None = None


def generate_tts_file(text: str, lang: str, poi_id: str) -> str | None:
    """Tạo file MP3 thực tế bằng Google Text-to-Speech và kiểm tra dung lượng file."""
    if not text or not text.strip():
        return None

    gtts_lang_map = {
        "vi": "vi",
        "en": "en",
        "zh": "zh-CN"
    }
    target_lang = gtts_lang_map.get(lang, "vi")

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
    """Lấy bài thuyết minh theo ID địa điểm và mã ngôn ngữ (vi, en, zh)."""
    item = db.narrations.find_one({"target_id": poi_id})
    if not item:
        raise HTTPException(status_code=404, detail="Thuyết minh không tồn tại")

    content_dict = item.get("content", {})
    audio_paths_dict = item.get("audio_paths", {})
    audio_status_dict = item.get("audio_status", {})

    content = content_dict.get(lang) or content_dict.get("vi", "")
    audio_path = audio_paths_dict.get(lang)
    audio_status = audio_status_dict.get(lang, "pending")

    is_ready = False
    if audio_path:
        local_file = AUDIO_BASE_DIR / lang / f"{poi_id}.mp3"
        is_ready = local_file.is_file() and local_file.stat().st_size > 0

    return {
        "poi_id": poi_id,
        "title": item.get("title"),
        "lang": lang,
        "content": content,
        "audio_url": audio_path if is_ready else None,
        "audio_status": "completed" if is_ready else audio_status,
    }


@app.post("/api/narrations")
def update_narration(data: NarrationUpdate, background_tasks: BackgroundTasks):
    """Cập nhật nội dung bài thuyết minh và xếp hàng tạo file MP3 ở background."""
    current_doc = db.narrations.find_one({"target_id": data.poi_id}) or {}
    existing_content = current_doc.get("content", {})

    contents_to_process = {
        "vi": data.vi_content,
        "en": data.en_content if data.en_content is not None else existing_content.get("en", ""),
        "zh": data.zh_content if data.zh_content is not None else existing_content.get("zh", ""),
    }

    update_payload = {
        "target_id": data.poi_id,
        "title": data.title,
        "content.vi": contents_to_process["vi"],
        "audio_status.vi": "processing",
    }

    if data.en_content is not None:
        update_payload["content.en"] = data.en_content
        update_payload["audio_status.en"] = "processing"

    if data.zh_content is not None:
        update_payload["content.zh"] = data.zh_content
        update_payload["audio_status.zh"] = "processing"

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
    và sinh đầy đủ 33 file MP3 (11 POI x 3 ngôn ngữ).
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
        "message": f"Đã xếp hàng tiến trình sinh âm thanh cho {len(narrations)} địa điểm (3 ngôn ngữ).",
        "total_pois": len(narrations),
    }