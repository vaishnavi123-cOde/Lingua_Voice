"""
Database Repair Script — Find and replace placeholder meanings in vocabulary table.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database_manager import db
from dictionary_service import dictionary_service, _is_placeholder


PLACEHOLDER_PATTERNS = [
    "meaning of", "definition pending", "loading...", "unknown",
]


def is_placeholder_meaning(meaning, word=None):
    if not meaning or not isinstance(meaning, str):
        return True
    text = meaning.strip().lower()
    if text in ("", "none", "null", "unknown", "loading...", "definition pending", "placeholder"):
        return True
    for pat in PLACEHOLDER_PATTERNS:
        if pat in text:
            return True
    if word and word.lower() in text:
        if len(text) < 20:
            return True
    return False


def repair_vocabulary_table():
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, word, language, meaning FROM vocabulary")
    rows = cursor.fetchall()

    repaired = 0
    skipped = 0
    examples = []

    for row_id, word, lang, meaning in rows:
        if not meaning:
            lang = lang or "es"
            definition = dictionary_service.get_meaning(word, lang)
            if definition:
                cursor.execute(
                    "UPDATE vocabulary SET meaning=? WHERE id=?",
                    (definition["meaning"], row_id),
                )
                repaired += 1
                examples.append((word, meaning or "(empty)", definition["meaning"]))
            else:
                cursor.execute(
                    "UPDATE vocabulary SET meaning='Meaning currently unavailable' WHERE id=? AND (meaning IS NULL OR meaning='')",
                    (row_id,),
                )
                repaired += 1
                examples.append((word, meaning or "(empty)", "Meaning currently unavailable"))
            continue

        if is_placeholder_meaning(meaning, word):
            lang = lang or "es"
            definition = dictionary_service.get_meaning(word, lang)
            if definition:
                cursor.execute(
                    "UPDATE vocabulary SET meaning=? WHERE id=?",
                    (definition["meaning"], row_id),
                )
                repaired += 1
                examples.append((word, meaning, definition["meaning"]))
            else:
                cursor.execute(
                    "UPDATE vocabulary SET meaning=? WHERE id=?",
                    ("Meaning currently unavailable", row_id),
                )
                repaired += 1
                examples.append((word, meaning, "Meaning currently unavailable"))
        else:
            skipped += 1

    conn.commit()
    conn.close()

    return repaired, skipped, examples


if __name__ == "__main__":
    print("=" * 60)
    print("  Vocabulary Definition Repair Tool")
    print("=" * 60)

    count_before = 0
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vocabulary")
    count_before = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE meaning IS NULL OR meaning=''")
    empty_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE meaning LIKE 'Meaning of %'")
    placeholder_count = cursor.fetchone()[0]
    conn.close()

    print(f"\nTotal vocabulary entries: {count_before}")
    print(f"Empty meanings: {empty_count}")
    print(f"Placeholder 'Meaning of...': {placeholder_count}")

    repaired, skipped, examples = repair_vocabulary_table()

    print(f"\nRepaired: {repaired}")
    print(f"Skipped (already valid): {skipped}")

    if examples:
        print("\nBefore → After Examples:")
        print("-" * 50)
        for word, before, after in examples[:10]:
            print(f"  {word:<15} | '{before}' → '{after}'")
        if len(examples) > 10:
            print(f"  ... and {len(examples) - 10} more")

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE meaning IS NULL OR meaning='' OR meaning LIKE 'Meaning of %'")
    remaining = cursor.fetchone()[0]
    conn.close()

    print(f"\nRemaining with issues: {remaining}")
    if remaining == 0:
        print("SUCCESS: All vocabulary entries have real meanings.")
    else:
        print(f"WARNING: {remaining} entries still need attention.")
    print("=" * 60)
