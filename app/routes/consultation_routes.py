from app.services.session_link import create_session_url, create_telemedicine_hash
from app.services.auth import require_token
from app.models.consultation import Consultation
from app.models.professional import Professional
from app.models.patient import Patient
from app.utils.serializers import convert_to_serializable
from borneo import PutRequest, QueryRequest
from flask import request
from flask_restx import Resource, Namespace
from app.services.nosql import get_handle
from app.extensions import api
from app.constants import (
    TELEATENDIMENTO_STATUS_CHOICES,
    TELEATENDIMENTO_TYPE_CHOICES,
    TELEATENDIMENTO_STATUS_LABELS,
    TELEATENDIMENTO_TYPE_LABELS,
    is_valid_status,
    is_valid_type,
)
from datetime import datetime, timezone, date
import os
import re

def clean_document(document):
    """Remove caracteres não numéricos do documento"""
    if not document:
        return ""
    return re.sub(r'\D', '', document)

ns = Namespace('teleatendimento', description='Endpoints de Teleconsultas')
api.add_namespace(ns, path='/teleatendimento_')

@ns.route('criar')
class CreateConsultation(Resource):
    @require_token
    def post(self):
        """Criar uma nova teleconsulta"""
        handle = get_handle()

        data = request.get_json() or {}
        
        patient_name = data.get('patient_name')
        patient_document = data.get('document')
        patient_report = data.get('patient_report', '')
        consultation_type = data.get('type')
        
        if not patient_name or not consultation_type:
            return {
                'message': 'patient_name and type are required',
                'status': 'error'
            }, 400
        
        # Validate consultation type
        consultation_type = consultation_type.lower()
        if not is_valid_type(consultation_type):
            return {
                'message': f'Invalid type. Accepted types: {", ".join(TELEATENDIMENTO_TYPE_CHOICES)}',
                'status': 'error',
                'valid_types': TELEATENDIMENTO_TYPE_CHOICES,
                'labels': TELEATENDIMENTO_TYPE_LABELS
            }, 400

        # Validate professional
        doctor_name = data.get('doctor_name', '').strip()
        doctor_id = data.get('doctor_id', '').strip()
        doctor_credential = clean_document(data.get('doctor_credential', ''))
        professional_document = clean_document(data.get('professional_document', ''))
        specialty = data.get('specialty', '').strip()
        
        nurse_name = data.get('nurse_name', '').strip()
        nurse_id = data.get('nurse_id', '').strip()
        
        # Check if at least one professional is provided
        if not doctor_name and not nurse_name:
            return {
                'message': 'Either doctor_name or nurse_name is required',
                'status': 'error'
            }, 400
        
        # If doctor, require credential and specialty
        if doctor_name:
            if not doctor_credential:
                return {
                    'message': 'doctor_credential is required when doctor_name is provided',
                    'status': 'error'
                }, 400
            if not specialty:
                return {
                    'message': 'specialty is required when doctor_name is provided',
                    'status': 'error'
                }, 400
            if not professional_document:
                return {
                    'message': 'professional_document is required when doctor_name is provided',
                    'status': 'error'
                }, 400

        # Check consultation limit
        max_consultations = int(os.getenv('MAX_TELECONSULTAS', 25))
        
        try:
            req_count = QueryRequest().set_statement(
                "SELECT * FROM consultations"
            )
            result_count = handle.query(req_count)
            existing_consultations = result_count.get_results()
            total_consultations = len(existing_consultations)
            
            if total_consultations >= max_consultations:
                return {
                    'message': f'Consultation limit reached. Maximum allowed: {max_consultations}',
                    'status': 'error',
                    'total_current': total_consultations,
                    'limit': max_consultations
                }, 429
        except Exception as e:
            return {
                'message': f'Error checking consultation limit: {str(e)}',
                'status': 'error'
            }, 500

        # Create or find existing patient
        try:
            patient_id = None
            patient_data = None
            
            # Try to find existing patient by document if provided
            if patient_document:
                req_search = QueryRequest().set_statement(
                    f"SELECT * FROM patients WHERE document = '{patient_document}'"
                )
                result_search = handle.query(req_search)
                existing_patients = result_search.get_results()
                
                if existing_patients:
                    # Patient already exists, use existing one
                    patient_data = existing_patients[0]
                    patient_id = patient_data.get('patient_id')
            
            # If patient not found, create new one
            if not patient_id:
                patient = Patient(name=patient_name, document=patient_document)
                patient_data = patient.to_dict()
                
                req_patient = PutRequest()
                req_patient.set_table_name("patients")
                req_patient.set_value(patient_data)
                handle.put(req_patient)
                
                patient_id = patient.patient_id
                
        except Exception as e:
            return {
                'message': f'Error with patient: {str(e)}',
                'status': 'error'
            }, 500

        # Create or find existing professionals
        try:
            professional_data = None
            
            # Handle doctor professional
            if doctor_name:
                doctor_id = None
                doctor_data = None
                
                # Try to find existing doctor by credential if provided
                if doctor_credential:
                    req_search = QueryRequest().set_statement(
                        f"SELECT * FROM professionals WHERE credential = '{doctor_credential}'"
                    )
                    result_search = handle.query(req_search)
                    existing_professionals = result_search.get_results()
                    
                    if existing_professionals:
                        # Professional already exists, use existing one
                        doctor_data = existing_professionals[0]
                        doctor_id = doctor_data.get('professional_id')
                
                # If professional not found, create new one
                if not doctor_id:
                    professional = Professional(
                        name=doctor_name,
                        profession='médico(a)',
                        credential=doctor_credential,
                        professional_document=professional_document,
                        specialty=specialty
                    )
                    doctor_data = professional.to_dict()
                    
                    req_professional = PutRequest()
                    req_professional.set_table_name("professionals")
                    req_professional.set_value(doctor_data)
                    handle.put(req_professional)
                    
                    doctor_id = professional.professional_id
                
                professional_data = doctor_data
            
            # Handle nurse professional
            elif nurse_name:
                nurse_id = None
                nurse_data = None
                
                # Try to find existing nurse by name if provided
                req_search = QueryRequest().set_statement(
                    f"SELECT * FROM professionals WHERE name = '{nurse_name}' AND profession = 'enfermeiro(a)'"
                )
                result_search = handle.query(req_search)
                existing_professionals = result_search.get_results()
                
                if existing_professionals:
                    # Professional already exists, use existing one
                    nurse_data = existing_professionals[0]
                    nurse_id = nurse_data.get('professional_id')
                
                # If professional not found, create new one
                if not nurse_id:
                    professional = Professional(
                        name=nurse_name,
                        profession='enfermeiro(a)',
                        credential='',
                        specialty=''
                    )
                    nurse_data = professional.to_dict()
                    
                    req_professional = PutRequest()
                    req_professional.set_table_name("professionals")
                    req_professional.set_value(nurse_data)
                    handle.put(req_professional)
                    
                    nurse_id = professional.professional_id
                
                professional_data = nurse_data
                
        except Exception as e:
            return {
                'message': f'Error with professional: {str(e)}',
                'status': 'error'
            }, 500

        scheduled_date = ""
        scheduled_time = ""
        triage = False
        
        if consultation_type == "agendada":
            scheduled_date = data.get('scheduled_date')
            scheduled_time = data.get('scheduled_time')
            
            if not scheduled_date or not scheduled_time:
                return {
                    'message': 'For scheduled appointments, scheduled_date and scheduled_time are required (format: "2026-02-25" and "15:00")',
                    'status': 'error'
                }, 400
                
        elif consultation_type == "espontanea":
            scheduled_date = date.today().strftime('%Y-%m-%d') 
            scheduled_time = ""

        # Create consultation
        consultation = Consultation(
            patient_id=patient_id,
            patient_name=patient_name,
            patient_document=patient_document,
            patient_report=patient_report,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            doctor_credential=doctor_credential,
            professional_document=professional_document,
            nurse_id=nurse_id,
            nurse_name=nurse_name,
            specialty=specialty,
            rating=0,
            comment='',
            type=consultation_type,
        )
        
        # Generate hash based on consultation ID
        session_hash = create_telemedicine_hash(consultation.consultation_id)
        
        # Update consultation with generated links
        consultation.session_link = create_session_url(session_hash)
        consultation.doctor_link = f"{os.environ['URL_FRONTEND']}/intro-consultorio?session={session_hash}"
        consultation.session_hash = session_hash
        
        consultation_data = consultation.to_dict()

        req = PutRequest()
        req.set_table_name("consultations")
        req.set_value(consultation_data)

        handle.put(req)

        return {
            'message': f'Consultation {consultation_type} created successfully',
            'patient': convert_to_serializable(patient_data),
            'professional': convert_to_serializable(professional_data),
            'consultation': convert_to_serializable(consultation_data),
            'links': {
                'patient_link': consultation.session_link,
                'doctor_link': consultation.doctor_link,
                'session_hash': session_hash
            },
            'schedule': {
                'date': scheduled_date,
                'time': scheduled_time,
                'type': consultation_type
            }
        }, 201

@ns.route('listar')
class ListConsultations(Resource):
    @require_token
    def get(self):
        """Listar todas as teleconsultas"""
        handle = get_handle()

        req = QueryRequest().set_statement(
            "SELECT * FROM consultations"
        )

        result = handle.query(req)

        consultations = result.get_results()

        return {
            'message': 'Consultations listed successfully',
            'consultations': [convert_to_serializable(c) for c in consultations],
            'total': len(consultations)
        }, 200

@ns.route('buscar/<string:session_hash>')
class SearchConsultation(Resource):
    @require_token
    def get(self, session_hash):
        """Buscar teleconsulta por session_hash"""
        handle = get_handle()
        
        try:
            req = QueryRequest().set_statement(
                f"SELECT * FROM consultations WHERE session_hash = '{session_hash}'"
            )
            result = handle.query(req)
            teleatendimentos = result.get_results()
            
            if not teleatendimentos:
                return {
                    'message': 'Teleatendimento não encontrado',
                    'status': 'not_found',
                    'session_hash': session_hash
                }, 404
            
            teleatendimento = teleatendimentos[0]
            patient_id = teleatendimento.get('patient_id')
            usuario_id = teleatendimento.get('doctor_id') or teleatendimento.get('nurse_id')
            
            # Busca dados do paciente
            patient = None
            if patient_id:
                req_patient = QueryRequest().set_statement(
                    f"SELECT * FROM patients WHERE patient_id = '{patient_id}'"
                )
                result_patient = handle.query(req_patient)
                patients = result_patient.get_results()
                patient = patients[0] if patients else None
            
            # Busca dados do profissional
            usuario = None
            if usuario_id:
                req_user = QueryRequest().set_statement(
                    f"SELECT * FROM professionals WHERE professional_id = '{usuario_id}'"
                )
                result_user = handle.query(req_user)
                usuarios = result_user.get_results()
                usuario = usuarios[0] if usuarios else None
            
            return {
                'message': 'Teleatendimento encontrado com sucesso',
                'status': 'success',
                'consultation': convert_to_serializable(teleatendimento),
                'patient': convert_to_serializable(patient),
                'professional': convert_to_serializable(usuario),
                'doctor_link': teleatendimento.get('doctor_link'),
                'session_link': teleatendimento.get('session_link'),
                'session_hash': teleatendimento.get('session_hash')
            }, 200
            
        except Exception as e:
            return {
                'message': f'Erro ao buscar teleatendimento: {str(e)}',
                'status': 'error',
                'session_hash': session_hash
            }, 500

@ns.route('buscar_por_paciente/<string:patient_document>')
class SearchConsultationByPatient(Resource):
    @require_token
    def get(self, patient_document):
        """Buscar teleconsultas por documento do paciente"""
        handle = get_handle()
        
        patient_document = clean_document(patient_document)
        
        try:
            req = QueryRequest().set_statement(
                f"SELECT * FROM consultations WHERE patient_document = '{patient_document}'"
            )
            result = handle.query(req)
            teleatendimentos = result.get_results()
            
            if not teleatendimentos:
                return {
                    'message': 'Nenhum teleatendimento encontrado para este paciente',
                    'status': 'not_found',
                    'patient_document': patient_document
                }, 404
            
            return {
                'message': f'{len(teleatendimentos)} teleatendimento(s) encontrado(s) para este paciente',
                'status': 'success',
                'teleatendimentos': [convert_to_serializable(t) for t in teleatendimentos],
                'patient_document': patient_document
            }, 200
            
        except Exception as e:
            return {
                'message': f'Erro ao buscar teleatendimentos: {str(e)}',
                'status': 'error',
                'patient_document': patient_document
            }, 500

@ns.route('buscar_por_profissional/<string:professional_id>')
class SearchConsultationByProfessional(Resource):
    @require_token
    def get(self, professional_id):
        """Buscar teleconsultas por ID do profissional"""
        handle = get_handle()
        
        try:
            req = QueryRequest().set_statement(
                f"SELECT * FROM consultations WHERE doctor_id = '{professional_id}' OR nurse_id = '{professional_id}'"
            )
            result = handle.query(req)
            teleatendimentos = result.get_results()
            
            if not teleatendimentos:
                return {
                    'message': 'Nenhum teleatendimento encontrado para este profissional',
                    'status': 'not_found',
                    'professional_id': professional_id
                }, 404
            
            return {
                'message': f'{len(teleatendimentos)} teleatendimento(s) encontrado(s) para este profissional',
                'status': 'success',
                'teleatendimentos': [convert_to_serializable(t) for t in teleatendimentos],
                'professional_id': professional_id
            }, 200
            
        except Exception as e:
            return {
                'message': f'Erro ao buscar teleatendimentos: {str(e)}',
                'status': 'error',
                'professional_id': professional_id
            }, 500

@ns.route('atualizar_status')
class UpdateConsultationStatus(Resource):
    @require_token
    def patch(self):
        """Atualizar status da teleconsulta"""
        handle = get_handle()
        data = request.get_json() or {}
        session_hash = data.get('session_hash')
        new_status = data.get('status')

        if not session_hash or not new_status:
            return {
                'message': 'session_hash and status are required for update',
                'status': 'error'
            }, 400
        
        # Valida o status
        new_status = new_status.lower()
        if not is_valid_status(new_status):
            return {
                'message': f'Invalid status. Accepted status: {", ".join(TELEATENDIMENTO_STATUS_CHOICES)}',
                'status': 'error',
                'valid_status': TELEATENDIMENTO_STATUS_CHOICES,
                'labels': TELEATENDIMENTO_STATUS_LABELS
            }, 400

        try:
            req = QueryRequest().set_statement(
                f"SELECT * FROM consultations WHERE session_hash = '{session_hash}'"
            )
            result = handle.query(req)
            tele_list = result.get_results()
            if not tele_list:
                return {
                    'message': 'Consultation not found',
                    'status': 'not_found',
                    'session_hash': session_hash
                }, 404

            tele = tele_list[0]
            tele['status'] = new_status
            tele['updated_at'] = datetime.now(timezone.utc).isoformat()

            put_req = PutRequest()
            put_req.set_table_name("consultations")
            put_req.set_value(tele)
            handle.put(put_req)

            return {
                'message': 'Consultation status updated successfully',
                'status': 'success',
                'session_hash': session_hash,
                'new_status': new_status
            }, 200

        except Exception as e:
            return {
                'message': f'Error updating consultation: {str(e)}',
                'status': 'error'
            }, 500

@ns.route('atualizar_tempo')
class UpdateConsultationTime(Resource):
    @require_token
    def patch(self):
        """Atualizar tempo de consulta"""
        handle = get_handle()
        data = request.get_json() or {}
        session_hash = data.get('session_hash')
        consultation_time = data.get('consultation_time')

        if not session_hash or consultation_time is None:
            return {
                'message': 'session_hash and consultation_time are required for update',
                'status': 'error'
            }, 400

        try:
            req = QueryRequest().set_statement(
                f"SELECT * FROM consultations WHERE session_hash = '{session_hash}'"
            )
            result = handle.query(req)
            tele_list = result.get_results()
            if not tele_list:
                return {
                    'message': 'Consultation not found',
                    'status': 'not_found',
                    'session_hash': session_hash
                }, 404

            tele = tele_list[0]
            tele['time_consultation'] = consultation_time
            tele['updated_at'] = datetime.now(timezone.utc).isoformat()

            put_req = PutRequest()
            put_req.set_table_name("consultations")
            put_req.set_value(tele)
            handle.put(put_req)

            return {
                'message': 'Consultation time updated successfully',
                'status': 'success',
                'session_hash': session_hash,
                'consultation_time': consultation_time
            }, 200

        except Exception as e:
            return {
                'message': f'Error updating consultation time: {str(e)}',
                'status': 'error'
            }, 500

@ns.route('avaliar')
class RateConsultation(Resource):
    @require_token
    def post(self):
        """Avaliar uma teleconsulta"""
        handle = get_handle()

        data = request.get_json() or {}
        session_hash = data.get('session_hash')
        nota = data.get('nota')
        feedback = data.get('comentario')

        try:
            # Busca o teleatendimento pelo session_hash
            req = QueryRequest().set_statement(
                f"SELECT * FROM consultations WHERE session_hash = '{session_hash.upper()}'"
            )
            result = handle.query(req)
            teleatendimentos = result.get_results()
            
            if not teleatendimentos:
                return {
                    'message': 'Teleatendimento não encontrado para este hash',
                    'status': 'error'
                }, 404
            
            # Atualiza com os dados do profissional
            teleatendimento_data = teleatendimentos[0]

            teleatendimento_data['rating'] = nota
            teleatendimento_data['comment'] = feedback

            req = PutRequest()
            req.set_table_name("consultations")
            req.set_value(teleatendimento_data)
            handle.put(req)

        except Exception as e:
            return {
                'message': f'Erro ao avaliar a sessão: {str(e)}',
                'status': 'error'
            }, 500

        return {
            'message': 'Avaliação realizada com sucesso',
            'status': 'success'
        }, 200
