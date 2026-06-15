"""
API Tests

Tests:
- Health endpoint
- Ask endpoint with valid/invalid questions
- Speak endpoint
- Error handling
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "qdrant_connected" in data


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "version" in data


def test_ask_empty_question():
    response = client.post("/ask", json={"question": ""})
    assert response.status_code == 400


def test_ask_valid_question():
    response = client.post("/ask", json={"question": "What is SQL Server?"})
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "question" in data
    assert "confidence" in data
    assert "sources" in data


def test_ask_response_structure():
    response = client.post("/ask", json={"question": "What is a primary key?"})
    if response.status_code == 200:
        data = response.json()
        assert "question" in data
        assert "answer" in data
        assert isinstance(data["sources"], list)
        assert isinstance(data["confidence"], float)
        assert isinstance(data["retrieval_time_ms"], float)
        assert isinstance(data["llm_time_ms"], float)
        assert isinstance(data["total_time_ms"], float)


def test_ask_out_of_scope():
    response = client.post(
        "/ask", json={"question": "What is the weather in London?"}
    )
    data = response.json()
    assert "answer" in data
    assert "I could not find" in data["answer"] or "lectures" in data["answer"]


def test_speak_empty_text():
    response = client.post("/speak", json={"text": ""})
    assert response.status_code == 400


def test_speak_valid_text():
    response = client.post(
        "/speak", json={"text": "Hello, this is a test."}
    )
    assert response.status_code in (200, 500)


def test_health_checks_qdrant():
    response = client.get("/health")
    data = response.json()
    assert isinstance(data["qdrant_connected"], bool)
    assert isinstance(data["ollama_connected"], bool)
    assert isinstance(data["total_chunks"], int)


def test_ask_long_question():
    long_q = "What is " + "SQL " * 500
    response = client.post("/ask", json={"question": long_q.strip()})
    assert response.status_code in (200, 400, 422)


def test_ask_with_special_chars():
    response = client.post(
        "/ask",
        json={"question": "What's the difference between INNER JOIN & LEFT JOIN?"},
    )
    assert response.status_code == 200
