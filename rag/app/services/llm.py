import logging
import time

from ollama import Client as OllamaClient

from app.config.settings import settings
from app.rag.prompt_templates import get_rag_prompt

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = OllamaClient(host=settings.OLLAMA_HOST)
        self.model = settings.OLLAMA_MODEL
        self._verify_connection()

    def _verify_connection(self):
        try:
            self.client.list()
            logger.info("Connected to Ollama at %s", settings.OLLAMA_HOST)
        except Exception as e:
            logger.warning("Ollama not reachable at %s: %s", settings.OLLAMA_HOST, e)

    def generate(
        self,
        question: str,
        context: str,
        sources: list | None = None,
    ) -> tuple[str, float]:
        start = time.perf_counter()
        prompt = get_rag_prompt(question=question, context=context)

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": settings.MAX_CONTEXT_LENGTH},
            )
            answer = response["message"]["content"].strip()
        except Exception as e:
            logger.error("LLM generation failed: %s", e)
            answer = "I could not generate an answer due to a system error."
        elapsed = (time.perf_counter() - start) * 1000
        return answer, elapsed

    def generate_stream(
        self,
        question: str,
        context: str,
    ):
        prompt = get_rag_prompt(question=question, context=context)

        try:
            stream = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": settings.MAX_CONTEXT_LENGTH},
                stream=True,
            )
            for chunk in stream:
                yield chunk["message"]["content"]
        except Exception as e:
            logger.error("LLM streaming failed: %s", e)
            yield "I could not generate an answer due to a system error."


llm_service = LLMService()
