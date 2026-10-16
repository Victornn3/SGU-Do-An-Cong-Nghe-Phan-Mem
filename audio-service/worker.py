import os
import json
import asyncio
import redis
import edge_tts
from gtts import gTTS
from deep_translator import GoogleTranslator

# Khởi tạo kết nối Redis (mặc định trỏ sang container redis trong Docker)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

VOICE_MAP = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-JennyNeural",
    "zh": "zh-CN-XiaoxiaoNeural"
}

GTTS_LANG_MAP = {
    "vi": "vi",
    "en": "en",
    "zh": "zh-CN"
}

# Đường dẫn thư mục media được mount volume chung trong Docker
MEDIA_DIR = "/app/media"

def translate_safe(text: str, target_lang: str) -> str:
    if target_lang == "vi":
        return text
    target_code = "en" if target_lang == "en" else "zh-CN"
    try:
        translated = GoogleTranslator(source="vi", target=target_code).translate(text)
        return translated if translated else text
    except Exception as e:
        print(f"[Translator] Cảnh báo dịch {target_lang} thất bại ({e}), sử dụng văn bản gốc.", flush=True)
        return text

async def generate_speech(text: str, lang: str, file_path: str):
    # 1. Thử dùng edge-tts (giọng đọc tự nhiên chất lượng cao)
    try:
        voice = VOICE_MAP.get(lang, "vi-VN-HoaiMyNeural")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(file_path)
        print(f"-> [Edge-TTS] Tạo xong: {file_path}", flush=True)
        return
    except Exception as e:
        print(f"⚠️ Edge-TTS gặp sự cố ({e}), đang tự động chuyển sang gTTS...", flush=True)

    # 2. Fallback sang gTTS nếu Edge-TTS bị lỗi 403 / kết nối
    try:
        gtts_code = GTTS_LANG_MAP.get(lang, "vi")
        # Chạy save() trong thread riêng để không block event loop
        await asyncio.to_thread(lambda: gTTS(text=text, lang=gtts_code).save(file_path))
        print(f"-> [gTTS Fallback] Tạo xong: {file_path}", flush=True)
    except Exception as e:
        print(f"❌ Cả 2 dịch vụ TTS đều thất bại: {e}", flush=True)

async def process_poi_event(poi_data: dict):
    poi_id = poi_data.get("poi_id")
    text_vi = poi_data.get("text_vi", "")

    if not poi_id or not text_vi:
        print(f"⚠️ Bỏ qua event do thiếu poi_id hoặc text_vi: {poi_data}", flush=True)
        return

    os.makedirs(MEDIA_DIR, exist_ok=True)
    print(f"\n🎧 [Worker] Bắt đầu xử lý âm thanh cho POI: {poi_id}", flush=True)

    for lang in ["vi", "en", "zh"]:
        translated = translate_safe(text_vi, lang)
        file_path = os.path.join(MEDIA_DIR, f"{poi_id}_{lang}.mp3")
        await generate_speech(translated, lang, file_path)

def main():
    print("--- AUDIO WORKER ĐANG LẮNG NGHE SỰ KIỆN TỪ REDIS ---", flush=True)
    pubsub = r.pubsub()
    pubsub.subscribe("poi_events")

    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                raw_data = message["data"]
                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode("utf-8")
                data = json.loads(raw_data)
                asyncio.run(process_poi_event(data))
            except Exception as e:
                print(f"❌ Lỗi xử lý message: {e}", flush=True)

if __name__ == "__main__":
    main()