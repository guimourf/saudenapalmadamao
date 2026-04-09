import uuid
from datetime import datetime, timezone
from typing import Dict, Any


class Queue:
    def __init__(
        self,
        name: str = "",
        queue_id: str = None,
        description: str = "",
        status: str = "active",
    ):
        self.queue_id = queue_id or str(uuid.uuid4())
        self.id = self.queue_id
        self.name = name
        self.description = description
        self.status = status
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "queue_id": self.queue_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Queue":
        queue = cls(
            name=data.get("name", ""),
            queue_id=data.get("queue_id") or data.get("id"),
            description=data.get("description", ""),
            status=data.get("status", "active"),
        )
        queue.created_at = data.get("created_at", queue.created_at)
        queue.updated_at = data.get("updated_at", queue.updated_at)
        return queue


class QueueEntry:
    def __init__(
        self,
        queue_id: str = "",
        consultation_hash: str = "",
        patient_id: str = "",
        patient_name: str = "",
        patient_document: str = "",
        position: int = 0,
        entry_id: str = None,
        status: str = "waiting",
    ):
        self.entry_id = entry_id or str(uuid.uuid4())
        self.id = self.entry_id
        self.queue_id = queue_id
        self.consultation_hash = consultation_hash
        self.patient_id = patient_id
        self.patient_name = patient_name
        self.patient_document = patient_document
        self.position = position
        self.status = status
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.removed_at = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entry_id": self.entry_id,
            "queue_id": self.queue_id,
            "consultation_hash": self.consultation_hash,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "patient_document": self.patient_document,
            "position": self.position,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "removed_at": self.removed_at,
        }
