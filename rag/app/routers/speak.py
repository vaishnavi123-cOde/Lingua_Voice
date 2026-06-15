import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.models.schemas import SpeechRequest
from app.services.tts import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["speak"])


@router.post("/speak")
async def speak(request: SpeechRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    try:
        audio_path = await tts_service.generate(
            text=text,
            voice=request.voice,
            speed=request.speed,
        )
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            filename="response.mp3",
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        logger.error("TTS failed: %s", e)
        raise HTTPException(status_code=500, detail="Speech generation failed")
