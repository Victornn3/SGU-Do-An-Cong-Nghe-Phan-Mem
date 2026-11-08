"""Kiểm thử Haversine và Geofence (N9). Hàm khoảng cách duy nhất của ứng dụng nằm ở
frontend/js/gps.js (JavaScript), nên test nạp đúng file đó bằng Node rồi so với bản tính
độc lập bằng Python. Không có Node thì bỏ qua các test này (CI của GitHub có sẵn Node)."""
import json
import math
import pathlib
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GPS_JS = ROOT / "frontend" / "js" / "gps.js"
with open(ROOT / "data" / "seed" / "pois.json", encoding="utf-8") as handle:
    POIS = json.load(handle)

NODE_RUNNER = r"""
const fs = require('fs'), vm = require('vm');
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), ctx);
const pairs = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(pairs.map(p => ctx.getDistanceMeters(p[0], p[1], p[2], p[3]))));
"""


def haversine_py(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def js_distances(pairs):
    out = subprocess.run(
        ["node", "-e", NODE_RUNNER, str(GPS_JS)],
        input=json.dumps(pairs), capture_output=True, text=True, check=True, timeout=30,
    )
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "Không có Node để chạy gps.js")
class GeofenceTests(unittest.TestCase):
    def test_haversine_js_khop_ban_tinh_python(self):
        pairs = [[a["latitude"], a["longitude"], b["latitude"], b["longitude"]] for a in POIS for b in POIS]
        for (la, lo, lb, lp), got in zip(pairs, js_distances(pairs)):
            self.assertAlmostEqual(got, haversine_py(la, lo, lb, lp), delta=0.01)

    def test_khoang_cach_p00_p01_khoang_72m(self):
        p0 = next(p for p in POIS if p["poi_code"] == "P00")
        p1 = next(p for p in POIS if p["poi_code"] == "P01")
        got = js_distances([[p0["latitude"], p0["longitude"], p1["latitude"], p1["longitude"]]])[0]
        self.assertAlmostEqual(got, 72.6, delta=0.6)

    def test_tam_diem_nam_trong_ban_kinh_cua_chinh_no(self):
        dists = js_distances([[p["latitude"], p["longitude"], p["latitude"], p["longitude"]] for p in POIS])
        for poi, d in zip(POIS, dists):
            self.assertEqual(d, 0)
            self.assertLessEqual(d, poi["geofence_radius"])

    def test_diem_cach_5m_trong_vung_cach_100m_ngoai_vung(self):
        meter = 1 / 111195  # 1 mét theo vĩ độ (độ)
        for poi in POIS:
            lat, lng, radius = poi["latitude"], poi["longitude"], poi["geofence_radius"]
            near, far = js_distances([
                [lat, lng, lat + 5 * meter, lng],
                [lat, lng, lat + 100 * meter, lng],
            ])
            self.assertLessEqual(near, radius, f"{poi['poi_code']}: điểm cách 5 m phải nằm trong vùng")
            self.assertGreater(far, radius, f"{poi['poi_code']}: điểm cách 100 m phải nằm ngoài vùng")

    def test_diem_xa_khu_di_tich_khong_thuoc_poi_nao(self):
        far = (21.0400, 105.8500)  # cách Văn Miếu hơn 1 km
        dists = js_distances([[far[0], far[1], p["latitude"], p["longitude"]] for p in POIS])
        for poi, d in zip(POIS, dists):
            self.assertGreater(d, poi["geofence_radius"], poi["poi_code"])


if __name__ == "__main__":
    unittest.main()
