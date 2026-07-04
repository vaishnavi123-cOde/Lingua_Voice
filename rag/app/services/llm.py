import logging
import time

from ollama import Client as OllamaClient

from app.config.settings import settings
from app.rag.prompt_templates import get_rag_prompt, get_teacher_prompt

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
        history: list | None = None,
    ) -> tuple[str, float]:
        start = time.perf_counter()
        prompt = get_rag_prompt(question=question, context=context, history=history)

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "num_ctx": settings.LLM_NUM_CTX,
                    "num_predict": settings.LLM_NUM_PREDICT,
                    "temperature": settings.LLM_TEMPERATURE,
                    "seed": 42,
                },
                keep_alive=settings.LLM_KEEP_ALIVE,
            )
            answer = response["message"]["content"].strip()
        except Exception as e:
            logger.error("LLM generation failed: %s", e, exc_info=True)
            raise
        elapsed = (time.perf_counter() - start) * 1000
        return answer, elapsed

    def generate_stream(
        self,
        question: str,
        context: str,
        history: list | None = None,
    ):
        prompt = get_rag_prompt(question=question, context=context, history=history)

        try:
            stream = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "num_ctx": settings.LLM_NUM_CTX,
                    "num_predict": settings.LLM_NUM_PREDICT,
                    "temperature": settings.LLM_TEMPERATURE,
                    "seed": 42,
                },
                keep_alive=settings.LLM_KEEP_ALIVE,
                stream=True,
            )
            for chunk in stream:
                yield chunk["message"]["content"]
        except Exception as e:
            logger.error("LLM streaming failed: %s", e, exc_info=True)
            raise


    def generate_teacher(
        self,
        question: str,
        context: str,
        history: list | None = None,
        teaching_state: dict | None = None,
    ) -> tuple[str, float]:
        start = time.perf_counter()
        prompt = get_teacher_prompt(
            question=question,
            context=context,
            history=history,
            teaching_state=teaching_state,
        )

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "num_ctx": settings.LLM_NUM_CTX,
                    "num_predict": settings.LLM_NUM_PREDICT,
                    "temperature": settings.LLM_TEACHER_TEMPERATURE,
                    "seed": 42,
                },
                keep_alive=settings.LLM_KEEP_ALIVE,
            )
            answer = response["message"]["content"].strip()
        except Exception as e:
            logger.error("Teacher LLM generation failed: %s", e, exc_info=True)
            raise
        elapsed = (time.perf_counter() - start) * 1000
        return answer, elapsed

    def generate_teacher_stream(
        self,
        question: str,
        context: str,
        history: list | None = None,
        teaching_state: dict | None = None,
    ):
        prompt = get_teacher_prompt(
            question=question,
            context=context,
            history=history,
            teaching_state=teaching_state,
        )

        try:
            stream = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "num_ctx": settings.LLM_NUM_CTX,
                    "num_predict": settings.LLM_NUM_PREDICT,
                    "temperature": settings.LLM_TEACHER_TEMPERATURE,
                    "seed": 42,
                },
                keep_alive=settings.LLM_KEEP_ALIVE,
                stream=True,
            )
            for chunk in stream:
                yield chunk["message"]["content"]
        except Exception as e:
            logger.error("Teacher LLM streaming failed: %s", e, exc_info=True)
            raise


llm_service = LLMService()
