
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI(title="PodVerse AI Studio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

def get_video_id(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host in ["youtu.be", "www.youtu.be"]:
        return parsed.path.strip("/").split("/")[0]

    if host in ["youtube.com", "www.youtube.com", "m.youtube.com"]:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [None])[0]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2]
    return None

@app.get("/")
def home():
    return {"message": "PodVerse AI Studio backend is running"}

@app.post("/analyze")
def analyze_video(request: VideoRequest):
    video_id = get_video_id(request.url.strip())

    if not video_id:
        return {"success": False, "message": "Please enter a valid YouTube URL."}

    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)

        segments = [
            {
                "start": round(item.start, 2),
                "duration": round(item.duration, 2),
                "text": item.text
            }
            for item in transcript
        ]

        return {
            "success": True,
            "video_id": video_id,
            "transcript_segments": segments,
            "message": "Transcript extracted successfully."
        }

    except Exception as error:
        return {
            "success": False,
            "video_id": video_id,
            "message": "Transcript unavailable for this video.",
            "detail": str(error)[:500]
        }
