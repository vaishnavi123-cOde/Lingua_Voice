import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self.enabled = settings.MONITORING_ENABLED
        self.metrics_file = Path(settings.METRICS_FILE)
        if self.enabled:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

    def record_retrieval(
        self,
        question: str,
        top_scores: list[float],
        retrieval_time_ms: float,
        num_results: int,
    ):
        if not self.enabled:
            return
        entry = {
            "event": "retrieval",
            "timestamp": datetime.utcnow().isoformat(),
            "question": question[:200],
            "top_scores": [round(s, 4) for s in top_scores[:5]],
            "mean_score": round(float(np.mean(top_scores)), 4) if top_scores else 0.0,
            "retrieval_time_ms": round(retrieval_time_ms, 2),
            "num_results": num_results,
        }
        self._write(entry)

    def record_response(
        self,
        question: str,
        answer: str,
        confidence: float,
        retrieval_time_ms: float,
        llm_time_ms: float,
        total_time_ms: float,
    ):
        if not self.enabled:
            return
        entry = {
            "event": "response",
            "timestamp": datetime.utcnow().isoformat(),
            "question": question[:200],
            "answer_length": len(answer),
            "confidence": round(confidence, 4),
            "retrieval_time_ms": round(retrieval_time_ms, 2),
            "llm_time_ms": round(llm_time_ms, 2),
            "total_time_ms": round(total_time_ms, 2),
        }
        self._write(entry)

    def record_error(self, error_type: str, detail: str):
        if not self.enabled:
            return
        entry = {
            "event": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "detail": detail[:500],
        }
        self._write(entry)

    def record_tts(self, text_length: int, duration_ms: float, success: bool):
        if not self.enabled:
            return
        entry = {
            "event": "tts",
            "timestamp": datetime.utcnow().isoformat(),
            "text_length": text_length,
            "duration_ms": round(duration_ms, 2),
            "success": success,
        }
        self._write(entry)

    def _write(self, entry: dict):
        try:
            with open(self.metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error("Failed to write metric: %s", e)


import numpy as np

metrics_collector = MetricsCollector()
