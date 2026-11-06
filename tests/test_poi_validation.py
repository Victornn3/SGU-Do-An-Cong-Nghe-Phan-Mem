"""Test quy tắc kiểm tra POI (N3). Chạy: python -m unittest discover tests -v"""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "validation", ROOT / "services" / "poi-service" / "app" / "validation.py"
)
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

LANGS = {"vi", "en", "zh"}
GOOD = {
    "latitude": 21.0285,
    "longitude": 105.8359,
    "geofence_radius": 15,
    "translations": {"vi": {"name": "Điểm", "description": "mô tả"}},
}


class RadiusTests(unittest.TestCase):
    def test_trong_khoang_cho_phep(self):
        for r in (10, 15, 25, "20"):
            self.assertEqual(v.validate_radius(r), float(r))

    def test_ngoai_khoang_bi_tu_choi(self):
        for r in (9.9, 0, -5, 25.1, 100):
            with self.assertRaises(v.ValidationError):
                v.validate_radius(r)

    def test_khong_phai_so(self):
        for r in ("abc", None, ""):
            with self.assertRaises(v.ValidationError):
                v.validate_radius(r)


class StatusTests(unittest.TestCase):
    def test_hop_le(self):
        for s in ("DRAFT", "PUBLISHED", "HIDDEN"):
            self.assertEqual(v.validate_status(s), s)

    def test_khong_hop_le(self):
        for s in ("published", "DELETED", "", None):
            with self.assertRaises(v.ValidationError):
                v.validate_status(s)


class CoordinateTests(unittest.TestCase):
    def test_hop_le(self):
        self.assertEqual(v.validate_coordinates(21.03, 105.83), (21.03, 105.83))

    def test_dao_lat_lng_bi_chan(self):
        with self.assertRaises(v.ValidationError):
            v.validate_coordinates(105.83, 21.03)

    def test_ngoai_ha_noi(self):
        with self.assertRaises(v.ValidationError):
            v.validate_coordinates(10.77, 106.69)  # TP.HCM


class TranslationTests(unittest.TestCase):
    def test_thieu_ten_tieng_viet(self):
        with self.assertRaises(v.ValidationError):
            v.validate_translations({"en": {"name": "x"}}, LANGS)

    def test_ngon_ngu_chua_khai_bao(self):
        with self.assertRaises(v.ValidationError):
            v.validate_translations({"vi": {"name": "x"}, "ko": {"name": "y"}}, LANGS)

    def test_thieu_ban_dich_khac_van_hop_le(self):
        # Thiếu en/zh được phép; phía khách sẽ hiện thông báo dự phòng
        out = v.validate_translations({"vi": {"name": "x"}}, LANGS)
        self.assertIn("vi", out)


class BuildFieldsTests(unittest.TestCase):
    def test_tao_moi_day_du(self):
        f = v.build_poi_fields(GOOD, LANGS)
        self.assertEqual(f["name"], "Điểm")
        self.assertEqual(f["geofence_radius"], 15.0)

    def test_ban_kinh_mac_dinh_15(self):
        data = {k: x for k, x in GOOD.items() if k != "geofence_radius"}
        self.assertEqual(v.build_poi_fields(data, LANGS)["geofence_radius"], 15)

    def test_cap_nhat_mot_phan(self):
        f = v.build_poi_fields({"geofence_radius": 20}, LANGS, partial=True)
        self.assertEqual(f, {"geofence_radius": 20.0})

    def test_cap_nhat_ban_kinh_sai(self):
        with self.assertRaises(v.ValidationError):
            v.build_poi_fields({"geofence_radius": 30}, LANGS, partial=True)

    def test_khong_cho_ghi_truong_la(self):
        f = v.build_poi_fields(dict(GOOD, password="x", _id="hack"), LANGS)
        self.assertNotIn("password", f)
        self.assertNotIn("_id", f)


if __name__ == "__main__":
    unittest.main()
