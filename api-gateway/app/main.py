import os
import jwt
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API Gateway - Secure Edition", version="2.0.0")

# [M3] Cấu hình CORS an toàn
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv("JWT_SECRET", "vanmieu_prod_secret_key_2026")

SERVICES = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001"),
    "pois": os.getenv("POI_SERVICE_URL", "http://poi-service:8002"),
    "languages": os.getenv("POI_SERVICE_URL", "http://poi-service:8002"),
    "narrations": os.getenv("NARRATION_SERVICE_URL", "http://narration-service:8003"),
    "tickets": os.getenv("TICKET_SERVICE_URL", "http://ticket-service:8004"),
    "stats": os.getenv("STATISTICS_SERVICE_URL", "http://statistics-service:8005"),
}

HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host",
    "content-length", "accept-encoding",
}


def is_public_request(method: str, service: str, path: str) -> bool:
    """
    [M1] Danh sách trắng (Whitelist) các API công khai cho khách tham quan.
    Tất cả các API nằm ngoài danh sách này BẮT BUỘC phải có Token Admin.
    """
    # 1. Trình duyệt gửi preflight OPTIONS để kiểm tra CORS
    if method == "OPTIONS":
        return True

    clean_path = path.strip("/")

    # 2. Đăng nhập Auth
    if service == "auth" and clean_path == "login":
        return True

    # 3. Khách xem điểm tham quan & ngôn ngữ (Chỉ cho phép GET)
    if service in ["pois", "languages"] and method == "GET":
        return True

    # 4. Khách nghe audio thuyết minh (Chỉ cho phép GET)
    if service == "narrations" and method == "GET":
        return True

    # 5. Khách quét mã QR vé vào cổng (POST /api/tickets/scan/{code})
    if service == "tickets" and clean_path.startswith("scan"):
        return True

    # 6. Khách gửi định vị GPS và đếm lượt truy cập thời gian thực
    if service == "stats" and clean_path in ["session-location", "visit"]:
        return True

    # Mọi API khác (tạo vé, xem thống kê, sửa nội dung...) đều là riêng tư
    return False


def verify_token(request: Request) -> tuple[bool, str]:
    """Kiểm tra tính hợp lệ của JWT Token gửi lên từ Header."""
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False, "Yêu cầu quyền Quản trị viên (Thiếu Header Authorization: Bearer <token>)!"

    token = auth_header.split(" ")[1].strip()
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return True, "OK"
    except jwt.ExpiredSignatureError:
        return False, "Phiên đăng nhập đã hết hạn! Vui lòng đăng nhập lại."
    except jwt.InvalidTokenError:
        return False, "Token quản trị không hợp lệ hoặc đã bị chỉnh sửa!"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


@app.api_route(
    "/api/{service_name}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
@app.api_route(
    "/api/{service_name}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def gateway_proxy(
    service_name: str,
    request: Request,
    path: str = "",
):
    # [M1] BẢO VỆ PHÂN QUYỀN TẠI GATEWAY
    if not is_public_request(request.method, service_name, path):
        is_valid, message = verify_token(request)
        if not is_valid:
            return Response(
                content=f'{{"success": false, "detail": "{message}"}}',
                status_code=401,
                media_type="application/json",
            )

    base_url = SERVICES.get(service_name)
    if base_url is None:
        return Response(
            content='{"detail":"Service Not Found"}',
            status_code=404,
            media_type="application/json",
        )

    target_url = f"{base_url.rstrip('/')}/api/{service_name}"
    if path:
        target_url += f"/{path}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                params=request.query_params,
                headers=headers,
                content=await request.body(),
            )

        response_headers = {}
        for key in ("content-type", "cache-control", "www-authenticate"):
            value = upstream.headers.get(key)
            if value:
                response_headers[key] = value

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
        )

    except httpx.TimeoutException:
        return Response(
            content='{"detail":"Upstream service timeout"}',
            status_code=504,
            media_type="application/json",
        )
    except httpx.RequestError:
        return Response(
            content='{"detail":"Cannot connect to upstream service"}',
            status_code=502,
            media_type="application/json",
        )