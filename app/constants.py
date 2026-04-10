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

PROFESSION_CHOICES = [
    'médico(a)',
    'enfermeiro(a)',
    'psicólogo(a)',
    'nutricionista',
    'fisioterapeuta',
    'dentista',
]

PROFESSION_LABELS = {
    'médico(a)': 'Médico(a)',
    'enfermeiro(a)': 'Enfermeiro(a)',
    'psicólogo(a)': 'Psicólogo(a)',
    'nutricionista': 'Nutricionista',
    'fisioterapeuta': 'Fisioterapeuta',
    'dentista': 'Dentista',
}

NURSE_PROFESSION = 'enfermeiro(a)'

PHYSICIAN_PROFESSION = 'médico(a)'

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
    """Verifica se a profissão é válida"""
    return profession in PROFESSION_CHOICES

def get_profession_label(profession):
    """Retorna o label em português da profissão"""
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

