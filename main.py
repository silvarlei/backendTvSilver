from fastapi import FastAPI, Response
import requests

app = FastAPI()

# Link direto para o vídeo .ts
VIDEO_URL = "http://saga10.pro:80/345715/562156/2639316"  # substitua pelo seu link real

@app.get("/video")
def stream_ts_video():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        video_response = requests.get(VIDEO_URL, stream=True, headers=headers, timeout=15)

        if video_response.status_code != 200:
            return Response(content=f"Erro ao acessar o vídeo: {video_response.status_code}", status_code=502)

        return Response(
            content=video_response.raw,
            media_type="video/MP2T",  # MIME type para .ts
            headers={
                "Content-Disposition": "inline; filename=video.ts"
            }
        )

    except Exception as e:
        return Response(content=f"Erro interno: {str(e)}", status_code=500)
