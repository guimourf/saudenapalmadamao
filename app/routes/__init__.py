from app.routes.routes import api_bp
from app.routes.patient_routes import ns as ns_patients
from app.routes.professional_routes import ns as ns_professionals
from app.routes.consultation_routes import ns as ns_consultations
from app.routes.services_routes import ns as ns_services

__all__ = [
    'api_bp',
    'ns_patients',
    'ns_professionals',
    'ns_consultations',
    'ns_services'
]
