import uuid
from .session_link import decode_telemedicine_hash

def generate_jitsi_link(room_name):
    link = f"https://meet.jit.si/{room_name}"
    return link

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
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Erro ao criar link da reunião: {str(e)}'
        }