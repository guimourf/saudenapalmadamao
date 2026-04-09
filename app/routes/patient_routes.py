from app.models.patient import Patient
from app.utils.serializers import convert_to_serializable
from app.services.auth import require_token
from flask import request
from flask_restx import Resource, Namespace
from app.services.nosql import get_handle
from app.extensions import api
import re

def clean_document(document):
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
        name = (data.get('name') or '').strip()
        document = clean_document(data.get('document', ''))
        
        if not name or not document:
            return {  
                'message': 'name and document are required',
                'status': 'error'
            }, 400

        try:
            existing_patients = handle.find("patients", {"document": document})
            
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

        handle.save("patients", patient_data)

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

        patients = handle.find("patients")

        return {
            'message': 'Patients listed successfully',
            'patients': [convert_to_serializable(p) for p in patients],
            'total': len(patients)
        }, 200
