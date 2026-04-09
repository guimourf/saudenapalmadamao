import sys
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()

# Chave secreta para assinar os JWTs (DEVE ser a mesma em gen_key.py e auth.py)
SECRET_KEY = os.getenv('JWT_SECRET_KEY')

if not SECRET_KEY:
    print("JWT_SECRET_KEY não está definida no arquivo .env")
    print("Defina a variável JWT_SECRET_KEY no arquivo .env antes de gerar tokens")
    sys.exit(1)

def generate_jwt_token(app_name: str) -> str:
    """Gera um JWT token com expiração de 30 dias"""
    now = datetime.now()
    expires_at = now + timedelta(days=30)
    
    payload = {
        'app_name': app_name,
        'iat': now,
        'exp': expires_at
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def display_token_info(app_name: str, token: str):
    """Exibe as informações do token gerado"""
    now = datetime.now()
    expires_at = now + timedelta(days=30)
    
    print("\n" + "="*70)
    print("JWT Token gerado com sucesso!")
    print("="*70)
    print(f"Nome da Aplicação: {app_name}")
    print(f"Token: {token}")
    print(f"Gerado em: {now.strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Expira em: {expires_at.strftime('%d/%m/%Y %H:%M:%S')} (30 dias)")
    print("\nUse este token no header Authorization das requisições:")
    print(f"   Authorization: Bearer {token}")
    print("\nGuarde este token com segurança!")
    print("="*70 + "\n")

def main():
    if len(sys.argv) < 2:
        print("Uso: python gen_key.py <nome_da_aplicacao>")
        print("\nExemplo:")
        print("  python gen_key.py mobile_app")
        print("  python gen_key.py web_app")
        print("  python gen_key.py backend_service")
        sys.exit(1)
    
    app_name = sys.argv[1]
    
    # Valida o nome
    if not app_name.strip():
        print("Erro: Nome da aplicação não pode estar vazio")
        sys.exit(1)
    
    # Gera o token
    token = generate_jwt_token(app_name)
    
    # Exibe informações
    display_token_info(app_name, token)

if __name__ == "__main__":
    main()
