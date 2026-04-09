from functools import wraps
from flask import request
from datetime import datetime
from typing import Tuple, Optional
import jwt
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

SECRET_KEY = os.getenv('JWT_SECRET_KEY')

def verify_token(token: str) -> Tuple[bool, Optional[str]]:
    if not token:
        return False, None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        app_name = payload.get('app_name')
        return True, app_name
    except jwt.ExpiredSignatureError:
        # Token expirou
        return False, None
    except jwt.InvalidTokenError:
        # Token inválido
        return False, None
    except Exception:
        # Qualquer outro erro
        return False, None

def get_token_from_request() -> Optional[str]:
    """Extrai o token do header Authorization"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        return None
    
    # Espera formato: "Bearer <token>"
    parts = auth_header.split()
    
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]

def require_token(f):
    """Decorator para proteger rotas com autenticação por JWT"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return {
                'message': 'Token de acesso não fornecido',
                'status': 'error',
                'help': 'Use: Authorization: Bearer <seu_token>'
            }, 401
        
        is_valid, app_name = verify_token(token)
        
        if not is_valid:
            return {
                'message': 'Token de acesso inválido ou expirado',
                'status': 'error'
            }, 401
        
        # Adiciona o nome da aplicação ao request
        request.app_name = app_name
        
        return f(*args, **kwargs)
    
    return decorated_function
