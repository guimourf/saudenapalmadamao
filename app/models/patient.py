import uuid
from datetime import datetime, timezone
from typing import Dict, Any

class Patient:
    def __init__(self, 
                 name: str = "",
                 patient_id: str = None,
                 document: str = "",
                 status: str = "active"):
        
        self.patient_id = patient_id or str(uuid.uuid4())
        self.name = name
        self.status = status
        self.document = document
        self.created_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "document": self.document,
            "status": self.status,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Patient':
        patient = cls(
            name=data.get("name", ""),
            patient_id=data.get("patient_id"),
            document=data.get("document", ""),
            status=data.get("status", "active")
        )
        patient.created_at = data.get("created_at", patient.created_at)
        return patient
