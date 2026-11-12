"""Test dịch tự động (không gọi mạng thật). Chạy: python -m unittest discover tests -v"""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "translate", ROOT / "services" / "narration-service" / "app" / "translate.py"
)
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


def fake_get(answer, seen=None):
    def http_get(url, params, timeout):
        if seen is not None:
            seen.append(params)
        return answer(params) if callable(answer) else answer
    return http_get


class ParseTests(unittest.TestCase):
    def test_noi_nhieu_cau(self):
        payload = [[["Hello. ", "Xin chào. "], ["Welcome.", "Chào mừng."]], None, "vi"]
        self.assertEqual(t.parse_response(payload), "Hello. Welcome.")

    def test_phan_hoi_la_bao_loi(self):
        for bad in (None, [], [[]], {"x": 1}):
            with self.assertRaises(t.TranslationError):
                t.parse_response(bad)


class ChunkTests(unittest.TestCase):
    def test_van_ban_ngan_giu_nguyen(self):
        self.assertEqual(t.split_chunks("Một câu. Hai câu."), ["Một câu. Hai câu."])

    def test_chia_theo_cau_khong_qua_gioi_han(self):
        text = " ".join(["Đây là một câu khá dài." for _ in range(100)])
        chunks = t.split_chunks(text, limit=200)
        self.assertTrue(all(len(c) <= 200 for c in chunks))
        self.assertEqual(" ".join(chunks), text)


class TranslateTests(unittest.TestCase):
    def test_gui_dung_ngon_ngu_va_noi_dung(self):
        seen = []
        out = t.translate_text("Xin chào", "zh-CN", http_get=fake_get([[["你好", "Xin chào"]]], seen))
        self.assertEqual(out, "你好")
        self.assertEqual(seen[0]["sl"], "vi")
        self.assertEqual(seen[0]["tl"], "zh-CN")
        self.assertEqual(seen[0]["q"], "Xin chào")

    def test_bai_dai_dich_tung_doan_roi_noi(self):
        seen = []
        text = " ".join(["Câu số %d." % i for i in range(400)])
        out = t.translate_text(text, "en", http_get=fake_get(lambda p: [[["X", p["q"]]]], seen))
        self.assertGreater(len(seen), 1)
        self.assertEqual(out, " ".join(["X"] * len(seen)))

    def test_van_ban_rong_khong_goi_mang(self):
        def http_get(*a, **k):
            raise AssertionError("không được gọi mạng")
        self.assertEqual(t.translate_text("  ", "en", http_get=http_get), "")

    def test_loi_mang_thanh_translation_error(self):
        def http_get(*a, **k):
            raise OSError("mất mạng")
        with self.assertRaises(t.TranslationError) as ctx:
            t.translate_text("Xin chào", "en", http_get=http_get)
        self.assertIn("mất mạng", str(ctx.exception))

    def test_dich_ca_ten_mo_ta_thuyet_minh(self):
        out = t.translate_fields(
            {"name": "Cổng", "description": "", "narration": "Bài"},
            "en",
            translator=lambda text, target, source: f"[{target}]{text}" if text else "",
        )
        self.assertEqual(out, {"name": "[en]Cổng", "description": "", "narration": "[en]Bài"})


if __name__ == "__main__":
    unittest.main()
