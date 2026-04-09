"""
Ponto de entrada do armazenamento: MongoDB.
"""
from app.services.database import get_handle, get_mongo_database, ensure_connected

__all__ = ["get_handle", "get_mongo_database", "ensure_connected"]
