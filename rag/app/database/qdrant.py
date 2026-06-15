import logging
import json
import os
from pathlib import Path
from contextlib import asynccontextmanager

from qdrant_client import QdrantClient

from app.config.settings import settings

logger = logging.getLogger(__name__)


class QdrantDatabase:
    def __init__(self):
        self.client: QdrantClient | None = None
        self.collection_name = settings.COLLECTION_NAME

    def _validate_meta_json(self) -> bool:
        """Validate and fix meta.json before connecting to prevent Pydantic v2 extra field errors."""
        meta_path = Path(settings.QDRANT_PATH) / "meta.json"
        if not meta_path.exists():
            logger.warning("meta.json not found at %s", meta_path)
            return True
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            modified = False
            EXTRA_FIELDS = ["metadata"]
            for col_config in meta.get("collections", {}).values():
                for field in EXTRA_FIELDS:
                    if field in col_config:
                        logger.warning("Removing extra field '%s' from meta.json", field)
                        del col_config[field]
                        modified = True
            if modified:
                with open(meta_path, "w") as f:
                    json.dump(meta, f)
                logger.info("meta.json fixed - extra fields removed")
            return True
        except Exception as e:
            logger.error("Failed to validate meta.json: %s", e)
            return False

    def connect(self):
        try:
            self._validate_meta_json()
            self.client = QdrantClient(path=settings.QDRANT_PATH)
            collection_info = self.client.get_collection(self.collection_name)
            logger.info(
                "Connected to Qdrant. Collection: %s, Points: %d",
                self.collection_name,
                collection_info.points_count,
            )
            return True
        except Exception as e:
            logger.error("Failed to connect to Qdrant: %s", e)
            return False

    def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("Disconnected from Qdrant")

    def get_client(self) -> QdrantClient:
        if self.client is None:
            self.connect()
        return self.client

    def get_collection_info(self) -> dict:
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "points_count": info.points_count,
                "vectors_config": str(info.config.params.vectors),
            }
        except Exception as e:
            logger.error("Failed to get collection info: %s", e)
            return {"error": str(e)}


qdrant_db = QdrantDatabase()
