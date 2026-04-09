from decimal import Decimal
import json

try:
    from bson import ObjectId
except ImportError:
    ObjectId = None


def consultation_for_public_response(data):
    """Remove links de chamada do payload de consulta."""
    if data is None:
        return None
    if not isinstance(data, dict):
        return convert_to_serializable(data)
    public = {k: v for k, v in data.items() if k not in ("meet_link", "host_url")}
    return convert_to_serializable(public)


def convert_to_serializable(obj):
    """Converte objetos não-serializáveis para tipos JSON serializáveis"""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    elif ObjectId and isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    else:
        return obj


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        elif ObjectId and isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)
