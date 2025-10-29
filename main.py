from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import requests

app = FastAPI()

VIDEO_URL = "http://solard2.metag.click:80/movie/729767765/551952986/4667973.mp4"  # substitua pelo seu link real

@app.get("/video")
def stream_ts_video():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        video_response = requests.get(VIDEO_URL, stream=True, headers=headers, timeout=15)

        if video_response.status_code != 200:
            return StreamingResponse(
                content=iter([f"Erro ao acessar o vídeo: {video_response.status_code}".encode()]),
                status_code=502,
                media_type="text/plain"
            )

        return StreamingResponse(
            video_response.iter_content(chunk_size=1024),
            media_type="video/MP2T",
            headers={
                "Content-Disposition": "inline; filename=video.ts"
            }
        )

    except Exception as e:
        return StreamingResponse(
            content=iter([f"Erro interno: {str(e)}".encode()]),
            status_code=500,
            media_type="text/plain"
        )
