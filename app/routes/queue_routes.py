from datetime import datetime, timezone
from app.models.queue import Queue, QueueEntry
from app.models.patient import Patient
from app.utils.serializers import convert_to_serializable
from app.services.auth import require_token
from flask import request
from flask_restx import Resource, Namespace
from app.services.nosql import get_handle
from app.services.queue_assignment import drain_waiting_with_available_nurses
from app.extensions import api
import re

ns = Namespace("fila", description="Endpoints de Filas")
api.add_namespace(ns, path="/fila_")


def clean_document(document):
    if not document:
        return ""
    return re.sub(r"\D", "", document)


def recalculate_queue_positions(handle, queue_id):
    entries = handle.find("queue_entries", {"queue_id": queue_id})
    waiting_entries = [e for e in entries if e.get("status") == "waiting"]
    waiting_entries.sort(key=lambda item: item.get("created_at", ""))
    for idx, item in enumerate(waiting_entries, start=1):
        if item.get("position") != idx:
            item["position"] = idx
            item["updated_at"] = datetime.now(timezone.utc).isoformat()
            handle.save("queue_entries", item)
    return waiting_entries


def add_patient_to_queue(handle, data):
    queue_id = (data.get("queue_id") or "").strip()
    patient_name = (data.get("patient_name") or "").strip()
    patient_document = clean_document(data.get("patient_document", ""))
    consultation_hash = (data.get("consultation_hash") or "").strip().upper()

    if not queue_id:
        return {"message": "queue_id is required", "status": "error"}, 400

    missing = []
    if not patient_name:
        missing.append("patient_name (nome do paciente)")
    if not patient_document:
        missing.append("patient_document (documento do paciente)")
    if missing:
        return {
            "message": "Envie nome e documento do paciente no JSON.",
            "status": "error",
            "missing": missing,
            "required": {
                "patient_name": "nome completo do paciente",
                "patient_document": "CPF ou documento (apenas números após normalização)",
            },
        }, 400

    try:
        queues = handle.find("queues", {"queue_id": queue_id})
        if not queues:
            return {"message": "Queue not found", "status": "error"}, 404
        if queues[0].get("status") != "active":
            return {"message": "Queue is not active", "status": "error"}, 409
    except Exception as e:
        return {
            "message": f"Error checking queue: {str(e)}",
            "status": "error",
        }, 500

    try:
        patients = handle.find("patients", {"document": patient_document})
        if patients:
            matched_patient = patients[0]
        else:
            patient = Patient(name=patient_name, document=patient_document)
            matched_patient = patient.to_dict()
            handle.save("patients", matched_patient)

        patient_id = matched_patient.get("patient_id", "")

        entries = handle.find("queue_entries", {"queue_id": queue_id})
        waiting_entries = [e for e in entries if e.get("status") == "waiting"]
        duplicate = [
            e
            for e in waiting_entries
            if (patient_id and e.get("patient_id") == patient_id)
            or (patient_document and e.get("patient_document") == patient_document)
        ]
        if duplicate:
            return {
                "message": "Patient already in queue",
                "status": "error",
                "entry": convert_to_serializable(duplicate[0]),
            }, 409
    except Exception as e:
        return {
            "message": f"Error checking queue entries: {str(e)}",
            "status": "error",
        }, 500

    entry = QueueEntry(
        queue_id=queue_id,
        consultation_hash=consultation_hash,
        patient_id=patient_id,
        patient_name=patient_name,
        patient_document=patient_document,
        position=0,
    )
    entry_data = entry.to_dict()

    handle.save("queue_entries", entry_data)

    waiting_entries = recalculate_queue_positions(handle, queue_id)
    position = next(
        (
            item.get("position")
            for item in waiting_entries
            if item.get("entry_id") == entry.entry_id
        ),
        len(waiting_entries),
    )

    drain = drain_waiting_with_available_nurses(handle)
    this_entry_assigned = next(
        (
            a
            for a in drain.get("assignments") or []
            if a.get("entry_id") == entry.entry_id
        ),
        None,
    )

    waiting_after = recalculate_queue_positions(handle, queue_id)
    queue_size = len(waiting_after)
    refreshed = handle.find("queue_entries", {"entry_id": entry.entry_id})
    if refreshed:
        entry_data = refreshed[0]
    if this_entry_assigned:
        position = 0

    return {
        "message": "Patient added to queue successfully",
        "status": "success",
        "entry": convert_to_serializable(entry_data),
        "position": position,
        "queue_size": queue_size,
        "auto_assignments": convert_to_serializable(drain.get("assignments") or []),
        "auto_assign_count": drain.get("count", 0),
        "assigned_to_this_entry": convert_to_serializable(this_entry_assigned),
    }, 201


def pop_from_queue(handle, data):
    queue_id = (data.get("queue_id") or "").strip()
    patient_document = clean_document(data.get("patient_document", "") or "")

    if not queue_id:
        return {"message": "queue_id is required", "status": "error"}, 400

    try:
        entries = handle.find("queue_entries", {"queue_id": queue_id})
        waiting_entries = [e for e in entries if e.get("status") == "waiting"]
        waiting_entries.sort(key=lambda item: item.get("created_at", ""))

        if patient_document:
            candidates = [
                e
                for e in waiting_entries
                if clean_document(e.get("patient_document", "") or "") == patient_document
            ]
            if not candidates:
                return {
                    "message": "Nenhum paciente em espera nesta fila com este patient_document",
                    "status": "not_found",
                    "patient_document": patient_document,
                    "queue_id": queue_id,
                }, 404
            candidates.sort(key=lambda item: item.get("created_at", ""))
            next_entry = candidates[0]
        else:
            if not waiting_entries:
                return {
                    "message": "Não há pacientes na fila para remover",
                    "status": "not_found",
                    "queue_id": queue_id,
                }, 404
            next_entry = waiting_entries[0]

        next_entry["status"] = "removed"
        next_entry["position"] = 0
        next_entry["removed_at"] = datetime.now(timezone.utc).isoformat()
        next_entry["updated_at"] = next_entry["removed_at"]

        handle.save("queue_entries", next_entry)
        waiting_entries = recalculate_queue_positions(handle, queue_id)

        remaining = len(waiting_entries)
        return {
            "message": "Patient removed from queue",
            "status": "success",
            "entry": convert_to_serializable(next_entry),
            "remaining": max(remaining, 0),
        }, 200
    except Exception as e:
        return {
            "message": f"Error removing from queue: {str(e)}",
            "status": "error",
        }, 500


def waiting_for_queue(handle, queue_id):
    queue_id = (queue_id or "").strip()
    if not queue_id:
        return {"message": "queue_id is required", "status": "error"}, 400

    try:
        queues = handle.find("queues", {"queue_id": queue_id})
        if not queues:
            return {"message": "Queue not found", "status": "error"}, 404

        entries = handle.find("queue_entries", {"queue_id": queue_id})
        waiting_entries = [e for e in entries if e.get("status") == "waiting"]
        waiting_entries.sort(key=lambda item: item.get("created_at", ""))

        patients = []
        for idx, entry in enumerate(waiting_entries):
            patients.append(
                convert_to_serializable(
                    {
                        "entry_id": entry.get("entry_id"),
                        "consultation_hash": entry.get("consultation_hash") or "",
                        "patient_id": entry.get("patient_id"),
                        "patient_name": entry.get("patient_name"),
                        "patient_document": entry.get("patient_document"),
                        "created_at": entry.get("created_at"),
                        "position": entry.get("position") or (idx + 1),
                    }
                )
            )

        return {
            "message": "Waiting queue retrieved successfully",
            "status": "success",
            "queue_id": queue_id,
            "count": len(patients),
            "patients": patients,
        }, 200
    except Exception as e:
        return {
            "message": f"Error listing waiting queue: {str(e)}",
            "status": "error",
        }, 500


@ns.route("criar")
class CreateQueue(Resource):
    @require_token
    def post(self):
        handle = get_handle()
        data = request.get_json() or {}

        name = (data.get("name") or "").strip()
        description = (data.get("description") or "").strip()

        if not name:
            return {"message": "name is required", "status": "error"}, 400

        try:
            existing = handle.find("queues", {"name": name})
            active_existing = [q for q in existing if q.get("status") == "active"]
            if active_existing:
                return {
                    "message": "Queue with this name already exists",
                    "status": "error",
                    "queue": convert_to_serializable(active_existing[0]),
                }, 409
        except Exception as e:
            return {
                "message": f"Error checking queue name: {str(e)}",
                "status": "error",
            }, 500

        queue = Queue(name=name, description=description)
        queue_data = queue.to_dict()

        handle.save("queues", queue_data)

        return {
            "message": "Queue created successfully",
            "status": "success",
            "queue": convert_to_serializable(queue_data),
        }, 201


@ns.route("adicionar")
class AddPatientToQueue(Resource):
    @require_token
    def post(self):
        handle = get_handle()
        data = request.get_json() or {}
        body, code = add_patient_to_queue(handle, data)
        return body, code


@ns.route("add")
class AddPatientToQueueEn(Resource):
    @require_token
    def post(self):
        handle = get_handle()
        data = request.get_json() or {}
        body, code = add_patient_to_queue(handle, data)
        return body, code


@ns.route("remover")
class PopQueue(Resource):
    @require_token
    def post(self):
        handle = get_handle()
        data = request.get_json() or {}
        body, code = pop_from_queue(handle, data)
        return body, code


@ns.route("pop")
class PopQueueEn(Resource):
    @require_token
    def post(self):
        handle = get_handle()
        data = request.get_json() or {}
        body, code = pop_from_queue(handle, data)
        return body, code


@ns.route("espera/<string:queue_id>")
class QueueWaiting(Resource):
    @require_token
    def get(self, queue_id):
        handle = get_handle()
        body, code = waiting_for_queue(handle, queue_id)
        return body, code


@ns.route("listar")
class ListQueues(Resource):
    @require_token
    def get(self):
        handle = get_handle()
        try:
            queues = handle.find("queues")
            queues.sort(key=lambda item: item.get("created_at", ""))

            entries = handle.find("queue_entries")
            waiting_entries = [e for e in entries if e.get("status") == "waiting"]
            waiting_entries.sort(key=lambda item: item.get("created_at", ""))

            queue_map = {}
            for queue in queues:
                qid = queue.get("queue_id") or queue.get("id")
                queue_map[qid] = {
                    "queue": convert_to_serializable(queue),
                    "patients": [],
                    "total": 0,
                }

            for entry in waiting_entries:
                qid = entry.get("queue_id")
                if qid not in queue_map:
                    continue
                patient_item = {
                    "entry_id": entry.get("entry_id"),
                    "consultation_hash": entry.get("consultation_hash") or "",
                    "patient_id": entry.get("patient_id"),
                    "patient_name": entry.get("patient_name"),
                    "patient_document": entry.get("patient_document"),
                    "created_at": entry.get("created_at"),
                    "position": entry.get("position") or (len(queue_map[qid]["patients"]) + 1),
                }
                queue_map[qid]["patients"].append(convert_to_serializable(patient_item))

            queues_with_patients = []
            for queue in queues:
                qid = queue.get("queue_id") or queue.get("id")
                queue_info = queue_map.get(
                    qid, {"queue": convert_to_serializable(queue), "patients": []}
                )
                queue_info["total"] = len(queue_info["patients"])
                queues_with_patients.append(queue_info)

            return {
                "message": "Queues listed successfully",
                "status": "success",
                "queues": queues_with_patients,
                "total": len(queues_with_patients),
            }, 200
        except Exception as e:
            return {
                "message": f"Error listing queues: {str(e)}",
                "status": "error",
            }, 500
