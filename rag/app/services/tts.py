import asyncio
import logging
import os
import time
import uuid
from pathlib import Path

import edge_tts

from app.config.settings import settings
from app.services.monitoring import metrics_collector

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self):
        self.output_dir = Path(settings.TTS_OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
    ) -> str:
        start = time.perf_counter()
        voice = voice or settings.TTS_VOICE
        speed = speed or settings.TTS_SPEED

        filename = f"speech_{uuid.uuid4().hex}.mp3"
        filepath = self.output_dir / filename

        percent = int((speed - 1.0) * 100)
        rate = f"+{percent}%" if percent >= 0 else f"{percent}%"

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
            )
            await communicate.save(str(filepath))
            duration = (time.perf_counter() - start) * 1000
            metrics_collector.record_tts(len(text), duration, True)
            logger.info("TTS generated: %s (%dms)", filename, duration)
            return str(filepath)
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            metrics_collector.record_tts(len(text), duration, False)
            logger.error("TTS generation failed: %s", e)
            raise

    def cleanup_old_files(self, max_age_hours: int = 1):
        try:
            now = time.time()
            for f in self.output_dir.iterdir():
                if f.is_file() and f.suffix == ".mp3":
                    age_hours = (now - f.stat().st_mtime) / 3600
                    if age_hours > max_age_hours:
                        f.unlink()
                        logger.debug("Cleaned up old audio: %s", f.name)
        except Exception as e:
            logger.error("TTS cleanup failed: %s", e)


tts_service = TTSService()
