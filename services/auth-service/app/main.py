import os
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import jwt

app = FastAPI(title="Auth Service")

JWT_SECRET = os.getenv("JWT_SECRET", "vanmieu_secret_key_2026")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(req: LoginRequest):
    if req.username != ADMIN_USERNAME or req.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=401, detail="Mật khẩu hoặc tài khoản không đúng"
        )
    
    payload = {
        "sub": req.username,
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return {"success": True, "access_token": token, "token_type": "bearer"}