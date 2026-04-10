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


def _patient_filters_from_request_args(args):
    out = {}
    for key in args:
        if key.startswith("_"):
            continue
        raw = args.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        low = key.lower()
        if low in ("cpf", "doc"):
            field = "document"
        else:
            field = key
        out[field] = str(raw).strip()
    return out


def _patient_matches_field(patient, field: str, value: str) -> bool:
    stored = patient.get(field)
    if field == "document":
        return clean_document(str(stored or "")) == clean_document(value)
    if stored is None:
        return False
    return str(stored).strip().lower() == value.strip().lower()


def _list_patients_filtered(handle, filters: dict):
    patients = handle.find("patients")
    if not filters:
        filtered = patients
    else:
        filtered = [
            p
            for p in patients
            if all(
                _patient_matches_field(p, fname, fval)
                for fname, fval in filters.items()
            )
        ]
    return {
        "message": "Patients listed successfully",
        "status": "success",
        "filters": filters,
        "total": len(filtered),
        "patients": [convert_to_serializable(p) for p in filtered],
    }, 200


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
        """
        Lista pacientes. Query ?campo=valor filtra pelo campo no documento (AND).
        Ex.: ?document=123... ou ?cpf=... (vai para document). Sem params = todos.
        """
        handle = get_handle()
        filters = _patient_filters_from_request_args(request.args)
        return _list_patients_filtered(handle, filters)
