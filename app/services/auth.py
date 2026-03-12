from functools import wraps
from flask import request
from datetime import datetime
from typing import Tuple, Optional
import jwt
import os
from dotenv import load_dotenv
import logging

# Carrega variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)

# Chave secreta para decodificar JWTs (DEVE ser a mesma em gen_key.py e auth.py)
SECRET_KEY = os.getenv('JWT_SECRET_KEY')

def verify_token(token: str) -> Tuple[bool, Optional[str]]:
    if not token:
        logger.warning("Token vazio fornecido")
        return False, None
    
    if not SECRET_KEY:
        logger.error("JWT_SECRET_KEY não está configurada!")
        return False, None
    
    try:
        # Tenta decodificar com diferentes opções
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        app_name = payload.get('app_name')
        logger.info(f"Token válido para app: {app_name}")
        return True, app_name
    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado")
        return False, None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token inválido: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"Erro ao verificar token: {str(e)}")
        return False, None

def get_token_from_request() -> Optional[str]:
    """Extrai o token do header Authorization"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header:
        logger.debug("Nenhum header Authorization fornecido")
        return None
    
    # Espera formato: "Bearer <token>"
    parts = auth_header.split()
    
    if len(parts) != 2:
        logger.warning(f"Header Authorization com formato inválido: esperado 2 partes, obteve {len(parts)}")
        return None
    
    if parts[0].lower() != 'bearer':
        logger.warning(f"Tipo de autenticação inválido: {parts[0]}")
        return None
    
    return parts[1]

def require_token(f):
    """Decorator para proteger rotas com autenticação por JWT"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            logger.warning("Token não fornecido na requisição")
            return {
                'message': 'Token de acesso não fornecido',
                'status': 'error',
                'help': 'Use: Authorization: Bearer <seu_token>'
            }, 401
        
        is_valid, app_name = verify_token(token)
        
        if not is_valid:
            logger.warning(f"Tentativa de acesso com token inválido")
            return {
                'message': 'Token de acesso inválido ou expirado',
                'status': 'error'
            }, 401
        
        # Adiciona o nome da aplicação ao request
        request.app_name = app_name
        logger.info(f"Requisição autorizada para app: {app_name}")
        
        return f(*args, **kwargs)
    
    return decorated_function