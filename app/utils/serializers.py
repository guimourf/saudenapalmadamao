from decimal import Decimal
import json

try:
    from bson import ObjectId
except ImportError:
    ObjectId = None


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
