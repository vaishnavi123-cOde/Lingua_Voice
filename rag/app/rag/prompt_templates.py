def get_teacher_prompt(
    question: str,
    context: str,
    history: list | None = None,
    teaching_state: dict | None = None,
) -> str:
    history_block = _build_history_block(history)
    state_block = _build_state_block(teaching_state)
    return f"""You are a SQL teacher for beginners.

{history_block}{state_block}Student: {question}

Facts:
{context}

Explain with an analogy, a real SQL statement like CREATE TABLE, and end with a question.
Teacher:"""


def _build_history_block(history: list | None) -> str:
    if not history:
        return ""
    lines = []
    for m in history[-4:]:
        role = m.get("role", "user").capitalize()
        content = m.get("content", "")
        if len(content) > 150:
            content = content[:150] + "..."
        lines.append(f"{role}: {content}")
    return "Recent conversation:\n" + "\n".join(lines) + "\n\n"


def _build_state_block(state: dict | None) -> str:
    if not state:
        return ""
    concept = (state.get("concept") or "").strip()
    if not concept:
        return ""
    parts = [f"Teaching topic: {concept}"]
    difficulty = state.get("difficulty", "beginner")
    parts.append(f"Level: {difficulty}")
    if state.get("lesson_progress"):
        parts.append("Covered: " + ", ".join(state["lesson_progress"][-3:]))
    if state.get("struggled_concepts"):
        parts.append("Struggled: " + ", ".join(state["struggled_concepts"][-2:]))
    return "Background:\n" + "\n".join(parts) + "\n\n"


def get_rag_prompt(question: str, context: str, history: list | None = None) -> str:
    return get_teacher_prompt(question=question, context=context, history=history)


def get_compression_prompt(question: str, passage: str) -> str:
    return f"""Extract only the parts of the passage below that are relevant to answering the question. Remove irrelevant metadata, UI text, and noise.

Question: {question}

Passage:
{passage}

Relevant excerpt:"""