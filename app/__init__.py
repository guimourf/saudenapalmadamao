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

    logger.info(f"DEBUG: {app.config['DEBUG']}")
    logger.info(f"SECRET_KEY: {app.config['SECRET_KEY']}")
    logger.info(f"JITSI_PUBLIC_URL: {os.getenv('JITSI_PUBLIC_URL')}")
    logger.info(f"JITSI_JWT_ISSUER: {os.getenv('JITSI_JWT_ISSUER')}")
    logger.info(f"JITSI_JWT_AUDIENCE: {os.getenv('JITSI_JWT_AUDIENCE')}")
    logger.info(f"JITSI_JWT_SUB: {os.getenv('JITSI_JWT_SUB')}")
    logger.info(f"JITSI_JWT_SECRET: {os.getenv('JITSI_JWT_SECRET')}")
    logger.info(f"JITSI_TTL: {os.getenv('JITSI_TTL')}")
    
    init_extensions(app)
    
    app.register_blueprint(api_bp)
    
    with app.app_context():
        try:
            from init_db import init_database
            init_database()
        except Exception as e:
            logger.warning(f" Não foi possível inicializar o banco: {e}")
    
    return app