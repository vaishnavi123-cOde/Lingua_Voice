import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.database.qdrant import qdrant_db
from app.models.schemas import ErrorResponse
from app.routers import ask, health, speak
from app.services.tts import tts_service
from app.utils.logging import setup_logging

logger = setup_logging()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="RAG-powered SQL Lecture Assistant with voice output",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup():
        logger.info("Starting %s v%s", settings.APP_NAME, settings.VERSION)

        # ---- Pre-flight checks ----
        checks_passed = True

        qdrant_ok = qdrant_db.connect()
        if not qdrant_ok:
            logger.error("PRE-FLIGHT FAILED: Qdrant connection error")
            checks_passed = False

        try:
            from app.services.embedding import embedding_service
            if embedding_service.model is not None:
                logger.info("Embedding model loaded: %s", settings.EMBED_MODEL)
            else:
                logger.error("PRE-FLIGHT FAILED: Embedding model not loaded")
                checks_passed = False
        except Exception as e:
            logger.error("PRE-FLIGHT FAILED: Embedding model error: %s", e)
            checks_passed = False

        try:
            from app.services.llm import llm_service
            llm_service.client.list()
            logger.info("Ollama connected: %s", settings.OLLAMA_HOST)
        except Exception as e:
            logger.warning("Ollama not reachable at %s: %s", settings.OLLAMA_HOST, e)

        if not checks_passed:
            logger.warning("Startup completed with pre-flight failures - some features may not work")

        tts_service.cleanup_old_files()

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("Shutting down %s", settings.APP_NAME)
        qdrant_db.disconnect()

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error="Internal server error", detail=str(exc)).model_dump(),
        )

    app.include_router(health.router)
    app.include_router(ask.router)
    app.include_router(speak.router)

    @app.get("/")
    def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.VERSION,
            "docs": "/docs" if settings.DEBUG else None,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )
