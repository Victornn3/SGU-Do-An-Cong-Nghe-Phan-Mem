"""Kiểm thử dữ liệu thuyết minh và ngôn ngữ (N9): đủ bản dịch, đủ nội dung cho mọi
ngôn ngữ đang bật, đường dẫn audio đúng quy ước. Chỉ dùng thư viện chuẩn nên chạy được
cả trong CI (chỉ cài pytest) lẫn bằng `python3 -m unittest`."""
import json
import pathlib
import unittest

SEED = pathlib.Path(__file__).resolve().parents[1] / "data" / "seed"


def doc(name):
    with open(SEED / name, encoding="utf-8") as handle:
        return json.load(handle)


POIS = doc("pois.json")
LANGS = doc("languages.json")
NARRATIONS = doc("narrations.json")
ACTIVE = [l["code"] for l in LANGS if l.get("is_active")]
POI_CODES = [p["poi_code"] for p in POIS]


class LanguageTests(unittest.TestCase):
    def test_ma_ngon_ngu_duy_nhat_va_co_du_truong(self):
        codes = [l["code"] for l in LANGS]
        self.assertEqual(len(codes), len(set(codes)))
        for lang in LANGS:
            for field in ("code", "name", "native_name", "tts_locale", "display_order", "is_active", "ui"):
                self.assertIn(field, lang, f"{lang.get('code')} thiếu trường {field}")

    def test_co_it_nhat_vi_en_zh_ko(self):
        for code in ("vi", "en", "zh", "ko"):
            self.assertIn(code, ACTIVE)

    def test_chuoi_giao_dien_du_khoa_o_moi_ngon_ngu(self):
        vi_keys = set(next(l for l in LANGS if l["code"] == "vi")["ui"].keys())
        for lang in LANGS:
            missing = vi_keys - set(lang["ui"].keys())
            self.assertFalse(missing, f"{lang['code']} thiếu chuỗi giao diện: {sorted(missing)[:5]}")


class NarrationTests(unittest.TestCase):
    def test_moi_poi_co_dung_mot_bai_thuyet_minh(self):
        ids = sorted(n["target_id"] for n in NARRATIONS)
        self.assertEqual(ids, sorted(POI_CODES))

    def test_moi_poi_co_noi_dung_cho_moi_ngon_ngu_dang_bat(self):
        for narration in NARRATIONS:
            for code in ACTIVE:
                text = (narration["content"].get(code) or "").strip()
                self.assertTrue(text, f"{narration['target_id']} thiếu nội dung '{code}'")

    def test_khong_co_ngon_ngu_la_trong_noi_dung(self):
        known = {l["code"] for l in LANGS}
        for narration in NARRATIONS:
            self.assertTrue(set(narration["content"]) <= known, narration["target_id"])

    def test_duong_dan_audio_dung_quy_uoc(self):
        for narration in NARRATIONS:
            for code, path in (narration.get("audio_paths") or {}).items():
                self.assertEqual(path, f"/audio/{code}/{narration['target_id']}.mp3")

    def test_so_file_mp3_can_sinh(self):
        # Số MP3 đầy đủ = số POI x số ngôn ngữ đang bật (hướng dẫn sinh lại ở README)
        self.assertEqual(len(NARRATIONS) * len(ACTIVE), 44)


class PoiTranslationTests(unittest.TestCase):
    def test_ten_va_mo_ta_du_o_moi_ngon_ngu(self):
        for poi in POIS:
            for code in ACTIVE:
                tr = poi["translations"].get(code) or {}
                self.assertTrue((tr.get("name") or "").strip(), f"{poi['poi_code']} thiếu tên '{code}'")
                self.assertTrue((tr.get("description") or "").strip(), f"{poi['poi_code']} thiếu mô tả '{code}'")


if __name__ == "__main__":
    unittest.main()
