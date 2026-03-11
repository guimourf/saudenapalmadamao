from app.models.professional import Professional
from app.utils.serializers import convert_to_serializable
from app.services.auth import require_token
from borneo import PutRequest, QueryRequest
from flask import request
from flask_restx import Resource, Namespace
from app.services.nosql import get_handle
from app.extensions import api
from app.constants import (
    PROFESSION_CHOICES,
    PROFESSION_LABELS,
    is_valid_profession,
)
import re

def clean_document(document):
    """Remove caracteres não numéricos do documento"""
    if not document:
        return ""
    return re.sub(r'\D', '', document)

ns = Namespace('profissional', description='Endpoints de Profissionais')
api.add_namespace(ns, path='/profissional_')

@ns.route('criar')
class CreateProfessional(Resource):
    @require_token
    def post(self):
        """Criar um novo profissional"""
        handle = get_handle()

        data = request.get_json() or {}
        
        name = data.get('name', '').strip()
        profession = data.get('profession', '').strip()
        credential = clean_document(data.get('credential', ''))
        professional_document = clean_document(data.get('professional_document', ''))
        specialty = data.get('specialty', '').strip()
        
        # Validation
        if not name:
            return {
                'message': 'name is required',
                'status': 'error'
            }, 400
        
        if not profession:
            return {
                'message': 'profession is required',
                'status': 'error',
                'valid_professions': PROFESSION_CHOICES,
                'labels': PROFESSION_LABELS
            }, 400
        
        if not is_valid_profession(profession):
            return {
                'message': f'Invalid profession. Accepted professions: {", ".join(PROFESSION_CHOICES)}',
                'status': 'error',
                'valid_professions': PROFESSION_CHOICES,
                'labels': PROFESSION_LABELS
            }, 400
        
        if not credential:
            return {
                'message': 'credential is required',
                'status': 'error'
            }, 400
        
        if not professional_document:
            return {
                'message': 'professional_document is required',
                'status': 'error'
            }, 400

        # Check if professional with this document already exists
        try:
            req_search = QueryRequest().set_statement(
                f"SELECT * FROM professionals WHERE professional_document = '{professional_document}'"
            )
            result_search = handle.query(req_search)
            existing_professionals = result_search.get_results()
            
            if existing_professionals:
                return {
                    'message': 'Professional with this document already exists',
                    'status': 'error',
                    'existing_professional': convert_to_serializable(existing_professionals[0])
                }, 409
        except Exception as e:
            return {
                'message': f'Error checking for existing professional: {str(e)}',
                'status': 'error'
            }, 500

        professional = Professional(
            name=name,
            profession=profession,
            credential=credential,
            professional_document=professional_document,
            specialty=specialty
        )
        professional_data = professional.to_dict()

        req = PutRequest()
        req.set_table_name("professionals")
        req.set_value(professional_data)

        handle.put(req)

        return {
            'message': 'Professional created successfully',
            'professional': convert_to_serializable(professional_data)
        }, 201
    
@ns.route('listar')
class ListProfessionals(Resource):
    @require_token
    def get(self):
        """Listar todos os profissionais"""
        handle = get_handle()

        req = QueryRequest().set_statement(
            "SELECT * FROM professionals"
        )

        result = handle.query(req)

        professionals = result.get_results()

        return {
            'message': 'Professionals listed successfully',
            'professionals': convert_to_serializable(professionals)
        }, 200
