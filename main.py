from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import requests


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
