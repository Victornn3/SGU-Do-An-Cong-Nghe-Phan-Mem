"""Sinh thuyết minh + file MP3 cho một ngôn ngữ MỚI chỉ bằng một câu lệnh.

Đặt file này tại:  services/narration-service/app/generate_language.py
(nằm trong thư mục app/ nên đã được Dockerfile copy vào container, không phải sửa gì khác)

Chạy trong container narration-service:

    docker compose exec narration-service python -m app.generate_language --lang ja
    docker compose exec narration-service python -m app.generate_language --all-active
    docker compose exec narration-service python -m app.generate_language --lang ja --dry-run

Với mỗi bài thuyết minh trong vm_narration.narrations:
  1. Chưa có content.<lang>  -> dịch từ tiếng Việt (translate.py), lưu vào MongoDB.
  2. Chưa có file MP3 hợp lệ -> sinh bằng gTTS, lưu data/audio/<lang>/<POI>.mp3,
     cập nhật audio_status.<lang> / audio_paths.<lang>.
  3. Đã đủ cả hai -> bỏ qua (không dịch lại, không ghi đè MP3). Dùng --force để sinh lại MP3.
Mặc định cũng dịch tên + mô tả POI sang <lang> (vm_poi.pois.translations.<lang>)
để giao diện không hiện tên tiếng Việt; tắt bằng --no-poi-text.

Chỉ đụng tới trường của ngôn ngữ được chọn; chạy lại nhiều lần an toàn.
Thoát mã 1 nếu còn mục lỗi (chạy lại sẽ làm tiếp phần còn thiếu).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from .translate import TranslationError, translate_text

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("generate-language")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
DB_NARRATION = os.getenv("MONGO_DATABASE", "vm_narration")
DB_POI = os.getenv("MONGO_DATABASE_POI", "vm_poi")
AUDIO_BASE_DIR = Path(os.getenv("AUDIO_BASE_DIR", "/data/audio"))
RETRIES = 2


def mp3_ok(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def with_retry(fn, *args):
    last = None
    for attempt in range(RETRIES + 1):
        try:
            return fn(*args)
        except Exception as exc:  # mạng chập chờn: thử lại
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last


def make_mp3(text: str, tts_locale: str, path: Path) -> None:
    from gtts import gTTS  # nhập muộn để test không cần cài gTTS

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".mp3.tmp")
    gTTS(text=text, lang=tts_locale, slow=False).save(str(tmp))
    if not mp3_ok(tmp):
        raise RuntimeError("file MP3 rỗng")
    os.replace(tmp, path)  # chỉ đổi tên khi file đã ghi xong, không để lại file dở


def process_language(db_n, db_p, lang: dict, force: bool, dry: bool, poi_text: bool) -> int:
    code = lang["code"]
    tts = lang.get("tts_locale") or code
    failed = 0
    log.info(f"\n=== Ngôn ngữ '{code}' (tts/dịch: {tts}) ===")

    for item in db_n.narrations.find({}):
        pid = item.get("target_id")
        content = item.get("content") or {}
        vi = (content.get("vi") or "").strip()
        text = (content.get(code) or "").strip()
        mp3 = AUDIO_BASE_DIR / code / f"{pid}.mp3"

        if not vi and not text:
            log.warning(f"[bỏ qua] {pid}: không có nội dung tiếng Việt để dịch")
            continue
        if text and mp3_ok(mp3) and not force:
            log.info(f"[đủ]     {pid}")
            continue
        if dry:
            log.info(f"[sẽ làm] {pid}: {'dịch + ' if not text else ''}tạo MP3")
            continue

        if not text:
            try:
                text = with_retry(translate_text, vi, tts)
            except (TranslationError, Exception) as exc:
                log.error(f"[LỖI dịch] {pid}: {exc}")
                failed += 1
                continue
            db_n.narrations.update_one({"target_id": pid}, {"$set": {f"content.{code}": text}})

        try:
            with_retry(make_mp3, text, tts, mp3)
        except Exception as exc:
            log.error(f"[LỖI MP3] {pid}: {exc}")
            db_n.narrations.update_one({"target_id": pid}, {"$set": {f"audio_status.{code}": "failed"}})
            failed += 1
            continue
        db_n.narrations.update_one(
            {"target_id": pid},
            {"$set": {f"audio_status.{code}": "completed", f"audio_paths.{code}": f"/audio/{code}/{pid}.mp3"}},
        )
        log.info(f"[xong]   {pid}")

    if poi_text:
        for poi in db_p.pois.find({}):
            trs = poi.get("translations") or {}
            src = trs.get("vi") or {"name": poi.get("name", ""), "description": poi.get("description", "")}
            have = trs.get(code) or {}
            for field in ("name", "description"):
                if (have.get(field) or "").strip() or not (src.get(field) or "").strip():
                    continue
                if dry:
                    log.info(f"[sẽ làm] POI {poi['poi_code']}.{field}: dịch")
                    continue
                try:
                    value = with_retry(translate_text, src[field], tts)
                except Exception as exc:
                    log.error(f"[LỖI dịch] POI {poi['poi_code']}.{field}: {exc}")
                    failed += 1
                    continue
                db_p.pois.update_one({"_id": poi["_id"]}, {"$set": {f"translations.{code}.{field}": value}})
                log.info(f"[xong]   POI {poi['poi_code']}.{field}")
    return failed


def main(argv=None, client=None) -> int:
    ap = argparse.ArgumentParser(description="Sinh thuyết minh + MP3 cho ngôn ngữ mới")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--lang", nargs="+", help="một hoặc nhiều mã ngôn ngữ, ví dụ ja")
    group.add_argument("--all-active", action="store_true", help="mọi ngôn ngữ đang bật (chỉ làm phần còn thiếu)")
    ap.add_argument("--force", action="store_true", help="sinh lại MP3 dù đã có")
    ap.add_argument("--dry-run", action="store_true", help="chỉ liệt kê việc sẽ làm")
    ap.add_argument("--no-poi-text", action="store_true", help="không dịch tên/mô tả POI")
    args = ap.parse_args(argv)

    if client is None:
        from pymongo import MongoClient

        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=10000)
    db_n, db_p = client[DB_NARRATION], client[DB_POI]

    query = {"is_active": True} if args.all_active else {"code": {"$in": args.lang}}
    languages = [l for l in db_p.languages.find(query) if l.get("code")]
    if args.lang:
        found = {l["code"] for l in languages}
        for code in args.lang:
            if code not in found:
                log.error(f"Không có ngôn ngữ '{code}' trong vm_poi.languages")
        languages = [l for l in languages if l.get("is_active", True)]
    languages = [l for l in languages if l["code"] != "vi"]
    if not languages:
        log.error("Không có ngôn ngữ nào để xử lý (cần bản ghi trong languages, is_active=true, khác 'vi').")
        return 1

    failed = 0
    for lang in languages:
        failed += process_language(db_n, db_p, lang, args.force, args.dry_run, not args.no_poi_text)
    log.info(f"\nHoàn tất. Số mục lỗi: {failed}" + (" — chạy lại lệnh để làm tiếp." if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
