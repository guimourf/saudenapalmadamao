from flask import Flask
from flask_cors import CORS
import os
import sys
import logging
from dotenv import load_dotenv
from app.extensions import init_extensions
from app.routes.routes import api_bp

load_dotenv()

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    
    # Configurações básicas
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    app.config['DEBUG'] = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Configurar CORS
    # Em produção, restringir origins. Em desenvolvimento, permitir "*"
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
    CORS(app, resources={r"/*": cors_config})
    
    init_extensions(app)
    
    # Handler para preflight requests
    @app.before_request
    def handle_preflight():
        from flask import request, make_response
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
            return response
    
    app.register_blueprint(api_bp)
    
    with app.app_context():
        try:
            # Escolhe qual init_db usar baseado na variável de ambiente
            if os.getenv('MONGO_URI'):
                from init_db_new import init_database
            else:
                from init_db import init_database
            init_database()
        except Exception as e:
            logger.warning(f" Não foi possível inicializar o banco: {e}")
    
    return app