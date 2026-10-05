from fastapi import FastAPI, Request, Response
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
AUDIO_SERVICE_URL = "http://audio_service:8003"

client = httpx.AsyncClient()

# Điều hướng luồng /auth/* sang Port 8001
@app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_auth(request: Request, path: str):
    url = f"{AUTH_SERVICE_URL}/auth/{path}"
    body = await request.body()
    resp = await client.request(request.method, url, headers=dict(request.headers), content=body)
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

# Điều hướng luồng /pois/* sang Port 8002
@app.api_route("/pois/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_museum(request: Request, path: str = ""):
    url = f"{MUSEUM_SERVICE_URL}/pois/{path}" if path else f"{MUSEUM_SERVICE_URL}/pois"
    body = await request.body()
    resp = await client.request(request.method, url, headers=dict(request.headers), content=body)
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

# Điều hướng luồng /audio/* sang Port 8003
@app.api_route("/audio/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_audio(request: Request, path: str):
    url = f"{AUDIO_SERVICE_URL}/audio/{path}"
    body = await request.body()
    resp = await client.request(request.method, url, headers=dict(request.headers), content=body)
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

