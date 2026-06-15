import os
from pathlib import Path


class Settings:
    APP_NAME: str = "SQL Lecture Assistant"
    VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    QDRANT_PATH: str = os.getenv("QDRANT_PATH", "./qdrant_db")
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    COLLECTION_NAME: str = "sql_lectures"

    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "BAAI/bge-large-en-v1.5")
    EMBED_DIM: int = 1024
    EMBED_NORMALIZE: bool = True

    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    OLLAMA_TIMEOUT: int = 60

    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    RETRIEVAL_MIN_SCORE: float = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.60"))
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "3"))
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

    TTS_VOICE: str = os.getenv("TTS_VOICE", "en-IN-PrabhatNeural")
    TTS_SPEED: float = float(os.getenv("TTS_SPEED", "1.0"))
    TTS_OUTPUT_DIR: str = os.getenv("TTS_OUTPUT_DIR", "./audio_cache")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")

    MAX_CONTEXT_LENGTH: int = 2000
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000")

    HYBRID_ALPHA: float = float(os.getenv("HYBRID_ALPHA", "0.7"))
    BM25_K1: float = 1.5
    BM25_B: float = 0.75

    ENABLE_HYBRID_SEARCH: bool = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
    ENABLE_RERANKING: bool = os.getenv("ENABLE_RERANKING", "true").lower() == "true"
    ENABLE_CONTEXT_COMPRESSION: bool = os.getenv("ENABLE_CONTEXT_COMPRESSION", "true").lower() == "true"

    MONITORING_ENABLED: bool = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    METRICS_FILE: str = os.getenv("METRICS_FILE", "logs/metrics.jsonl")


settings = Settings()
