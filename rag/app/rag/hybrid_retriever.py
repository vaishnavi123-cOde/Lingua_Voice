import logging
import math
import re
from collections import Counter

from app.config.settings import settings
from app.models.retrieval_result import RetrievalResult

logger = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(self):
        self.alpha = settings.HYBRID_ALPHA
        self.k1 = settings.BM25_K1
        self.b = settings.BM25_B

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def _compute_bm25_scores(
        self,
        query: str,
        documents: list[RetrievalResult],
    ) -> list[float]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [0.0] * len(documents)

        doc_tokens_list = [self._tokenize(d.text) for d in documents]
        avg_doc_len = sum(len(t) for t in doc_tokens_list) / max(len(documents), 1)

        doc_freq = Counter()
        for tokens in doc_tokens_list:
            for token in set(tokens):
                doc_freq[token] += 1

        N = len(documents)
        scores = []
        for doc_idx, tokens in enumerate(doc_tokens_list):
            doc_len = len(tokens)
            score = 0.0
            for token in query_tokens:
                if token not in doc_freq:
                    continue
                idf = math.log((N - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5) + 1.0)
                tf = tokens.count(token)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / avg_doc_len)
                score += idf * numerator / denominator
            scores.append(score)
        return scores

    def retrieve(
        self,
        question: str,
        vector_results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        if not vector_results:
            return vector_results

        try:
            bm25_scores = self._compute_bm25_scores(question, vector_results)

            max_vec = max(r.score for r in vector_results) or 1.0
            max_bm25 = max(bm25_scores) or 1.0

            for i, r in enumerate(vector_results):
                norm_vec = r.score / max_vec
                norm_bm25 = bm25_scores[i] / max_bm25
                hybrid = self.alpha * norm_vec + (1 - self.alpha) * norm_bm25
                r.score = round(hybrid, 4)

            vector_results.sort(key=lambda x: x.score, reverse=True)
            logger.debug("Hybrid retrieval applied. Alpha=%.2f", self.alpha)
        except Exception as e:
            logger.error("Hybrid retrieval failed: %s", e)

        return vector_results
