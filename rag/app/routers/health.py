import logging

from fastapi import APIRouter

from app.config.settings import settings
from app.database.qdrant import qdrant_db
from app.models.schemas import HealthResponse
from app.services.embedding import embedding_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check():
    qdrant_ok = qdrant_db.client is not None
    ollama_ok = False
    try:
        from app.services.llm import llm_service

        llm_service.client.list()
        ollama_ok = True
    except Exception:
        pass

    info = {}
    if qdrant_ok:
        info = qdrant_db.get_collection_info()

    return HealthResponse(
        status="healthy" if qdrant_ok else "degraded",
        version=settings.VERSION,
        qdrant_connected=qdrant_ok,
        ollama_connected=ollama_ok,
        total_chunks=info.get("points_count", 0),
        embeddings_loaded=embedding_service.model is not None,
    )
