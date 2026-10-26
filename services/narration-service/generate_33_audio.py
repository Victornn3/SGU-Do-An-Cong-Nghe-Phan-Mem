import os
import sys
from pathlib import Path
from pymongo import MongoClient
from gtts import gTTS

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "van_mieu")
AUDIO_BASE_DIR = Path(os.getenv("AUDIO_BASE_DIR", "/data/audio"))

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

LANG_MAP = {
    "vi": "vi",
    "en": "en",
    "zh": "zh-CN"
}

narrations = list(db.narrations.find({}))
if not narrations:
    print("[Error] Không tìm thấy dữ liệu thuyết minh trong MongoDB!")
    sys.exit(1)

print(f"Bắt đầu sinh âm thanh cho {len(narrations)} địa điểm...")
total = 0

for item in narrations:
    poi_id = item.get("target_id")
    contents = item.get("content", {})

    for lang_code, gtts_lang in LANG_MAP.items():
        text = contents.get(lang_code, "").strip()
        if not text:
            continue

        target_dir = AUDIO_BASE_DIR / lang_code
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{poi_id}.mp3"

        if file_path.exists() and file_path.stat().st_size > 0:
            print(f"[Exists] {lang_code.upper()} - {poi_id}")
            total += 1
            continue

        print(f"Đang sinh {lang_code.upper()} cho {poi_id}...", end=" ", flush=True)
        try:
            tts = gTTS(text=text, lang=gtts_lang, slow=False)
            tts.save(str(file_path))
            print("OK!")
            total += 1
        except Exception as e:
            print(f"Lỗi: {e}")

print(f"\nHoàn tất! Tổng cộng {total}/33 file âm thanh đã sẵn sàng tại {AUDIO_BASE_DIR}.")