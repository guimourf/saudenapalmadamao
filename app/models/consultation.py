import uuid
from datetime import datetime, timezone
from typing import Dict, Any

class Consultation:
    def __init__(self, 
                 patient_id: str = "",
                 patient_name: str = "",
                 patient_document: str = "",
                 patient_report: str = "",
                 nurse_id: str = "",
                 nurse_name: str = "",
                 doctor_id: str = "",
                 doctor_name: str = "",
                 doctor_credential: str = "",
                 professional_document: str = "",
                 specialty: str = "",
                 meet_link: str = "",
                 session_link: str = "",
                 doctor_link: str = "",
                 session_hash: str = "",
                 rating: int = 0,
                 comment: str = "",
                 type: str = "",
                 consultation_id: str = None,
                 status: str = "waiting",
                 triage: bool = False,
                 scheduled_date: str = "",
                 scheduled_time: str = "",
                 time_consultation: int = 0):
        
        self.consultation_id = consultation_id or str(uuid.uuid4())
        self.patient_id = patient_id
        self.patient_name = patient_name
        self.patient_document = patient_document
        self.patient_report = patient_report
        self.nurse_id = nurse_id
        self.nurse_name = nurse_name
        self.doctor_id = doctor_id
        self.doctor_name = doctor_name
        self.doctor_credential = doctor_credential
        self.professional_document = professional_document
        self.specialty = specialty
        self.meet_link = meet_link
        self.session_link = session_link
        self.doctor_link = doctor_link
        self.session_hash = session_hash
        self.rating = rating
        self.comment = comment
        self.type = type
        self.status = status
        self.triage = triage
        self.time_consultation = time_consultation
        
        # Dates and times
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.triage_started_at = None
        self.referral_at = None
        self.consultation_started_at = None
        self.completed_at = None
        self.scheduled_date = scheduled_date
        self.scheduled_time = scheduled_time
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.consultation_id,
            "consultation_id": self.consultation_id,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "patient_document": self.patient_document,
            "patient_report": self.patient_report,
            "nurse_id": self.nurse_id,
            "nurse_name": self.nurse_name,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "doctor_credential": self.doctor_credential,
            "professional_document": self.professional_document,
            "specialty": self.specialty,
            "meet_link": self.meet_link,
            "session_link": self.session_link,
            "doctor_link": self.doctor_link,
            "session_hash": self.session_hash,
            "rating": self.rating,
            "comment": self.comment,
            "feedback": self.comment,
            "type": self.type,
            "status": self.status,
            "triage": self.triage,
            "time_consultation": self.time_consultation,
            "created_at": self.created_at,
            "triage_started_at": self.triage_started_at,
            "referral_at": self.referral_at,
            "consultation_started_at": self.consultation_started_at,
            "completed_at": self.completed_at,
            "scheduled_date": self.scheduled_date,
            "scheduled_time": self.scheduled_time,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Consultation':
        consultation = cls(
            patient_id=data.get("patient_id", ""),
            patient_name=data.get("patient_name", ""),
            patient_document=data.get("patient_document", ""),
            patient_report=data.get("patient_report", ""),
            nurse_id=data.get("nurse_id", ""),
            nurse_name=data.get("nurse_name", ""),
            doctor_id=data.get("doctor_id", ""),
            doctor_name=data.get("doctor_name", ""),
            doctor_credential=data.get("doctor_credential", ""),
            professional_document=data.get("professional_document", ""),
            specialty=data.get("specialty", ""),
            meet_link=data.get("meet_link", ""),
            session_link=data.get("session_link",""),
            type=data.get("type", ""),
            consultation_id=data.get("consultation_id") or data.get("id"),
            status=data.get("status", "waiting"),
            rating=data.get("rating", 0),
            comment=data.get("comment") or data.get("feedback", ""),
            triage=data.get("triage", False),
            time_consultation=data.get("time_consultation", 0)
        )
        consultation.created_at = data.get("created_at", consultation.created_at)
        consultation.triage_started_at = data.get("triage_started_at")
        consultation.referral_at = data.get("referral_at")
        consultation.consultation_started_at = data.get("consultation_started_at")
        consultation.completed_at = data.get("completed_at")
        consultation.scheduled_date = data.get("scheduled_date", "")
        consultation.scheduled_time = data.get("scheduled_time", "")
        return consultation
    
    def update_timestamp(self):
        """Updates the timestamp of last modification"""
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def update_status(self, new_status: str):
        """Updates the status of the consultation"""
        self.status = new_status
        self.update_timestamp()
        
        if new_status == "in_progress" and not self.consultation_started_at:
            self.consultation_started_at = self.updated_at
        elif new_status == "completed" and not self.completed_at:
            self.completed_at = self.updated_at
    
    def schedule_appointment(self, date: str, time: str):
        """Schedules the consultation for a specific date/time"""
        self.scheduled_date = date
        self.scheduled_time = time
        self.update_timestamp()