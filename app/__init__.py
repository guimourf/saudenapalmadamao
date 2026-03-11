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
    
    init_extensions(app)
    
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