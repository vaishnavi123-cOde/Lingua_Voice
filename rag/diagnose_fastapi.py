"""
diagnose_fastapi.py - FastAPI RAG Backend Diagnostic Script

Checks:
1. Python version and package versions
2. Import chain (FastAPI app, routes, models)
3. Qdrant local database connection
4. Ollama availability and model list
5. SentenceTransformer embedding model loading
6. Edge-TTS voice synthesis
7. All registered routes
8. Environment configuration

Usage:
    python diagnose_fastapi.py
"""

import os
import sys
import json
from pathlib import Path

os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
INFO = "[INFO]"


def print_header(title):
    print(f"\n{'=' * 65}")
    print(f"  {title}")
    print(f"{'=' * 65}")


def check(label, ok, detail=""):
    icon = PASS if ok else FAIL
    print(f"  {icon} {label}")
    if detail:
        for line in detail.split("\n"):
            print(f"         {line}")


def step_1_python():
    print_header("Step 1: Python Environment")
    check("Python version", sys.version_info >= (3, 10),
          f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    check("Platform", True, sys.platform)
    cwd = Path.cwd()
    check("Working directory exists", cwd.exists(), str(cwd))
    check("app/ package exists", (cwd / "app").is_dir())
    check("qdrant_db/ exists", (cwd / "qdrant_db").is_dir())
    check(".env exists", (cwd / ".env").is_file())


def step_2_imports():
    print_header("Step 2: Import Chain")
    steps = [
        ("settings", "from app.config.settings import settings"),
        ("qdrant_db", "from app.database.qdrant import qdrant_db"),
        ("schemas", "from app.models.schemas import QuestionRequest, SpeechRequest, HealthResponse, AnswerResponse"),
        ("embedding_service", "from app.services.embedding import embedding_service"),
        ("retrieval_service", "from app.services.retrieval import retrieval_service"),
        ("llm_service", "from app.services.llm import llm_service"),
        ("tts_service", "from app.services.tts import tts_service"),
        ("hybrid_retriever", "from app.rag.hybrid_retriever import HybridRetriever"),
        ("reranker", "from app.rag.reranker import Reranker"),
        ("context_compressor", "from app.rag.context_compressor import ContextCompressor"),
        ("health router", "from app.routers.health import router as health_router"),
        ("ask router", "from app.routers.ask import router as ask_router"),
        ("speak router", "from app.routers.speak import router as speak_router"),
        ("FastAPI app", "from app.main import app"),
    ]
    for label, imp in steps:
        try:
            exec(imp)
            check(f"import {label}", True)
        except Exception as e:
            check(f"import {label}", False, str(e))


def step_3_routes():
    print_header("Step 3: Registered Routes")
    try:
        from app.main import app
        routes = [(r.path, list(r.methods)[0] if r.methods else "ANY") for r in app.routes if hasattr(r, "methods")]
        required = {"/": "GET", "/health": "GET", "/ask": "POST", "/speak": "POST"}
        for path, method in required:
            found = any(p == path and m == method for p, m in routes)
            check(f"{method:5} {path}", found)
        print(f"\n  {INFO} All registered routes:")
        for path, method in sorted(routes):
            print(f"         {method:5} {path}")
    except Exception as e:
        check("list routes", False, str(e))


def step_4_qdrant():
    print_header("Step 4: Qdrant Local Database")
    qdrant_path = Path("./qdrant_db")
    meta_file = qdrant_path / "meta.json"
    storage_file = qdrant_path / "collection" / "sql_lectures" / "storage.sqlite"

    check("qdrant_db/ directory exists", qdrant_path.is_dir())
    check("meta.json exists", meta_file.is_file())
    if meta_file.exists():
        with open(meta_file) as f:
            meta = json.load(f)
        cols = list(meta.get("collections", {}).keys())
        check("collections in meta.json", bool(cols), f"{cols}")
    check("storage.sqlite exists", storage_file.is_file(), f"{storage_file.stat().st_size / (1024*1024):.1f} MB")

    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(path=str(qdrant_path))
        col_info = client.get_collection("sql_lectures")
        check("Qdrant client connect", True,
              f"Points: {col_info.points_count}, "
              f"Dim: {col_info.config.params.vectors.size}, "
              f"Distance: {col_info.config.params.vectors.distance}")
        client.close()
    except Exception as e:
        check("Qdrant client connect", False, str(e))


def step_5_ollama():
    print_header("Step 5: Ollama LLM Backend")
    try:
        from ollama import Client
        c = Client(host="http://localhost:11434")
        models = c.list()
        model_names = [m.model for m in models.models]
        check("Ollama server reachable", True, f"Host: http://localhost:11434")

        from app.config.settings import settings
        configured_model = settings.OLLAMA_MODEL
        check(f"Configured model '{configured_model}' available",
              configured_model in model_names,
              f"Available: {model_names}")
        if configured_model not in model_names:
            check(f"Fallback: use '{model_names[0]}'",
                  True,
                  f"Run: ollama pull {configured_model} to download configured model")
    except Exception as e:
        check("Ollama connection", False, str(e))


def step_6_embeddings():
    print_header("Step 6: SentenceTransformer Embeddings")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("BAAI/bge-large-en-v1.5")
        test_vec = model.encode("Hello world", normalize_embeddings=True)
        check("Embedding model loaded", True,
              f"Dim: {len(test_vec)}, Max SEQ: {model.max_seq_length}")
    except Exception as e:
        check("Embedding model", False, str(e))


def step_7_env_config():
    print_header("Step 7: Environment Configuration")
    try:
        from app.config.settings import settings
        items = [
            ("APP_NAME", settings.APP_NAME),
            ("VERSION", settings.VERSION),
            ("QDRANT_PATH", settings.QDRANT_PATH),
            ("COLLECTION_NAME", settings.COLLECTION_NAME),
            ("EMBED_MODEL", settings.EMBED_MODEL),
            ("OLLAMA_HOST", settings.OLLAMA_HOST),
            ("OLLAMA_MODEL", settings.OLLAMA_MODEL),
            ("CORS_ORIGINS", settings.CORS_ORIGINS),
            ("TTS_VOICE", settings.TTS_VOICE),
            ("RETRIEVAL_TOP_K", settings.RETRIEVAL_TOP_K),
            ("RETRIEVAL_MIN_SCORE", settings.RETRIEVAL_MIN_SCORE),
        ]
        for label, val in items:
            check(f"{label}", True, str(val))
    except Exception as e:
        check("settings", False, str(e))


def step_8_tts():
    print_header("Step 8: Edge-TTS Voice Synthesis")
    try:
        import edge_tts
        voices = ["en-IN-PrabhatNeural", "en-US-JennyNeural"]
        for v in voices:
            try:
                communicate = edge_tts.Communicate("test", voice=v)
                check(f"TTS voice '{v}'", True)
            except Exception:
                check(f"TTS voice '{v}'", False, "Voice may not be available")
    except Exception as e:
        check("edge-tts import", False, str(e))


def step_9_data_files():
    print_header("Step 9: Data Files (chunks + embeddings)")
    files = [
        ("chunks.pkl", "Text chunks for retrieval"),
        ("embeddings.npy", "Transcript vector embeddings"),
        ("embeddings_ocr.npy", "OCR slide vector embeddings"),
    ]
    for name, desc in files:
        path = Path(name)
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            check(f"{name} ({desc})", True, f"{size_mb:.2f} MB")
        else:
            check(f"{name} ({desc})", False)


def step_10_endpoints():
    print_header("Step 10: Live Endpoint Tests")
    port = 8000
    import urllib.request
    import json as _json

    endpoints = [
        ("GET", f"http://127.0.0.1:{port}/", "Root endpoint"),
        ("GET", f"http://127.0.0.1:{port}/health", "Health check"),
        ("POST", f"http://127.0.0.1:{port}/ask", "Ask endpoint"),
        ("POST", f"http://127.0.0.1:{port}/speak", "Speak endpoint"),
    ]
    for method, url, desc in endpoints:
        try:
            req = urllib.request.Request(url, method=method)
            if method == "POST":
                req.data = b'{"question":"test"}' if "ask" in url else b'{"text":"test"}'
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode()
                check(f"{method} {desc}", resp.status == 200,
                      f"HTTP {resp.status}, body: {body[:100]}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            check(f"{method} {desc}", e.code in (200, 400, 422),
                  f"HTTP {e.code}, body: {body[:100]}")
        except Exception as e:
            check(f"{method} {desc}", False, str(e))

    docs_url = f"http://127.0.0.1:{port}/docs"
    try:
        with urllib.request.urlopen(docs_url, timeout=5) as resp:
            check("Swagger UI /docs", resp.status == 200, docs_url)
    except Exception as e:
        check("Swagger UI /docs", False, f"{docs_url} - {e}")


if __name__ == "__main__":
    print(f"\n{'#' * 65}")
    print(f"  FastAPI RAG Backend Diagnostic Tool")
    print(f"  Working dir: {Path.cwd()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"{'#' * 65}")

    step_1_python()
    step_2_imports()
    step_3_routes()
    step_4_qdrant()
    step_5_ollama()
    step_6_embeddings()
    step_7_env_config()
    step_8_tts()
    step_9_data_files()

    print(f"\n{'=' * 65}")
    print(f"  Starting live endpoint tests (port 8000)...")
    print(f"  Server must be running! If not, ctrl+c and start server first.")
    print(f"{'=' * 65}")
    step_10_endpoints()

    print(f"\n{'#' * 65}")
    print(f"  Diagnostic Complete")
    print(f"{'#' * 65}")
    print(f"\n  Recommended start command:")
    print(f"  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print(f"\n  OpenAPI docs:")
    print(f"  http://127.0.0.1:8000/docs")
    print()
