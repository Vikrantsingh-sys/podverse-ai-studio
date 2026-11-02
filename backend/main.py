
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.parse import urlparse

app = FastAPI(title="PodVerse AI Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

@app.get("/")
def home():
    return {"message": "PodVerse AI Studio backend is running"}

@app.post("/analyze")
def analyze_video(request: VideoRequest):
    url = request.url.strip()
    parsed = urlparse(url)

    if parsed.hostname not in [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "www.youtube-nocookie.com"
    ]:
        return {"success": False, "message": "Please enter a valid YouTube URL."}

    return {
        "success": True,
        "message": "YouTube link received successfully.",
        "url": url,
        "next_step": "Transcript analysis will be added next."
    }
