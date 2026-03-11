import jwt
import os
import time
from dotenv import load_dotenv

load_dotenv()

class JitsiTokenGenerator:
    def __init__(self):
        self.app_id = os.getenv('JAAS_APP_ID')
        self.kid = os.getenv('JAAS_API_KEY')
        self.private_key_path = os.getenv('JITSI_SECRET_KEY_PATH', 'jitsi-secret.pk')
        
        try:
            with open(self.private_key_path, 'r') as f:
                self.private_key = f.read()
        except FileNotFoundError:
            raise Exception(f"Arquivo de chave privada não encontrado: {self.private_key_path}")
    
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
