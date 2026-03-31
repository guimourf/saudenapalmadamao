import jwt
import os
import time
import logging
from urllib.parse import quote
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class JitsiTokenGenerator:
    def __init__(self):
        self.iss = os.getenv('JITSI_JWT_ISSUER')
        self.aud = os.getenv('JITSI_JWT_AUDIENCE')
        self.sub = os.getenv('JITSI_JWT_SUB')
        self.secret = os.getenv('JITSI_JWT_SECRET')
        self.public_url = (os.getenv('JITSI_PUBLIC_URL') or '').rstrip('/')
        self.ttl = int(os.getenv('JWT_TTL_SECONDS', '86400'))

        print(f"JitsiTokenGenerator: {self.secret}")

        

        if not all([self.iss, self.aud, self.sub, self.secret]):
            raise Exception('JITSI_JWT_ISSUER, JITSI_JWT_AUDIENCE, JITSI_JWT_SUB e JITSI_JWT_SECRET são obrigatórios')

    def generate_token(
        self,
        room_name: str,
        user_name: str,
        role: str = "participant",
        user_id: str = None,
        email: str = None,
        affiliation: str = None,
    ) -> dict:
        aff = affiliation or ("owner" if role.lower() == "medico" else "member")
        resolved_email = email
        display_name = user_name
        if not resolved_email and user_name and '@' in user_name:
            resolved_email = user_name
        if not resolved_email:
            resolved_email = 'user@exemplo.local'

        now = int(time.time())
        exp = now + self.ttl
        payload = {
            "aud": self.aud,
            "iss": self.iss,
            "sub": self.sub,
            "room": room_name,
            "nbf": now - 10,
            "exp": exp,
            "context": {
                "user": {
                    "id": user_id or "host",
                    "name": display_name,
                    "email": resolved_email,
                    "affiliation": aff
                }
            }
        }

        try:
            token = jwt.encode(payload, self.secret, algorithm="HS256")
            logger.info(f"Token Jitsi gerado para room: {room_name}")
            result = {
                "token": token,
                "jwt_payload": payload,
                "expires_at_epoch": exp,
                "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(exp)),
            }
            if self.public_url:
                result["host_url"] = f"{self.public_url}/{room_name}?jwt={quote(token, safe='')}"
                result["guest_url"] = f"{self.public_url}/{room_name}"
            return result
        except Exception as e:
            logger.error(f"Erro ao gerar token Jitsi: {str(e)}")
            raise


_jitsi_token_generator = None

def get_jitsi_token_generator() -> JitsiTokenGenerator:
    global _jitsi_token_generator
    if _jitsi_token_generator is None:
        _jitsi_token_generator = JitsiTokenGenerator()
    return _jitsi_token_generator


def generate_jitsi_token(
    room_name: str,
    user_name: str,
    role: str = "participant",
    user_id: str = None,
    email: str = None,
    affiliation: str = None,
) -> dict:
    generator = get_jitsi_token_generator()
    return generator.generate_token(room_name, user_name, role, user_id, email, affiliation)
