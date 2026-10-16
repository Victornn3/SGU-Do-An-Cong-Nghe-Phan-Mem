from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
import os
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI(title="Auth Service")

# Cấu hình mã hóa mật khẩu & JWT
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "saigon_museum_microservices_secret_key_2026"
ALGORITHM = "HS256"

# Kết nối MongoDB
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.museum_db
users_collection = db.admin_users

class UserAuth(BaseModel):
    username: str
    password: str

@app.post("/auth/register")
async def register(user: UserAuth):
    # Kiểm tra username đã tồn tại chưa
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Tài khoản đã tồn tại")
    
    # Mã hóa mật khẩu bcrypt
    hashed_password = pwd_context.hash(user.password)
    await users_collection.insert_one({"username": user.username, "password": hashed_password})
    return {"message": "Đăng ký thành công", "username": user.username}

@app.post("/auth/login")
async def login(user: UserAuth):
    db_user = await users_collection.find_one({"username": user.username})
    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Sai username hoặc password")
    
    # Tạo JWT Token
    token_data = {"sub": user.username}
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    
    # Khớp đúng chuẩn API Contract JSON
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username
    }
