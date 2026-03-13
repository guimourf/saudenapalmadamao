from flask_cors import CORS
from flask_restx import Api
import os
from dotenv import load_dotenv

load_dotenv()

# Origens permitidas para CORS
ALLOWED_ORIGINS = [
    'https://v0-virtual-clinic-application.vercel.app',
    'https://saudenapalmadamao.onrender.com',
    'http://localhost:8080',
    'http://localhost:5000',
    'http://localhost:3000'
]

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
        "origins": ALLOWED_ORIGINS,
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
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,PATCH,DELETE,OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
        return response