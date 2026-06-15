import logging
import time

from app.config.settings import settings
from app.database.qdrant import qdrant_db
from app.models.retrieval_result import RetrievalResult
from app.services.embedding import embedding_service
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.reranker import Reranker
from app.rag.context_compressor import ContextCompressor

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self):
        self.hybrid_retriever = HybridRetriever()
        self.reranker = Reranker()
        self.context_compressor = ContextCompressor()

    def retrieve(self, question: str) -> tuple[list[RetrievalResult], float, float]:
        start = time.perf_counter()

        query_vector = embedding_service.encode_query(question)

        client = qdrant_db.get_client()
        raw_results = client.query_points(
            collection_name=settings.COLLECTION_NAME,
            query=query_vector,
            limit=settings.RETRIEVAL_TOP_K * 2,
            with_payload=True,
        ).points

        results = [
            RetrievalResult(
                text=r.payload.get("text", ""),
                source=r.payload.get("source", "unknown"),
                score=r.score,
            )
            for r in raw_results
            if r.score >= settings.RETRIEVAL_MIN_SCORE
        ]

        retrieval_time = (time.perf_counter() - start) * 1000

        if settings.ENABLE_HYBRID_SEARCH:
            hybrid_results = self.hybrid_retriever.retrieve(question, results)
            if hybrid_results:
                results = hybrid_results

        if settings.ENABLE_RERANKING and results:
            reranked = self.reranker.rerank(question, results)
            if reranked:
                results = reranked

        final = results[: settings.RERANK_TOP_K]
        for i, r in enumerate(final):
            r.rank = i + 1

        confidence = self._compute_confidence(final)

        if settings.ENABLE_CONTEXT_COMPRESSION and final:
            final = self.context_compressor.compress(question, final)

        return final, confidence, retrieval_time

    def _compute_confidence(self, results: list[RetrievalResult]) -> float:
        if not results:
            return 0.0
        scores = [r.score for r in results]
        if len(scores) == 1:
            return float(scores[0])
        weights = [0.5, 0.3, 0.2][: len(scores)]
        weighted = sum(s * w for s, w in zip(scores, weights))
        return round(float(weighted), 4)


retrieval_service = RetrievalService()
