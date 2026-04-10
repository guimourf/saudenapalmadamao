from app.models.professional import Professional
from app.utils.serializers import convert_to_serializable
from app.services.auth import require_token
from flask import request
from flask_restx import Resource, Namespace
from app.services.nosql import get_handle
from app.services.queue_assignment import (
    coerce_professional_cadastro_status,
    drain_waiting_with_available_nurses,
    list_nurses_marked_available,
)
from app.extensions import api
from datetime import datetime, timezone

from app.constants import (
    PROFESSION_CHOICES,
    PROFESSION_LABELS,
    NURSE_PROFESSION,
    PHYSICIAN_PROFESSION,
    PROFESSIONAL_AVAILABILITY_CHOICES,
    PROFESSIONAL_AVAILABILITY_LABELS,
    PROFESSIONAL_STATUS_CHOICES,
    PROFESSIONAL_STATUS_LABELS,
    canonical_profession,
    canonical_professional_availability,
    is_valid_profession,
    is_valid_professional_status,
)
import re

def clean_document(document):
    """Remove caracteres não numéricos do documento"""
    if not document:
        return ""
    return re.sub(r'\D', '', document)


def _professionals_by_document(handle, raw_document):
    """
    Profissionais cujo professional_document bate com raw_document após limpeza.
    Cobre string numérica no Mongo, número (legado) e formatação só com máscara no campo.
    """
    doc = clean_document(raw_document)
    if not doc:
        return [], doc
    or_clauses = [{"professional_document": doc}]
    if doc.isdigit():
        try:
            or_clauses.append({"professional_document": int(doc)})
        except ValueError:
            pass
    rows = handle.find("professionals", {"$or": or_clauses})
    if rows:
        return rows, doc
    matches = [
        p
        for p in handle.find("professionals")
        if clean_document(str(p.get("professional_document") or "")) == doc
    ]
    return matches, doc


def _professional_by_document(handle, raw_document):
    doc = clean_document(raw_document)
    if not doc:
        return None, doc
    rows, _ = _professionals_by_document(handle, raw_document)
    if not rows:
        return None, doc
    return rows[0], doc


def _dedupe_professionals_by_id(professionals):
    by_id = {}
    no_id = []
    for p in professionals:
        pid = p.get("professional_id") or ""
        if not pid:
            no_id.append(p)
            continue
        prev = by_id.get(pid)
        if prev is None or (p.get("updated_at") or "") > (prev.get("updated_at") or ""):
            by_id[pid] = p
    return list(by_id.values()) + no_id

def _filters_from_request_args(args):
    """
    Cada ?nome=valor vira filtro no documento (AND entre todos).
    Nome do parâmetro vira minúsculo (availability e Availability são o mesmo campo).
    Alias: profissao → profession.
    """
    aliases = {"profissao": "profession"}
    out = {}
    for key in args:
        if key.startswith("_"):
            continue
        raw = args.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        field = aliases.get(key.lower(), key.lower())
        out[field] = str(raw).strip()
    return out


_INT_FILTER_FIELDS = frozenset({"position", "priority"})


def _profession_matches_field(prof, field: str, value: str) -> bool:
    """Compara valor da query com prof[field]. Documento: só dígitos; availability: canônico + sinónimos."""
    if field == "professional_document":
        return clean_document(str(prof.get(field) or "")) == clean_document(value)

    if field == "profession":
        want = canonical_profession(value)
        got = canonical_profession(prof.get("profession"))
        if want is None or got is None:
            return False
        return want == got

    if field == "availability":
        want_c = canonical_professional_availability(value)
        got_c = canonical_professional_availability(prof.get("availability"))
        if want_c and got_c:
            return want_c == got_c
        if want_c and not got_c:
            return False
        stored = prof.get("availability")
        if stored is None:
            return False
        return str(stored).strip().lower() == value.strip().lower()

    if field in _INT_FILTER_FIELDS:
        stored = prof.get(field)
        if stored is None:
            return False
        try:
            return int(stored) == int(str(value).strip())
        except (TypeError, ValueError):
            return str(stored) == str(value).strip()

    stored = prof.get(field)
    if stored is None:
        return False
    return str(stored).strip().lower() == value.strip().lower()


def _professional_ids_with_consultation_queue_position(handle, position: int) -> set:
    """professional_id presente em teleconsulta com queue_position == position."""
    allowed: set = set()
    for c in handle.find("consultations"):
        try:
            qpos = int(c.get("queue_position"))
        except (TypeError, ValueError):
            continue
        if qpos != position:
            continue
        for k in ("nurse_id", "doctor_id"):
            pid = (c.get(k) or "").strip()
            if pid:
                allowed.add(pid)
    return allowed


_CONSULTATION_QUEUE_POSITION_KEYS = frozenset(
    {
        "consultation_queue_position",
        "fila_posicao",
        "posicao_fila",
        "posicao",
        "queue_position",
    }
)


def list_professionals_filtered_response(handle, filters: dict):
    filters = dict(filters)
    cpos_raw = None
    pos_pairs = [(k, filters.pop(k)) for k in list(filters) if k in _CONSULTATION_QUEUE_POSITION_KEYS]
    if pos_pairs:
        vals = {str(v).strip() for _, v in pos_pairs}
        if len(vals) > 1:
            return {
                "message": "Use only one of: posicao, fila_posicao, consultation_queue_position, queue_position (same value)",
                "status": "error",
                "filters": {**filters, **dict(pos_pairs)},
            }, 400
        cpos_raw = pos_pairs[0][1]

    professionals = handle.find("professionals")
    normalized = []
    for p in professionals:
        p, _ = _normalize_professional_availability(handle, p)
        normalized.append(p)

    if not filters:
        filtered = normalized
    else:
        filtered = [
            p
            for p in normalized
            if all(
                _profession_matches_field(p, fname, fval)
                for fname, fval in filters.items()
            )
        ]
    filtered = _dedupe_professionals_by_id(filtered)

    filters_applied = dict(filters)
    if cpos_raw is not None:
        try:
            pos = int(str(cpos_raw).strip())
        except ValueError:
            return {
                "message": "Invalid consultation queue position (use an integer)",
                "status": "error",
                "filters": {**filters_applied, "consultation_queue_position": cpos_raw},
            }, 400
        allowed_ids = _professional_ids_with_consultation_queue_position(handle, pos)
        filtered = [
            p for p in filtered if (p.get("professional_id") or "") in allowed_ids
        ]
        filters_applied["consultation_queue_position"] = pos

    return {
        "message": "Professionals listed successfully",
        "status": "success",
        "filters": filters_applied,
        "total": len(filtered),
        "professionals": convert_to_serializable(filtered),
    }, 200


def _normalize_professional_availability(handle, prof):
    """Garante availability nos 4 estados canônicos (inglês); normaliza sinônimos em PT."""
    updated = False
    raw = prof.get("availability")
    canon = canonical_professional_availability(raw) if raw else None

    if canon:
        if prof.get("availability") != canon:
            prof["availability"] = canon
            updated = True
    else:
        current_status = (prof.get("status") or "").strip().lower()
        if current_status in PROFESSIONAL_AVAILABILITY_CHOICES:
            prof["availability"] = current_status
            prof["status"] = "active"
            updated = True
        else:
            prof["availability"] = "available"
            updated = True

    before_coerce_status = prof.get("status")
    coerce_professional_cadastro_status(prof)
    if prof.get("status") != before_coerce_status:
        updated = True

    if updated:
        prof["updated_at"] = datetime.now(timezone.utc).isoformat()
        handle.save("professionals", prof)
    return prof, updated


ns = Namespace('profissional', description='Endpoints de Profissionais')
api.add_namespace(ns, path='/profissional_')

@ns.route('criar')
class CreateProfessional(Resource):
    @require_token
    def post(self):
        handle = get_handle()

        data = request.get_json() or {}
        
        name = data.get('name', '').strip()
        profession = data.get('profession', '').strip()
        credential = clean_document(data.get('credential', ''))
        professional_document = clean_document(data.get('professional_document', ''))
        specialty = data.get('specialty', '').strip()
        
        # Validation
        if not name:
            return {
                'message': 'name is required',
                'status': 'error'
            }, 400
        
        if not profession:
            return {
                'message': 'profession is required',
                'status': 'error',
                'valid_professions': PROFESSION_CHOICES,
                'labels': PROFESSION_LABELS
            }, 400
        
        if not is_valid_profession(profession):
            return {
                'message': f'Invalid profession. Accepted professions: {", ".join(PROFESSION_CHOICES)}',
                'status': 'error',
                'valid_professions': PROFESSION_CHOICES,
                'labels': PROFESSION_LABELS
            }, 400

        profession = canonical_profession(profession)

        if profession == PHYSICIAN_PROFESSION:
            if not credential:
                return {
                    'message': 'credential is required for médico(a)',
                    'status': 'error',
                }, 400
        else:
            credential = credential or ""

        if not professional_document:
            return {
                'message': 'professional_document is required',
                'status': 'error'
            }, 400

        try:
            existing_professionals, _ = _professionals_by_document(
                handle, professional_document
            )
            if existing_professionals:
                return {
                    'message': 'Professional with this document already exists',
                    'status': 'error',
                    'existing_professional': convert_to_serializable(existing_professionals[0])
                }, 409
            if credential:
                cred_rows = handle.find("professionals", {"credential": credential})
                for ex in cred_rows:
                    ex_doc = clean_document(ex.get("professional_document", "") or "")
                    if ex_doc != professional_document:
                        return {
                            'message': 'credential already registered to another professional_document',
                            'status': 'error',
                            'existing_professional_document': ex_doc or None,
                        }, 409
        except Exception as e:
            return {
                'message': f'Error checking for existing professional: {str(e)}',
                'status': 'error'
            }, 500

        professional = Professional(
            name=name,
            profession=profession,
            credential=credential,
            professional_document=professional_document,
            specialty=specialty
        )
        professional_data = professional.to_dict()

        handle.save("professionals", professional_data)

        return {
            'message': 'Professional created successfully',
            'professional': convert_to_serializable(professional_data)
        }, 201
    
@ns.route('listar')
class ListProfessionals(Resource):
    @require_token
    def get(self):
        """
        Filtros na query (AND); chaves viram minúsculas. Ex.: ?availability=available&profession=enfermeiro(a).
        availability aceita sinónimos (disponível). Posição na fila (teleconsulta.queue_position):
        posicao, fila_posicao, consultation_queue_position ou queue_position — ex.: ?availability=available&posicao=1.
        Campos numéricos no profissional: position, priority. Alias: profissao → profession.
                """
        handle = get_handle()
        filters = _filters_from_request_args(request.args)
        return list_professionals_filtered_response(handle, filters)


@ns.route('filtrar_profissao/<string:profession>')
class ListProfessionalsByProfession(Resource):
    """Legado: mesmo que listar?profession=..."""

    @require_token
    def get(self, profession):
        handle = get_handle()
        profession = (profession or "").strip()
        if not profession:
            return {
                'message': 'profession is required',
                'status': 'error',
            }, 400
        return list_professionals_filtered_response(handle, {"profession": profession})


@ns.route('disponiveis')
class ListAvailableProfessionals(Resource):
    """Legado: lista enfermeiros no critério da fila (duplicatas/linhas mistas tratadas no serviço)."""

    @require_token
    def get(self):
        handle = get_handle()
        try:
            filtered = list_nurses_marked_available(handle)
        except Exception as e:
            return {
                'message': f'Error listing available professionals: {str(e)}',
                'status': 'error',
            }, 500
        return {
            'message': 'Available nurses listed successfully',
            'status': 'success',
            'filters': {},
            'total': len(filtered),
            'professionals': convert_to_serializable(filtered),
        }, 200


@ns.route('migrar_availability')
class MigrateAvailability(Resource):
    @require_token
    def patch(self):
        handle = get_handle()
        professionals = handle.find("professionals")
        changed = 0
        for p in professionals:
            _, updated = _normalize_professional_availability(handle, p)
            if updated:
                changed += 1
        return {
            'message': 'Availability migration executed',
            'status': 'success',
            'updated_count': changed,
            'total': len(professionals),
        }, 200


@ns.route('buscar/<string:professional_document>')
class GetProfessionalByDocument(Resource):
    @require_token
    def get(self, professional_document):
        handle = get_handle()
        try:
            prof, doc = _professional_by_document(handle, professional_document)
            if not doc:
                return {
                    'message': 'professional_document inválido ou vazio',
                    'status': 'error',
                }, 400
            if not prof:
                return {
                    'message': 'Professional not found',
                    'status': 'not_found',
                    'professional_document': doc,
                }, 404
            prof, _ = _normalize_professional_availability(handle, prof)
            return {
                'message': 'Professional retrieved successfully',
                'status': 'success',
                'professional_document': doc,
                'professional': convert_to_serializable(prof),
            }, 200
        except Exception as e:
            return {
                'message': f'Error fetching professional: {str(e)}',
                'status': 'error',
            }, 500


@ns.route('atualizar/<string:professional_document>')
class UpdateProfessionalByDocument(Resource):
    @require_token
    def patch(self, professional_document):
        handle = get_handle()
        data = request.get_json() or {}

        name = data.get('name')
        profession = data.get('profession')
        credential = data.get('credential')
        specialty = data.get('specialty')

        has_any = any(
            x is not None and (not isinstance(x, str) or x.strip() != '')
            for x in (name, profession, credential, specialty)
        )
        if not has_any:
            return {
                'message': 'Informe ao menos um campo: name, profession, credential, specialty',
                'status': 'error',
            }, 400

        try:
            prof, doc = _professional_by_document(handle, professional_document)
            if not doc:
                return {
                    'message': 'professional_document inválido ou vazio',
                    'status': 'error',
                }, 400
            if not prof:
                return {
                    'message': 'Professional not found',
                    'status': 'not_found',
                    'professional_document': doc,
                }, 404
            prof, _ = _normalize_professional_availability(handle, prof)

            if name is not None:
                name = name.strip()
                if not name:
                    return {'message': 'name não pode ser vazio', 'status': 'error'}, 400
                prof['name'] = name

            if profession is not None:
                profession = profession.strip()
                if not profession:
                    return {'message': 'profession não pode ser vazio', 'status': 'error'}, 400
                if not is_valid_profession(profession):
                    return {
                        'message': f'Invalid profession. Accepted: {", ".join(PROFESSION_CHOICES)}',
                        'status': 'error',
                        'valid_professions': PROFESSION_CHOICES,
                        'labels': PROFESSION_LABELS,
                    }, 400
                prof['profession'] = canonical_profession(profession)

            if credential is not None:
                credential = clean_document(credential)
                eff_canon = canonical_profession(prof.get("profession")) or ""
                if not credential and eff_canon == PHYSICIAN_PROFESSION:
                    return {
                        'message': 'credential inválido ou vazio para médico(a)',
                        'status': 'error',
                    }, 400
                prof['credential'] = credential

            if specialty is not None:
                prof['specialty'] = specialty.strip()

            prof['updated_at'] = datetime.now(timezone.utc).isoformat()

            handle.save('professionals', prof)

            return {
                'message': 'Professional updated successfully',
                'status': 'success',
                'professional_document': doc,
                'professional': convert_to_serializable(prof),
            }, 200
        except Exception as e:
            return {
                'message': f'Error updating professional: {str(e)}',
                'status': 'error',
            }, 500


@ns.route('disponibilidade/<string:professional_document>')
class UpdateProfessionalAvailability(Resource):
    @require_token
    def patch(self, professional_document):
        handle = get_handle()
        data = request.get_json() or {}
        availability = canonical_professional_availability(data.get("availability"))

        if not availability:
            return {
                'message': 'availability inválido ou ausente',
                'status': 'error',
                'valid_availability': PROFESSIONAL_AVAILABILITY_CHOICES,
                'labels': PROFESSIONAL_AVAILABILITY_LABELS,
            }, 400

        try:
            prof, doc = _professional_by_document(handle, professional_document)
            if not doc:
                return {
                    'message': 'professional_document inválido ou vazio',
                    'status': 'error',
                }, 400
            if not prof:
                return {
                    'message': 'Professional not found',
                    'status': 'not_found',
                    'professional_document': doc,
                }, 404
            prof, _ = _normalize_professional_availability(handle, prof)

            prof['availability'] = availability
            prof['updated_at'] = datetime.now(timezone.utc).isoformat()

            handle.save('professionals', prof)

            auto_assignment = None
            auto_assignments = []
            if (
                availability == "available"
                and canonical_profession(prof.get("profession")) == NURSE_PROFESSION
            ):
                drain = drain_waiting_with_available_nurses(handle)
                auto_assignments = drain.get("assignments") or []
                pid = prof.get("professional_id")
                auto_assignment = next(
                    (a for a in auto_assignments if a.get("nurse_id") == pid),
                    None,
                )

            return {
                'message': 'Professional availability updated successfully',
                'status': 'success',
                'professional_document': doc,
                'availability': availability,
                'professional': convert_to_serializable(prof),
                'auto_assignment': convert_to_serializable(auto_assignment),
                'auto_assignments': convert_to_serializable(auto_assignments),
            }, 200
        except Exception as e:
            return {
                'message': f'Error updating professional availability: {str(e)}',
                'status': 'error',
            }, 500


@ns.route('status/<string:professional_document>')
class UpdateProfessionalStatus(Resource):
    @require_token
    def patch(self, professional_document):
        handle = get_handle()
        data = request.get_json() or {}
        status = (data.get('status') or '').strip().lower()

        if not status:
            return {
                'message': 'status is required',
                'status': 'error',
                'valid_status': PROFESSIONAL_STATUS_CHOICES,
                'labels': PROFESSIONAL_STATUS_LABELS,
            }, 400

        if not is_valid_professional_status(status):
            return {
                'message': f'Invalid status. Accepted: {", ".join(PROFESSIONAL_STATUS_CHOICES)}',
                'status': 'error',
                'valid_status': PROFESSIONAL_STATUS_CHOICES,
                'labels': PROFESSIONAL_STATUS_LABELS,
            }, 400

        try:
            prof, doc = _professional_by_document(handle, professional_document)
            if not doc:
                return {
                    'message': 'professional_document inválido ou vazio',
                    'status': 'error',
                }, 400
            if not prof:
                return {
                    'message': 'Professional not found',
                    'status': 'not_found',
                    'professional_document': doc,
                }, 404

            prof['status'] = status
            prof['updated_at'] = datetime.now(timezone.utc).isoformat()

            handle.save('professionals', prof)

            return {
                'message': 'Professional status updated successfully',
                'status': 'success',
                'professional_document': doc,
                'new_status': status,
                'professional': convert_to_serializable(prof),
            }, 200
        except Exception as e:
            return {
                'message': f'Error updating professional status: {str(e)}',
                'status': 'error',
            }, 500
