from flask import Blueprint, jsonify, request
from app.services.nosql import get_handle
from app.utils.serializers import consultation_for_public_response
from datetime import datetime, timezone

# Import de todos os namespaces das rotas
from app.routes.patient_routes import ns as ns_patients
from app.routes.professional_routes import ns as ns_professionals
from app.routes.consultation_routes import ns as ns_consultations
from app.routes.services_routes import ns as ns_services
import app.routes.queue_routes  

api_bp = Blueprint('api', __name__)

# -------------- Index Route (Legado) --------------

@api_bp.route('/')
def index():
    """Endpoint raiz da API com informações de documentação"""
    session_hash = request.args.get('session')
    
    response_data = {
        'message': 'API Saúde na Palma da Mão - Acesse /docs/ para documentação',
        'status': 'success',
    }
    
    # Se tem session hash, busca os dados automaticamente
    if session_hash:
        try:
            handle = get_handle()
            
            consultations = handle.find(
                "consultations",
                {"session_hash": session_hash.upper()},
            )
            
            if consultations:
                consultation = consultations[0]
                patient_id = consultation.get('patient_id')
                
                # Search patient data too
                patient = None
                
                if patient_id:
                    patients = handle.find("patients", {"patient_id": patient_id})
                    
                    if patients:
                        patient = patients[0]
                
                # Include data in response
                response_data.update({
                    'session_found': True,
                    'session_hash': session_hash.upper(),
                    'consultation': consultation_for_public_response(consultation),
                    'patient': patient,
                    'jitsi_room': f"Teleconsultation-{session_hash.upper()}",
                    'message': f'Session {session_hash.upper()} loaded successfully'
                })
            else:
                response_data.update({
                    'session_found': False,
                    'session_hash': session_hash.upper(),
                    'error': 'Consultation not found for this session'
                })
                
        except Exception as e:
            response_data.update({
                'session_found': False,
                'session_hash': session_hash.upper(),
                'error': f'Error searching consultation: {str(e)}'
            })
    
    return jsonify(response_data)

@api_bp.route('/intro-consultorio/')
def intro_consultorio():
    """Endpoint para introdução do consultório"""
    session_hash = request.args.get('session')
    
    response_data = {
        'message': 'API Saúde na Palma da Mão - Acesse /docs/ para documentação',
        'status': 'success',
    }
    
    # Se tem session hash, busca os dados automaticamente
    if session_hash:
        try:
            handle = get_handle()
            
            teleatendimentos = handle.find(
                "consultations",
                {"session_hash": session_hash.upper()},
            )
            
            if teleatendimentos:
                teleatendimento = teleatendimentos[0]
                usuario_id = teleatendimento.get('doctor_id') or teleatendimento.get('nurse_id')
                
                # Busca dados do profissional também
                professional = None
                
                if usuario_id:
                    professionals = handle.find(
                        "professionals", {"professional_id": usuario_id}
                    )
                    
                    if professionals:
                        professional = professionals[0]
                
                # Inclui os dados na resposta
                response_data.update({
                    'session_found': True,
                    'session_hash': session_hash.upper(),
                    'teleatendimento': consultation_for_public_response(teleatendimento),
                    'professional': professional,
                    'jitsi_room': f"Teleconsulta-{session_hash.upper()}",
                    'message': f'Sessão {session_hash.upper()} carregada com sucesso'
                })
            else:
                response_data.update({
                    'session_found': False,
                    'session_hash': session_hash.upper(),
                    'error': 'Teleatendimento não encontrado para esta sessão'
                })
                
        except Exception as e:
            response_data.update({
                'session_found': False,
                'session_hash': session_hash.upper(),
                'error': f'Erro ao buscar teleatendimento: {str(e)}'
            })
    
    return jsonify(response_data)
