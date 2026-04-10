from __future__ import annotations

import re
import unicodedata
from typing import Dict, NamedTuple, Tuple

TELEATENDIMENTO_STATUS = {
    'QUEUE': 'queue',
    'WAITING': 'waiting',
    'TRIAGE': 'triage',
    'REFFERRAL': 'refferal',
    'AUTHORIZED': 'authorized',
    'COMPLETED': 'completed',
    'CANCELLED': 'cancelled',
}

TELEATENDIMENTO_STATUS_CHOICES = [
    'queue',
    'waiting',
    'triage',
    'refferal',
    'authorized',
    'completed',
    'cancelled',
]

TELEATENDIMENTO_STATUS_LABELS = {
    'queue': 'Na fila',
    'waiting': 'Aguardando',
    'triage': 'Triagem',
    'refferal': 'Reagendado',
    'authorized': 'Autorizado',
    'completed': 'Completo',
    'cancelled': 'Cancelado',
}

TELEATENDIMENTO_TYPES = {
    'AGENDADA': 'Agendada',          
    'ESPONTANEA': 'Espontânea',          
}

TELEATENDIMENTO_TYPE_CHOICES = [
    'agendada',
    'espontanea',
]

TELEATENDIMENTO_TYPE_LABELS = {
    'agendada': 'Agendada',
    'espontanea': 'Espontânea',
}

# Espontânea ainda "em curso": não permitir segunda espontânea para o mesmo paciente.
ESPONTANEA_IN_PROGRESS_STATUSES = frozenset({
    'queue',
    'waiting',
    'authorized',
    'refferal',
})


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _profession_match_key(s: str) -> str:
    """Chave estável: sem acento, minúsculo, sem (a)/(o) nem espaços."""
    t = _strip_accents((s or "").strip().lower())
    for token in ("(a)", "(o)", "(as)", "(os)", "(a/o)", "(o/a)"):
        t = t.replace(token, "")
    t = re.sub(r"[\s.\-_/]+", "", t)
    return t


class ProfessionType(NamedTuple):
    """
    Tipo de profissão: id estável (inglês), valor gravado no banco (stored),
    label de UI e todas as formas aceites (masculino, feminino, (a), sinónimos).
    """

    id: str
    stored: str
    label: str
    options: Tuple[str, ...]


# --- Definição por tipo (Doctor, Nurse, …): opções → mesmo `stored` ---
Doctor = ProfessionType(
    id="doctor",
    stored="médico(a)",
    label="Médico(a)",
    options=(
        "médico(a)",
        "médico",
        "médica",
        "medico(a)",
        "medico",
        "medica",
        "doutor",
        "doutora",
        "doctor",
        "physician",
    ),
)

Nurse = ProfessionType(
    id="nurse",
    stored="enfermeiro(a)",
    label="Enfermeiro(a)",
    options=(
        "enfermeiro(a)",
        "enfermeiro",
        "enfermeira",
        "nurse",
    ),
)

Psychologist = ProfessionType(
    id="psychologist",
    stored="psicólogo(a)",
    label="Psicólogo(a)",
    options=(
        "psicólogo(a)",
        "psicólogo",
        "psicóloga",
        "psicologo(a)",
        "psicologo",
        "psicologa",
        "psychologist",
    ),
)

Nutritionist = ProfessionType(
    id="nutritionist",
    stored="nutricionista",
    label="Nutricionista",
    options=(
        "nutricionista",
        "nutritionist",
    ),
)

Physiotherapist = ProfessionType(
    id="physiotherapist",
    stored="fisioterapeuta",
    label="Fisioterapeuta",
    options=(
        "fisioterapeuta",
        "fisionoterapeuta",
        "physiotherapist",
    ),
)

Dentist = ProfessionType(
    id="dentist",
    stored="dentista",
    label="Dentista",
    options=(
        "dentista",
        "dentist",
        "odontologo",
        "odontólogo",
        "odontologa",
        "odontóloga",
        "cirurgião dentista",
        "cirurgiao dentista",
    ),
)

PROFESSION_TYPES: Tuple[ProfessionType, ...] = (
    Doctor,
    Nurse,
    Psychologist,
    Nutritionist,
    Physiotherapist,
    Dentist,
)

PROFESSION_BY_ID: Dict[str, ProfessionType] = {pt.id: pt for pt in PROFESSION_TYPES}
PROFESSION_BY_STORED: Dict[str, ProfessionType] = {pt.stored: pt for pt in PROFESSION_TYPES}

PROFESSION_CHOICES = [pt.stored for pt in PROFESSION_TYPES]

PROFESSION_LABELS = {pt.stored: pt.label for pt in PROFESSION_TYPES}

# Compatível com código existente
NURSE_PROFESSION = Nurse.stored
PHYSICIAN_PROFESSION = Doctor.stored

# Nomes longos opcionais (export)
PROFESSION_DOCTOR = Doctor
PROFESSION_NURSE = Nurse
PROFESSION_PSYCHOLOGIST = Psychologist
PROFESSION_NUTRITIONIST = Nutritionist
PROFESSION_PHYSIOTHERAPIST = Physiotherapist
PROFESSION_DENTIST = Dentist


def _build_profession_alias_map() -> Dict[str, str]:
    """Mapeia _profession_match_key(opção) → valor `stored` (canónico no banco)."""
    out: Dict[str, str] = {}
    for pt in PROFESSION_TYPES:
        for opt in pt.options:
            k = _profession_match_key(opt)
            if k:
                out[k] = pt.stored
        sk = _profession_match_key(pt.stored)
        if sk:
            out.setdefault(sk, pt.stored)
    return out


_PROFESSION_KEY_TO_CANONICAL = _build_profession_alias_map()


def canonical_profession(value) -> str | None:
    """
    Normaliza texto para o `stored` de um ProfessionType.
    Aceita qualquer string listada em `.options` (ex.: enfermeira → enfermeiro(a)).
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s in PROFESSION_BY_STORED:
        return s
    key = _profession_match_key(s)
    if key in _PROFESSION_KEY_TO_CANONICAL:
        c = _PROFESSION_KEY_TO_CANONICAL[key]
        if c in PROFESSION_BY_STORED:
            return c
    for pt in PROFESSION_TYPES:
        if _profession_match_key(pt.stored) == key:
            return pt.stored
    return None


def is_valid_status(status):
    """Verifica se o status é válido"""
    return status in TELEATENDIMENTO_STATUS_CHOICES

def is_valid_type(type_value):
    """Verifica se o tipo é válido"""
    return type_value in TELEATENDIMENTO_TYPE_CHOICES

def get_status_label(status):
    """Retorna o label em português do status"""
    return TELEATENDIMENTO_STATUS_LABELS.get(status, status)

def get_type_label(type_value):
    """Retorna o label em português do tipo"""
    return TELEATENDIMENTO_TYPE_LABELS.get(type_value, type_value)



def is_valid_profession(profession):
    """Aceita sinónimos (médico/médica/enfermeiro/enfermeira etc.) e devolve canónico via canonical_profession."""
    return canonical_profession(profession) is not None

def get_profession_label(profession):
    """Retorna o label em português da profissão (aceita sinónimos)."""
    c = canonical_profession(profession)
    if c:
        return PROFESSION_LABELS.get(c, profession)
    return PROFESSION_LABELS.get(profession, profession)


# Profissional: cadastro (status) vs disponibilidade para atendimento (availability)
PROFESSIONAL_STATUS = {
    'ACTIVE': 'active',
    'INACTIVE': 'inactive',
}

PROFESSIONAL_STATUS_CHOICES = [
    'active',
    'inactive',
]

PROFESSIONAL_STATUS_LABELS = {
    'active': 'Ativo',
    'inactive': 'Inativo',
}

PROFESSIONAL_AVAILABILITY = {
    'AVAILABLE': 'available',
    'UNAVAILABLE': 'unavailable',
    'ON_BREAK': 'on_break',
    'BUSY': 'busy',
}

PROFESSIONAL_AVAILABILITY_CHOICES = [
    'available',
    'unavailable',
    'on_break',
    'busy',
]

PROFESSIONAL_AVAILABILITY_LABELS = {
    'available': 'Disponível',
    'unavailable': 'Indisponível',
    'on_break': 'Descanso',
    'busy': 'Ocupado',
}

def get_professional_status_label(value):
    """Retorna o label em português do status de cadastro do profissional"""
    return PROFESSIONAL_STATUS_LABELS.get(value, value)


def get_professional_availability_label(value):
    """Retorna o label em português da disponibilidade do profissional"""
    return PROFESSIONAL_AVAILABILITY_LABELS.get(value, value)


# Sinônimos em português (UI / registros antigos) → valor canônico em inglês
_PORTUGUESE_AVAILABILITY_TO_CANONICAL = {
    'disponível': 'available',
    'disponivel': 'available',
    'indisponível': 'unavailable',
    'indisponivel': 'unavailable',
    'descanso': 'on_break',
    'ocupado': 'busy',
}


def is_valid_professional_status(value):
    return value in PROFESSIONAL_STATUS_CHOICES


def canonical_professional_availability(value):
    """Normaliza texto para um valor de PROFESSIONAL_AVAILABILITY_CHOICES (inglês) ou None."""
    if value is None:
        return None
    v = value.strip().lower()
    if not v:
        return None
    if v in PROFESSIONAL_AVAILABILITY_CHOICES:
        return v
    v = _PORTUGUESE_AVAILABILITY_TO_CANONICAL.get(v)
    return v if v in PROFESSIONAL_AVAILABILITY_CHOICES else None


def is_valid_professional_availability(value):
    return canonical_professional_availability(value) is not None

