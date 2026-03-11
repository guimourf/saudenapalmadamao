from flask_cors import CORS
from flask_restx import Api

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
    cors.init_app(app)
    api.init_app(app)
    
    app.config['CORS_HEADERS'] = 'Content-Type'