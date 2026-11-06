"""Quy tắc kiểm tra dữ liệu POI (thuần Python, không phụ thuộc FastAPI/Mongo)
để dễ viết test. Khớp PRD: bán kính 10–25 m (mặc định 15), trạng thái
DRAFT / PUBLISHED / HIDDEN."""

STATUSES = ("DRAFT", "PUBLISHED", "HIDDEN")
MIN_RADIUS = 10
MAX_RADIUS = 25
DEFAULT_RADIUS = 15
# Vùng bao quanh Hà Nội, chặn nhập nhầm tọa độ (vd đảo lat/lng)
LAT_RANGE = (20.5, 21.5)
LNG_RANGE = (105.3, 106.3)


class ValidationError(ValueError):
    """Dữ liệu không hợp lệ; thông điệp hiển thị được cho admin."""


def validate_status(status):
    if status not in STATUSES:
        raise ValidationError(
            "status phải là một trong: " + ", ".join(STATUSES)
        )
    return status


def validate_radius(value):
    try:
        radius = float(value)
    except (TypeError, ValueError):
        raise ValidationError("geofence_radius phải là số")
    if not (MIN_RADIUS <= radius <= MAX_RADIUS):
        raise ValidationError(
            "geofence_radius phải từ %d đến %d mét" % (MIN_RADIUS, MAX_RADIUS)
        )
    return radius


def validate_coordinates(lat, lng):
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        raise ValidationError("latitude/longitude phải là số")
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1]):
        raise ValidationError("latitude nằm ngoài khu vực Hà Nội")
    if not (LNG_RANGE[0] <= lng <= LNG_RANGE[1]):
        raise ValidationError("longitude nằm ngoài khu vực Hà Nội")
    return lat, lng


def validate_translations(translations, language_codes):
    """translations: {mã_ngôn_ngữ: {name, description}}. Chỉ chấp nhận mã
    ngôn ngữ có trong bảng languages; tiếng Việt (vi) bắt buộc có tên."""
    if not isinstance(translations, dict):
        raise ValidationError("translations phải là đối tượng {mã_ngôn_ngữ: {...}}")
    for code, content in translations.items():
        if code not in language_codes:
            raise ValidationError("Ngôn ngữ chưa được khai báo: " + str(code))
        if not isinstance(content, dict):
            raise ValidationError("translations.%s phải là đối tượng" % code)
    vi = translations.get("vi") or {}
    if not str(vi.get("name", "")).strip():
        raise ValidationError("Thiếu tên tiếng Việt (translations.vi.name)")
    return translations


def build_poi_fields(payload, language_codes, partial=False):
    """Kiểm tra payload và trả về các trường được phép ghi vào DB.
    partial=True: dùng cho cập nhật, chỉ kiểm tra trường có gửi lên."""
    fields = {}
    if not partial or "latitude" in payload or "longitude" in payload:
        lat, lng = validate_coordinates(
            payload.get("latitude"), payload.get("longitude")
        )
        fields["latitude"], fields["longitude"] = lat, lng
    if "geofence_radius" in payload or not partial:
        fields["geofence_radius"] = validate_radius(
            payload.get("geofence_radius", DEFAULT_RADIUS)
        )
    if "translations" in payload or not partial:
        fields["translations"] = validate_translations(
            payload.get("translations"), language_codes
        )
        vi = fields["translations"]["vi"]
        # name/description gốc luôn đồng bộ với bản tiếng Việt
        fields["name"] = vi.get("name", "")
        fields["description"] = vi.get("description", "")
    if "status" in payload:
        fields["status"] = validate_status(payload["status"])
    for key in ("display_order", "image_url"):
        if key in payload:
            fields[key] = payload[key]
    return fields
