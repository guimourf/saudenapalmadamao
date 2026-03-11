from borneo import TableRequest, TableLimits
from app.services.nosql import get_handle

def init_database():
    handle = get_handle()
    
    # Tabelas para criar
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
                rating NUMBER,
                comment STRING,
                type STRING,
                status STRING,
                triage BOOLEAN,
                time_consultation NUMBER,
                scheduled_date STRING,
                scheduled_time STRING,
                triage_started_at STRING,
                referral_at STRING,
                consultation_started_at STRING,
                completed_at STRING,
                created_at STRING,
                updated_at STRING,
                PRIMARY KEY(consultation_id)
            )
        """
    }
    
    # Cria cada tabela
    for table_name, ddl in tables.items():
        try:
            print(f"Criando {table_name}...")
            
            request = TableRequest()
            request.set_statement(ddl)
            
            limits = TableLimits(20, 20, 1)
            request.set_table_limits(limits)
            
            result = handle.table_request(request)
            result.wait_for_completion(handle, 60000, 1000)
            
            print(f"{table_name} OK")
            
        except Exception as e:
            if "already exists" in str(e) or "rate limit" in str(e):
                print(f"{table_name} já existe")
            else:
                print(f"{table_name}: {e}")
    
    handle.close()

if __name__ == "__main__":
    init_database()