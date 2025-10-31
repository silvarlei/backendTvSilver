#!/usr/bin/env python3
import re
import unicodedata
from collections import defaultdict
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError

# ====== CONFIG ======
MONGO_URI = "mongodb+srv://teste:teste@cluster0.zjhbafz.mongodb.net/M3U?retryWrites=true&w=majority"
DB_NAME = "M3U"
COL_CANAIS = "canais"
COL_GRUPOS = "grupos"
BATCH_SIZE = 1000
# ====================

_WHITESPACE_RE = re.compile(r"\s+")
_EDGE_CLEAN_RE = re.compile(r"[^a-z0-9\s-]")  # permite letras, dígitos, espaço e traço

def normalize_for_id(s: str) -> str:
    """Gera slug-like grupoID a partir de um valor de Grupo."""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))  # remove diacríticos
    s = s.lower()
    s = s.replace("–", "-").replace("—", "-").replace("―", "-")  # variantes de hífen
    s = _EDGE_CLEAN_RE.sub("", s)  # remove símbolos exceto espaço e traço
    s = _WHITESPACE_RE.sub(" ", s).strip()  # colapsa espaços
    s = s.replace(" ", "-")  # transforma em slug
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "sem-grupo"

def choose_representative(variants_counts: dict) -> str:
    """Escolhe o nome representativo do grupo: o valor original com maior contagem (tie -> lexicográfico)."""
    if not variants_counts:
        return ""
    items = sorted(variants_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return items[0][0]

def build_groups_and_update_canais():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    canais = db[COL_CANAIS]
    grupos = db[COL_GRUPOS]

    try:
        # 1) Agrupa valores originais e conta ocorrências por Grupo
        pipeline = [
            {"$match": {"Grupo": {"$exists": True, "$ne": None, "$ne": ""}}},
            {"$group": {"_id": "$Grupo", "count": {"$sum": 1}}}
        ]
        agg = list(canais.aggregate(pipeline))
        if not agg:
            print("Nenhum valor de Grupo encontrado para processar.")
            return

        # mapa normalizado -> { original_value: count, ... }
        map_norm = defaultdict(lambda: defaultdict(int))
        for doc in agg:
            orig = doc["_id"]
            cnt = int(doc.get("count", 1))
            norm = normalize_for_id(orig)
            map_norm[norm][orig] += cnt

        # 2) Upsert na coleção grupos
        bulk_upserts = []
        for norm, variants in map_norm.items():
            nome_repr = choose_representative(variants)
            grupo_doc = {
                "grupoID": norm,
                "nome": nome_repr,
                "nome_norm": norm,
                "count": sum(variants.values())
            }
            bulk_upserts.append(
                UpdateOne({"grupoID": norm}, {"$set": grupo_doc}, upsert=True)
            )
        if bulk_upserts:
            # executar em batches
            for i in range(0, len(bulk_upserts), BATCH_SIZE):
                batch = bulk_upserts[i:i+BATCH_SIZE]
                res = grupos.bulk_write(batch)
                print(f"Upsert grupos batch {i//BATCH_SIZE + 1}: matched {res.matched_count}, upserted {res.upserted_count}, modified {res.modified_count}")

        # 3) Atualizar cada documento em canais adicionando grupoID (bulk)
        # Usamos cursor para processar em batches
        ops = []
        total_updates = 0
        cursor = canais.find({}, {"_id": 1, "Grupo": 1})
        for doc in cursor:
            _id = doc["_id"]
            orig = doc.get("Grupo") or ""
            norm = normalize_for_id(orig)
            if not norm:
                norm = "sem-grupo"
            ops.append(UpdateOne({"_id": _id}, {"$set": {"grupoID": norm}}))
            if len(ops) >= BATCH_SIZE:
                res = canais.bulk_write(ops)
                total_updates += res.modified_count + (res.upserted_count if hasattr(res, "upserted_count") else 0)
                ops = []
        if ops:
            res = canais.bulk_write(ops)
            total_updates += res.modified_count + (res.upserted_count if hasattr(res, "upserted_count") else 0)

        print(f"Total documentos 'canais' atualizados com grupoID: {total_updates}")

        # 4) Criar índices
        try:
            grupos.create_index([("grupoID", 1)], unique=True)
            canais.create_index([("grupoID", 1)])
            print("Índices criados: grupos.grupoID (unique), canais.grupoID")
        except Exception as ix_err:
            print("Erro ao criar índices:", ix_err)

        print("Migração parcial concluída com êxito.")

    except PyMongoError as e:
        print("Erro no MongoDB durante a migração:", e)
    finally:
        client.close()

if __name__ == "__main__":
    build_groups_and_update_canais()
