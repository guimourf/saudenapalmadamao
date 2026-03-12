from flask_cors import CORS
from flask_restx import Api
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração de CORS dinâmica
allowed_origins = os.getenv('CORS_ORIGINS', '*')
if allowed_origins != '*':
    allowed_origins = [origin.strip() for origin in allowed_origins.split(',')]

cors_config = {
    "origins": allowed_origins,
    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "expose_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True,
    "max_age": 3600
}

cors = CORS()
api = Api(
    version='1.0',
    title='Saúde na Palma da Mão API',
    description='API para o sistema de saúde municipal',
    doc='/docs/',  # Documentação automática em /docs/
    prefix='/api/v1'
)

db_connection = None  # Conexão placeholder para banco de dados
def init_extensions(app):
    cors.init_app(app, resources={r"/*": cors_config})
    api.init_app(app)
    
    app.config['CORS_HEADERS'] = 'Content-Type'