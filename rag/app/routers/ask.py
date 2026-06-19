import logging
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import AnswerResponse, QuestionRequest, Source
from app.services.llm import llm_service
from app.services.monitoring import metrics_collector
from app.services.retrieval import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    start = time.perf_counter()
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        results, confidence, retrieval_time = retrieval_service.retrieve(question)

        if not results:
            metrics_collector.record_response(
                question=question,
                answer="No relevant information found.",
                confidence=0.0,
                retrieval_time_ms=retrieval_time,
                llm_time_ms=0.0,
                total_time_ms=(time.perf_counter() - start) * 1000,
            )
            return AnswerResponse(
                question=question,
                answer="I could not find that information in the lectures.",
                sources=[],
                confidence=0.0,
                retrieval_time_ms=retrieval_time,
                llm_time_ms=0.0,
                total_time_ms=(time.perf_counter() - start) * 1000,
            )

        context_parts = [
            f"[Source: {r.source}]\n{r.text}" for r in results
        ]
        context = "\n\n---\n\n".join(context_parts)

        answer, llm_time = llm_service.generate(question, context)

        sources = [
            Source(
                source=r.source,
                score=r.score,
                rank=r.rank,
            )
            for r in results
        ]

        total_time = (time.perf_counter() - start) * 1000

        metrics_collector.record_response(
            question=question,
            answer=answer,
            confidence=confidence,
            retrieval_time_ms=retrieval_time,
            llm_time_ms=llm_time,
            total_time_ms=total_time,
        )

        metrics_collector.record_retrieval(
            question=question,
            top_scores=[r.score for r in results],
            retrieval_time_ms=retrieval_time,
            num_results=len(results),
        )

        logger.info(
            "Question: %.50s | Confidence: %.4f | Retrieval: %.0fms | LLM: %.0fms | Total: %.0fms",
            question,
            confidence,
            retrieval_time,
            llm_time,
            total_time,
        )

        return AnswerResponse(
            question=question,
            answer=answer,
            sources=sources,
            confidence=confidence,
            retrieval_time_ms=retrieval_time,
            llm_time_ms=llm_time,
            total_time_ms=total_time,
        )

    except Exception as e:
        logger.error("Failed to process question: %s", e, exc_info=True)
        metrics_collector.record_error("ask_error", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/stream")
def ask_question_stream(request: QuestionRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        results, confidence, retrieval_time = retrieval_service.retrieve(question)

        if not results:
            return StreamingResponse(
                iter(["I could not find that information in the lectures."]),
                media_type="text/plain",
            )

        context_parts = [
            f"[Source: {r.source}]\n{r.text}" for r in results
        ]
        context = "\n\n---\n\n".join(context_parts)

        sources = [
            {
                "source": r.source,
                "score": r.score,
                "rank": r.rank,
            }
            for r in results
        ]
        stream_start = time.perf_counter()

        async def generate():
            answer_chunks = []
            async for chunk in llm_service.generate_stream(question, context):
                answer_chunks.append(chunk)
                yield chunk
            answer = "".join(answer_chunks)
            total_time = (time.perf_counter() - stream_start) * 1000
            metrics_collector.record_response(
                question=question,
                answer=answer,
                confidence=confidence,
                retrieval_time_ms=retrieval_time,
                llm_time_ms=0.0,
                total_time_ms=total_time,
            )
            yield f"\n\n__SOURCES__:{sources}"

        return StreamingResponse(
            generate(),
            media_type="text/plain",
        )

    except Exception as e:
        logger.error("Failed to process streaming question: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
