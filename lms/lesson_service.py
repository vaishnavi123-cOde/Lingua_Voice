"""
Lesson Service — Duolingo-style lesson orchestration engine.

Composes lessons from level words + SRS reviews + weak words,
generates per-word exercise sequences, and handles lesson completion.
"""
import random
from datetime import date, datetime
from database_manager import db
from level_generator import level_generator


# ── Exercise Templates ──────────────────────────────────────────
# Each word in a lesson goes through a subset of these types.

EXERCISE_TYPES = [
    "learn",        # Show word + meaning + example sentence
    "listen",       # Hear the word, pick correct translation
    "speak",        # Say the word, speech recognition check
    "translate",    # See translation, type the word
    "sentence",     # Fill in the blank in a sentence
    "recall",       # See meaning, recall the word (SRS-style)
]

# XP rewards per exercise type
EXERCISE_XP = {
    "learn": 5,
    "listen": 10,
    "speak": 15,
    "translate": 10,
    "sentence": 12,
    "recall": 8,
}

# ── Helpers ─────────────────────────────────────────────────────


def _make_exercise(word, meaning, lang, exercise_type, idx):
    """Build an exercise dict for a word."""
    e = {
        "id": f"ex-{idx}",
        "type": exercise_type,
        "word": word,
        "meaning": meaning,
        "language": lang,
        "xp": EXERCISE_XP.get(exercise_type, 10),
    }

    if exercise_type == "learn":
        example = _generate_example(word, meaning, lang)
        e["example"] = example

    elif exercise_type == "listen":
        options = _generate_distractors(word, lang)
        e["options"] = options
        e["correct"] = word

    elif exercise_type == "translate":
        e["prompt"] = meaning
        e["correct"] = word

    elif exercise_type == "sentence":
        blank_sentence = _generate_sentence_with_blank(word, meaning, lang)
        e["sentence"] = blank_sentence["text"]
        e["correct"] = blank_sentence["answer"]

    elif exercise_type == "recall":
        e["prompt"] = meaning
        e["correct"] = word

    return e


def _generate_example(word, meaning, lang):
    """Generate a simple example sentence. Uses template-based approach."""
    templates = {
        "es": [
            f"'{word}' significa '{meaning}'.",
            f"Yo uso '{word}' todos los días.",
            f"'{word}' es una palabra importante.",
            f"Necesito aprender '{word}'.",
        ],
        "en": [
            f"'{word}' means '{meaning}'.",
            f"I use '{word}' every day.",
            f"'{word}' is an important word.",
            f"I need to learn '{word}'.",
        ],
        "hi": [
            f"'{word}' का अर्थ '{meaning}' है।",
            f"मैं '{word}' का उपयोग करता हूँ।",
        ],
    }
    t = templates.get(lang, templates["en"])
    return random.choice(t)


def _generate_distractors(correct_word, lang):
    """Generate multiple-choice options including the correct word."""
    options = [correct_word]
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT word FROM vocabulary WHERE language=? AND word!=? ORDER BY RANDOM() LIMIT 3",
            (lang, correct_word),
        )
        others = [row[0] for row in cursor.fetchall()]
        conn.close()
        options.extend(others)
    except Exception:
        pass

    # Pad with generic fillers if needed
    fillers = {
        "es": ["casa", "agua", "sol", "mesa", "flor"],
        "en": ["house", "water", "sun", "table", "flower"],
        "hi": ["घर", "पानी", "सूरज", "मेज़", "फूल"],
    }.get(lang, ["house", "water", "sun"])

    while len(options) < 4:
        w = random.choice(fillers)
        if w not in options:
            options.append(w)

    random.shuffle(options)
    return options


def _generate_sentence_with_blank(word, meaning, lang):
    """Generate a fill-in-the-blank sentence."""
    blanks = {
        "es": [
            (f"Yo _____ todos los días.", word),
            (f"Necesito _____ ahora.", word),
            (f"'{word}' es _____ .", "importante"),
        ],
        "en": [
            (f"I like to _____ every day.", word),
            (f"Please _____ this for me.", word),
            (f"Can you _____ ?", word),
        ],
    }
    candidates = blanks.get(lang, blanks["en"])
    sentence, answer = random.choice(candidates)
    display = sentence.replace("_____", "______")
    return {"text": display, "answer": answer}


# ── Main Composition ────────────────────────────────────────────


def compose_lesson(user_id, level_id, language):
    """Compose a full lesson with words, exercises, and SRS reviews.

    Returns a dict with:
        title, level_id, language,
        words: list of word objects to learn,
        exercises: flat list of exercise dicts,
        srs_reviews: list of due word reviews injected at breakpoints,
        total_xp: sum of all exercise XP,
        review_breakpoints: indices where SRS reviews appear.
    """
    from srs_manager import srs_manager
    from learner_intelligence import LearnerIntelligenceEngine

    # 1. Get level words
    content = level_generator.generate_level_content(level_id, language, [])
    level_words = content.get("words", []) if isinstance(content, dict) else content[:5]

    if not level_words:
        return None

    # Normalize words to dicts
    words = []
    for w in level_words:
        if isinstance(w, str):
            words.append({"word": w, "meaning": w, "language": language})
        elif isinstance(w, dict):
            words.append(w)

    # Ensure each word has a meaning
    for w in words:
        if not w.get("meaning"):
            w["meaning"] = w["word"]

    # 2. Get SRS due reviews (inject 1-3 at breakpoints)
    try:
        due = srs_manager.get_due_words(user_id, language) or []
        random.shuffle(due)
        srs_reviews = due[:3]
    except Exception:
        srs_reviews = []

    # 3. Get weak words from learner intelligence
    weak_words = []
    try:
        lie = LearnerIntelligenceEngine(user_id)
        plan = lie.generate_daily_plan(language)
        if plan and "reviews" in plan:
            weak_words = [r["word"] for r in plan["reviews"][:2] if isinstance(r, dict)]
    except Exception:
        plan = None

    # 4. Build exercise sequence
    exercises = []
    word_exercise_count = {}
    word_map = {}

    for w in words:
        word_text = w["word"]
        meaning = w.get("meaning", word_text)
        word_map[word_text] = w

        # Pick 3-5 exercise types for this word (varies per word)
        ex_types = EXERCISE_TYPES.copy()
        random.shuffle(ex_types)

        # Always start with 'learn'
        chosen = ["learn"]
        remaining = [t for t in ex_types if t != "learn"]
        n = random.randint(2, min(4, len(remaining)))
        chosen.extend(remaining[:n])

        for j, ex_type in enumerate(chosen):
            idx = len(exercises)
            ex = _make_exercise(word_text, meaning, language, ex_type, idx)
            ex["word_index"] = len(word_exercise_count)
            exercises.append(ex)

        word_exercise_count[word_text] = len(chosen)

    # 5. Inject SRS reviews at breakpoints
    review_breakpoints = []
    if srs_reviews:
        step = max(1, len(exercises) // (len(srs_reviews) + 1))
        for i, rw in enumerate(srs_reviews):
            bp = step * (i + 1)
            if bp < len(exercises):
                review_breakpoints.append(bp)
                rw_text = rw.get("word", rw) if isinstance(rw, dict) else rw
                exercises.insert(bp, {
                    "id": f"srs-review-{i}",
                    "type": "review",
                    "word": rw_text,
                    "meaning": rw.get("meaning", ""),
                    "language": language,
                    "xp": 5,
                    "is_srs": True,
                })
                # Adjust subsequent breakpoints
                review_breakpoints = [
                    x + 1 if x >= bp else x for x in review_breakpoints
                ]

    # 6. Calculate total XP
    total_xp = sum(e.get("xp", 0) for e in exercises)

    # 7. Get title
    try:
        meta = level_generator.get_level_metadata(level_id)
        title = meta.get("name", f"Level {level_id}")
    except Exception:
        title = f"Level {level_id}"

    return {
        "title": title,
        "level_id": level_id,
        "language": language,
        "words": words,
        "exercises": exercises,
        "srs_reviews": srs_reviews,
        "total_xp": total_xp,
        "review_breakpoints": review_breakpoints,
        "word_count": len(words),
        "exercise_count": len(exercises),
    }


# ── Lesson Completion ────────────────────────────────────────────


def complete_lesson(user_id, level_id, language, score, total, xp_earned, word_progress=None):
    """Complete a lesson: update SRS, record progress, award XP."""
    from srs_manager import srs_manager
    from adaptive_chatbot import AdaptiveChatbot

    passed = score >= total * 0.6  # 60% to pass

    # Award XP
    if xp_earned > 0:
        try:
            chatbot = AdaptiveChatbot()
            chatbot.update_user_progress(user_id, language, xp_earned)
        except Exception:
            pass

    # Update SRS for each word in word_progress
    if word_progress:
        for wp in word_progress:
            word = wp.get("word")
            correct = wp.get("correct", False)
            rt = wp.get("response_time_ms", 1000)
            if word:
                try:
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM vocabulary WHERE user_id=? AND word=? AND language=?",
                        (user_id, word, language),
                    )
                    row = cursor.fetchone()
                    conn.close()
                    if row:
                        word_id = row[0]
                        if correct:
                            srs_manager.handle_correct(word_id, rt)
                        else:
                            srs_manager.handle_incorrect(word_id, rt)
                except Exception:
                    pass

    # Record level completion
    conn = db.get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO user_completed_levels (user_id, level_id, xp_earned, score, passed) VALUES (?, ?, ?, ?, ?)",
        (user_id, level_id, xp_earned, score, 1 if passed else 0),
    )
    conn.commit()
    conn.close()

    return {
        "passed": passed,
        "xp_earned": xp_earned,
        "score": score,
        "total": total,
        "level_id": level_id,
    }
