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
        
        # Obter e processar a chave privada
        private_key_raw = os.getenv('JITSI_SECRET_KEY', '')
        
        if not private_key_raw:
            logger.error("JITSI_SECRET_KEY não encontrada nas variáveis de ambiente")
            raise Exception("JITSI_SECRET_KEY não encontrada nas variáveis de ambiente")
        
        self.private_key = private_key_raw
        
        if '\\n' in self.private_key:
            self.private_key = self.private_key.replace('\\n', '\n')
        
        if self.private_key.startswith("'") and self.private_key.endswith("'"):
            self.private_key = self.private_key[1:-1]
        
        if '\\n' in self.private_key:
            self.private_key = self.private_key.replace('\\n', '\n')
        
        # Log para debug
        logger.info(f"Chave privada carregada: {len(self.private_key)} caracteres")
        logger.debug(f"Começa com: {self.private_key[:30]}")
        logger.debug(f"Termina com: {self.private_key[-30:]}")
    
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
