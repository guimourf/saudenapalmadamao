TELEATENDIMENTO_STATUS = {
    'WAITING': 'waiting',
    'TRIAGE': 'triage',
    'REFFERRAL': 'refferal',
    'AUTHORIZED': 'authorized',
    'COMPLETED': 'completed',
    'CANCELLED': 'cancelled',
}

TELEATENDIMENTO_STATUS_CHOICES = [  
    'waiting',
    'triage',
    'refferal',
    'authorized',
    'completed',
    'cancelled',
]

TELEATENDIMENTO_STATUS_LABELS = {
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

