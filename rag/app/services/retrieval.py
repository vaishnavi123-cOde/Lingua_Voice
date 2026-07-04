import logging
import re
import time
from collections import OrderedDict

from qdrant_client.http import models

from app.config.settings import settings
from app.database.qdrant import qdrant_db
from app.models.retrieval_result import RetrievalResult
from app.services.embedding import embedding_service
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.reranker import Reranker
from app.rag.context_compressor import ContextCompressor

logger = logging.getLogger(__name__)

# Common SQL typos map
SQL_TYPOS = {
    "primaru": "primary",
    "foriegn": "foreign",
    "forign": "foreign",
    "forgein": "foreign",
    "uniuqe": "unique",
    "unquie": "unique",
    "selec": "select",
    "selct": "select",
    "selet": "select",
    "slect": "select",
    "insret": "insert",
    "inserrt": "insert",
    "updat": "update",
    "updte": "update",
    "delte": "delete",
    "delet": "delete",
    "wgere": "where",
    "wehre": "where",
    "whre": "where",
    "wher": "where",
    "grup": "group",
    "grp": "group",
    "grooup": "group",
    "ordr": "order",
    "oder": "order",
    "havng": "having",
    "havin": "having",
    "joint": "join",
    "joine": "join",
    "joun": "join",
    "creat": "create",
    "cret": "create",
    "crerate": "create",
    "talbe": "table",
    "tabl": "table",
    "tble": "table",
    "colum": "column",
    "colmn": "column",
    "coloumn": "column",
    "foregin": "foreign",
    "foriegn key": "foreign key",
    "primaru key": "primary key",
    "primery": "primary",
    "primry": "primary",
    "queery": "query",
    "querry": "query",
    "qurey": "query",
    "queires": "queries",
    "queris": "queries",
    "indx": "index",
    "indez": "index",
    "indxes": "indexes",
    "contraint": "constraint",
    "contrains": "constraint",
    "contrainst": "constraint",
    "refereces": "references",
    "refrences": "references",
    "referecnes": "references",
    "cascad": "cascade",
    "cacade": "cascade",
    "transacton": "transaction",
    "transacion": "transaction",
    "triger": "trigger",
    "triggr": "trigger",
    "funciton": "function",
    "fucntion": "function",
    "procdure": "procedure",
    "procedur": "procedure",
    "normalis": "normaliz",
    "normalisaton": "normalization",
    "subquer": "subquery",
    "subquerry": "subquery",
    "correlated subquer": "correlated subquery",
    "correalted": "correlated",
}


class RetrievalCache:
    def __init__(self, capacity: int = 64):
        self.capacity = capacity
        self._cache: OrderedDict[str, tuple[list[RetrievalResult], float, float]] = OrderedDict()

    def get(self, key: str):
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: str, value: tuple[list[RetrievalResult], float, float]):
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()


class RetrievalService:
    def __init__(self):
        self.hybrid_retriever = HybridRetriever()
        self.reranker = Reranker()
        self.context_compressor = ContextCompressor()
        self.cache = RetrievalCache(capacity=settings.RETRIEVAL_CACHE_SIZE)
        self._last_results: list[RetrievalResult] | None = None

    def normalize_query(self, question: str) -> str:
        q = question.lower().strip()
        q = re.sub(r"[^\w\s]", " ", q)
        q = re.sub(r"\s+", " ", q).strip()
        words = q.split()
        corrected = []
        for w in words:
            if w in SQL_TYPOS:
                corrected.append(SQL_TYPOS[w])
            else:
                corrected.append(w)
        return " ".join(corrected)

    def is_follow_up(self, question: str, history: list | None, current_concept: str = "") -> bool:
        q_lower = question.lower().strip()
        q_clean = q_lower.strip("?.! ")

        q_concept = self._extract_concept(q_clean)
        # If question contains a different SQL concept from current topic → NOT a follow-up
        if q_concept and current_concept and q_concept.lower() != current_concept.lower():
            return False
        # If question introduces a new concept and there is no current topic → NOT a follow-up
        if q_concept and not current_concept:
            return False

        follow_up_indicators = [
            "yes", "no", "okay", "ok", "sure", "got it", "i see",
            "understood", "makes sense",
            "i don't understand", "i don't get it",
            "can you explain", "explain again", "say that again",
            "repeat", "again", "what does that mean",
            "why", "how",
            "can you give", "give an example", "show me", "show an example",
            "tell me more", "tell me about",
            "i understand", "i see",
        ]
        for indicator in follow_up_indicators:
            if q_clean == indicator or q_clean.startswith(indicator):
                return True

        return False

    def _extract_concept(self, text: str) -> str:
        from app.routers.ask import SQL_CONCEPTS
        for concept in SQL_CONCEPTS:
            if concept in text:
                return concept
        return ""

    def detect_topic_change(self, question: str, current_concept: str) -> bool:
        q_lower = question.lower().strip()
        new_concept = self._extract_concept(q_lower)
        if not new_concept:
            return False
        if not current_concept:
            return False
        return new_concept.lower() != current_concept.lower()

    def retrieve(
        self, question: str, history: list | None = None, current_concept: str = ""
    ) -> tuple[list[RetrievalResult], float, float]:
        start = time.perf_counter()

        # Use previous results only for genuine follow-ups (same topic)
        if self.is_follow_up(question, history, current_concept) and self._last_results:
            elapsed = (time.perf_counter() - start) * 1000
            logger.info("Follow-up on same topic — reusing last retrieval (%.1fms)", elapsed)
            return self._last_results, 0.85, elapsed

        # New topic or first question — do fresh retrieval
        normalized = self.normalize_query(question)

        cached = self.cache.get(normalized)
        if cached:
            results, confidence, _ = cached
            elapsed = (time.perf_counter() - start) * 1000
            logger.info("Cache hit for normalized query (%.1fms)", elapsed)
            return results, confidence, elapsed

        query_vector = embedding_service.encode_query(normalized)

        client = qdrant_db.get_client()
        raw_results = client.query_points(
            collection_name=settings.COLLECTION_NAME,
            query=query_vector,
            limit=settings.RETRIEVAL_TOP_K,
            with_payload=True,
            score_threshold=settings.RETRIEVAL_MIN_SCORE,
            search_params=models.SearchParams(
                hnsw_ef=settings.HNSW_EF,
                exact=False,
            ),
        ).points

        results = [
            RetrievalResult(
                text=r.payload.get("text", ""),
                source=self._clean_source(r.payload.get("source", "unknown")),
                score=r.score,
            )
            for r in raw_results
        ]

        retrieval_time = (time.perf_counter() - start) * 1000

        if settings.ENABLE_HYBRID_SEARCH and len(results) > 1:
            hybrid_results = self.hybrid_retriever.retrieve(normalized, results)
            if hybrid_results:
                results = hybrid_results

        if settings.ENABLE_RERANKING and len(results) > 1:
            reranked = self.reranker.rerank(normalized, results)
            if reranked:
                results = reranked

        if settings.ENABLE_DIVERSE_RANKING and len(results) > 1:
            results = self._diverse_ranking(results)

        results = self._deduplicate(results)
        final = results[: settings.RERANK_TOP_K]
        for i, r in enumerate(final):
            r.rank = i + 1

        confidence = self._compute_confidence(final)

        if settings.ENABLE_CONTEXT_COMPRESSION and final:
            final = self.context_compressor.compress(normalized, final)

        self.cache.put(normalized, (final, confidence, retrieval_time))
        self._last_results = final

        return final, confidence, retrieval_time

    def build_clean_context(self, results: list[RetrievalResult]) -> str:
        if not results:
            return ""
        parts = []
        for r in results:
            text = r.text.strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    def _clean_source(self, source: str) -> str:
        s = re.sub(r"\.(pdf|jpg|jpeg|png|gif|bmp|txt|mp4|mp3|docx|pptx)", "", source)
        s = re.sub(r"^ocr[\s_]+", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^transcript[\s_]+", "", s, flags=re.IGNORECASE)
        s = re.sub(r"_\d{8}_\d+[^_]*", "", s)
        s = re.sub(r"-20\d{6}_\d+", "", s)
        s = re.sub(r"[_-]\d+$", "", s)
        s = re.sub(r"Meeting Recording\s*\d*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"Recorded[\s\S]*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s{2,}", " ", s)
        s = re.sub(r"[\/\\]", " – ", s)
        s = s.strip().strip("-").strip("–").strip("_").strip()
        s = re.sub(r"\s+", " ", s)
        return s if s else "Lecture Content"

    def _deduplicate(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        seen_sources = set()
        deduped = []
        for r in results:
            if r.source not in seen_sources:
                seen_sources.add(r.source)
                deduped.append(r)
        return deduped

    def _diverse_ranking(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        seen_sources = set()
        diverse = []
        for r in results:
            if r.source not in seen_sources:
                seen_sources.add(r.source)
                diverse.append(r)
        for r in results:
            if r not in diverse:
                diverse.append(r)
        return diverse

    def _compute_confidence(self, results: list[RetrievalResult]) -> float:
        if not results:
            return 0.0
        scores = [r.score for r in results]
        if len(scores) == 1:
            return float(scores[0])
        weights = [0.5, 0.3, 0.2][: len(scores)]
        weighted = sum(s * w for s, w in zip(scores, weights))
        return round(float(weighted), 4)

    def clear_cache(self):
        self.cache.clear()
        self._last_results = None
        logger.info("Retrieval cache cleared")


retrieval_service = RetrievalService()
