import asyncio
import edge_tts
import gradio as gr

from ollama import chat
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# ----------------------------------
# Load Models
# ----------------------------------

print("Loading embedding model...")
embed_model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5"
)

print("Connecting to Qdrant...")
client = QdrantClient(
    path="./qdrant_db"
)

print("Ready!")

# ----------------------------------
# Edge TTS
# ----------------------------------

async def generate_audio(text, speed):

    percent = int((speed - 1.0) * 100)

    if percent >= 0:
        rate = f"+{percent}%"
    else:
        rate = f"{percent}%"

    communicate = edge_tts.Communicate(
        text=text,
        voice="en-IN-PrabhatNeural",
        rate=rate
    )

    await communicate.save("response.mp3")

    return "response.mp3"

# ----------------------------------
# Main RAG Function
# ----------------------------------

def ask_question(question, speed):

    if not question.strip():
        return "Please enter a question.", None

    query_embedding = embed_model.encode(
        question
    ).tolist()

    results = client.query_points(
        collection_name="sql_lectures",
        query=query_embedding,
        limit=3
    ).points

    if not results:
        return (
            "I could not find that information in the lectures.",
            None
        )

    best_score = results[0].score

    print("\nQUESTION:", question)

    for r in results:
        print(
            "Score:",
            round(r.score, 4),
            "|",
            r.payload["source"]
        )

    if best_score < 0.60:
        return (
            "I could not find that information in the lectures.",
            None
        )

    context = "\n\n".join(
        result.payload["text"]
        for result in results
    )

    prompt = f"""
You are a lecture retrieval assistant.

STRICT RULES:

1. Use ONLY the lecture context.
2. Do NOT use outside knowledge.
3. If the answer is not present in the context, say:

I could not find that information in the lectures.

Context:
{context}

Question:
{question}

Answer:
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

    answer = response["message"]["content"].strip()

    # Add sources
    source_text = "\n\nSources:\n"

    for r in results:
        source_text += (
            f"- {r.payload['source']} "
            f"(score={round(r.score,3)})\n"
        )

    final_answer = answer + source_text

    audio_file = asyncio.run(
        generate_audio(answer, speed)
    )

    return final_answer, audio_file
# ----------------------------------
# Gradio UI
# ----------------------------------

demo = gr.Interface(
    fn=ask_question,

    inputs=[
        gr.Textbox(
            lines=2,
            label="Ask SQL Question",
            placeholder="What is SQL?"
        ),

        gr.Slider(
            minimum=0.5,
            maximum=2.0,
            value=1.0,
            step=0.25,
            label="Voice Speed"
        )
    ],

    outputs=[
        gr.Textbox(
            label="Answer"
        ),

        gr.Audio(
            label="Voice Response"
        )
    ],

    title="SQL Lecture Assistant",

    description="""
RAG System

Whisper → BGE Embeddings → Qdrant → Qwen → Edge-TTS
"""
)

demo.launch()