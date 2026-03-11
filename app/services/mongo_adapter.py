"""
Adapter MongoDB que emula a interface do Borneo (Oracle NoSQL)
Permite usar MongoDB com a mesma API do Oracle NoSQL
"""
from bson import ObjectId
from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

# Configuração MongoDB
MONGO_URI = os.getenv('MONGO_URI')
DB_NAME = 'SaudenaPalmadaMao'

# Cliente MongoDB global
_mongo_client = None
_mongo_db = None

def get_mongo_db():
    """Obtém conexão com MongoDB"""
    global _mongo_client, _mongo_db
    
    if _mongo_client is None:
        try:
            _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            _mongo_client.admin.command('ping')  # Testa conexão
            _mongo_db = _mongo_client[DB_NAME]
            print(f"MongoDB conectado ao database: {DB_NAME}")
        except Exception as e:
            print(f"Erro ao conectar MongoDB: {e}")
            raise e
    
    return _mongo_db

class MongoNoSQLRequest:
    """Classe base que emula requests do Borneo"""
    def __init__(self):
        self._table_name = None
        self._value = None
        self._statement = None
        
    def set_table_name(self, table_name: str):
        """Define o nome da tabela (collection no MongoDB)"""
        self._table_name = table_name
        return self
        
    def set_value(self, value: dict):
        """Define o valor/documento"""
        self._value = value
        return self

class MongoPutRequest(MongoNoSQLRequest):
    """Emula PutRequest do Borneo para inserção/atualização"""
    pass

class MongoQueryRequest(MongoNoSQLRequest):
    """Emula QueryRequest do Borneo para consultas"""
    def set_statement(self, statement: str):
        """Define a query SQL-like e converte para MongoDB query"""
        self._statement = statement
        return self

class MongoQueryResult:
    """Emula QueryResult do Borneo"""
    def __init__(self, documents: List[Dict]):
        self._documents = documents
        
    def get_results(self) -> List[Dict]:
        """Retorna os resultados da query"""
        # Converte ObjectId para string para compatibilidade JSON
        results = []
        for doc in self._documents:
            converted_doc = self._convert_objectids(doc)
            results.append(converted_doc)
        return results
    
    def _convert_objectids(self, obj):
        """Converte ObjectId para string recursivamente"""
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_objectids(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_objectids(item) for item in obj]
        else:
            return obj
        return results

class MongoNoSQLHandle:
    """Emula NoSQLHandle do Borneo usando MongoDB"""
    
    def __init__(self):
        self._db = get_mongo_db()
        
    def _get_db(self):
        """Obtém a referência do banco de dados MongoDB"""
        if self._db is None:
            self._db = get_mongo_db()
        return self._db
    
    def put(self, request: MongoPutRequest):
        """Insere ou atualiza documento (emula put do Borneo)"""
        try:
            db = self._get_db()
            collection = db[request._table_name]
            
            # Adiciona timestamps automáticos
            if 'created_at' not in request._value:
                request._value['created_at'] = datetime.utcnow().isoformat()
            request._value['updated_at'] = datetime.utcnow().isoformat()
            
            # Se tem ID único (como consultation_id), tenta upsert
            unique_field = None
            unique_value = None
            
            # Procura por campos únicos conhecidos
            for field in ['consultation_id', 'session_hash', 'id', 'user_id']:
                if field in request._value:
                    unique_field = field
                    unique_value = request._value[field]
                    break
            
            if unique_field and unique_value:
                # Prepara dados para update (remove _id se existir)
                update_data = request._value.copy()
                if '_id' in update_data:
                    del update_data['_id']
                
                # Upsert - atualiza se existe, insere se não existe
                result = collection.update_one(
                    {unique_field: unique_value},
                    {'$set': update_data},
                    upsert=True
                )
                # Retorna apenas informações serializáveis
                return {
                    "success": True,
                    "operation": "upsert",
                    "matched": result.matched_count,
                    "modified": result.modified_count,
                    "upserted": str(result.upserted_id) if result.upserted_id else None
                }
            else:
                # Insert simples
                result = collection.insert_one(request._value)
                # Retorna apenas informações serializáveis
                return {
                    "success": True,
                    "operation": "insert",
                    "inserted_id": str(result.inserted_id)
                }
                
        except Exception as e:
            raise Exception(f"Erro no put MongoDB: {str(e)}")
            raise Exception(f"Erro no put MongoDB: {str(e)}")
    
    def query(self, request: MongoQueryRequest):
        """Executa query SQL-like convertendo para MongoDB (emula query do Borneo)"""
        try:
            # Parse da query SQL simples para MongoDB query
            mongo_query = self._parse_sql_to_mongo(request._statement)
            collection_name = mongo_query['collection']
            query_filter = mongo_query['filter']
            
            db = self._get_db()
            collection = db[collection_name]
            
            # Executa a query
            if query_filter:
                documents = list(collection.find(query_filter))
            else:
                documents = list(collection.find())
            
            return MongoQueryResult(documents)
            
        except Exception as e:
            raise Exception(f"Erro na query MongoDB: {str(e)}")
    
    def do_table_request(self, request, timeout=None, delay=None):
        """Emula do_table_request do Borneo (para criação de tabelas/collections)"""
        # MongoDB cria collections automaticamente, então apenas simula sucesso
        print(f"📊 Collection será criada automaticamente quando necessário")
        return {"status": "success"}
    
    def close(self):
        """Emula close do Borneo"""
        # MongoDB connection é gerenciada pelo Flask-PyMongo
        pass
    
    def get_table_usage(self, table_name):
        """Emula get_table_usage do Borneo"""
        try:
            db = self._get_db()
            collection = db[table_name]
            count = collection.count_documents({})
            return {"table_name": table_name, "count": count}
        except Exception as e:
            return {"error": str(e)}
        pass
    
    def get_table_usage(self, table_name):
        """Emula get_table_usage do Borneo"""
        try:
            collection = self._mongo.db[table_name]
            count = collection.count_documents({})
            return {"table_name": table_name, "count": count}
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_sql_to_mongo(self, sql_statement: str) -> Dict[str, Any]:
        """
        Converte SQL simples para query MongoDB
        Suporta: SELECT * FROM table WHERE field = 'value'
        """
        sql = sql_statement.strip()
        sql_upper = sql.upper()
        # Parse básico de SELECT * FROM table WHERE ...
        if not sql_upper.startswith('SELECT'):
            raise Exception("Apenas SELECT suportado")
        # Extrai nome da tabela
        from_index = sql_upper.find('FROM')
        if from_index == -1:
            raise Exception("FROM não encontrado")
        where_index = sql_upper.find('WHERE')
        if where_index != -1:
            # Tem WHERE clause
            table_part = sql[from_index + 4:where_index].strip()
            where_part = sql[where_index + 5:].strip()
        else:
            # Sem WHERE clause
            table_part = sql[from_index + 4:].strip()
            where_part = ""
        collection_name = table_part.lower()
        # Parse do WHERE (muito básico)
        mongo_filter = {}
        if where_part:
            # Suporta apenas: field = 'value'
            if '=' in where_part:
                field, value = where_part.split('=', 1)
                field = field.strip()  # NÃO converte para minúsculo, preserva o case
                value = value.strip().strip("'\"")
                mongo_filter[field] = value
        return {
            'collection': collection_name,
            'filter': mongo_filter
        }
    
    def table_request(self, table_name: str):
        """Emula table_request do Borneo"""
        return MongoTableRequest(table_name)

# Instância global do handle MongoDB
_mongo_handle = None

class MongoTableRequest:
    """Emula TableRequest do Borneo"""
    def __init__(self, table_name: str):
        self._table_name = table_name
    
    def wait_for_completion(self, handle, timeout=None, delay=None):
        """Emula wait_for_completion do Borneo"""
        # MongoDB cria collections automaticamente, então simula sucesso
        return {"status": "success", "table_name": self._table_name}

def get_mongo_handle():
    """Retorna handle MongoDB que emula interface do Borneo"""
    global _mongo_handle
    if _mongo_handle is None:
        _mongo_handle = MongoNoSQLHandle()
    return _mongo_handle

# Classes exportadas para compatibilidade com Borneo
PutRequest = MongoPutRequest
QueryRequest = MongoQueryRequest
NoSQLHandle = MongoNoSQLHandle

# Função principal que substitui get_handle() do Oracle
def get_handle():
    """
    Função compatível com Oracle NoSQL que retorna handle MongoDB
    Substitui: from app.services.nosql import get_handle
    """
    return get_mongo_handle()