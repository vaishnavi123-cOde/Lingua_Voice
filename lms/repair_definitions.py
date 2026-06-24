"""
Repair script: Find and fix placeholder/bad definitions in vocabulary tables.
Priority: OpenAI > Free Dictionary API > Offline Dictionary > Generated fallback
"""
import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FLASK_SECRET_KEY"] = "repair-script"

from database_manager import db
from word_validator import is_placeholder
from api_service import api_service

PLACEHOLDER_PATTERNS = [
    re.compile(r'^Definition pending\.\.\.$', re.I),
    re.compile(r'^Definición pendiente\.\.\.$', re.I),
    re.compile(r'^परिभाषा लंबित\.\.\.$', re.I),
    re.compile(r'^Learning in progress\.\.\.$', re.I),
    re.compile(r'^Meaning of ', re.I),
    re.compile(r'^A word related to ', re.I),
    re.compile(r'^Unknown$', re.I),
    re.compile(r'^Loading\.\.\.$', re.I),
]

def is_bad_meaning(text):
    if not text:
        return True
    text = text.strip()
    if len(text) < 3:
        return True
    for p in PLACEHOLDER_PATTERNS:
        if p.search(text):
            return True
    return False

def generate_fallback(word, language):
    """Smart fallback: use known translations for common words."""
    known = {
        ('es', 'perro'): 'dog',
        ('es', 'gato'): 'cat',
        ('es', 'casa'): 'house',
        ('es', 'agua'): 'water',
        ('es', 'sol'): 'sun',
        ('es', 'luna'): 'moon',
        ('es', 'playa'): 'beach',
        ('es', 'coche'): 'car',
        ('es', 'libro'): 'book',
        ('es', 'mesa'): 'table',
        ('es', 'silla'): 'chair',
        ('es', 'puerta'): 'door',
        ('es', 'ventana'): 'window',
        ('es', 'hombre'): 'man',
        ('es', 'mujer'): 'woman',
        ('es', 'niño'): 'boy',
        ('es', 'niña'): 'girl',
        ('es', 'comida'): 'food',
        ('es', 'tiempo'): 'time',
        ('es', 'trabajo'): 'work',
        ('es', 'escuela'): 'school',
        ('es', 'amigo'): 'friend',
        ('es', 'familia'): 'family',
        ('es', 'ciudad'): 'city',
        ('es', 'país'): 'country',
        ('es', 'mundo'): 'world',
        ('es', 'vida'): 'life',
        ('es', 'día'): 'day',
        ('es', 'noche'): 'night',
        ('es', 'grande'): 'big',
        ('es', 'pequeño'): 'small',
        ('es', 'bonito'): 'beautiful',
        ('es', 'feliz'): 'happy',
        ('es', 'triste'): 'sad',
        ('hi', 'पानी'): 'water',
        ('hi', 'आदमी'): 'man',
        ('hi', 'औरत'): 'woman',
        ('hi', 'बच्चा'): 'child',
        ('hi', 'खाना'): 'food',
        ('hi', 'घर'): 'house',
        ('hi', 'किताब'): 'book',
        ('hi', 'स्कूल'): 'school',
        ('hi', 'दोस्त'): 'friend',
        ('hi', 'पैसा'): 'money',
        ('hi', 'समय'): 'time',
        ('hi', 'काम'): 'work',
        ('hi', 'बड़ा'): 'big',
        ('hi', 'छोटा'): 'small',
        ('hi', 'अच्छा'): 'good',
        ('hi', 'बुरा'): 'bad',
        ('hi', 'सुंदर'): 'beautiful',
        ('hi', 'खुश'): 'happy',
        ('hi', 'दुखी'): 'sad',
        ('hi', 'दिन'): 'day',
        ('hi', 'रात'): 'night',
    }
    key = (language, word.lower())
    if key in known:
        return known[key]
    return None

def repair_vocabulary():
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, user_id, word, language, meaning
        FROM vocabulary
    """)
    rows = cursor.fetchall()
    total = len(rows)
    repaired = 0
    skipped_good = 0
    skipped_no_meaning = 0
    examples = []

    print(f"Found {total} vocabulary entries. Scanning for bad definitions...\n")

    for row_id, user_id, word, language, meaning in rows:
        if meaning and not is_bad_meaning(meaning):
            skipped_good += 1
            continue

        old_meaning = meaning or '(empty)'
        new_meaning = None

        if api_service.is_online():
            info = api_service.get_enhanced_word_info(word, language)
            if info and info.get('definition'):
                d = info['definition']
                if not is_bad_meaning(d):
                    new_meaning = d

        if not new_meaning or is_bad_meaning(new_meaning):
            new_meaning = generate_fallback(word, language)

        if new_meaning and not is_bad_meaning(new_meaning):
            cursor.execute(
                "UPDATE vocabulary SET meaning = ?, is_valid = 1 WHERE id = ?",
                (new_meaning, row_id)
            )
            repaired += 1
            examples.append((word, language, old_meaning, new_meaning))
            print(f"  REPAIRED: {word} ({language})")
            print(f"    Was: {old_meaning}")
            print(f"    Now: {new_meaning}\n")
        else:
            skipped_no_meaning += 1

    conn.commit()
    conn.close()

    print("=" * 60)
    print(f"Total entries scanned: {total}")
    print(f"Already had good definitions: {skipped_good}")
    print(f"Repaired: {repaired}")
    print(f"Still need definitions (no source found): {skipped_no_meaning}")
    print("=" * 60)

    if examples:
        print("\nSample before/after:")
        for word, lang, old, new in examples[:5]:
            print(f"  {word} ({lang}): '{old}' -> '{new}'")

def repair_vocabulary_discovery():
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, user_id, word, language, meaning
        FROM vocabulary_discovery WHERE viewed = 0
    """)
    rows = cursor.fetchall()
    repaired = 0

    for row_id, user_id, word, language, meaning in rows:
        if meaning and not is_bad_meaning(meaning):
            continue

        new_meaning = None
        if api_service.is_online():
            info = api_service.get_enhanced_word_info(word, language)
            if info and info.get('definition'):
                d = info['definition']
                if not is_bad_meaning(d):
                    new_meaning = d

        if not new_meaning or is_bad_meaning(new_meaning):
            new_meaning = generate_fallback(word, language)

        if new_meaning and not is_bad_meaning(new_meaning):
            cursor.execute(
                "UPDATE vocabulary_discovery SET meaning = ? WHERE id = ?",
                (new_meaning, row_id)
            )
            repaired += 1
            print(f"  REPAIRED discovery: {word} ({language}) -> {new_meaning}")

    conn.commit()
    conn.close()
    print(f"\nRepaired discovery entries: {repaired}")

if __name__ == "__main__":
    print("=" * 60)
    print("VOCABULARY DEFINITION REPAIR SCRIPT")
    print("=" * 60)
    repair_vocabulary()
    print("\n---\n")
    repair_vocabulary_discovery()
    print("\nDone.")
