import os
import json
import asyncio
import redis
import edge_tts
from deep_translator import MyMemoryTranslator

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0)

VOICE_MAP = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-JennyNeural",
    "zh": "zh-CN-XiaoxiaoNeural"
}

def translate_safe(text: str, target_lang: str):
    if target_lang == "vi":
        return text
    target_code = "en-GB" if target_lang == "en" else "zh-CN"
    try:
        return MyMemoryTranslator(source='vi-VN', target=target_code).translate(text)
    except Exception as e:
        print(f"Lỗi dịch {target_lang}: {e}")
        return text

async def process_poi_event(poi_data):
    poi_id = poi_data.get("poi_id")
    text_vi = poi_data.get("text_vi", "")
    os.makedirs("media", exist_ok=True)

    for lang in ["vi", "en", "zh"]:
        translated = translate_safe(text_vi, lang)
        voice = VOICE_MAP.get(lang, "vi-VN-HoaiMyNeural")
        file_path = os.path.join("media", f"{poi_id}_{lang}.mp3")
        
        communicate = edge_tts.Communicate(translated, voice)
        await communicate.save(file_path)
        print(f"-> Tạo xong: {file_path}")

def main():
    print("--- AUDIO WORKER ĐANG LẮNG NGHE SỰ KIỆN TỪ REDIS ---")
    pubsub = r.pubsub()
    pubsub.subscribe("poi_events")
    for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"].decode("utf-8"))
                asyncio.run(process_poi_event(data))
            except Exception as e:
                print(f"Lỗi: {e}")

if __name__ == "__main__":
    main()
