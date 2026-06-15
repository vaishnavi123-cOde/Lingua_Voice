"""
Re-index pipeline after OCR deduplication.

Usage:
    python -m app.reindex
"""

import logging
import pickle

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config.settings import settings
from app.services.embedding import embedding_service

logger = logging.getLogger(__name__)


def reindex():
    logger.info("Loading deduplicated chunks...")
    with open("chunks_dedup.pkl", "rb") as f:
        chunks = pickle.load(f)

    logger.info("Generating embeddings for %d chunks...", len(chunks))
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedding_service.encode_documents(texts)

    client = QdrantClient(path=settings.QDRANT_PATH)

    try:
        client.delete_collection(settings.COLLECTION_NAME)
        logger.info("Deleted old collection")
    except Exception:
        pass

    client.create_collection(
        collection_name=settings.COLLECTION_NAME,
        vectors_config=VectorParams(
            size=settings.EMBED_DIM,
            distance=Distance.COSINE,
        ),
    )

    points = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(
            PointStruct(
                id=idx,
                vector=embedding.tolist(),
                payload={
                    "text": chunk["text"],
                    "source": chunk["source"],
                },
            )
        )

    client.upsert(
        collection_name=settings.COLLECTION_NAME,
        points=points,
    )

    logger.info("Inserted %d points into %s", len(points), settings.COLLECTION_NAME)
    logger.info("Re-indexing complete!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    reindex()
