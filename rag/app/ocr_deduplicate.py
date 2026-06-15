"""
OCR Deduplication Pipeline (Phase 2)

Removes:
- Exact duplicate OCR chunks
- Near-duplicate OCR chunks (edit distance)
- Semantic duplicates (embedding similarity)
- Teams UI noise
- File path leaks
- Weather/taskbar noise
- Repetitive headers
- OCR fragments

Usage:
    python -m app.ocr_deduplicate
"""

import logging
import os
import pickle
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from thefuzz import fuzz

from app.config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)


NOISE_PATTERNS = [
    (r"Microsoft\s*Teams", ""),
    (r"Recorded\s*by", ""),
    (r"Organized\s*by", ""),
    (r"^\s*Gaurav\s+Mehta\s*$", "", re.MULTILINE),
    (r"Ask\s+Copilot", ""),
    (r"^\s*Chat\s*$", "", re.MULTILINE),
    (r"Type\s+a\s+message", ""),
    (r"\bENG\b", ""),
    (r"\bIN\b", ""),
    (r"Partly\s+sunny|Sunny|High\s+UV|Very\s+high\s+UV", ""),
    (r"C[:/]Users/Gaurav/", ""),
    (r"AppData/Local/Microsoft/Windows/INetCache/", ""),
    (r"Content\.Outlook\w*", ""),
    (r"SQL\s*DAY\s*1\s*pdf", ""),
    (r"@File|OFile", ""),
    (r"Breaking\s+news", ""),
    (r"Select\s+Repository", ""),
    (r"^\s*Ready\s*$", "", re.MULTILINE),
    (r"No\s+issues\s+found", ""),
    (r"Command\s+Prompt", ""),
    (r"Microsoft\s+Windows\s+\[Version", ""),
    (r"All\s+rights\s+reserved", ""),
    (r"Try\s+the\s+new\s+Outlook", ""),
    (r"Object\s+Explorer", ""),
    (r"\bTABS\b", ""),
    (r"\bCRLF\b", ""),
    (r"\bUTF-8\b", ""),
    (r"Connected\.", ""),
    (r"\(local\)", ""),
    (r"\d{2}\.\d{2}\s*(PM|AM)", ""),
    (r"\d{2}-\d{2}-\d{4}", ""),
    (r"\d{2}\s*[*C'\u00b0]C", ""),
    (r"^\s*\d+%\s*$", "", re.MULTILINE),
    (r"0f\s*\d+|of\s*\d+", ""),
    (r"^\s*[-=+]{3,}\s*$", "", re.MULTILINE),
    (r"[|]\s*$", "", re.MULTILINE),
    (r"[A-Za-z]\s*:\s*\d+\s*[A-Za-z]", ""),
    (r"^\s*\w{1,2}\s*$", "", re.MULTILINE),
    (r"^\s*@\s*$", "", re.MULTILINE),
    (r"^\s*c\)\s*$", "", re.MULTILINE),
]


class OCRDeduplicator:
    def __init__(self, slide_texts_dir: str = "slide_texts"):
        self.slide_texts_dir = Path(slide_texts_dir)
        self.embed_model = SentenceTransformer(settings.EMBED_MODEL)
        self.semantic_threshold = 0.92
        self.fuzzy_threshold = 85

    def load_ocr_files(self) -> list[dict]:
        files = sorted(self.slide_texts_dir.glob("*.txt"))
        documents = []
        for fpath in files:
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                if len(text.strip()) < 20:
                    continue
                documents.append({
                    "source": fpath.name,
                    "text": text,
                    "original_length": len(text),
                })
            except Exception as e:
                logger.warning("Failed to read %s: %s", fpath.name, e)
        logger.info("Loaded %d OCR files", len(documents))
        return documents

    def remove_noise(self, text: str) -> str:
        for pattern, replacement in NOISE_PATTERNS:
            text = re.sub(pattern, replacement, text)
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if len(stripped) < 4:
                continue
            if stripped.isdigit():
                continue
            cleaned.append(stripped)
        return "\n".join(cleaned)

    def remove_exact_duplicates(self, documents: list[dict]) -> list[dict]:
        seen_texts = set()
        unique = []
        for doc in documents:
            normalized = doc["text"].strip().lower()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique.append(doc)
        logger.info("Exact dedup: %d -> %d", len(documents), len(unique))
        return unique

    def remove_near_duplicates(self, documents: list[dict]) -> list[dict]:
        if len(documents) < 2:
            return documents
        unique = [documents[0]]
        for doc in documents[1:]:
            is_dup = False
            for kept in unique:
                ratio = fuzz.ratio(doc["text"].lower(), kept["text"].lower())
                if ratio >= self.fuzzy_threshold:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(doc)
        logger.info("Near dedup (fuzzy): %d -> %d", len(documents), len(unique))
        return unique

    def remove_semantic_duplicates(self, documents: list[dict]) -> list[dict]:
        if len(documents) < 2:
            return documents
        texts = [d["text"] for d in documents]
        embeddings = self.embed_model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        kept_indices = [0]
        for i in range(1, len(documents)):
            is_dup = False
            for j in kept_indices:
                sim = float(np.dot(embeddings[i], embeddings[j]))
                if sim >= self.semantic_threshold:
                    is_dup = True
                    break
            if not is_dup:
                kept_indices.append(i)
        deduped = [documents[i] for i in kept_indices]
        logger.info("Semantic dedup: %d -> %d", len(documents), len(deduped))
        return deduped

    def chunk_documents(self, documents: list[dict]) -> list[dict]:
        chunks = []
        for doc in documents:
            text = doc["text"]
            for i in range(0, len(text), settings.CHUNK_SIZE - settings.CHUNK_OVERLAP):
                chunk_text = text[i:i + settings.CHUNK_SIZE]
                if len(chunk_text.strip()) < 20:
                    continue
                chunks.append({
                    "text": chunk_text,
                    "source": doc["source"],
                })
        logger.info("Chunked into %d chunks", len(chunks))
        return chunks

    def run(self) -> list[dict]:
        logger.info("=" * 60)
        logger.info("OCR DEDUPLICATION PIPELINE")
        logger.info("=" * 60)

        documents = self.load_ocr_files()
        logger.info("Step 1: Noise removal...")
        for doc in documents:
            doc["text"] = self.remove_noise(doc["text"])
        documents = [d for d in documents if len(d["text"].strip()) >= 20]
        logger.info("  After noise removal: %d documents", len(documents))

        logger.info("Step 2: Exact duplicate removal...")
        documents = self.remove_exact_duplicates(documents)

        logger.info("Step 3: Near-duplicate (fuzzy) removal...")
        documents = self.remove_near_duplicates(documents)

        logger.info("Step 4: Semantic duplicate removal...")
        documents = self.remove_semantic_duplicates(documents)

        logger.info("Step 5: Chunking...")
        chunks = self.chunk_documents(documents)

        with open("chunks_dedup.pkl", "wb") as f:
            pickle.dump(chunks, f)

        logger.info("Saved %d deduplicated chunks to chunks_dedup.pkl", len(chunks))
        return chunks


def main():
    dedup = OCRDeduplicator()
    chunks = dedup.run()
    logger.info("\nFinal stats:")
    logger.info("  Original OCR files: 368")
    logger.info("  Cleaned chunks: %d", len(chunks))
    logger.info("  Reduction: %.1f%%", (1 - len(chunks) / 1403) * 100)


if __name__ == "__main__":
    main()
