import os
import logging
from app.services.nosql import get_handle

logger = logging.getLogger(__name__)

def init_database():
    try:
        handle = get_handle()
        
        # Verifica se é MongoDB ou Oracle
        if not os.getenv('MONGO_URI'):
            init_oracle_tables(handle)
        
    except Exception as e:
        logger.error(f"Erro na inicialização: {e}")
        raise

def init_oracle_tables(handle):
    from borneo import TableRequest
    import time
    
    tables = {
        "patients": """
        CREATE TABLE IF NOT EXISTS patients (
            patient_id STRING,
            name STRING,
            document STRING,
            status STRING,
            created_at STRING,
            PRIMARY KEY(patient_id)
        )
        """,
        "professionals": """
        CREATE TABLE IF NOT EXISTS professionals (
            professional_id STRING,
            name STRING,
            profession STRING,
            credential STRING,
            specialty STRING,
            status STRING,
            created_at STRING,
            updated_at STRING,
            PRIMARY KEY(professional_id)
        )
        """,
        "sessions": """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id STRING,
            usuario_id STRING,
            session_hash STRING,
            session_link STRING,
            status STRING,
            created_at STRING,
            PRIMARY KEY(session_id)
        )
        """,
        "consultations": """
        CREATE TABLE IF NOT EXISTS consultations (
            consultation_id STRING,
            session_id STRING,
            patient_id STRING,
            patient_name STRING,
            patient_report STRING,
            nurse_id STRING,
            nurse_name STRING,
            doctor_id STRING,
            doctor_name STRING,
            doctor_credential STRING,
            specialty STRING,
            meet_link STRING,
            session_link STRING,
            doctor_link STRING,
            session_hash STRING,
            rating INTEGER,
            comment STRING,
            feedback STRING,
            type STRING,
            status STRING,
            triage BOOLEAN,
            time_consultation INTEGER,
            created_at STRING,
            scheduled_date STRING,
            scheduled_time STRING,
            triage_started_at STRING,
            referral_at STRING,
            consultation_started_at STRING,
            completed_at STRING,
            updated_at STRING,
            PRIMARY KEY(consultation_id)
        )
        """
    }
    
    for table_name, ddl in tables.items():
        try:
            request = TableRequest().set_statement(ddl)
            handle.do_table_request(request, 50000, 1000)
            print(f"Tabela {table_name} criada/verificada")
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"Tabela {table_name}: {e}")

if __name__ == "__main__":
    init_database()