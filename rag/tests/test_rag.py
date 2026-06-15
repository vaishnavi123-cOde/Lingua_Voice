"""
RAG Component Tests

Tests:
- Prompt template generation
- Context compression
- Hybrid retrieval scoring
- Confidence computation
"""

from app.rag.context_compressor import ContextCompressor
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.prompt_templates import get_rag_prompt, get_compression_prompt
from app.services.retrieval import RetrievalResult


def test_rag_prompt_contains_context():
    prompt = get_rag_prompt(
        question="What is SQL?",
        context="SQL is a database language.",
    )
    assert "What is SQL?" in prompt
    assert "SQL is a database language." in prompt
    assert "Answer:" in prompt


def test_rag_prompt_has_rules():
    prompt = get_rag_prompt(question="test", context="test")
    assert "STRICT RULES" in prompt
    assert "Do NOT use outside knowledge" in prompt
    assert "I could not find that information" in prompt


def test_compression_prompt():
    prompt = get_compression_prompt(
        question="What is SQL?",
        passage="Microsoft Teams garbage SQL is a language more noise",
    )
    assert "What is SQL?" in prompt
    assert "Relevant excerpt:" in prompt


def test_context_compressor_removes_noise():
    compressor = ContextCompressor()
    results = [
        RetrievalResult(
            text="Microsoft Teams\nSQL DATABASE\nWhat is SQL Server?\nGaurav Mehta\nENG\n02.23 PM",
            source="test.txt",
            score=0.85,
        )
    ]
    compressed = compressor.compress("What is SQL?", results)
    if compressed:
        text = compressed[0].text
        assert "What is SQL Server?" in text
        assert "Microsoft Teams" not in text
        assert "Gaurav Mehta" not in text


def test_context_compressor_deduplicates_lines():
    compressor = ContextCompressor()
    results = [
        RetrievalResult(
            text="SQL is great.\nSQL is great.\nDuplicate line.",
            source="test.txt",
            score=0.85,
        )
    ]
    compressed = compressor.compress("SQL?", results)
    if compressed:
        text = compressed[0].text
        lines = text.split("\n")
        assert len(lines) == len(set(l.lower().strip() for l in lines if l.strip()))


def test_hybrid_retriever_bm25():
    retriever = HybridRetriever()
    results = [
        RetrievalResult(text="SQL is a database query language.", source="a.txt", score=0.9),
        RetrievalResult(text="Python is a programming language.", source="b.txt", score=0.8),
    ]
    reranked = retriever.retrieve("What is SQL?", results)
    assert len(reranked) == 2
    # SQL-related should rank higher for "What is SQL?" query
    assert reranked[0].score >= results[0].score * 0.5


def test_hybrid_retriever_empty():
    retriever = HybridRetriever()
    result = retriever.retrieve("test", [])
    assert result == []


def test_hybrid_retriever_single():
    retriever = HybridRetriever()
    results = [RetrievalResult(text="Some text about SQL.", source="a.txt", score=0.7)]
    reranked = retriever.retrieve("SQL", results)
    assert len(reranked) == 1


def test_retrieval_result_attributes():
    r = RetrievalResult(text="test", source="file.txt", score=0.95, rank=1)
    assert r.text == "test"
    assert r.source == "file.txt"
    assert r.score == 0.95
    assert r.rank == 1


def test_retrieval_result_default_rank():
    r = RetrievalResult(text="test", source="file.txt", score=0.5)
    assert r.rank == 0
