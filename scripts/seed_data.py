#!/usr/bin/env python3
"""Idempotent MongoDB seed for Van Mieu narration system (Flat POIs version)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
from pymongo import MongoClient, UpdateOne

# Lấy thư mục gốc VM (cha của scripts) để không bị lỗi dấu gạch chéo trên Windows
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("SEED_DATA_DIR", BASE_DIR / "data" / "seed"))

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "van_mieu")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me-before-demo")


def load_json(name: str):
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def upsert_many(collection, documents, key_field: str):
    ops = []

    now = datetime.now(timezone.utc)

    for doc in documents:
        key = doc.get(key_field) or doc.get("_id")

        if not key:
            raise ValueError(
                f"Document missing {key_field}: {doc}"
            )

        payload = dict(doc)

        # Không cập nhật _id trong $set vì MongoDB coi đây
        # là trường bất biến của document đã tồn tại.
        payload.pop("_id", None)

        payload["updated_at"] = now

        ops.append(
            UpdateOne(
                {"_id": key},
                {
                    "$set": payload,
                    "$setOnInsert": {
                        "created_at": now
                    },
                },
                upsert=True,
            )
        )

    if ops:
        result = collection.bulk_write(
            ops,
            ordered=False,
        )

        return (
            result.upserted_count,
            result.modified_count,
        )

    return 0, 0


def seed_admin(db):
    password_hash = bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.admins.update_one(
        {"username": ADMIN_USERNAME},
        {
            "$set": {
                "username": ADMIN_USERNAME,
                "role": "admin",
                "is_active": True,
                "updated_at": datetime.now(timezone.utc),
            },
            "$setOnInsert": {
                "_id": ADMIN_USERNAME,
                "password_hash": password_hash,
                "created_at": datetime.now(timezone.utc),
            },
        },
        upsert=True,
    )
    existing = db.admins.find_one({"username": ADMIN_USERNAME})
    if existing and not existing.get("password_hash"):
        db.admins.update_one(
            {"username": ADMIN_USERNAME},
            {"$set": {"password_hash": password_hash}},
        )


def ensure_indexes(db):
    db.pois.create_index("poi_code", unique=True)
    db.narrations.create_index("target_id", unique=True)
    db.tickets.create_index("ticket_code", unique=True)
    db.admins.create_index("username", unique=True)


def main() -> int:
    print(f"[seed] Connecting {MONGODB_URI} / {MONGODB_DB}")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=15000)
    client.admin.command("ping")
    db = client[MONGODB_DB]

    ensure_indexes(db)

    # Đã lược bỏ zones.json, chỉ load pois và narrations
    pois = load_json("pois.json")
    narrations = load_json("narrations.json")

    p_up, p_mod = upsert_many(db.pois, pois, "poi_code")

    # Danh mục ngôn ngữ: thêm ngôn ngữ mới chỉ cần thêm 1 bản ghi vào languages.json
    languages = load_json("languages.json")
    l_up, l_mod = upsert_many(db.languages, languages, "code")
    print("[seed] languages upserted={0} modified={1}".format(l_up, l_mod))

    narration_docs = []
    for item in narrations:
        doc = dict(item)
        doc["_id"] = item["target_id"]
        if "approved" not in doc:
            doc["approved"] = True
        narration_docs.append(doc)
    n_up, n_mod = upsert_many(db.narrations, narration_docs, "target_id")

    seed_admin(db)

    print(
        "[seed] pois upserted={0} modified={1} total={2}".format(
            p_up, p_mod, db.pois.count_documents({})
        )
    )
    print(
        "[seed] narrations upserted={0} modified={1} total={2}".format(
            n_up, n_mod, db.narrations.count_documents({})
        )
    )
    print(f"[seed] admin user ready: {ADMIN_USERNAME}")
    print("[seed] done (idempotent)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"[seed] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)