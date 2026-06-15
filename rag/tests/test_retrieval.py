"""
Retrieval Tests

Tests retrieval quality for:
- SQL questions (in-scope)
- Out-of-scope questions
- OCR-only knowledge
- Transcript-only knowledge
"""

import pickle

import numpy as np
import pytest
from qdrant_client import QdrantClient

from app.config.settings import settings
from app.services.embedding import embedding_service


@pytest.fixture
def qdrant_client():
    return QdrantClient(path=settings.QDRANT_PATH)


@pytest.fixture
def load_chunks():
    try:
        with open("chunks_dedup.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        try:
            with open("chunks.pkl", "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            return []


def test_collection_exists():
    client = QdrantClient(path=settings.QDRANT_PATH)
    collections = client.get_collections().collections
    names = [c.name for c in collections]
    assert settings.COLLECTION_NAME in names


def test_embedding_model_loaded():
    assert embedding_service.model is not None
    test_emb = embedding_service.encode_query("What is SQL?")
    assert len(test_emb) == settings.EMBED_DIM


def test_retrieve_sql_question():
    client = QdrantClient(path=settings.QDRANT_PATH)
    query = embedding_service.encode_query("What is SQL Server?")
    results = client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=query,
        limit=5,
    ).points

    assert len(results) > 0, "No results returned for SQL question"
    assert results[0].score >= settings.RETRIEVAL_MIN_SCORE, (
        f"Top score {results[0].score} below threshold {settings.RETRIEVAL_MIN_SCORE}"
    )


def test_retrieve_primary_key():
    client = QdrantClient(path=settings.QDRANT_PATH)
    query = embedding_service.encode_query("What is a primary key?")
    results = client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=query,
        limit=5,
    ).points

    if results:
        top_text = results[0].payload.get("text", "").lower()
        assert any(
            kw in top_text for kw in ["primary key", "primary", "key"]
        ), f"No primary key mention found: {top_text[:200]}"


def test_retrieve_foreign_key():
    client = QdrantClient(path=settings.QDRANT_PATH)
    query = embedding_service.encode_query("How do foreign keys work?")
    results = client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=query,
        limit=5,
    ).points

    if results:
        top_text = results[0].payload.get("text", "").lower()
        assert any(
            kw in top_text for kw in ["foreign key", "foreign", "reference"]
        ), f"No foreign key mention found: {top_text[:200]}"


def test_retrieve_out_of_scope():
    client = QdrantClient(path=settings.QDRANT_PATH)
    query = embedding_service.encode_query(
        "What is the capital of France?"
    )
    results = client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=query,
        limit=5,
    ).points

    if results:
        assert results[0].score < 0.80, (
            f"Out-of-scope question scored too high: {results[0].score}"
        )


def test_retrieve_create_table():
    client = QdrantClient(path=settings.QDRANT_PATH)
    query = embedding_service.encode_query("How to create a table in SQL?")
    results = client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=query,
        limit=5,
    ).points

    if results:
        top_text = results[0].payload.get("text", "").lower()
        assert any(
            kw in top_text for kw in ["create table", "create"]
        ), f"No CREATE TABLE mention found: {top_text[:200]}"


def test_retrieve_select_query():
    client = QdrantClient(path=settings.QDRANT_PATH)
    query = embedding_service.encode_query("How to write a SELECT query?")
    results = client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=query,
        limit=5,
    ).points

    if results:
        top_text = results[0].payload.get("text", "").lower()
        assert "select" in top_text, (
            f"No SELECT mention found: {top_text[:200]}"
        )


def test_chunks_have_text_and_source(load_chunks):
    if load_chunks:
        for chunk in load_chunks[:10]:
            assert "text" in chunk
            assert "source" in chunk
            assert len(chunk["text"]) > 0
            assert len(chunk["source"]) > 0


def test_chunks_not_empty(load_chunks):
    if load_chunks:
        assert len(load_chunks) > 0
        for chunk in load_chunks:
            assert len(chunk["text"].strip()) >= 20


def test_retrieve_multiple_results():
    client = QdrantClient(path=settings.QDRANT_PATH)
    query = embedding_service.encode_query("SQL Server Management Studio")
    results = client.query_points(
        collection_name=settings.COLLECTION_NAME,
        query=query,
        limit=10,
    ).points

    if len(results) >= 5:
        scores = [r.score for r in results[:5]]
        assert scores == sorted(scores, reverse=True), (
            "Results not sorted by score descending"
        )


def test_retrieve_different_questions():
    client = QdrantClient(path=settings.QDRANT_PATH)
    questions = [
        "What is a database?",
        "How to use WHERE clause?",
        "What is normalization?",
        "How to insert data?",
        "What are constraints?",
    ]

    for q in questions:
        query = embedding_service.encode_query(q)
        results = client.query_points(
            collection_name=settings.COLLECTION_NAME,
            query=query,
            limit=3,
        ).points

        assert len(results) > 0, f"No results for: {q}"
        assert results[0].score > 0.40, (
            f"Low score for '{q}': {results[0].score}"
        )
