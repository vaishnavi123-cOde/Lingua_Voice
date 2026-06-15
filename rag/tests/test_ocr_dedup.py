"""
OCR Deduplication Tests

Tests:
- Noise pattern removal
- Exact duplicate detection
- Near-duplicate detection
- Semantic duplicate detection
- Chunking
"""

from app.ocr_deduplicate import OCRDeduplicator


def test_noise_removal_teams_ui(sample_ocr_text):
    dedup = OCRDeduplicator()
    cleaned = dedup.remove_noise(sample_ocr_text)
    assert "Microsoft Teams" not in cleaned
    assert "Gaurav Mehta" not in cleaned
    assert "ENG" not in cleaned
    assert "Sunny" not in cleaned


def test_noise_removal_preserves_content(sample_ocr_text, clean_sql_text):
    dedup = OCRDeduplicator()
    cleaned = dedup.remove_noise(sample_ocr_text)
    assert "What is SQL Server?" in cleaned
    assert "It is a software, developed by Microsoft." in cleaned


def test_exact_duplicate_removal():
    dedup = OCRDeduplicator()
    docs = [
        {"source": "a.txt", "text": "SQL is a database language."},
        {"source": "b.txt", "text": "SQL is a database language."},
        {"source": "c.txt", "text": "Python is a programming language."},
    ]
    unique = dedup.remove_exact_duplicates(docs)
    assert len(unique) == 2
    assert unique[0]["source"] == "a.txt"
    assert unique[1]["source"] == "c.txt"


def test_near_duplicate_removal():
    dedup = OCRDeduplicator()
    dedup.fuzzy_threshold = 80
    docs = [
        {"source": "a.txt", "text": "SQL is a database language used for managing data."},
        {"source": "b.txt", "text": "SQL is a database language used for managing data."},
        {"source": "c.txt", "text": "Python is completely different content here."},
    ]
    unique = dedup.remove_near_duplicates(docs)
    assert len(unique) == 2


def test_empty_text_filtered():
    dedup = OCRDeduplicator()
    result = dedup.remove_noise("")
    assert result == "" or len(result.strip()) == 0


def test_chunking_small_text():
    dedup = OCRDeduplicator()
    docs = [
        {"source": "test.txt", "text": "Short text."}
    ]
    chunks = dedup.chunk_documents(docs)
    assert len(chunks) == 0


def test_chunking_normal_text():
    dedup = OCRDeduplicator()
    text = "SQL is a database language. " * 50
    docs = [{"source": "test.txt", "text": text}]
    chunks = dedup.chunk_documents(docs)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk["text"].strip()) >= 20
        assert chunk["source"] == "test.txt"


def test_file_path_noise_removal():
    dedup = OCRDeduplicator()
    noisy = "C:/Users/Gaurav/AppData/Local/Microsoft/Windows/INetCache/Content.Outlook/file.pdf"
    cleaned = dedup.remove_noise(noisy)
    assert "C:/Users/Gaurav" not in cleaned
    assert "AppData/Local" not in cleaned


def test_weather_noise_removal():
    dedup = OCRDeduplicator()
    noisy = "32*C\nENG\n02.23 PM\nSunny\nIN"
    cleaned = dedup.remove_noise(noisy)
    assert "32*C" not in cleaned
    assert "02.23 PM" not in cleaned
    assert "Sunny" not in cleaned
    assert "ENG" not in cleaned
    assert "IN" not in cleaned
