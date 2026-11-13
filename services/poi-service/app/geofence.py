import math

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Tính khoảng cách giữa 2 tọa độ GPS theo công thức Haversine.
    Trả về khoảng cách tính bằng mét (m).
    """
    R = 6371000.0  # Bán kính Trái Đất (mét)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def check_geofence_entry(user_lat: float, user_lon: float, poi: dict) -> bool:
    """
    Kiểm tra xem người dùng có nằm trong bán kính Geofence của POI hay không.
    """
    distance = calculate_haversine_distance(
        user_lat, user_lon, poi["latitude"], poi["longitude"]
    )
    return distance <= poi.get("geofence_radius", 10.0)