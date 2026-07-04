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
    EMBED_FP16: bool = os.getenv("EMBED_FP16", "true").lower() == "true"
    EMBED_BATCH_SIZE: int = int(os.getenv("EMBED_BATCH_SIZE", "32"))
    EMBED_CACHE_SIZE: int = int(os.getenv("EMBED_CACHE_SIZE", "256"))

    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    OLLAMA_TIMEOUT: int = 60

    LLM_NUM_CTX: int = int(os.getenv("LLM_NUM_CTX", "2048"))
    LLM_NUM_PREDICT: int = int(os.getenv("LLM_NUM_PREDICT", "1024"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_TEACHER_TEMPERATURE: float = float(os.getenv("LLM_TEACHER_TEMPERATURE", "0.7"))
    LLM_KEEP_ALIVE: str = os.getenv("LLM_KEEP_ALIVE", "5m")

    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "4"))
    RETRIEVAL_MIN_SCORE: float = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.60"))
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "3"))
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
    HNSW_EF: int = int(os.getenv("HNSW_EF", "64"))
    ENABLE_DIVERSE_RANKING: bool = os.getenv("ENABLE_DIVERSE_RANKING", "true").lower() == "true"
    RETRIEVAL_CACHE_SIZE: int = int(os.getenv("RETRIEVAL_CACHE_SIZE", "64"))

    TTS_VOICE: str = os.getenv("TTS_VOICE", "en-IN-PrabhatNeural")
    TTS_SPEED: float = float(os.getenv("TTS_SPEED", "1.0"))
    TTS_OUTPUT_DIR: str = os.getenv("TTS_OUTPUT_DIR", "./audio_cache")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")

    MAX_CONTEXT_LENGTH: int = 600
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 100

    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8001,http://127.0.0.1:8001")

    HYBRID_ALPHA: float = float(os.getenv("HYBRID_ALPHA", "0.7"))
    BM25_K1: float = 1.5
    BM25_B: float = 0.75

    ENABLE_HYBRID_SEARCH: bool = os.getenv("ENABLE_HYBRID_SEARCH", "false").lower() == "true"
    ENABLE_RERANKING: bool = os.getenv("ENABLE_RERANKING", "false").lower() == "true"
    ENABLE_CONTEXT_COMPRESSION: bool = os.getenv("ENABLE_CONTEXT_COMPRESSION", "true").lower() == "true"

    MONITORING_ENABLED: bool = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
    METRICS_FILE: str = os.getenv("METRICS_FILE", "logs/metrics.jsonl")


settings = Settings()
