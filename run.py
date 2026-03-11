import sys
import logging

# Desabilita buffer de stdout
sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)

from app import create_app

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def init_db():
    from init_db_new import init_database
    init_database()

app = create_app()

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'init-db':
        init_db()
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)