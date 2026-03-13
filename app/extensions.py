from flask_cors import CORS
from flask_restx import Api
import os
from dotenv import load_dotenv

load_dotenv()

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
        "origins": os.getenv('CORS_ORIGINS', '*'),
        "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }})
    api.init_app(app)