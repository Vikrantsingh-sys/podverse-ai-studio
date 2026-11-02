
import os
import json
import urllib.request
import urllib.error

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi


app = FastAPI(title="PodVerse AI Studio")


# CORS SETTINGS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# REQUEST MODELS
class VideoRequest(BaseModel):
    url: str


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class SemanticRequest(BaseModel):
    segments: list[TranscriptSegment]
    duration: int = Field(default=60, ge=10, le=600)
    count: int = Field(default=3, ge=1, le=20)


# YOUTUBE VIDEO ID EXTRACTOR
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


# HOME ROUTE
@app.get("/")
def home():
    return {
        "success": True,
        "message": "PodVerse AI Studio backend is running"
    }


# YOUTUBE TRANSCRIPT ANALYSIS
@app.post("/analyze")
def analyze_video(request: VideoRequest):

    video_id = get_video_id(request.url.strip())

    if not video_id:
        return {
            "success": False,
            "message": "Please enter a valid YouTube URL."
        }

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


# GEMINI AI SEMANTIC CLIP ANALYSIS
@app.post("/analyze-semantic")
def analyze_semantic(request: SemanticRequest):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is missing in Render Environment."
        )

    if not request.segments:
        raise HTTPException(
            status_code=400,
            detail="Transcript is empty."
        )

    # Prepare transcript with original timestamps and indexes
    transcript = [
        {
            "index": index,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        }
        for index, segment in enumerate(request.segments)
    ]

    prompt = f"""
You are an expert podcast editor and short-form video strategist.

Analyze the transcript and select the {request.count} strongest
and most engaging podcast moments.

CLIP REQUIREMENTS:
- Target duration: approximately {request.duration} seconds per clip.
- Select meaningful discussions, stories, insights, opinions,
  surprising statements, or useful explanations.
- Do not select random sentences.
- Each clip must make sense on its own.
- Preserve the complete context of the conversation.
- Start at a natural beginning and finish at a natural ending.
- Prefer moments with a strong opening hook.
- Avoid overlapping clips where possible.
- Use only the supplied segment indexes.
- Never invent dialogue or timestamps.
- Return fewer clips rather than weak or incomplete clips.

Return valid JSON only in this exact structure:

{{
  "clips": [
    {{
      "start_index": 0,
      "end_index": 10,
      "hook": "An engaging short title",
      "reason": "Why this moment is interesting"
    }}
  ]
}}

TRANSCRIPT:
{json.dumps(transcript, ensure_ascii=False)}
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3
        }
    }

    api_url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-2.5-flash:generateContent"
    )

    api_request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(api_request, timeout=120) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

        ai_text = (
            result["candidates"][0]["content"]["parts"][0]["text"]
        )

        ai_data = json.loads(ai_text)

        selected_clips = []

        for clip in ai_data.get("clips", []):

            start_index = clip.get("start_index")
            end_index = clip.get("end_index")

            if not isinstance(start_index, int):
                continue

            if not isinstance(end_index, int):
                continue

            if start_index < 0 or end_index < start_index:
                continue

            if end_index >= len(request.segments):
                continue

            start_time = request.segments[start_index].start
            end_time = request.segments[end_index].end

            clip_duration = end_time - start_time

            if clip_duration <= 0:
                continue

            if clip_duration > request.duration + 5:
                continue

            clip_text = " ".join(
                segment.text
                for segment in request.segments[
                    start_index:end_index + 1
                ]
            )

            selected_clips.append({
                "start": start_time,
                "end": end_time,
                "duration": round(clip_duration, 2),
                "hook": str(
                    clip.get("hook", "Podcast Highlight")
                ),
                "reason": str(
                    clip.get("reason", "")
                ),
                "text": clip_text
            })

        return {
            "success": True,
            "total_clips": len(selected_clips),
            "clips": selected_clips,
            "message": "AI semantic analysis completed."
        }

    except urllib.error.HTTPError as error:
        error_detail = error.read().decode(
            "utf-8",
            errors="replace"
        )

        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {error_detail[:1000]}"
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to Gemini API: {str(error)}"
        )

    except (KeyError, IndexError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=502,
            detail=f"Unexpected Gemini response: {str(error)}"
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"AI analysis failed: {str(error)[:500]}"
        )
