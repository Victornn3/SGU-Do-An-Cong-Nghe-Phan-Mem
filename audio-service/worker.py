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

def get_smart_audio_text(text: str, max_chars: int = 450) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text  # Nếu ngắn thì đọc hết 100%
    truncated = text[:max_chars]
    last_dot = truncated.rfind(".")
    if last_dot != -1:
        return truncated[:last_dot + 1]  # Nếu dài thì dừng đúng dấu chấm câu
    return truncated + "..."

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
    
    # Lọc thông minh: ngắn đọc hết, dài lấy đoạn đầu trọn câu
    audio_script = get_smart_audio_text(text_vi, max_chars=450)

    # 1. Tạo ngay Tiếng Việt trước (không cần dịch nên có ngay sau 1-2 giây)
    file_vi = os.path.join(MEDIA_DIR, f"{poi_id}_vi.mp3")
    await generate_speech(audio_script, "vi", file_vi)
    print(f"⚡ [Worker] Đã tạo xong Tiếng Việt cho POI: {poi_id}", flush=True)

    # 2. Dịch đoạn text đó và tạo file tiếng Anh, tiếng Trung
    for lang in ["en", "zh"]:
        translated = translate_safe(audio_script, lang)
        file_path = os.path.join(MEDIA_DIR, f"{poi_id}_{lang}.mp3")
        await generate_speech(translated, lang, file_path)

    

async def process_artifact_event(art_data: dict):
    poi_id = art_data.get("poi_id")
    artifact_id = art_data.get("artifact_id")
    text_vi = art_data.get("text_vi", "")

    if not poi_id or not artifact_id or not text_vi:
        print(f"⚠️ Bỏ qua event do thiếu thông tin: {art_data}", flush=True)
        return

    os.makedirs(MEDIA_DIR, exist_ok=True)
    print(f"\n🏺 [Worker] Bắt đầu xử lý âm thanh cho Hiện vật: {artifact_id} (Bảo tàng: {poi_id})", flush=True)

    # Lọc thông minh: hiện vật để mốc 350 ký tự (hầu hết hiện vật sẽ đọc trọn vẹn)
    audio_script = get_smart_audio_text(text_vi, max_chars=350)

    # 1. Tạo ngay Tiếng Việt trước
    file_vi = os.path.join(MEDIA_DIR, f"{poi_id}_{artifact_id}_vi.mp3")
    await generate_speech(audio_script, "vi", file_vi)
    print(f"⚡ [Worker] Đã tạo xong Tiếng Việt cho hiện vật: {artifact_id}", flush=True)

    # 2. Dịch và tạo tiếng Anh & tiếng Trung
    for lang in ["en", "zh"]:
        translated = translate_safe(audio_script, lang)
        file_path = os.path.join(MEDIA_DIR, f"{poi_id}_{artifact_id}_{lang}.mp3")
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
                event_type = data.get("event")

                print(f"📥 [Worker] Nhận sự kiện: {event_type}", flush=True)

                if event_type == "ARTIFACT_SAVED":
                    asyncio.run(process_artifact_event(data))
                elif event_type == "POI_CREATED":
                    asyncio.run(process_poi_event(data))
                else:
                    # Dự phòng nếu event gửi lên không có trường "event"
                    if "artifact_id" in data:
                        asyncio.run(process_artifact_event(data))
                    else:
                        asyncio.run(process_poi_event(data))

            except Exception as e:
                print(f"❌ Lỗi xử lý message từ Redis: {e}", flush=True)

if __name__ == "__main__":
    main()