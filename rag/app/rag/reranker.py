import logging

try:
    from sentence_transformers import CrossEncoder

    HAS_CROSS_ENCODER = True
except ImportError:
    HAS_CROSS_ENCODER = False

from app.config.settings import settings
from app.models.retrieval_result import RetrievalResult

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        if not HAS_CROSS_ENCODER:
            logger.warning("CrossEncoder not available. Reranking disabled.")
            return
        try:
            logger.info("Loading reranker: %s", settings.RERANK_MODEL)
            self.model = CrossEncoder(settings.RERANK_MODEL)
            logger.info("Reranker loaded successfully")
        except Exception as e:
            logger.warning("Failed to load reranker: %s", e)
            self.model = None

    def rerank(
        self,
        question: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        if self.model is None or not results:
            return results

        try:
            pairs = [(question, r.text) for r in results]
            scores = self.model.predict(pairs)

            for i, r in enumerate(results):
                r.score = round(float(scores[i]), 4)

            results.sort(key=lambda x: x.score, reverse=True)
            logger.debug("Reranking applied. Top score: %.4f", results[0].score)
        except Exception as e:
            logger.error("Reranking failed: %s", e)

        return results
