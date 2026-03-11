from borneo import NoSQLHandle, NoSQLHandleConfig, Region
from borneo.iam import SignatureProvider
import os
import logging

logger = logging.getLogger(__name__)

def get_handle():    
    # Se MONGO_URI está definido, usa MongoDB
    if os.getenv("MONGO_URI"):
        from app.services.mongo_adapter import MongoNoSQLHandle
        return MongoNoSQLHandle()
        
    with open(os.getenv("OCI_PRIVATE_KEY"), "r") as f:
        private_key_content = f.read()

    provider = SignatureProvider(
        tenant_id=os.getenv("OCI_TENANCY_OCID"),
        user_id=os.getenv("OCI_USER_OCID"),
        fingerprint=os.getenv("OCI_FINGERPRINT"),
        private_key=private_key_content,
    )

    config = NoSQLHandleConfig(
        endpoint=f"https://nosql.{os.getenv('OCI_REGION')}.oci.oraclecloud.com",
        provider=provider
    )

    return NoSQLHandle(config)