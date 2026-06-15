import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

import asyncio
import edge_tts

from ollama import chat
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading embedding model...")

embed_model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5"
)

print("Connecting to Qdrant...")

client = QdrantClient(
    path="./qdrant_db"
)

COLLECTION_NAME = "sql_lectures"


# ----------------------------
# Request Models
# ----------------------------

class QuestionRequest(BaseModel):
    question: str


class SpeechRequest(BaseModel):
    text: str


# ----------------------------
# Edge TTS
# ----------------------------

async def generate_audio(text):

    communicate = edge_tts.Communicate(
        text=text,
        voice="en-IN-PrabhatNeural"
    )

    await communicate.save(
        "response.mp3"
    )

    return "response.mp3"


# ----------------------------
# Health
# ----------------------------

@app.get("/")
def home():

    return {
        "message":
        "SQL Lecture Assistant API Running"
    }


@app.get("/health")
def health():

    return {
        "status":
        "healthy"
    }


# ----------------------------
# Ask Endpoint
# ----------------------------

@app.post("/ask")
def ask_question(
    request: QuestionRequest
):

    question = request.question.strip()

    if not question:

        return {
            "answer":
            "Please enter a question."
        }

    query_embedding = embed_model.encode(
        question,
        normalize_embeddings=True
    ).tolist()

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        limit=3
    ).points

    if not results:

        return {
            "answer":
            "I could not find that information in the lectures."
        }

    best_score = results[0].score

    print("\nQuestion:", question)
    print("Best Score:", round(best_score, 4))

    if best_score < 0.60:

        return {
            "answer":
            "I could not find that information in the lectures."
        }

    context = "\n\n".join(
        r.payload["text"]
        for r in results
    )

    prompt = f"""
You are a lecture assistant.

STRICT RULES:

1. Answer ONLY from the provided context.
2. Do NOT use outside knowledge.
3. If the answer is not explicitly present in the context, respond exactly:

I could not find that information in the lectures.

4. Keep answers concise.

Context:
{context}

Question:
{question}
"""

    response = chat(
        model="qwen2.5:0.5b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    answer = response[
        "message"
    ][
        "content"
    ].strip()

    sources = []

    for r in results:

        sources.append(
            {
                "source":
                r.payload["source"],

                "score":
                round(
                    r.score,
                    4
                )
            }
        )

    return {
        "question": question,
        "answer": answer,
        "sources": sources
    }


# ----------------------------
# TTS Endpoint
# ----------------------------

@app.post("/speak")
def speak(
    request: SpeechRequest
):

    text = request.text.strip()

    if not text:

        return {
            "error":
            "No text provided."
        }

    audio_file = asyncio.run(
        generate_audio(text)
    )

    return FileResponse(
        audio_file,
        media_type="audio/mpeg",
        filename="response.mp3"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)