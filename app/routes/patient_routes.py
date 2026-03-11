from app.models.patient import Patient
from app.utils.serializers import convert_to_serializable
from app.services.auth import require_token
from borneo import PutRequest, QueryRequest
from flask import request
from flask_restx import Resource, Namespace
from app.services.nosql import get_handle
from app.extensions import api
import re

def clean_document(document):
    """Remove caracteres não numéricos do documento"""
    if not document:
        return ""
    return re.sub(r'\D', '', document)

ns = Namespace('paciente', description='Endpoints de Pacientes')
api.add_namespace(ns, path='/paciente_')

@ns.route('criar')
class CreatePatient(Resource):
    @require_token
    def post(self):
        """Criar um novo paciente"""
        handle = get_handle()

        data = request.get_json() or {}
        name = data.get('name')
        document = clean_document(data.get('document', ''))
        
        if not name or not document:
            return {  
                'message': 'name and document are required',
                'status': 'error'
            }, 400

        # Check if patient with this document already exists
        try:
            req_search = QueryRequest().set_statement(
                f"SELECT * FROM patients WHERE document = '{document}'"
            )
            result_search = handle.query(req_search)
            existing_patients = result_search.get_results()
            
            if existing_patients:
                return {
                    'message': 'Patient with this document already exists',
                    'status': 'error',
                    'existing_patient': convert_to_serializable(existing_patients[0])
                }, 409
        except Exception as e:
            return {
                'message': f'Error checking for existing patient: {str(e)}',
                'status': 'error'
            }, 500

        patient = Patient(
            name=name,
            document=document
        )
        patient_data = patient.to_dict()

        req = PutRequest()
        req.set_table_name("patients")
        req.set_value(patient_data)

        handle.put(req)

        return {
            'message': 'Patient created successfully',
            'patient': convert_to_serializable(patient_data)
        }, 201
    
@ns.route('listar')
class ListPatients(Resource):
    @require_token
    def get(self):
        """Listar todos os pacientes"""
        handle = get_handle()

        req = QueryRequest().set_statement(
            "SELECT * FROM patients"
        )

        result = handle.query(req)

        patients = result.get_results()

        return {
            'message': 'Patients listed successfully',
            'patients': [convert_to_serializable(p) for p in patients],
            'total': len(patients)
        }, 200
