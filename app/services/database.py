"""
Camada de persistência MongoDB (banco oficial da aplicação).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "SaudenaPalmadaMao")

_client: Optional[MongoClient] = None
_db: Optional[Database] = None

# Ordem de prioridade para upsert (mesma regra que antes; evita insert duplicado)
UNIQUE_FIELD_PRIORITY = [
    "entry_id",
    "consultation_id",
    "session_hash",
    "professional_id",
    "patient_id",
    "id",
    "user_id",
]


def _require_uri() -> str:
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI não está definido no ambiente")
    return MONGO_URI


def get_mongo_database() -> Database:
    global _client, _db
    _require_uri()
    if _db is not None:
        return _db
    _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    _client.admin.command("ping")
    _db = _client[MONGO_DB_NAME]
    return _db


def ensure_connected() -> None:
    """Usado no startup da aplicação."""
    get_mongo_database()


def _convert_objectids(obj: Any) -> Any:
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _convert_objectids(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_objectids(i) for i in obj]
    return obj


def find_many(collection_name: str, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    db = get_mongo_database()
    coll = db[collection_name]
    docs = list(coll.find(filter_dict or {}))
    return [_convert_objectids(d) for d in docs]


def save_document(collection_name: str, document: Dict[str, Any]) -> Dict[str, Any]:
    """Insere ou atualiza documento por campo único conhecido (upsert)."""
    db = get_mongo_database()
    coll = db[collection_name]

    if "created_at" not in document:
        document["created_at"] = datetime.now(timezone.utc).isoformat()
    document["updated_at"] = datetime.now(timezone.utc).isoformat()

    unique_field = None
    unique_value = None
    for field in UNIQUE_FIELD_PRIORITY:
        if field not in document:
            continue
        val = document[field]
        if val is None or val == "":
            continue
        unique_field = field
        unique_value = val
        break

    if unique_field:
        update_data = dict(document)
        update_data.pop("_id", None)
        result = coll.update_one(
            {unique_field: unique_value},
            {"$set": update_data},
            upsert=True,
        )
        return {
            "success": True,
            "operation": "upsert",
            "matched": result.matched_count,
            "modified": result.modified_count,
            "upserted": str(result.upserted_id) if result.upserted_id else None,
        }

    ins = coll.insert_one(document)
    return {
        "success": True,
        "operation": "insert",
        "inserted_id": str(ins.inserted_id),
    }


class MongoHandle:
    """Facade usada pelas rotas (compatível com o padrão antigo handle.find / handle.save)."""

    def find(self, collection: str, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return find_many(collection, filter_dict)

    def save(self, collection: str, document: Dict[str, Any]) -> Dict[str, Any]:
        return save_document(collection, document)


_handle: Optional[MongoHandle] = None


def get_handle() -> MongoHandle:
    global _handle
    if _handle is None:
        _handle = MongoHandle()
    return _handle
