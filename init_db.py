import logging

from app.services.database import ensure_connected

logger = logging.getLogger(__name__)


def init_database():
    """Verifica conexão com MongoDB (collections são criadas sob demanda)."""
    try:
        ensure_connected()
        logger.info("MongoDB: conexão OK")
    except Exception as e:
        logger.error("Falha ao conectar ao MongoDB: %s", e)
        raise
