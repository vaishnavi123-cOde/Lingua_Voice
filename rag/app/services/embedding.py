import logging
import os
from collections import OrderedDict

os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config.settings import settings

logger = logging.getLogger(__name__)


class LRUCache:
    def __init__(self, capacity: int = 128):
        self.capacity = capacity
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    def get(self, key: str) -> list[float] | None:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: str, value: list[float]):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()


class EmbeddingService:
    def __init__(self):
        self.model: SentenceTransformer | None = None
        self.dimension = settings.EMBED_DIM
        self._query_cache = LRUCache(capacity=settings.EMBED_CACHE_SIZE)
        self._load_model()

    def _load_model(self):
        try:
            logger.info("Loading embedding model: %s", settings.EMBED_MODEL)
            self.model = SentenceTransformer(settings.EMBED_MODEL)
            if settings.EMBED_FP16 and self.model.device.type == "cuda":
                self.model.half()
                logger.info("Embedding model converted to fp16 on CUDA")
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
            batch_size=settings.EMBED_BATCH_SIZE,
        )
        return embeddings

    def encode_query(self, text: str) -> list[float]:
        cached = self._query_cache.get(text)
        if cached is not None:
            return cached
        embedding = self.encode(text)
        if embedding.ndim == 2:
            embedding = embedding[0]
        result = embedding.tolist()
        self._query_cache.put(text, result)
        return result

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        return self.encode(texts)

    def clear_cache(self):
        self._query_cache.clear()
        logger.info("Embedding cache cleared")


embedding_service = EmbeddingService()
