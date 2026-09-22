"""
Server-side transcription - browser SpeechRecognition was unreliable
across Brave/Firefox/Chrome (likely secure-context/vendor differences,
not something worth debugging further under deadline pressure). This
replaces it: the browser records audio and uploads it, this endpoint
transcribes it with Gemini - reuses your existing GEMINI_API_KEY, no
new signup, no new secret.

NOTE: I couldn't see p1_service/rag/service/gemini_service.py to
confirm the exact google-genai call pattern your project already uses
elsewhere. This follows the documented google-genai SDK shape as of
the version already pinned in p1_service/requirements.txt. Test this
first - if client.files.upload / client.models.generate_content don't
match your installed SDK version, send me gemini_service.py and I'll
fix it in one pass rather than you debugging SDK internals tonight.
"""

import os
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException
from google import genai

router = APIRouter()

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY is not configured on this server.",
            )
        _client = genai.Client(api_key=api_key)
    return _client


@router.post("/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts a recorded audio clip (whatever format the browser's
    MediaRecorder produced - webm/ogg/wav) and returns
    { "transcript": "..." }.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio received.")

    suffix = os.path.splitext(file.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        client = _get_client()
        uploaded = client.files.upload(file=tmp_path)

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        response = client.models.generate_content(
            model=model_name,
            contents=[
                uploaded,
                (
                    "Transcribe this audio exactly as spoken, in the "
                    "language it was spoken in. Return ONLY the "
                    "transcript text - no preamble, no quotation marks, "
                    "no commentary."
                ),
            ],
        )
        transcript = (response.text or "").strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")
    finally:
        os.unlink(tmp_path)

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="Could not transcribe that - please try again or type your question.",
        )

    return {"transcript": transcript}
