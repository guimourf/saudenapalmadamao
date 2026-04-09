import hashlib
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class TelemedicineHashGenerator:
    def __init__(self):
        self.base_url = os.getenv('URL_FRONTEND', 'http://localhost:5000')
        print(f"Base URL configurado: {self.base_url}")
    
    def generate_hash_from_telemedicine_id(self, consultation_id: str) -> str:
        """
        Gera hash diretamente do ID do consultation
        """
        hash_obj = hashlib.md5(consultation_id.encode())
        return hash_obj.hexdigest()[:8].upper()

    def validate_hash(self, short_hash: str) -> bool:
        if len(short_hash) != 8:
            return False
        
        # Verifica se é hexadecimal válido
        try:
            int(short_hash, 16)
            return True
        except ValueError:
            return False

    def decode_hash(self, short_hash: str) -> Optional[Dict]:
        """
        Decodifica o hash e busca o consultation completo no banco
        """
        if not self.validate_hash(short_hash):
            return None
        
        try:
            # Importa aqui para evitar circular imports
            from app.services.nosql import get_handle

            handle = get_handle()
            consultations = handle.find(
                "consultations",
                {"session_hash": short_hash.upper()},
            )
            
            if not consultations:
                return {
                    'success': False,
                    'message': 'Consultation não encontrado',
                    'hash': short_hash.upper()
                }
            
            consultation = consultations[0]
            
            return {
                'success': True,
                'message': 'Consultation encontrado com sucesso',
                'hash': short_hash.upper(),
                'consultation': consultation
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Erro ao buscar consultation: {str(e)}',
                'hash': short_hash.upper(),
                'error': str(e)
            }

    def create_session_url(self, short_hash: str) -> str:
        """
        Cria URL no formato localhost:5000/?session=<hash>
        """
        return f"{self.base_url}/?session={short_hash}"


# Instância global
telemedicine_hash_generator = TelemedicineHashGenerator()


def create_telemedicine_hash(consultation_id: str) -> str:
    """
    Função auxiliar para criar hash do consultation
    """
    return telemedicine_hash_generator.generate_hash_from_telemedicine_id(consultation_id)


def decode_telemedicine_hash(short_hash: str) -> Optional[Dict]:
    """
    Função auxiliar para decodificar hash e buscar consultation
    """
    return telemedicine_hash_generator.decode_hash(short_hash)


def create_session_url(short_hash: str) -> str:
    """
    Função auxiliar para criar URL de sessão
    """
    return telemedicine_hash_generator.create_session_url(short_hash)