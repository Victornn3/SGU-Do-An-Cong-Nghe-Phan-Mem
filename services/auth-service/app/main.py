import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from pymongo import MongoClient
import jwt
import bcrypt

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-service")

app = FastAPI(title="Auth Service", version="2.0.0")

# Lấy biến môi trường (M3)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DATABASE", "vm_auth")
JWT_SECRET = os.getenv("JWT_SECRET")

# Cảnh báo bảo mật nếu không cấu hình JWT_SECRET qua biến môi trường
if not JWT_SECRET:
    logger.warning("CẢNH BÁO: JWT_SECRET chưa được thiết lập qua biến môi trường! Sử dụng khóa tạm thời.")
    JWT_SECRET = "vanmieu_prod_secret_key_must_change_in_production"

# Kết nối cơ sở dữ liệu MongoDB
client = MongoClient(MONGO_URL)
db = client[MONGO_DB]


def ensure_default_admin():
    """
    Tự động kiểm tra và tạo tài khoản admin băm bcrypt trong MongoDB
    nếu cơ sở dữ liệu chưa có tài khoản nào (Cơ chế tự phục hồi an toàn).
    """
    try:
        if db.admins.count_documents({}) == 0:
            default_user = "admin"
            default_pass = "admin123"
            # Băm mật khẩu bằng thuật toán bcrypt
            salt = bcrypt.gensalt(rounds=10)
            hashed_pw = bcrypt.hashpw(default_pass.encode("utf-8"), salt).decode("utf-8")
            
            db.admins.insert_one({
                "username": default_user,
                "password_hash": hashed_pw,
                "role": "admin",
                "created_at": datetime.now(timezone.utc)
            })
            logger.info("Đã tự động khởi tạo tài khoản admin với mật khẩu băm bcrypt trong DB.")
    except Exception as e:
        logger.error(f"Lỗi kiểm tra DB admins: {e}")


@app.on_event("startup")
def startup_event():
    ensure_default_admin()


class LoginRequest(BaseModel):
    username: str
    password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu nhập vào với mã băm bcrypt trong DB (M2)."""
    try:
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password)
    except Exception as e:
        logger.error(f"Lỗi so khớp mật khẩu bcrypt: {e}")
        return False


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "auth-service"}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    """
    [M2] Đăng nhập quản trị:
    Tìm user trong db.admins và so khớp mật khẩu băm bcrypt.
    Tuyệt đối không so sánh chữ trần với biến môi trường.
    """
    username = req.username.strip()
    
    # 1. Tìm user trong collection db.admins
    admin_user = db.admins.find_one({"username": username})
    if not admin_user:
        raise HTTPException(
            status_code=401, 
            detail="Tài khoản hoặc mật khẩu không chính xác!"
        )

    # 2. Lấy hash mật khẩu từ DB (chấp nhận cả password_hash hoặc hashed_password)
    hashed_pw = admin_user.get("password_hash") or admin_user.get("hashed_password") or admin_user.get("password")
    if not hashed_pw or not verify_password(req.password, hashed_pw):
        raise HTTPException(
            status_code=401, 
            detail="Tài khoản hoặc mật khẩu không chính xác!"
        )

    # 3. Tạo JWT Token chuẩn
    payload = {
        "sub": username,
        "role": admin_user.get("role", "admin"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        "iat": datetime.now(timezone.utc),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return {
        "success": True, 
        "access_token": token, 
        "token_type": "bearer",
        "username": username
    }


@app.get("/api/auth/verify")
def verify_token(authorization: Optional[str] = Header(None)):
    """API cho Gateway hoặc các service khác kiểm tra tính hợp lệ của Token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Thiếu Token xác thực hoặc Token không đúng định dạng!")
    
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {"valid": True, "user": payload.get("sub"), "role": payload.get("role")}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ!")