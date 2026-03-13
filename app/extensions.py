from flask_cors import CORS
from flask_restx import Api
import os
from dotenv import load_dotenv

load_dotenv()

# Limpar CORS_ORIGINS de quebras de linha e espaços
cors_origins = os.getenv('CORS_ORIGINS', '*').strip()

cors = CORS()
api = Api(
    version='1.0',
    title='Saúde na Palma da Mão API',
    description='API para o sistema de saúde municipal',
    doc='/docs/',
    prefix='/api/v1'
)

db_connection = None

def init_extensions(app):
    CORS(app, resources={r"/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }})
    api.init_app(app)
    
    # Adicionar headers de Access-Control nas responses
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', cors_origins if cors_origins != '*' else '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response