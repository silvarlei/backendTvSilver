from atualizaBase import build_groups_and_update_canais
from fastapi import FastAPI, Query, HTTPException
from typing import List, Optional
from pymongo import MongoClient, errors
from pymongo.collection import Collection

app = FastAPI(title="API Canais")

# Ajuste a connection string conforme seu ambiente
           
MONGO_URI = "mongodb+srv://teste:teste@cluster0.zjhbafz.mongodb.net/M3U?retryWrites=true&w=majority"
DB_NAME = "M3U"
COLLECTION_NAME = "grupos"

def get_mongo_collection() -> Collection:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # força a conexão para detectar erros cedo
    client.admin.command("ping")
    db = client[DB_NAME]
    return db[COLLECTION_NAME]

def distinct_grupos() -> List[str]:
    """
    Distinct simples no campo 'Grupo'. Remove valores None/'' e converte para string.
    """
    colecao = get_mongo_collection()
    valores = colecao.distinct("Grupo")
    grupos = [str(g).strip() for g in valores if g is not None and str(g).strip() != ""]
    grupos.sort()
    return grupos

def distinct_grupos_case_insensitive() -> List[str]:
    """
    Distinct ignorando caixa (case-insensitive). Retorna uma forma representativa de cada grupo.
    """
    colecao = get_mongo_collection()
    pipeline = [
        {"$match": {"Grupo": {"$exists": True, "$ne": None, "$ne": ""}}},
        {"$project": {"GrupoTrim": {"$trim": {"input": "$Grupo"}}}},
        {"$group": {"_id": {"$toLower": "$GrupoTrim"}, "exemplo": {"$first": "$GrupoTrim"}, "count": {"$sum": 1}}},
        {"$sort": {"exemplo": 1}}
    ]
    results = list(colecao.aggregate(pipeline))
    grupos = [r["exemplo"] for r in results if r.get("exemplo")]
    return grupos

# @app.get("/grupos", response_model=List[str])
# def listar_grupos(case_insensitive: Optional[bool] = Query(False, description="Agrupar ignorando caixa")):
#     try:
        
#         if case_insensitive:
#             grupos = distinct_grupos_case_insensitive()
#         else:
#             grupos = distinct_grupos()
#         if not grupos:
#             raise HTTPException(status_code=404, detail="Nenhum grupo encontrado")
#         return grupos
#     except errors.PyMongoError as e:
#         raise HTTPException(status_code=500, detail=f"Erro no MongoDB: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/grupos", response_model=List[str])
def listar_grupos(case_insensitive: Optional[bool] = Query(False, description="Agrupar ignorando caixa")):
    try:
        
        if case_insensitive:
            grupos = distinct_grupos_case_insensitive()
        else:
            grupos = distinct_grupos()
        if not grupos:
            raise HTTPException(status_code=404, detail="Nenhum grupo encontrado")
        return grupos
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Erro no MongoDB: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
