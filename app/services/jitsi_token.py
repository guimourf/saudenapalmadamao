import jwt
import os
import time
import logging
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Tentar carregar .env apenas em desenvolvimento (localhost)
# Em produção, as variáveis virão do ambiente do servidor
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class JitsiTokenGenerator:
    def __init__(self):
        self.app_id = os.getenv('JAAS_APP_ID')
        self.kid = os.getenv('JAAS_API_KEY')
        
        # Carregar a chave privada do arquivo .pk
        key_path = Path(__file__).resolve().parent.parent.parent / 'keys' / 'jitsi-secret.pk'
        
        if not key_path.exists():
            logger.error(f"Arquivo de chave privada não encontrado em: {key_path}")
            raise Exception(f"Arquivo de chave privada não encontrado em: {key_path}")
        
        with open(key_path, 'r') as f:
            self.private_key = f.read().strip()
        
        logger.info(f"Chave privada Jitsi carregada do arquivo: {key_path}")
    
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
        
        try:
            token = jwt.encode(payload, self.private_key, algorithm="RS256", headers={"kid": self.kid})
            logger.info(f"Token Jitsi gerado com sucesso para room: {room_name}")
            return token
        except Exception as e:
            logger.error(f"Erro ao gerar token Jitsi: {str(e)}")
            logger.error(f"Chave privada começa com: {self.private_key[:50]}")
            raise


_jitsi_token_generator = None

def get_jitsi_token_generator() -> JitsiTokenGenerator:
    global _jitsi_token_generator
    if _jitsi_token_generator is None:
        _jitsi_token_generator = JitsiTokenGenerator()
    return _jitsi_token_generator


def generate_jitsi_token(room_name: str, user_name: str, role: str = "participant") -> str:
    generator = get_jitsi_token_generator()
    return generator.generate_token(room_name, user_name, role)
