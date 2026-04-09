from app.services.session_link import create_session_url, create_telemedicine_hash
from app.services.meet import generate_jitsi_link
from app.services.jitsi_token import generate_jitsi_token
from app.services.auth import require_token
from app.models.consultation import Consultation
from app.models.professional import Professional
from app.models.patient import Patient
from app.models.queue import QueueEntry
from app.utils.serializers import convert_to_serializable, consultation_for_public_response
from flask import request
from flask_restx import Resource, Namespace
from app.services.nosql import get_handle
from app.routes.professional_routes import _professionals_by_document
from app.services.queue_assignment import (
    drain_waiting_with_available_nurses,
    find_consultations_by_session_hash,
    set_professional_availability_by_id,
)
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


def _recalculate_queue_positions(handle, queue_id):
    entries = handle.find("queue_entries", {"queue_id": queue_id})
    waiting_entries = [e for e in entries if e.get("status") == "waiting"]
    waiting_entries.sort(key=lambda item: item.get("created_at", ""))
    for idx, item in enumerate(waiting_entries, start=1):
        if item.get("position") != idx:
            item["position"] = idx
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            handle.save("queue_entries", item)

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
        patient_document = clean_document(data.get('document', '') or '')
        patient_report = data.get('patient_report', '')
        consultation_type = data.get('type')
        
        if not patient_name or not consultation_type:
            return {
                'message': 'patient_name and type are required',
                'status': 'error'
            }, 400

        if not patient_document:
            return {
                'message': 'document is required (patient CPF/document; apenas dígitos após normalização)',
                'status': 'error',
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

        # Dados de profissional/fila
        doctor_name = data.get('doctor_name', '').strip()
        doctor_id = ""
        doctor_credential = clean_document(data.get('doctor_credential', ''))
        professional_document = clean_document(data.get('professional_document', ''))
        specialty = data.get('specialty', '').strip()
        nurse_name = data.get('nurse_name', '').strip()
        nurse_id = ""
        queue_name = (data.get('queue_name') or '').strip()

        if consultation_type == "espontanea":
            if not queue_name:
                return {
                    'message': 'queue_name is required for espontanea consultation',
                    'status': 'error'
                }, 400
            # Espontânea entra na fila: não recebe profissional manualmente na criação
            doctor_name = ""
            doctor_id = ""
            doctor_credential = ""
            professional_document = ""
            specialty = ""
            nurse_name = ""
            nurse_id = ""
        else:
            # Agendada exige profissional
            if not doctor_name and not nurse_name:
                return {
                    'message': 'Either doctor_name or nurse_name is required',
                    'status': 'error'
                }, 400

        # Se médico foi informado, exige credencial e especialidade
        if consultation_type != "espontanea" and doctor_name:
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
            existing_consultations = handle.find("consultations")
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

        # Paciente: sempre localizar ou criar pelo documento (evita duplicata)
        try:
            existing_patients = handle.find(
                "patients", {"document": patient_document}
            )
            if existing_patients:
                patient_data = existing_patients[0]
                patient_id = patient_data.get('patient_id')
            else:
                patient = Patient(name=patient_name, document=patient_document)
                patient_data = patient.to_dict()
                handle.save("patients", patient_data)
                patient_id = patient.patient_id
        except Exception as e:
            return {
                'message': f'Error with patient: {str(e)}',
                'status': 'error'
            }, 500

        # Profissional (não espontânea): prioridade ao documento; evita cadastro duplicado
        professional_data = None
        try:
            if consultation_type != "espontanea" and doctor_name:
                doctor_data = None
                by_doc, _ = _professionals_by_document(handle, professional_document)
                medicos = [
                    p
                    for p in by_doc
                    if (p.get("profession") or "").strip() == "médico(a)"
                ]
                medico = medicos[0] if medicos else None

                if medico:
                    doctor_data = medico
                else:
                    if by_doc:
                        return {
                            'message': 'professional_document já cadastrado para outra profissão',
                            'status': 'error',
                            'existing_profession': (by_doc[0].get('profession') or ''),
                        }, 409
                    cred_list = handle.find(
                        "professionals", {"credential": doctor_credential}
                    )
                    if cred_list:
                        ex = cred_list[0]
                        ex_doc = clean_document(
                            ex.get("professional_document", "") or ""
                        )
                        if ex_doc and ex_doc != professional_document:
                            return {
                                'message': 'doctor_credential vinculada a outro professional_document',
                                'status': 'error',
                            }, 409
                        if professional_document and not ex_doc:
                            ex["professional_document"] = professional_document
                            ex["updated_at"] = datetime.now(timezone.utc).isoformat()
                            handle.save("professionals", ex)
                        doctor_data = ex
                    else:
                        doctor_new = Professional(
                            name=doctor_name,
                            profession="médico(a)",
                            credential=doctor_credential,
                            professional_document=professional_document,
                            specialty=specialty,
                        )
                        doctor_data = doctor_new.to_dict()
                        handle.save("professionals", doctor_data)

                doctor_id = doctor_data.get("professional_id", "")
                professional_data = doctor_data

            elif consultation_type != "espontanea" and nurse_name:
                if not professional_document:
                    return {
                        'message': 'professional_document is required when nurse_name is provided',
                        'status': 'error',
                    }, 400
                by_doc, _ = _professionals_by_document(handle, professional_document)
                enfermeiros = [
                    p
                    for p in by_doc
                    if (p.get("profession") or "").strip() == "enfermeiro(a)"
                ]
                if enfermeiros:
                    nurse_data = enfermeiros[0]
                else:
                    if by_doc:
                        return {
                            'message': 'professional_document já cadastrado para outra profissão',
                            'status': 'error',
                            'existing_profession': (by_doc[0].get('profession') or ''),
                        }, 409
                    nurse_new = Professional(
                        name=nurse_name,
                        profession="enfermeiro(a)",
                        credential=professional_document,
                        professional_document=professional_document,
                        specialty="",
                    )
                    nurse_data = nurse_new.to_dict()
                    handle.save("professionals", nurse_data)

                nurse_id = nurse_data.get("professional_id", "")
                professional_data = nurse_data

        except Exception as e:
            return {
                'message': f'Error with professional: {str(e)}',
                'status': 'error'
            }, 500

        scheduled_date = ""
        scheduled_time = ""
        triage = False
        queue_status = ""
        queue_data = None
        
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
            queue_status = "waiting"
            try:
                queues = handle.find("queues", {"name": queue_name})
                active_queues = [q for q in queues if q.get("status") == "active"]
                if not active_queues:
                    return {
                        'message': 'Active queue not found for queue_name',
                        'status': 'error',
                        'queue_name': queue_name
                    }, 404
                queue_data = active_queues[0]

                queue_entries = handle.find(
                    "queue_entries", {"queue_id": queue_data.get("queue_id")}
                )
                duplicate = [
                    e
                    for e in queue_entries
                    if e.get("status") == "waiting"
                    and (
                        (patient_id and e.get("patient_id") == patient_id)
                        or (
                            patient_document
                            and e.get("patient_document") == patient_document
                        )
                    )
                ]
                if duplicate:
                    return {
                        'message': 'Patient already in queue',
                        'status': 'error',
                        'queue_name': queue_name,
                        'entry': convert_to_serializable(duplicate[0]),
                    }, 409
            except Exception as e:
                return {
                    'message': f'Error validating queue for espontanea consultation: {str(e)}',
                    'status': 'error',
                }, 500

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
            queue_name=queue_name if consultation_type == "espontanea" else "",
            queue_status=queue_status,
        )
        
        # Generate hash based on consultation ID
        session_hash = create_telemedicine_hash(consultation.consultation_id)
        room_name = f"Teleconsulta-{session_hash.upper()}"
        meet_link = ""
        host_url = ""
        if consultation_type != "espontanea":
            try:
                meet_link = generate_jitsi_link(room_name)
            except ValueError as e:
                return {
                    'message': str(e),
                    'status': 'error',
                }, 500

            professional_email = (
                data.get('professional_email') or data.get('doctor_email') or ''
            )
            professional_email = professional_email.strip() or None
            host_name = (doctor_name or nurse_name).strip()
            host_user_id = doctor_id if doctor_name else nurse_id

            try:
                jitsi_out = generate_jitsi_token(
                    room_name,
                    host_name,
                    'medico',
                    host_user_id,
                    professional_email,
                    'owner',
                )
            except Exception as e:
                return {
                    'message': f'Erro ao gerar host_url (Jitsi): {str(e)}',
                    'status': 'error',
                }, 500

            host_url = jitsi_out.get('host_url') or ''
            if not host_url:
                return {
                    'message': 'host_url exige JWT Jitsi (env) e JITSI_PUBLIC_URL configurados',
                    'status': 'error',
                }, 500

        consultation.session_link = create_session_url(session_hash)
        consultation.doctor_link = (
            f"{os.environ['URL_FRONTEND']}intro-consultorio?session={session_hash}"
            if consultation_type != "espontanea"
            else ""
        )
        consultation.session_hash = session_hash
        consultation.meet_link = meet_link
        consultation.host_url = host_url
        
        consultation_data = consultation.to_dict()
        handle.save("consultations", consultation_data)

        queue_entry_data = None
        queue_position = None
        auto_assignments = []
        if consultation_type == "espontanea" and queue_data:
            queue_entry = QueueEntry(
                queue_id=queue_data.get("queue_id") or queue_data.get("id") or "",
                consultation_hash=session_hash,
                patient_id=patient_id,
                patient_name=patient_name,
                patient_document=patient_document,
                position=0,
            )
            queue_entry_data = queue_entry.to_dict()
            handle.save("queue_entries", queue_entry_data)

            waiting_entries = handle.find(
                "queue_entries", {"queue_id": queue_entry_data.get("queue_id")}
            )
            waiting_entries = [e for e in waiting_entries if e.get("status") == "waiting"]
            waiting_entries.sort(key=lambda item: item.get("created_at", ""))
            for idx, item in enumerate(waiting_entries, start=1):
                if item.get("position") != idx:
                    item["position"] = idx
                    item["updated_at"] = datetime.now(timezone.utc).isoformat()
                    handle.save("queue_entries", item)
                if item.get("entry_id") == queue_entry_data.get("entry_id"):
                    queue_position = idx

            drain = drain_waiting_with_available_nurses(handle)
            auto_assignments = drain.get("assignments") or []
            tele_refresh = find_consultations_by_session_hash(handle, session_hash)
            if tele_refresh:
                consultation_data = tele_refresh[0]
            refreshed_entry = handle.find(
                "queue_entries", {"entry_id": queue_entry.entry_id}
            )
            if refreshed_entry:
                queue_entry_data = refreshed_entry[0]

        return {
            'message': f'Consultation {consultation_type} created successfully',
            'patient': convert_to_serializable(patient_data),
            'professional': convert_to_serializable(professional_data),
            'consultation': consultation_for_public_response(consultation_data),
            'queue': convert_to_serializable({
                'queue_id': queue_data.get("queue_id") if queue_data else None,
                'queue_name': queue_name if consultation_type == "espontanea" else "",
                'queue_status': queue_status,
                'entry': queue_entry_data,
                'position': queue_position,
            }),
            'links': {
                'patient_link': consultation.session_link,
                'doctor_link': consultation.doctor_link,
                'session_hash': session_hash,
            },
            'schedule': {
                'date': scheduled_date,
                'time': scheduled_time,
                'type': consultation_type
            },
            'auto_assignments': convert_to_serializable(auto_assignments),
        }, 201

@ns.route('listar')
class ListConsultations(Resource):
    @require_token
    def get(self):
        """Listar todas as teleconsultas"""
        handle = get_handle()

        consultations = handle.find("consultations")

        return {
            'message': 'Consultations listed successfully',
            'consultations': [consultation_for_public_response(c) for c in consultations],
            'total': len(consultations)
        }, 200

@ns.route('buscar/<string:session_hash>')
class SearchConsultation(Resource):
    @require_token
    def get(self, session_hash):
        """Buscar teleconsulta por session_hash"""
        handle = get_handle()
        
        try:
            teleatendimentos = handle.find(
                "consultations", {"session_hash": session_hash}
            )
            
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
                patients = handle.find("patients", {"patient_id": patient_id})
                patient = patients[0] if patients else None
            
            # Busca dados do profissional
            usuario = None
            if usuario_id:
                usuarios = handle.find(
                    "professionals", {"professional_id": usuario_id}
                )
                usuario = usuarios[0] if usuarios else None

            if usuario:
                udoc = clean_document(usuario.get("professional_document") or "")
                if udoc and not clean_document(
                    teleatendimento.get("professional_document") or ""
                ):
                    teleatendimento = dict(teleatendimento)
                    teleatendimento["professional_document"] = udoc
                    teleatendimento["updated_at"] = (
                        datetime.now(timezone.utc).isoformat()
                    )
                    handle.save("consultations", teleatendimento)

            return {
                'message': 'Teleatendimento encontrado com sucesso',
                'status': 'success',
                'consultation': consultation_for_public_response(teleatendimento),
                'patient': convert_to_serializable(patient),
                'professional': convert_to_serializable(usuario),
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
            teleatendimentos = handle.find(
                "consultations", {"patient_document": patient_document}
            )
            if not teleatendimentos:
                return {
                    'message': 'Nenhum teleatendimento encontrado para este paciente',
                    'status': 'not_found',
                    'patient_document': patient_document
                }, 404
            
            return {
                'message': f'{len(teleatendimentos)} teleatendimento(s) encontrado(s) para este paciente',
                'status': 'success',
                'teleatendimentos': [consultation_for_public_response(t) for t in teleatendimentos],
                'patient_document': patient_document
            }, 200
            
        except Exception as e:
            return {
                'message': f'Erro ao buscar teleatendimentos: {str(e)}',
                'status': 'error',
                'patient_document': patient_document
            }, 500

@ns.route('buscar_por_profissional/<string:professional_document>')
class SearchConsultationByProfessional(Resource):
    @require_token
    def get(self, professional_document):
        handle = get_handle()
        doc = clean_document(professional_document)

        if not doc:
            return {
                'message': 'professional_document inválido ou vazio',
                'status': 'error',
            }, 400

        try:
            profs, _ = _professionals_by_document(handle, doc)
            if not profs:
                return {
                    'message': 'Profissional não encontrado para este documento',
                    'status': 'not_found',
                    'professional_document': doc,
                }, 404

            professional_ids = list(
                dict.fromkeys(
                    (p.get('professional_id') or '').strip()
                    for p in profs
                    if (p.get('professional_id') or '').strip()
                )
            )

            seen = set()
            teleatendimentos = []
            for pid in professional_ids:
                for t in handle.find(
                    "consultations",
                    {"$or": [{"doctor_id": pid}, {"nurse_id": pid}]},
                ):
                    cid = t.get('consultation_id') or t.get('id')
                    if cid and cid not in seen:
                        seen.add(cid)
                        teleatendimentos.append(t)

            if not teleatendimentos:
                return {
                    'message': 'Nenhum teleatendimento encontrado para este profissional',
                    'status': 'not_found',
                    'professional_document': doc,
                }, 404

            return {
                'message': f'{len(teleatendimentos)} teleatendimento(s) encontrado(s) para este profissional',
                'status': 'success',
                'teleatendimentos': [consultation_for_public_response(t) for t in teleatendimentos],
                'professional_document': doc,
            }, 200

        except Exception as e:
            return {
                'message': f'Erro ao buscar teleatendimentos: {str(e)}',
                'status': 'error',
                'professional_document': doc,
            }, 500


@ns.route('inserir_enfermeiro')
class InsertNurseIntoConsultation(Resource):
    @require_token
    def patch(self):
        handle = get_handle()
        data = request.get_json() or {}

        professional_document = clean_document(data.get('professional_document') or '')
        queue_name = (data.get('queue_name') or '').strip()
        session_hash = (data.get('session_hash') or '').strip().upper()

        if not professional_document or not queue_name or not session_hash:
            return {
                'message': 'professional_document, queue_name and session_hash are required',
                'status': 'error',
            }, 400

        try:
            professionals, _ = _professionals_by_document(
                handle, professional_document
            )
            nurse = next(
                (
                    p for p in professionals
                    if (p.get("profession") or "").strip() == "enfermeiro(a)"
                ),
                None,
            )
            if not nurse:
                return {
                    'message': 'Nurse not found for professional_document',
                    'status': 'not_found',
                    'professional_document': professional_document,
                }, 404

            queues = handle.find("queues", {"name": queue_name})
            active_queues = [q for q in queues if q.get("status") == "active"]
            if not active_queues:
                return {
                    'message': 'Active queue not found for queue_name',
                    'status': 'not_found',
                    'queue_name': queue_name,
                }, 404
            queue = active_queues[0]
            queue_id = queue.get("queue_id") or queue.get("id")

            tele_list = handle.find("consultations", {"session_hash": session_hash})
            if not tele_list:
                return {
                    'message': 'Consultation not found',
                    'status': 'not_found',
                    'session_hash': session_hash,
                }, 404
            tele = tele_list[0]

            entries = handle.find("queue_entries", {"queue_id": queue_id})
            entry = next(
                (
                    e
                    for e in entries
                    if (e.get("consultation_hash") or "").strip().upper() == session_hash
                    and e.get("status") == "waiting"
                ),
                None,
            )
            if not entry:
                return {
                    'message': 'Waiting queue entry not found for this consultation in queue',
                    'status': 'not_found',
                    'queue_name': queue_name,
                    'session_hash': session_hash,
                }, 404

            tele["nurse_id"] = nurse.get("professional_id", "")
            tele["nurse_name"] = nurse.get("name", "")
            ndoc = clean_document(nurse.get("professional_document") or "")
            if ndoc:
                tele["professional_document"] = ndoc
            tele["queue_name"] = queue_name
            tele["queue_status"] = ""
            tele["status"] = "waiting"
            tele["updated_at"] = datetime.now(timezone.utc).isoformat()
            handle.save("consultations", tele)

            set_professional_availability_by_id(
                handle, tele.get("nurse_id") or "", "busy"
            )

            entry["status"] = "removed"
            entry["position"] = 0
            entry["removed_at"] = datetime.now(timezone.utc).isoformat()
            entry["updated_at"] = entry["removed_at"]
            handle.save("queue_entries", entry)
            _recalculate_queue_positions(handle, queue_id)

            return {
                'message': 'Nurse inserted into consultation successfully',
                'status': 'success',
                'consultation': consultation_for_public_response(tele),
                'queue_entry': convert_to_serializable(entry),
            }, 200
        except Exception as e:
            return {
                'message': f'Error inserting nurse into consultation: {str(e)}',
                'status': 'error',
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
            tele_list = handle.find(
                "consultations", {"session_hash": session_hash}
            )
            if not tele_list:
                return {
                    'message': 'Consultation not found',
                    'status': 'not_found',
                    'session_hash': session_hash
                }, 404

            tele = tele_list[0]
            prev_nurse_id = (tele.get("nurse_id") or "").strip()
            tele['status'] = new_status
            tele['updated_at'] = datetime.now(timezone.utc).isoformat()

            handle.save("consultations", tele)

            if new_status in ("completed", "cancelled") and prev_nurse_id:
                set_professional_availability_by_id(
                    handle, prev_nurse_id, "available"
                )

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
            tele_list = handle.find(
                "consultations", {"session_hash": session_hash}
            )
            if not tele_list:
                return {
                    'message': 'Consultation not found',
                    'status': 'not_found',
                    'session_hash': session_hash
                }, 404

            tele = tele_list[0]
            tele['time_consultation'] = consultation_time
            tele['updated_at'] = datetime.now(timezone.utc).isoformat()

            handle.save("consultations", tele)

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
            teleatendimentos = handle.find(
                "consultations",
                {"session_hash": (session_hash or "").strip().upper()},
            )
            if not teleatendimentos:
                return {
                    'message': 'Teleatendimento não encontrado para este hash',
                    'status': 'error'
                }, 404

            teleatendimento_data = teleatendimentos[0]
            teleatendimento_data['rating'] = nota
            teleatendimento_data['comment'] = feedback

            handle.save("consultations", teleatendimento_data)

        except Exception as e:
            return {
                'message': f'Erro ao avaliar a sessão: {str(e)}',
                'status': 'error'
            }, 500

        return {
            'message': 'Avaliação realizada com sucesso',
            'status': 'success'
        }, 200
