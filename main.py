from fastapi import FastAPI, Request, HTTPException ,Query
from fastapi.responses import StreamingResponse
import requests

from pymongo import MongoClient, errors
from pydantic import BaseModel
from typing import List
from bson import ObjectId
from typing import List
import grupo as gru
import espacos as esp

app = FastAPI()

# Link direto para o vídeo MP4
VIDEO_URL_MP4 = "http://solard2.metag.click:80/movie/729767765/551952986/4667973.mp4"

# Link direto para o vídeo TS (HLS)
VIDEO_URL_TS = "http://solard2.metag.click:80/729767765/551952986/4666509"

@app.get("/video")
def stream_mp4_video():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        video_response = requests.get(VIDEO_URL_MP4, stream=True, headers=headers, timeout=15)

        if video_response.status_code != 200:
            return StreamingResponse(
                content=iter([f"Erro ao acessar o vídeo MP4: {video_response.status_code}".encode()]),
                status_code=502,
                media_type="text/plain"
            )

        return StreamingResponse(
            video_response.iter_content(chunk_size=1024),
            media_type="video/mp4"
        )

    except Exception as e:
        return StreamingResponse(
            content=iter([f"Erro interno MP4: {str(e)}".encode()]),
            status_code=500,
            media_type="text/plain"
        )

@app.get("/tv")
def stream_ts_video():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        video_response = requests.get(VIDEO_URL_TS, stream=True, headers=headers, timeout=15)

        if video_response.status_code != 200:
            return StreamingResponse(
                content=iter([f"Erro ao acessar o vídeo TS: {video_response.status_code}".encode()]),
                status_code=502,
                media_type="text/plain"
            )

        return StreamingResponse(
            video_response.iter_content(chunk_size=1024),
            media_type="video/MP2T",
            headers={
                "Content-Disposition": "attachment; filename=tv.ts"
            }
        )

    except Exception as e:
        return StreamingResponse(
            content=iter([f"Erro interno TS: {str(e)}".encode()]),
            status_code=500,
            media_type="text/plain"
        )

@app.get("/videoranger")
async def stream_mp4_video(request: Request):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        # Captura o cabeçalho Range enviado pelo navegador
        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header

        # Faz a requisição com suporte a streaming bruto
        video_response = requests.get(VIDEO_URL_MP4, stream=True, headers=headers, timeout=15)

        # Verifica se a resposta foi bem-sucedida
        if video_response.status_code not in [200, 206]:
            return StreamingResponse(
                content=iter([f"Erro ao acessar o vídeo MP4: {video_response.status_code}".encode()]),
                status_code=502,
                media_type="text/plain"
            )

        # Monta os headers corretos para o navegador
        response_headers = {
            "Accept-Ranges": "bytes"
        }

        if "Content-Length" in video_response.headers:
            response_headers["Content-Length"] = video_response.headers["Content-Length"]
        if "Content-Range" in video_response.headers:
            response_headers["Content-Range"] = video_response.headers["Content-Range"]

        return StreamingResponse(
            video_response.raw,
            status_code=206 if range_header else 200,
            media_type="video/mp4",
            headers=response_headers
        )

    except requests.exceptions.RequestException as e:
        return StreamingResponse(
            content=iter([f"Erro de rede ao acessar o vídeo: {str(e)}".encode()]),
            status_code=504,
            media_type="text/plain"
        )
    except Exception as e:
        return StreamingResponse(
            content=iter([f"Erro interno: {str(e)}".encode()]),
            status_code=500,
            media_type="text/plain"
        )


# Modelo de dados
class TV(BaseModel):
    IdVideo: str | None
    Nome: str | None
    Grupo: str | None
    Url: str | None
    Logo: str | None



# Modelo de dados
class Canal(BaseModel):
    IdVideo: str | None
    Nome: str | None
    Grupo: str | None
    Url: str | None
    Logo: str | None
    grupoID: str | None
   

# Conexão com MongoDB Atlas
def get_mongo_collection():
    try:
        client = MongoClient(
            "mongodb+srv://teste:teste@cluster0.zjhbafz.mongodb.net/M3U?retryWrites=true&w=majority",
            serverSelectionTimeoutMS=5000  # timeout de conexão
        )
        db = client["M3U"]
        return db["canais"]
    except errors.ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao MongoDB Atlas.")
    except errors.ConfigurationError:
        raise HTTPException(status_code=500, detail="Erro na configuração da string de conexão.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")


# Conexão com MongoDB Atlas
def get_mongo_collection_grupo():
    try:
        client = MongoClient(
            "mongodb+srv://teste:teste@cluster0.zjhbafz.mongodb.net/M3U?retryWrites=true&w=majority",
            serverSelectionTimeoutMS=5000  # timeout de conexão
        )
        db = client["M3U"]
        return db["grupos"]
    except errors.ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao MongoDB Atlas.")
    except errors.ConfigurationError:
        raise HTTPException(status_code=500, detail="Erro na configuração da string de conexão.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")

def get_mongo_collection_tv():
    try:
        client = MongoClient(
            "mongodb+srv://teste:teste@cluster0.zjhbafz.mongodb.net/M3U?retryWrites=true&w=majority",
            serverSelectionTimeoutMS=5000  # timeout de conexão
        )
        db = client["M3U"]
        return db["tv"]
    except errors.ServerSelectionTimeoutError:
        raise HTTPException(status_code=503, detail="Não foi possível conectar ao MongoDB Atlas.")
    except errors.ConfigurationError:
        raise HTTPException(status_code=500, detail="Erro na configuração da string de conexão.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado: {str(e)}")
    

@app.get("/canais", response_model=List[Canal])
def listar_canais(
    group: str | None = Query(default=None, description="Filtrar por grupo"),
    name: str | None = Query(default=None, description="Filtrar por nome"),
    groupid: str | None = Query(default=None, description="Filtrar por groupid"),
    limit: int = Query(default=10, ge=1, le=100, description="Número máximo de canais"),
    skip: int = Query(default=0, ge=0, description="Número de canais a pular")
):
    try:
        colecao = get_mongo_collection()

        filtro = {}
        if group:
            filtro["Grupo"] = {"$regex":group, "$options": "i"}
        if name:
            filtro["Nome"] = {"$regex": name, "$options": "i"}
        if groupid:
            filtro["grupoID"] = {"$regex": groupid, "$options": "i"}

        canais = list(colecao.find(filtro,{"IdVideo": 1, "Nome": 1, "Grupo": 1, "Url": 1,"Logo":1,"grupoID":1}).skip(skip).limit(limit))

        if not canais:
            raise HTTPException(status_code=404, detail="Nenhum canal encontrado com os filtros aplicados.")
        return canais
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar canais: {str(e)}")




# @app.get("/player/{idvideo}")
# async def stream_mp4_video(idvideo: str, request: Request):
#     # busca a URL no Mongo (IdVideo ou _id)
#     colecao = get_mongo_collection()
#     doc = colecao.find_one({"IdVideo": idvideo}, {"Url": 1, "_id": 1})
#     if not doc:
#         try:
#             oid = ObjectId(idvideo)
#             doc = colecao.find_one({"_id": oid}, {"Url": 1, "_id": 1})
#         except Exception:
#             doc = None

#     if not doc:
#         raise HTTPException(status_code=404, detail="Vídeo não encontrado")

#     video_url = doc.get("Url") or doc.get("url")
#     if not video_url:
#         raise HTTPException(status_code=404, detail="URL do vídeo não encontrada no documento")

#     # repassa Range do cliente para o upstream
#     headers = {"User-Agent": "Mozilla/5.0"}
#     client_range = request.headers.get("range")
#     if client_range:
#         headers["Range"] = client_range

#     try:
#         upstream = requests.get(video_url, stream=True, headers=headers, timeout=20)
#     except requests.RequestException as e:
#         raise HTTPException(status_code=504, detail=f"Erro de rede ao acessar o vídeo upstream: {e}")

#     if upstream.status_code not in (200, 206):
#         raise HTTPException(status_code=502, detail=f"Upstream retornou status {upstream.status_code}")

#     # monta headers de resposta para o cliente; repassa os valores do upstream quando presentes
#     resp_headers = {
#         "Accept-Ranges": "bytes",
#         "Content-Type": upstream.headers.get("Content-Type", "video/mp4")
#     }
#     if "Content-Range" in upstream.headers:
#         resp_headers["Content-Range"] = upstream.headers["Content-Range"]
#     if "Content-Length" in upstream.headers:
#         resp_headers["Content-Length"] = upstream.headers["Content-Length"]

#     # expõe headers úteis para clientes web (se estiver usando CORS, combine com CORSMiddleware)
#     resp_headers["Access-Control-Expose-Headers"] = "Content-Range, Content-Length, Accept-Ranges"

#     # generator que transmite em chunks e fecha a conexão upstream ao final
#     def iter_chunks(chunk_size: int = 64 * 1024):
#         try:
#             for chunk in upstream.iter_content(chunk_size=chunk_size):
#                 if chunk:
#                     yield chunk
#         finally:
#             try:
#                 upstream.close()
#             except Exception:
#                 pass

#     status = 206 if client_range else 200
#     return StreamingResponse(iter_chunks(), status_code=status, media_type=resp_headers["Content-Type"], headers=resp_headers)


@app.get("/player/{idvideo}")
async def stream_mp4_video(idvideo: str, request: Request):
    colecao = get_mongo_collection()
    doc = colecao.find_one({"IdVideo": idvideo}, {"Url": 1, "_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    video_url = doc["Url"]
    headers = {"User-Agent": "Mozilla/5.0"}
    client_range = request.headers.get("range")
    if client_range:
        headers["Range"] = client_range

    upstream = requests.get(video_url, stream=True, headers=headers, timeout=20)

    content_length = upstream.headers.get("Content-Length")
    content_type = "video/mp4; codecs=\"avc1.42E01E, mp4a.40.2\""

    resp_headers = {
        "Accept-Ranges": "bytes",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Range",
        "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
        "Content-Disposition": 'inline; filename="video.mp4"',
        "Content-Encoding": "identity",
        "Content-Type": content_type,
    }

    if "Content-Range" in upstream.headers:
        resp_headers["Content-Range"] = upstream.headers["Content-Range"]
    elif content_length:
        resp_headers["Content-Range"] = f"bytes 0-{int(content_length)-1}/{content_length}"
        resp_headers["Content-Length"] = content_length

    def iter_chunks(size=64*1024):
        for chunk in upstream.iter_content(chunk_size=size):
            if chunk:
                yield chunk
        upstream.close()

    return StreamingResponse(iter_chunks(), status_code=206, media_type=content_type, headers=resp_headers)


# Modelo de dados
class Grupo(BaseModel):
    nome: str | None
    grupoID: str | None

@app.get("/grupos", response_model=List[Grupo])
def listar_grupos(case_insensitive: gru.Optional[bool] = Query(False, description="Agrupar ignorando caixa")):
             
    try:

        colecao = get_mongo_collection_grupo()
        grupos = list(colecao.find("",{ "nome": 1, "grupoID":1}))
        return grupos  
        # if case_insensitive:
        #     grupos = esp.limpar_emoticons_e_espacos(gru.distinct_grupos_case_insensitive())
        # else:
        #     grupos = esp.limpar_emoticons_e_espacos( gru.distinct_grupos())
        # if not grupos:
        #     raise HTTPException(status_code=404, detail="Nenhum grupo encontrado")
        # return grupos
    except errors.PyMongoError as e:
        raise HTTPException(status_code=500, detail=f"Erro no MongoDB: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/canaisTv", response_model=List[TV])
def listar_tv(
    group: str | None = Query(default=None, description="Filtrar por grupo"),
    name: str | None = Query(default=None, description="Filtrar por nome"),
    limit: int = Query(default=10, ge=1, le=100, description="Número máximo de tv"),
    skip: int = Query(default=0, ge=0, description="Número de tv a pular")
):
    try:
        colecao = get_mongo_collection_tv()

        filtro = {}
        if group:
            filtro["Grupo"] = {"$regex":group, "$options": "i"}
        if name:
            filtro["Nome"] = {"$regex": name, "$options": "i"}
  

        canais = list(colecao.find(filtro,{"IdVideo": 1, "Nome": 1, "Grupo": 1, "Url": 1,"Logo":1}).skip(skip).limit(limit))

        if not canais:
            raise HTTPException(status_code=404, detail="Nenhum canal encontrado com os filtros aplicados.")
        return canais
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar tv: {str(e)}")

