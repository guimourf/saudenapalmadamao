import jwt
import os
import time
import logging
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Carregar .env do diretório raiz do projeto
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class JitsiTokenGenerator:
    def __init__(self):
        self.app_id = os.getenv('JAAS_APP_ID')
        self.kid = os.getenv('JAAS_API_KEY')
        
        # Obter e processar a chave privada
        private_key_raw = os.getenv('JITSI_SECRET_KEY', '')
        
        if not private_key_raw:
            logger.error("JITSI_SECRET_KEY não encontrada nas variáveis de ambiente")
            raise Exception("JITSI_SECRET_KEY não encontrada nas variáveis de ambiente")
        
        # Converter \n escapados para quebras de linha reais
        self.private_key = private_key_raw.replace('\\n', '\n')
    
    def generate_token(self, room_name: str, user_name: str, role: str = "participant") -> str:
        is_moderator = role.lower() == "medico"
        
        payload = {
            "aud": "jitsi",
            "iss": "chat",
            "sub": self.app_id,
            "room": room_name,
            "exp": int(time.time()) + 7200,
            "context": {
                "features": {
                    "livestreaming": False,
                    "recording": False
                },
                "user": {
                    "name": user_name,
                    "moderator": is_moderator
                }
            }
        }
        
        token = jwt.encode(payload, self.private_key, algorithm="RS256", headers={"kid": self.kid})
        return token


_jitsi_token_generator = None

def get_jitsi_token_generator() -> JitsiTokenGenerator:
    global _jitsi_token_generator
    if _jitsi_token_generator is None:
        _jitsi_token_generator = JitsiTokenGenerator()
    return _jitsi_token_generator


def generate_jitsi_token(room_name: str, user_name: str, role: str = "participant") -> str:
    generator = get_jitsi_token_generator()
    return generator.generate_token(room_name, user_name, role)
