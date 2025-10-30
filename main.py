from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import requests

app = FastAPI()

# Link direto para o vídeo MP4
VIDEO_URL_MP4 = "http://solard2.metag.click:80/movie/729767765/551952986/4244413.mp4"

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
