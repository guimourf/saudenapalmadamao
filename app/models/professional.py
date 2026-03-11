import uuid
from datetime import datetime, timezone
from typing import Dict, Any

class Professional:
    def __init__(self, 
                 name: str = "",
                 professional_id: str = None,
                 profession: str = "",
                 credential: str = "",
                 professional_document: str = "",
                 specialty: str = "",
                 status: str = "active"):
        
        self.professional_id = professional_id or str(uuid.uuid4())
        self.name = name
        self.profession = profession
        self.credential = credential
        self.professional_document = professional_document
        self.specialty = specialty
        self.status = status
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "professional_id": self.professional_id,
            "name": self.name,
            "profession": self.profession,
            "credential": self.credential,
            "professional_document": self.professional_document,
            "specialty": self.specialty,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Professional':
        professional = cls(
            name=data.get("name", ""),
            professional_id=data.get("professional_id"),
            profession=data.get("profession", ""),
            credential=data.get("credential", ""),
            professional_document=data.get("professional_document", ""),
            specialty=data.get("specialty", ""),
            status=data.get("status", "active")
        )
        professional.created_at = data.get("created_at", professional.created_at)
        professional.updated_at = data.get("updated_at", professional.updated_at)
        return professional