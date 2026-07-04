import json
import logging
import re
import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    AnswerResponse,
    QuestionRequest,
    Source,
    TeachingState,
)
from app.services.llm import llm_service
from app.services.monitoring import metrics_collector
from app.services.retrieval import retrieval_service
from app.rag.prompt_templates import get_teacher_prompt

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ask"])


class TeacherMemory:
    def __init__(self, max_sessions: int = 100):
        self._sessions: dict[str, dict] = {}
        self._max_sessions = max_sessions

    def get_or_create(self, session_id: str | None) -> str:
        if session_id and session_id in self._sessions:
            return session_id
        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = {
            "teaching_state": TeachingState().model_dump(),
            "turn_count": 0,
            "topics_covered": [],
            "mistakes": [],
            "asked_questions": [],
        }
        if len(self._sessions) > self._max_sessions:
            oldest = next(iter(self._sessions))
            del self._sessions[oldest]
        return sid

    def get_state(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if session:
            return session["teaching_state"]
        return TeachingState().model_dump()

    def update_state(self, session_id: str, teaching_state: dict | None):
        session = self._sessions.get(session_id)
        if session and teaching_state:
            old_concept = session["teaching_state"].get("concept", "")
            new_concept = teaching_state.get("concept", "")
            if new_concept and new_concept != old_concept:
                if old_concept and old_concept not in session["topics_covered"]:
                    session["topics_covered"].append(old_concept)
            session["teaching_state"] = teaching_state
            session["turn_count"] += 1

    def record_mistake(self, session_id: str, concept: str):
        session = self._sessions.get(session_id)
        if session and concept and concept not in session["mistakes"]:
            session["mistakes"].append(concept)

    def record_question(self, session_id: str, question: str):
        session = self._sessions.get(session_id)
        if session:
            session["asked_questions"].append(question)
            if len(session["asked_questions"]) > 20:
                session["asked_questions"] = session["asked_questions"][-20:]

    def get_session_summary(self, session_id: str) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {}
        return {
            "turn_count": session.get("turn_count", 0),
            "topics_covered": session.get("topics_covered", []),
            "mistakes": session.get("mistakes", []),
            "last_questions": session.get("asked_questions", [])[-3:],
        }

    def knows_concept(self, session_id: str, concept: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        if concept in session["topics_covered"]:
            return True
        current = session["teaching_state"].get("concept", "")
        return concept.lower() == current.lower()

    def struggled_with(self, session_id: str, concept: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        return concept in session["mistakes"]


teacher_memory = TeacherMemory()

FALLBACK_PROMPTS = {
    "explain": "Does that make sense? Should I go into more detail?",
    "socratic_ask": "What do you think? There is no wrong answer here.",
    "exercise": "Give it a try. Type your answer and I will check it.",
    "check": "Do you understand this? Would you like another example?",
    "encourage": "Ready for the next topic? Or do you want more practice?",
}

SQL_CONCEPTS = [
    "primary key", "foreign key", "unique key", "composite key",
    "select", "where", "from", "join", "inner join", "left join",
    "right join", "full outer join", "cross join", "self join",
    "group by", "having", "order by", "limit", "offset",
    "insert", "update", "delete", "create table", "alter table",
    "drop table", "index", "view", "subquery", "nested query",
    "correlated subquery", "exists", "not exists", "between",
    "like", "is null", "is not null", "distinct",
    "count", "sum", "avg", "min", "max", "aggregate function",
    "union", "intersect", "except", "case", "coalesce", "nullif",
    "constraint", "not null", "default", "check", "references",
    "normalization", "transaction", "commit", "rollback", "savepoint",
    "stored procedure", "function", "trigger", "cursor",
    "grant", "revoke", "deny", "role", "permission",
    "database design", "schema", "table", "column", "data type",
    "varchar", "int", "decimal", "date", "datetime", "boolean",
    "relationship", "cascade", "set null", "no action", "set default",
    "derived table", "cte", "with",
    "window function", "rank", "dense_rank", "row_number", "partition by",
]

# Single-char concepts are too noisy for substring matching — removed: "in"


def _infer_concept(question: str, results: list) -> str:
    q_lower = question.lower().strip("?.! ")
    # Only match concepts directly mentioned in the question
    for concept in SQL_CONCEPTS:
        if concept in q_lower:
            return concept.title()
    # Check if question is asking about a generic SQL topic (not a specific keyword)
    # But report it generically rather than matching noisy substrings
    return ""


def _infer_teacher_action(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ["let's practice", "try this", "fill in", "complete the", "predict", "find the mistake"]):
        return "exercise"
    if any(w in lower for w in ["think about", "imagine", "what if", "let me ask", "here's a question", "can you tell"]):
        return "socratic_ask"
    if any(w in lower for w in ["does that make sense", "do you understand", "are you following", "did that help"]):
        return "check"
    if any(w in lower for w in ["great", "excellent", "well done", "you're getting", "perfect", "good job", "nice work"]):
        return "encourage"
    return "explain"


_QUESTION_PAT = re.compile(
    r"(?:"
    r"(?:Does that make sense|Can you tell me|What do you think|Do you understand|"
    r"Would you like|Shall I|Do you want|Should I|Want me to|How about|"
    r"Maybe try|You could ask|What about|Try asking|Consider asking|"
    r"Why do you think|What would happen|Can you guess|"
    r"Are you ready|Let me ask you|Here's a question|"
    r"Can you explain|What's the difference|Tell me what|"
    r"Which of these|What is the output|What will this query|"
    r"Why Not|What about|How about|What is|What are|"
    r"Can you|Do you|Are you|Is it|Was it|"
    r"Should you|Could you|Did you|Have you)"
    r".*\??)", re.IGNORECASE | re.MULTILINE | re.DOTALL,
)

_LEAKED_SECTION_RE = re.compile(
    r"(?:\n|^)"
    r"(?:LECTURE CONTENT|REFERENCE NOTES|INTERNAL NOTES|FACTUAL CONTENT|Facts to use|Facts about|Facts:|"
    r"RECENT CONVERSATION|Recent conversation|SESSION STATE|Background:)"
    r"(?:\s*:\s*)?[\s\S]*", re.IGNORECASE,
)

_DIALOGUE_RE = re.compile(r"(?:\n|^)(?:STUDENT|TEACHER|Student|Teacher)\s*:.*?(?:\n|$)", re.MULTILINE)

_LEAKED_SOURCE_RE = re.compile(r"\[Source:[^\]]*\]")


def _extract_student_prompt(text: str) -> str | None:
    lines = text.strip().split("\n")
    last_part = "\n".join(lines[-max(1, len(lines) // 3):])
    questions = _QUESTION_PAT.findall(last_part)
    if questions:
        q = questions[-1].strip().lstrip("#*-").strip()
        if len(q) < 15 or q.count(" ") < 3:
            return None
        if _LEAKED_SOURCE_RE.search(q):
            return None
        if re.search(r"[\\/]Users[\\/]|[\\/]AppData[\\/]|INetCache|Content\.Outlook", q, re.IGNORECASE):
            return None
        return q
    for line in reversed(lines):
        stripped = line.strip().lstrip("#*-").strip()
        if stripped.endswith("?") and len(stripped) > 15 and stripped.count(" ") > 3:
            if _LEAKED_SOURCE_RE.search(stripped):
                continue
            if re.search(r"[\\/]Users[\\/]|[\\/]AppData[\\/]|INetCache|Content\.Outlook", stripped, re.IGNORECASE):
                continue
            return stripped
    return None


def _remove_student_prompt(text: str, prompt: str) -> str:
    idx = text.rfind(prompt)
    if idx > len(text) * 0.4:
        before = text[:idx].rstrip("\n").rstrip()
        return before
    return text


_TRAILING_LABEL_RE = re.compile(
    r"(?:\n|^)"
    r"(?:Follow.up\s*Question|Question|Answer|Response|Teacher|"
    r"Your\s*Turn|Student\s*Prompt|Next\s*Question|Check\s*Understanding)"
    r"(?:\s*:?\s*)?$",
    re.IGNORECASE,
)


def _clean_trailing_labels(text: str) -> str:
    text = _TRAILING_LABEL_RE.sub("", text)
    return text.strip()


_COPIED_INSTRUCTION_RE = re.compile(
    r"(?:\n|^)"
    r"(?:Answer the question|One analogy|One real SQL example|"
    r"ONE real SQL example|Your answer must include|End with one|"
    r"Never copy|Write your answer|Do not use labels|"
    r"Just explain|After the SQL|Start with a keyword|"
    r"Must start with|Structure:|RULES:|"
    r"Question\s*:|Answer\s*:|"
    r"First sentence|Middle sentence|Last sentence|"
    r"Now let.s ask|Welcome to|"
    r"Facts\s*:|Student\s*:|"
    r"Answer with|Write 3-4|Include an analogy|In this example|"
    r"In this analogy|SQL Statement|New Question|Here.s a simple|"
    r"Certainly|Let.s break|Let.s use the|"
    r"Facts about|Great! Here.s|Analogy \(Real|"
    r"Questio\b)"
    r"(?:\n|:)?",
    re.IGNORECASE,
)


def _strip_copied_instructions(text: str) -> str:
    text = _COPIED_INSTRUCTION_RE.sub("", text)
    return text.strip()


_DISTRACTING_FACTS_RE = re.compile(
    r"(?:"
    r"IBM|SEQUEL|platform[.]dependent|"
    r"non[.]procedural|case[.]insensitive|"
    r"developed\s+by\s+Microsoft|"
    r"Microsoft\s+Windows\s+operating\s+system|"
    r"implemented\s+from\s+the\s+specification|"
    r"ORDBMS|object[.]relational"
    r")",
    re.IGNORECASE,
)


def _filter_factual_content(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        if _DISTRACTING_FACTS_RE.search(line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _generate_fallback_prompt(action: str, concept: str) -> str:
    base = FALLBACK_PROMPTS.get(action, "Does that make sense? Should I go into more detail?")
    if concept:
        return f"Now that you understand {concept}, would you like to try a practice question?"
    return base


def _strip_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\*\*?[A-Z][a-z]+.*?\*\*?:", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|", ", ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()


def _clean_leaked_content(text: str) -> str:
    text = _LEAKED_SECTION_RE.sub("", text)
    text = _LEAKED_SOURCE_RE.sub("", text)
    text = _DIALOGUE_RE.sub("", text)
    # Filter IBM/SEQUEL from answer itself
    text = re.sub(
        r"\s*,?\s*(?:which is|an|a|the)\s+IBM\s+(?:product|language|creation)",
        "", text, flags=re.IGNORECASE
    )
    text = re.sub(r"IBM[^.]*\.\s*", "", text)
    text = re.sub(r"C:[/\\]Users[/\\][^\\/\n]+[/\\][^\n]{0,200}", "", text)
    text = re.sub(r"C\s+[/\\]Users[/\\][^\\/\n]+[/\\][^\n]{0,200}", "", text)
    text = re.sub(r"[A-Z]:[/\\][^\n]{0,200}", "", text)
    text = re.sub(r"INetCache[^\n]*", "", text)
    text = re.sub(r"Content\.Outlook[^\n]*", "", text)
    text = re.sub(r"Meeting Recording[^\n]*", "", text)
    text = re.sub(r"Recorded by[^\n]*", "", text)
    text = re.sub(r"Microsoft\s*Teams[^\n]*", "", text)
    text = re.sub(r"AppData[^\n]*", "", text)
    text = re.sub(r"Chat[^\n]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Partly\s*sunny[^\n]*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _build_teaching_state(
    current_state: dict,
    inferred_concept: str,
    teacher_action: str,
    session_id: str,
) -> dict:
    merged = {**current_state}
    if inferred_concept:
        merged["concept"] = inferred_concept
    if teacher_action != "encourage":
        merged["pedagogical_goal"] = (
            f"Teach {inferred_concept or 'SQL'} to {current_state.get('difficulty', 'beginner')} level"
        )
    session_info = teacher_memory.get_session_summary(session_id)
    if session_info.get("mistakes"):
        merged["struggled_concepts"] = session_info["mistakes"]
    if session_info.get("topics_covered"):
        merged["lesson_progress"] = session_info["topics_covered"]
    return merged


@router.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    start = time.perf_counter()
    question = request.question.strip()
    history = request.history or []

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    session_id = teacher_memory.get_or_create(request.session_id)
    current_state = request.teaching_state or teacher_memory.get_state(session_id)
    teacher_memory.record_question(session_id, question)

    try:
        current_concept = current_state.get("concept", "")
        results, confidence, retrieval_time = retrieval_service.retrieve(
            question, history=history, current_concept=current_concept
        )

        if not results:
            return AnswerResponse(
                question=question,
                answer="I could not find that topic in the lecture materials. Would you like me to explain general SQL concepts instead?",
                sources=[],
                confidence=0.0,
                retrieval_time_ms=retrieval_time,
                llm_time_ms=0.0,
                total_time_ms=(time.perf_counter() - start) * 1000,
                teacher_action="explain",
                teaching_state=TeachingState(**current_state),
                student_prompt="Would you like me to explain basic SQL concepts instead?",
                student_prompt_type="question",
                session_id=session_id,
            )

        inferred_concept = _infer_concept(question, results)
        if current_concept and inferred_concept and inferred_concept.lower() != current_concept.lower():
            logger.info("Topic change: %s -> %s — resetting teaching state", current_concept, inferred_concept)
            current_state = TeachingState(concept=inferred_concept, difficulty=current_state.get("difficulty", "beginner")).model_dump()
        elif current_concept and not inferred_concept:
            # No explicit concept in question — use is_follow_up to decide
            if not retrieval_service.is_follow_up(question, history, current_concept):
                logger.info("Likely topic change — resetting concept (was: %s)", current_concept)
                current_state["concept"] = ""
        elif not current_concept and inferred_concept:
            current_state["concept"] = inferred_concept

        context = retrieval_service.build_clean_context(results)
        context = _filter_factual_content(context)

        raw_answer, llm_time = llm_service.generate_teacher(
            question=question,
            context=context,
            history=history,
            teaching_state=current_state,
        )

        clean_answer = raw_answer.strip()
        clean_answer = clean_answer.replace("\ufffd", "'")
        clean_answer = _clean_leaked_content(clean_answer)
        clean_answer = _strip_copied_instructions(clean_answer)
        clean_answer = _strip_markdown(clean_answer)
        clean_answer = re.sub(r"^[^a-zA-Z0-9]+", "", clean_answer)
        clean_answer = re.sub(r"\n{3,}", "\n\n", clean_answer).strip()

        teacher_action = _infer_teacher_action(raw_answer)
        student_prompt = _extract_student_prompt(raw_answer)

        if student_prompt:
            clean_answer = _remove_student_prompt(clean_answer, student_prompt)
        clean_answer = _clean_trailing_labels(clean_answer)

        if not student_prompt:
            student_prompt = _generate_fallback_prompt(teacher_action, inferred_concept)

        merged_state = _build_teaching_state(
            current_state, inferred_concept, teacher_action, session_id
        )

        teacher_memory.update_state(session_id, merged_state)

        speech_text = _strip_markdown(clean_answer)

        sources = [
            Source(source=r.source, score=r.score, rank=r.rank)
            for r in results
        ]

        total_time = (time.perf_counter() - start) * 1000

        metrics_collector.record_response(
            question=question,
            answer=clean_answer,
            confidence=confidence,
            retrieval_time_ms=retrieval_time,
            llm_time_ms=llm_time,
            total_time_ms=total_time,
        )

        logger.info(
            "Teacher | Action: %s | Concept: %s | Turn: %d | Q: %.40s | Total: %.0fms | LLM: %.0fms",
            teacher_action,
            merged_state.get("concept", "?"),
            teacher_memory.get_session_summary(session_id).get("turn_count", 0),
            question,
            total_time,
            llm_time,
        )

        return AnswerResponse(
            question=question,
            answer=clean_answer,
            sources=sources,
            confidence=confidence,
            retrieval_time_ms=retrieval_time,
            llm_time_ms=llm_time,
            total_time_ms=total_time,
            teacher_action=teacher_action,
            teaching_state=TeachingState(**merged_state),
            student_prompt=student_prompt,
            student_prompt_type="question",
            session_id=session_id,
        )

    except Exception as e:
        logger.error("Failed to process question: %s", e, exc_info=True)
        metrics_collector.record_error("ask_error", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask/stream")
def ask_question_stream(request: QuestionRequest):
    question = request.question.strip()
    history = request.history or []

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    session_id = teacher_memory.get_or_create(request.session_id)
    current_state = request.teaching_state or teacher_memory.get_state(session_id)

    try:
        current_concept = current_state.get("concept", "")
        results, confidence, retrieval_time = retrieval_service.retrieve(
            question, history=history, current_concept=current_concept
        )

        if not results:
            return StreamingResponse(
                iter(["I could not find that topic in the lecture materials. Would you like a general SQL explanation instead?"]),
                media_type="text/plain",
            )

        inferred_concept = _infer_concept(question, results)
        if current_concept and inferred_concept and inferred_concept.lower() != current_concept.lower():
            logger.info("Topic change: %s -> %s — resetting teaching state", current_concept, inferred_concept)
            current_state = TeachingState(concept=inferred_concept, difficulty=current_state.get("difficulty", "beginner")).model_dump()
        elif current_concept and not inferred_concept:
            if not retrieval_service.is_follow_up(question, history, current_concept):
                logger.info("Likely topic change — resetting concept (was: %s)", current_concept)
                current_state["concept"] = ""
        elif not current_concept and inferred_concept:
            current_state["concept"] = inferred_concept

        context = retrieval_service.build_clean_context(results)
        context = _filter_factual_content(context)

        sources_data = [
            {"source": r.source, "score": r.score, "rank": r.rank}
            for r in results
        ]
        stream_start = time.perf_counter()

        async def generate():
            answer_chunks = []
            async for chunk in llm_service.generate_teacher_stream(
                question=question,
                context=context,
                history=history,
                teaching_state=current_state,
            ):
                answer_chunks.append(chunk)
                clean_chunk = _strip_markdown(chunk)
                yield clean_chunk
            answer = "".join(answer_chunks)

            full_clean = answer.strip()
            full_clean = _clean_leaked_content(full_clean)
            full_clean = _strip_copied_instructions(full_clean)
            full_clean = _strip_markdown(full_clean)
            full_clean = re.sub(r"\n{3,}", "\n\n", full_clean).strip()

            teacher_action = _infer_teacher_action(answer)
            student_prompt = _extract_student_prompt(answer)

            if student_prompt:
                full_clean = _remove_student_prompt(full_clean, student_prompt)
            full_clean = _clean_trailing_labels(full_clean)

            if not student_prompt:
                student_prompt = _generate_fallback_prompt(teacher_action, inferred_concept)

            merged_state = _build_teaching_state(
                current_state, inferred_concept, teacher_action, session_id
            )
            teacher_memory.update_state(session_id, merged_state)

            total_time = (time.perf_counter() - stream_start) * 1000
            metrics_collector.record_response(
                question=question,
                answer=full_clean,
                confidence=confidence,
                retrieval_time_ms=retrieval_time,
                llm_time_ms=0.0,
                total_time_ms=total_time,
            )

            meta = {
                "sources": sources_data,
                "teacher_action": teacher_action,
                "teaching_state": merged_state,
                "student_prompt": student_prompt,
                "student_prompt_type": "question",
                "session_id": session_id,
            }
            yield f"\n\n__META__:{json.dumps(meta)}"

        return StreamingResponse(
            generate(),
            media_type="text/plain",
        )

    except Exception as e:
        logger.error("Failed to process streaming question: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
