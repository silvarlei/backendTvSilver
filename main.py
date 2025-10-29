from fastapi import FastAPI, Response
import requests

app = FastAPI()

# Link fixo do vídeo (pode ser .mp4 ou .ts)
VIDEO_URL = "http://saga10.pro:80/345715/562156/2639316"

@app.get("/video")
def stream_video():
    try:
        video_response = requests.get(VIDEO_URL, stream=True)
        if video_response.status_code != 200:
            return Response(content="Erro ao acessar o vídeo", status_code=502)

        headers = {
            "Content-Type": "video/MP2T",  # ou "video/MP2T" para .ts
            "Content-Disposition": "inline; filename=video/MP2T"
        }

        return Response(content=video_response.raw, headers=headers, media_type="video/mp4")
    except Exception as e:
        return Response(content=f"Erro interno: {str(e)}", status_code=500)
