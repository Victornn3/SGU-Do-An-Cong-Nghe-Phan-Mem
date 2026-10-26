import os

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

SERVICES = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001"),
    "pois": os.getenv("POI_SERVICE_URL", "http://poi-service:8002"),
    "narrations": os.getenv(
        "NARRATION_SERVICE_URL", "http://narration-service:8003"
    ),
    "tickets": os.getenv("TICKET_SERVICE_URL", "http://ticket-service:8004"),
    "stats": os.getenv(
        "STATISTICS_SERVICE_URL", "http://statistics-service:8005"
    ),
}

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "accept-encoding",
}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


@app.api_route(
    "/api/{service_name}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@app.api_route(
    "/api/{service_name}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def gateway_proxy(
    service_name: str,
    request: Request,
    path: str = "",
):
    base_url = SERVICES.get(service_name)

    if base_url is None:
        return Response(
            content='{"detail":"Service Not Found"}',
            status_code=404,
            media_type="application/json",
        )

    # Giữ nguyên quy tắc định tuyến hiện tại.
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

        # Không chuyển nguyên toàn bộ response headers vì một số header
        # có thể không còn đúng sau khi gateway tạo response mới.
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