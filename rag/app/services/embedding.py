import logging
import os

os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.model: SentenceTransformer | None = None
        self.dimension = settings.EMBED_DIM
        self._load_model()

    def _load_model(self):
        try:
            logger.info("Loading embedding model: %s", settings.EMBED_MODEL)
            self.model = SentenceTransformer(settings.EMBED_MODEL)
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error("Failed to load embedding model: %s", e)
            raise

    def encode(self, text: str | list[str]) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Embedding model not loaded")
        texts = [text] if isinstance(text, str) else text
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=settings.EMBED_NORMALIZE,
            show_progress_bar=False,
        )
        return embeddings

    def encode_query(self, text: str) -> list[float]:
        embedding = self.encode(text)
        if embedding.ndim == 2:
            embedding = embedding[0]
        return embedding.tolist()

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        return self.encode(texts)


embedding_service = EmbeddingService()
