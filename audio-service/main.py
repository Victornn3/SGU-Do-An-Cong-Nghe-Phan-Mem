import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Museum Audio Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("media", exist_ok=True)
app.mount("/audio/files", StaticFiles(directory="media"), name="files")

@app.get("/audio/languages")
async def get_supported_languages():
    return [
        {"code": "vi", "name": "🇻🇳 Tiếng Việt"},
        {"code": "en", "name": "🇬🇧 English"},
        {"code": "zh", "name": "🇨🇳 中文"}
    ]
