from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.constants import (
    NURSE_PROFESSION,
    PROFESSIONAL_AVAILABILITY_CHOICES,
    PROFESSIONAL_STATUS_CHOICES,
    canonical_profession,
    canonical_professional_availability,
)
from app.services.session_link import create_doctor_url

def normalize_session_hash(value: Optional[str]) -> str:
    return (value or "").strip().upper()


def _clean_professional_document(value: Any) -> str:
    """Somente dígitos, igual à rota de profissionais."""
    if value is None or value == "":
        return ""
    return re.sub(r"\D", "", str(value))


def find_consultations_by_session_hash(
    handle, session_hash: str
) -> List[Dict[str, Any]]:
    ch = normalize_session_hash(session_hash)
    if not ch:
        return []
    docs = handle.find("consultations", {"session_hash": ch})
    if docs:
        return docs
    return handle.find(
        "consultations",
        {"session_hash": {"$regex": f"^{re.escape(ch)}$", "$options": "i"}},
    )


def mark_consultation_queue_position_cleared(handle, consultation_hash: str) -> None:
    ch = normalize_session_hash(consultation_hash)
    if not ch:
        return
    docs = find_consultations_by_session_hash(handle, ch)
    if not docs:
        return
    tele = dict(docs[0])
    tele["queue_position"] = -1
    tele["updated_at"] = datetime.now(timezone.utc).isoformat()
    handle.save("consultations", tele)


def sync_queue_entry_positions_to_consultations(handle, queue_id: str) -> None:
    qid = (queue_id or "").strip()
    if not qid:
        return
    entries = handle.find("queue_entries", {"queue_id": qid, "status": "waiting"})
    entries.sort(key=lambda item: item.get("created_at", ""))
    for e in entries:
        ch = normalize_session_hash(e.get("consultation_hash") or "")
        if not ch:
            continue
        docs = find_consultations_by_session_hash(handle, ch)
        if not docs:
            continue
        tele = dict(docs[0])
        pos = int(e.get("position") or 0)
        if tele.get("queue_position") != pos:
            tele["queue_position"] = pos
            tele["updated_at"] = datetime.now(timezone.utc).isoformat()
            handle.save("consultations", tele)


def coerce_professional_cadastro_status(prof: Dict[str, Any]) -> None:
    st = (prof.get("status") or "").strip().lower()
    if st in PROFESSIONAL_STATUS_CHOICES:
        prof["status"] = st
        return
    av = canonical_professional_availability(prof.get("availability") or "")
    prof["status"] = "active" if av == "available" else "inactive"


def _normalize_professional_availability_no_persist(prof: Dict[str, Any]) -> Dict[str, Any]:
    raw = prof.get("availability")
    canon = canonical_professional_availability(raw) if raw else None
    if canon:
        prof["availability"] = canon
    else:
        current_status = (prof.get("status") or "").strip().lower()
        if current_status in PROFESSIONAL_AVAILABILITY_CHOICES:
            prof["availability"] = current_status
            prof["status"] = "active"
        else:
            prof["availability"] = "available"
    coerce_professional_cadastro_status(prof)
    return prof


def set_professional_availability_by_id(
    handle, professional_id: str, availability_value: str
) -> None:
    pid = (professional_id or "").strip()
    if not pid:
        return
    av = canonical_professional_availability(availability_value)
    if not av or av not in PROFESSIONAL_AVAILABILITY_CHOICES:
        return
    rows = handle.find("professionals", {"professional_id": pid})
    if not rows:
        return
    prof = dict(rows[0])
    prof["availability"] = av
    prof["updated_at"] = datetime.now(timezone.utc).isoformat()
    handle.save("professionals", prof)


def _nurse_eligible_for_auto_assign(p: Dict[str, Any]) -> bool:
    if canonical_profession(p.get("profession")) != NURSE_PROFESSION:
        return False
    if (p.get("status") or "").strip().lower() != "active":
        return False
    av = canonical_professional_availability(p.get("availability") or "available")
    return av == "available"


def list_nurses_marked_available(handle) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for raw in handle.find("professionals"):
        if canonical_profession(raw.get("profession")) != NURSE_PROFESSION:
            continue
        p = _normalize_professional_availability_no_persist(dict(raw))
        pid = p.get("professional_id") or ""
        if not pid:
            continue
        buckets.setdefault(pid, []).append(p)

    nurses: List[Dict[str, Any]] = []
    for pid, variants in buckets.items():
        chosen = None
        for p in variants:
            if _nurse_eligible_for_auto_assign(p):
                chosen = p
                break
        if chosen is None:
            chosen = max(
                variants,
                key=lambda x: (x.get("updated_at") or x.get("created_at") or ""),
            )
        if _nurse_eligible_for_auto_assign(chosen):
            nurses.append(chosen)
    nurses.sort(key=lambda x: x.get("created_at", ""))
    return nurses


def list_available_nurses(handle) -> List[Dict[str, Any]]:
    return list_nurses_marked_available(handle)


def _recalc_positions(handle, queue_id: str) -> None:
    from app.routes import queue_routes

    queue_routes.recalculate_queue_positions(handle, queue_id)


def assign_nurse_to_waiting_entry(
    handle, nurse: Dict[str, Any], entry: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    consultation_hash = normalize_session_hash(entry.get("consultation_hash"))
    if not consultation_hash:
        return None
    consultations = find_consultations_by_session_hash(handle, consultation_hash)
    if not consultations:
        return None

    tele = dict(consultations[0])
    tele["nurse_id"] = nurse.get("professional_id", "")
    tele["nurse_name"] = nurse.get("name", "")
    ndoc = _clean_professional_document(nurse.get("professional_document"))
    if ndoc:
        tele["professional_document"] = ndoc
    sh = (tele.get("session_hash") or consultation_hash or "").strip()
    if sh:
        tele["doctor_link"] = create_doctor_url(sh)
    tele["queue_position"] = -1
    tele["status"] = "waiting"
    tele["updated_at"] = datetime.now(timezone.utc).isoformat()
    handle.save("consultations", tele)

    queue_id = entry.get("queue_id") or ""
    entry["status"] = "removed"
    entry["position"] = 0
    entry["removed_at"] = datetime.now(timezone.utc).isoformat()
    entry["updated_at"] = entry["removed_at"]
    handle.save("queue_entries", entry)

    _recalc_positions(handle, queue_id)

    set_professional_availability_by_id(
        handle, nurse.get("professional_id", ""), "busy"
    )

    return {
        "nurse_id": nurse.get("professional_id"),
        "nurse_name": nurse.get("name"),
        "professional_document": nurse.get("professional_document"),
        "entry_id": entry.get("entry_id"),
        "consultation_hash": consultation_hash,
        "queue_id": queue_id,
        "doctor_link": tele.get("doctor_link") or create_doctor_url(consultation_hash),
    }


def _waiting_entries_with_consultation(handle) -> List[Dict[str, Any]]:
    waiting = [e for e in handle.find("queue_entries", {"status": "waiting"})]
    waiting.sort(key=lambda item: item.get("created_at", ""))
    out = []
    for e in waiting:
        ch = normalize_session_hash(e.get("consultation_hash"))
        if not ch:
            continue
        if find_consultations_by_session_hash(handle, ch):
            out.append(e)
    return out


def drain_waiting_with_available_nurses(handle) -> Dict[str, Any]:
    assignments: List[Dict[str, Any]] = []
    used_nurse_ids: set = set()

    while True:
        nurses = [
            n
            for n in list_available_nurses(handle)
            if n.get("professional_id") not in used_nurse_ids
        ]
        if not nurses:
            break

        assignable = _waiting_entries_with_consultation(handle)
        if not assignable:
            break

        nurse = nurses[0]
        entry = assignable[0]
        detail = assign_nurse_to_waiting_entry(handle, nurse, entry)
        if detail is None:
            break

        used_nurse_ids.add(nurse.get("professional_id"))
        assignments.append(detail)

    return {"assignments": assignments, "count": len(assignments)}
