"""
diagnose_qdrant.py - Qdrant Database Diagnostic Tool

Checks:
1. Installed package versions (qdrant-client, pydantic, etc.)
2. Data file integrity (chunks.pkl, embeddings.npy)
3. Qdrant database structure (meta.json, storage.sqlite)
4. Collection accessibility and metadata
5. Vector count and dimension compatibility

Usage:
    python diagnose_qdrant.py          (check only)
    python diagnose_qdrant.py --fix    (check + auto-fix meta.json)
"""

import json
import os
import pickle
import sys
from pathlib import Path

QDRANT_DIR = Path("./qdrant_db")
META_FILE = QDRANT_DIR / "meta.json"
STORAGE_FILE = QDRANT_DIR / "collection" / "sql_lectures" / "storage.sqlite"
CHUNKS_FILE = Path("./chunks.pkl")
EMBEDDINGS_FILE = Path("./embeddings.npy")
EMBEDDINGS_OCR_FILE = Path("./embeddings_ocr.npy")


def print_header(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def check_package_versions():
    print_header("Package Versions")
    packages = ["qdrant_client", "pydantic", "numpy", "sentence_transformers"]
    for pkg in packages:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "unknown")
            print(f"  {pkg:<25} {ver}")
        except ImportError as e:
            print(f"  {pkg:<25} NOT INSTALLED - {e}")


def check_data_files():
    print_header("Data File Integrity")
    for name, path in [
        ("chunks.pkl (transcript chunks)", CHUNKS_FILE),
        ("embeddings.npy (transcript vectors)", EMBEDDINGS_FILE),
        ("embeddings_ocr.npy (OCR vectors)", EMBEDDINGS_OCR_FILE),
    ]:
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  [OK] {name:<45} {size_mb:.2f} MB")
        else:
            print(f"  [!!] {name:<45} MISSING")


def check_chunks_content():
    print_header("Chunks Content")
    if not CHUNKS_FILE.exists():
        print("  [!!] chunks.pkl not found")
        return
    try:
        with open(CHUNKS_FILE, "rb") as f:
            chunks = pickle.load(f)
        print(f"  Total chunks: {len(chunks)}")
        if chunks:
            sample = chunks[0]
            print(f"  Sample keys: {list(sample.keys())}")
            print(f"  Sample source: {sample.get('source', 'N/A')}")
            text = sample.get("text", "")
            print(f"  Sample text preview: {text[:100]}...")
    except Exception as e:
        print(f"  [!!] Failed to load chunks.pkl: {e}")


def check_embeddings():
    print_header("Embeddings")
    for name, path in [("embeddings.npy", EMBEDDINGS_FILE), ("embeddings_ocr.npy", EMBEDDINGS_OCR_FILE)]:
        if not path.exists():
            print(f"  [!!] {name} not found")
            continue
        try:
            import numpy as np
            arr = np.load(path)
            print(f"  {name:<25} shape={arr.shape}, dtype={arr.dtype}")
        except Exception as e:
            print(f"  [!!] {name} failed to load: {e}")


def check_qdrant_directory():
    print_header("Qdrant Database Directory")
    if not QDRANT_DIR.exists():
        print(f"  [!!] Directory does not exist: {QDRANT_DIR}")
        return
    print(f"  [OK] Directory exists: {QDRANT_DIR}")
    if META_FILE.exists():
        print(f"  [OK] meta.json: {META_FILE.stat().st_size} bytes")
        with open(META_FILE) as f:
            meta = json.load(f)
        print(f"  Collections defined: {list(meta.get('collections', {}).keys())}")
        for col_name, col_config in meta.get("collections", {}).items():
            vectors = col_config.get("vectors", {})
            print(f"    -> {col_name}:")
            print(f"       Vector size: {vectors.get('size', 'N/A')}")
            print(f"       Distance: {vectors.get('distance', 'N/A')}")
            for field in ["metadata", "strict_mode_config"]:
                if field in col_config:
                    print(f"       [WARN] Found '{field}' field (may cause Pydantic v2 validation error)")
    else:
        print(f"  [!!] meta.json not found")
    if STORAGE_FILE.exists():
        print(f"  [OK] storage.sqlite: {STORAGE_FILE.stat().st_size / (1024 * 1024):.1f} MB")
    else:
        print(f"  [!!] storage.sqlite not found")


def check_qdrant_local_connection():
    print_header("Qdrant Local Connection Test")
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(path=str(QDRANT_DIR))
        collections = client.get_collections()
        print(f"  [OK] Connected to local Qdrant")
        print(f"  Collections count: {len(collections.collections)}")
        for col in collections.collections:
            print(f"    -> {col.name}")
            try:
                info = client.get_collection(col.name)
                print(f"       Points: {info.points_count}")
                try:
                    vectors_config = info.config.params.vectors
                    print(f"       Vector size: {vectors_config.size}")
                    print(f"       Distance: {vectors_config.distance}")
                except Exception:
                    print(f"       Vector config: present")
            except Exception as e:
                print(f"       [!!] Failed to get info: {e}")
        client.close()
        return True
    except Exception as e:
        print(f"  [!!] Failed to connect: {e}")
        if "extra_forbidden" in str(e) or "Extra inputs are not permitted" in str(e):
            print(f"  CAUSE: meta.json has extra fields not in CreateCollection model")
            print(f"  FIX: python diagnose_qdrant.py --fix")
        return False


def check_compatibility():
    print_header("Compatibility Check")
    try:
        import pydantic
        pyd_major = int(pydantic.__version__.split(".")[0])
        print(f"  Pydantic v{pydantic.__version__} ({'v2+' if pyd_major >= 2 else 'v1'})")
        if pyd_major >= 2:
            print(f"  [WARN] Pydantic v2 has 'extra=forbid' on some Qdrant models")
            print(f"         Extra fields in meta.json will cause CreateCollection to fail")
    except Exception as e:
        print(f"  [!!] Could not check pydantic: {e}")

    try:
        from qdrant_client.http import models
        cc = models.CreateCollection
        if hasattr(cc, "model_config"):
            extra = cc.model_config.get("extra")
            print(f"  CreateCollection.extra = {extra}")
            if extra == "forbid":
                print(f"  [WARN] Strict mode: extra fields in meta.json will cause validation errors")
    except Exception as e:
        print(f"  [!!] Could not check CreateCollection: {e}")


def fix_meta_json():
    """Remove extra fields from meta.json to fix Pydantic validation."""
    print_header("Auto-Fix meta.json")
    if not META_FILE.exists():
        print("  [!!] meta.json not found - nothing to fix")
        return False

    with open(META_FILE) as f:
        meta = json.load(f)

    fixed = False
    EXTRA_FIELDS = ["metadata"]
    for col_name, col_config in meta.get("collections", {}).items():
        for field in EXTRA_FIELDS:
            if field in col_config:
                print(f"  Removing '{field}' from collection '{col_name}'")
                del col_config[field]
                fixed = True

    if fixed:
        with open(META_FILE, "w") as f:
            json.dump(meta, f)
        print("  [OK] meta.json fixed and saved")
        return True
    else:
        print("  [OK] No extra fields found - meta.json is clean")
        return True


def reindex_setup():
    """Recommend re-indexing if needed."""
    print_header("Re-index Recommendation")
    needs_reindex = False

    if not CHUNKS_FILE.exists():
        print("  [!!] chunks.pkl missing - need: python chunk_documents.py")
        needs_reindex = True
    if not EMBEDDINGS_FILE.exists() and not EMBEDDINGS_OCR_FILE.exists():
        print("  [!!] embeddings missing - need: python embeddings.py or python embeddings_ocr.py")
        needs_reindex = True
    if not QDRANT_DIR.exists() or not STORAGE_FILE.exists():
        print("  [!!] qdrant_db empty/missing - need: python qdrant_setup.py")
        needs_reindex = True

    if not needs_reindex:
        print("  [OK] All data files present - re-index not required")
    else:
        print("  [WARN] Re-index required - see steps above")


if __name__ == "__main__":
    print(f"\n{'#' * 60}")
    print(f"  Qdrant Diagnostic Tool")
    print(f"  Working dir: {Path.cwd()}")
    print(f"{'#' * 60}")

    check_package_versions()
    check_data_files()
    check_chunks_content()
    check_embeddings()
    check_qdrant_directory()
    check_compatibility()
    check_qdrant_local_connection()
    reindex_setup()

    print(f"\n{'=' * 60}")
    print("  TO FIX: python diagnose_qdrant.py --fix")
    print(f"{'=' * 60}\n")

    if "--fix" in sys.argv:
        print("\n*** RUNNING AUTO-FIX ***")
        fixed = fix_meta_json()
        if fixed:
            print("\nRe-testing connection...\n")
            check_qdrant_local_connection()
