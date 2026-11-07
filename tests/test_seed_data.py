"""Kiểm tra dữ liệu mẫu (N6, N9): 11 POI, đủ 3 ngôn ngữ, bán kính và trạng thái hợp lệ."""
import json
import pathlib
import unittest

SEED = pathlib.Path(__file__).resolve().parents[1] / "data" / "seed"
POIS = json.load(open(SEED / "pois.json", encoding="utf-8"))
LANGS = json.load(open(SEED / "languages.json", encoding="utf-8"))
NARRATIONS = json.load(open(SEED / "narrations.json", encoding="utf-8"))
CODES = {l["code"] for l in LANGS}


class SeedTests(unittest.TestCase):
    def test_co_11_poi_ma_duy_nhat(self):
        codes = [p["poi_code"] for p in POIS]
        self.assertEqual(len(codes), 11)
        self.assertEqual(len(set(codes)), 11)

    def test_ban_kinh_10_den_25(self):
        for p in POIS:
            self.assertTrue(10 <= p["geofence_radius"] <= 25, p["poi_code"])

    def test_toa_do_trong_khu_van_mieu(self):
        for p in POIS:
            self.assertTrue(21.026 <= p["latitude"] <= 21.031, p["poi_code"])
            self.assertTrue(105.834 <= p["longitude"] <= 105.838, p["poi_code"])

    def test_trang_thai_hop_le(self):
        for p in POIS:
            self.assertIn(p["status"], ("DRAFT", "PUBLISHED", "HIDDEN"))

    def test_moi_poi_du_ban_dich_cac_ngon_ngu(self):
        for p in POIS:
            for code in CODES:
                t = p["translations"].get(code, {})
                self.assertTrue(t.get("name") and t.get("description"), (p["poi_code"], code))

    def test_khoa_giao_dien_dong_nhat_giua_cac_ngon_ngu(self):
        base = set(next(l for l in LANGS if l["code"] == "vi")["ui"])
        for l in LANGS:
            self.assertEqual(set(l["ui"]) ^ base, set(), l["code"])

    def test_moi_poi_co_thuyet_minh(self):
        targets = {n["target_id"] for n in NARRATIONS}
        for p in POIS:
            self.assertIn(p["poi_code"], targets)


if __name__ == "__main__":
    unittest.main()
