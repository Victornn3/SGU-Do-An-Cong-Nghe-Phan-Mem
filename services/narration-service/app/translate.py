"""Dịch tự động từ tiếng Việt sang các ngôn ngữ khác (Google Translate).

Dùng thư viện `requests` (đã có sẵn vì gTTS phụ thuộc vào nó), tức cùng đường
kết nối HTTPS mà gTTS đang dùng thành công. Thuần Python để dễ viết test
(xem tests/test_auto_translate.py).
"""
import logging
import re

logger = logging.getLogger("narration-service.translate")

TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
TIMEOUT_SECONDS = 10
MAX_CHUNK = 1000  # gửi GET nên chia bài dài thành nhiều đoạn ngắn


class TranslationError(RuntimeError):
    """Không dịch được (mất mạng, Google từ chối, phản hồi lạ...)."""


def _default_http_get(url, params, timeout):
    import requests  # nhập muộn để test không cần cài requests

    resp = requests.get(url, params=params, timeout=timeout,
                        headers={"User-Agent": "Mozilla/5.0"})
    if resp.status_code != 200:
        raise TranslationError(f"Google Translate trả về HTTP {resp.status_code}")
    return resp.json()


def parse_response(payload) -> str:
    """Phản hồi có dạng [[["câu đã dịch", "câu gốc", ...], ...], ...]: nối các câu lại."""
    try:
        segments = payload[0]
        text = "".join(seg[0] for seg in segments if seg and seg[0])
    except (TypeError, IndexError, KeyError) as exc:
        raise TranslationError(f"Phản hồi dịch không đúng định dạng: {exc}")
    if not text.strip():
        raise TranslationError("Phản hồi dịch rỗng")
    return text.strip()


def split_chunks(text: str, limit: int = MAX_CHUNK) -> list:
    """Chia văn bản theo câu, mỗi đoạn không quá `limit` ký tự."""
    sentences = re.split(r"(?<=[.!?。])\s+", text.strip())
    chunks, current = [], ""
    for sentence in sentences:
        while len(sentence) > limit:  # câu quá dài: cắt cứng
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:limit])
            sentence = sentence[limit:]
        if current and len(current) + 1 + len(sentence) > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


def translate_text(text: str, target: str, source: str = "vi", http_get=None) -> str:
    """Dịch một đoạn văn bản. Văn bản rỗng trả về rỗng; lỗi thì ném TranslationError."""
    if not text or not text.strip():
        return ""
    if target == source:
        return text
    http_get = http_get or _default_http_get
    parts = []
    for chunk in split_chunks(text):
        params = {"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": chunk}
        try:
            payload = http_get(TRANSLATE_URL, params, TIMEOUT_SECONDS)
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"Không gọi được Google Translate ({target}): {type(exc).__name__}: {exc}")
        parts.append(parse_response(payload))
    return " ".join(parts)


def translate_fields(fields: dict, target: str, source: str = "vi", translator=translate_text) -> dict:
    """Dịch mọi trường văn bản trong dict, ví dụ {"name":..., "description":..., "narration":...}."""
    return {key: translator(value, target, source) for key, value in fields.items()}
