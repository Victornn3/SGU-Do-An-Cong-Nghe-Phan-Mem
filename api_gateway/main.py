import os
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="API Gateway")

# Bật CORS bắt buộc để Web Demo kết nối không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cấu hình địa chỉ các Service nội bộ
AUTH_SERVICE_URL = "http://auth_service:8001"
MUSEUM_SERVICE_URL = "http://museum_service:8002"
AUDIO_SERVICE_URL = "http://audio_service:8001"

client = httpx.AsyncClient()

MEDIA_DIR = Path("/app/media")
if not MEDIA_DIR.exists():
    MEDIA_DIR = Path("media")
os.makedirs(str(MEDIA_DIR), exist_ok=True)

app.mount("/audio/files", StaticFiles(directory=str(MEDIA_DIR)), name="audio_files")

ASSETS_DIR = Path("/app/assets")
if not ASSETS_DIR.exists():
    ASSETS_DIR = Path("assets")

os.makedirs(str(ASSETS_DIR), exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# ==================== ĐIỀU HƯỚNG REVERSE PROXY ====================
# Điều hướng luồng /auth/* sang Port 8001
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_auth(request: Request, path: str):
    url = f"{AUTH_SERVICE_URL}/auth/{path}"
    body = await request.body()
    resp = await client.request(request.method, url, headers=dict(request.headers), content=body)
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

# Điều hướng luồng /pois/* sang Port 8002
# Đoạn code MỚI đã sửa:
@app.api_route("/pois", methods=["GET", "POST", "PUT", "DELETE"])
@app.api_route("/pois/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_museum(request: Request, path: str = ""):
    url = f"{MUSEUM_SERVICE_URL}/pois/{path}" if path else f"{MUSEUM_SERVICE_URL}/pois"
    body = await request.body()
    req_headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    resp = await client.request(request.method, url, headers=req_headers, content=body)
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
# Điều hướng luồng /audio/* sang Port 8003
@app.api_route("/audio/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_audio(request: Request, path: str):
    url = f"{AUDIO_SERVICE_URL}/audio/{path}"
    body = await request.body()
    resp = await client.request(request.method, url, headers=dict(request.headers), content=body)
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))


# ==================== PHỤC VỤ GIAO DIỆN FRONTEND ====================
FRONTEND_DIR = Path("/frontend")
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path("/app/frontend")
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Mount thư mục static nếu có
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Route trang chủ: http://localhost:8000/
@app.get("/")
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return Response(content="Không tìm thấy index.html", status_code=404)

# Route admin: http://localhost:8000/admin
@app.get("/admin")
async def serve_admin():
    admin_path = FRONTEND_DIR / "admin.html"
    if admin_path.exists():
        return FileResponse(str(admin_path))
    return Response(content=f"Không tìm thấy admin.html tại: {admin_path}", status_code=404)
