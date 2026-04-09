import os
from pathlib import Path
from dotenv import load_dotenv
from .session_link import decode_telemedicine_hash

env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


def generate_jitsi_link(room_name):
    base = os.getenv('JITSI_PUBLIC_URL')
    if not base:
        raise ValueError('JITSI_PUBLIC_URL não configurado')
    return f"{base}/{room_name}"


def create_meet_link_from_hash(session_hash):
    try:
        decoded_session = decode_telemedicine_hash(session_hash)

        if decoded_session is None:
            return {
                'success': False,
                'error': 'Hash da sessão inválido'
            }

        room_name = f"Teleconsulta-{session_hash.upper()}"
        meet_link = generate_jitsi_link(room_name)

        return {
            'success': True,
            'meet_link': meet_link,
            'room_name': room_name,
            'session_hash': session_hash,
            'session_data': decoded_session
        }

    except ValueError as e:
        return {
            'success': False,
            'error': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Erro ao criar link da reunião: {str(e)}'
        }
