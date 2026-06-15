def get_rag_prompt(question: str, context: str) -> str:
    return f"""You are a SQL lecture assistant for a training course.

STRICT RULES:
1. Answer ONLY from the provided lecture context below.
2. Do NOT use any outside knowledge or training data.
3. If the answer is not explicitly present in the context, respond exactly:
   "I could not find that information in the lectures."
4. Keep answers concise and educational.
5. When relevant, include specific SQL examples from the context.
6. Cite the source filename when referencing specific content.

Context:
{context}

Question:
{question}

Answer:"""


def get_compression_prompt(question: str, passage: str) -> str:
    return f"""Extract only the parts of the passage below that are relevant to answering the question. Remove irrelevant metadata, UI text, and noise.

Question: {question}

Passage:
{passage}

Relevant excerpt:"""


NOISE_PATTERNS = [
    "Microsoft Teams",
    "Recorded by",
    "Organized by",
    "Gaurav Mehta",
    "Ask Copilot",
    "Chat",
    "Type a message",
    "ENG",
    "IN",
    "Partly sunny",
    "Sunny",
    "High UV",
    "Very high UV",
    "C/Users/Gaurav/",
    "AppData/Local/Microsoft/Windows/INetCache/",
    "Content.Outlook",
    "SQL DAY 1pdf",
    "@File",
    "OFile",
    "Breaking news",
    "Select Repository",
    "Ready",
    "No issues found",
    "Command Prompt",
    "Microsoft Windows [Version",
    "All rights reserved",
    "Try the new Outlook",
    "Object Explorer",
    "TABS",
    "CRLF",
    "UTF-8",
    "Connected.",
    "(local)",
]
