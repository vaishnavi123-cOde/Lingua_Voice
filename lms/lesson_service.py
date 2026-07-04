"""
Lesson Service — 8-stage Duolingo-style lesson orchestration engine.
Composes lessons from level words + SRS reviews + weak words,
generates per-word exercise sequences, and handles lesson completion.
"""
import random
from datetime import date, datetime
from database_manager import db
from level_generator import level_generator


EXERCISE_XP = {
    "introduction": 3,
    "recognition": 8,
    "listening": 10,
    "speaking": 15,
    "context": 12,
    "active_recall": 10,
    "smart_review": 5,
}

STAGE_NAMES = {
    "introduction": "Learn New Word",
    "recognition": "Word Recognition",
    "listening": "Listening Practice",
    "speaking": "Speaking Practice",
    "context": "Words in Context",
    "active_recall": "Active Recall",
    "smart_review": "Smart Review",
    "summary": "Lesson Summary",
}


def _make_exercise(word, meaning, lang, stage, idx, word_obj=None):
    from dictionary_service import dictionary_service, _is_placeholder
    defn = dictionary_service.get_meaning(word, lang)
    if defn:
        meaning = defn["meaning"]
    elif not meaning or _is_placeholder(meaning, word):
        meaning = word

    pronunciation = _get_pronunciation(word, lang)
    explanation = _get_explanation(word, meaning, lang)

    e = {
        "id": f"ex-{idx}",
        "stage": stage,
        "type": stage,
        "stage_name": STAGE_NAMES.get(stage, stage),
        "word": word,
        "meaning": meaning,
        "language": lang,
        "xp": EXERCISE_XP.get(stage, 10),
        "pronunciation": pronunciation,
        "explanation": explanation,
    }

    from vocabulary_engine import vocabulary_engine

    if stage == "introduction":
        sent_data = _generate_example_sentence(word, meaning, lang)
        e["sentence"] = sent_data["text"]
        e["sentence_translation"] = sent_data["translation"]
        e["translation"] = meaning
        related = vocabulary_engine.generate_related_words(word, meaning, lang)
        e["related_words"] = [r.get("word") for r in related[:3]] if related else []

    elif stage == "recognition":
        mode = random.choice(["meaning", "word_pick"])
        if mode == "meaning":
            options = _generate_recognition_options(word, meaning, lang, use_words=False)
            e["mode"] = "meaning"
            e["correct"] = meaning
        else:
            options = _generate_recognition_options(word, meaning, lang, use_words=True)
            e["mode"] = "word_pick"
            e["correct"] = word
        e["options"] = options

    elif stage == "listening":
        options = _generate_distractors(word, lang)
        e["options"] = options
        e["correct"] = word

    elif stage == "speaking":
        e["prompt_text"] = word
        e["prompt_meaning"] = meaning

    elif stage == "context":
        mode = random.choice(["fill_blank", "meaning_select"])
        if mode == "fill_blank":
            sentence_data = _generate_fill_blank(word, meaning, lang)
            e["mode"] = mode
            e["sentence"] = sentence_data["text"]
            e["correct"] = sentence_data["answer"]
            e["sentence_translation"] = sentence_data.get("translation", "")
        elif mode == "meaning_select":
            options = _generate_recognition_options(word, meaning, lang, use_words=False)
            e["mode"] = mode
            sent = _generate_example_sentence(word, meaning, lang)
            e["context_sentence"] = sent["text"]
            e["options"] = options
            e["correct"] = meaning

    elif stage == "active_recall":
        mode = random.choice(["translate", "recall"])
        e["mode"] = mode
        if mode == "translate":
            e["prompt"] = meaning
            e["correct"] = word
        else:
            e["prompt_word"] = meaning
            e["correct"] = word

    return e


def _get_pronunciation(word, lang):
    """Generate a readable pronunciation guide for a word."""
    import re
    if lang == "es":
        vowels = re.findall(r'[aeiouáéíóú]', word.lower())
        stress = "stress on " if not vowels else ""
        return f"[{word}]"
    elif lang == "hi":
        return f"[{word}]"
    else:
        return f"/{word}/"


def _get_explanation(word, meaning, lang):
    short = meaning[:60] if len(meaning) > 60 else meaning
    if lang == "es":
        return f'"{word}" significa "{short}". Úsala en conversaciones cotidianas.'
    elif lang == "hi":
        return f'"{word}" ka arth "{short}" hai. Iska upyog rozana ki baat-cheet mein karein.'
    else:
        return f'"{word}" means "{short}". Use it in everyday conversations.'


def _generate_example_sentence(word, meaning, lang):
    templates = {
        "es": [
            ("{w} significa {m}.", f"{word} means {meaning}."),
            ("Yo uso {w} todos los días.", f"I use {word} every day."),
            ("{w} es una palabra importante.", f"{word} is an important word."),
            ("Necesito aprender {w}.", f"I need to learn {word}."),
            ("{w} es muy útil.", f"{word} is very useful."),
            ("Voy a practicar {w}.", f"I am going to practice {word}."),
            ("Ella dijo {w} ayer.", f"She said {word} yesterday."),
            ("{w} está en la frase.", f"{word} is in the sentence."),
            ("Aprendí {w} hoy.", f"I learned {word} today."),
            ("¿Sabes qué significa {w}?", f"Do you know what {word} means?"),
        ],
        "en": [
            ("{w} means {m}.", f"{word} means {meaning}."),
            ("I use {w} every day.", f"I use {word} every day."),
            ("{w} is an important word.", f"{word} is an important word."),
            ("I need to learn {w}.", f"I need to learn {word}."),
            ("The word {w} is very common.", f"The word {word} is very common."),
            ("She said {w} yesterday.", f"She said {word} yesterday."),
            ("I practice {w} every day.", f"I practice {word} every day."),
            ("Do you know {w}?", f"Do you know {word}?"),
            ("Learning {w} is fun.", f"Learning {word} is fun."),
            ("Can you use {w} in a sentence?", f"Can you use {word} in a sentence?"),
        ],
        "hi": [
            ("{w} ka arth {m} hai.", f"{word} means {meaning}."),
            ("Main {w} ka upyog karta hoon.", f"I use {word}."),
            ("{w} ek mahatvapoorn shabd hai.", f"{word} is an important word."),
            ("Mujhe {w} seekhna hai.", f"I need to learn {word}."),
            ("Kya aap {w} jante hain?", f"Do you know {word}?"),
        ],
    }
    t = templates.get(lang, templates["en"])
    pattern, translation = random.choice(t)
    text = pattern.replace("{w}", word).replace("{m}", meaning)
    return {"text": text, "translation": translation}


def _generate_recognition_options(correct_word, correct_meaning, lang, use_words=False):
    from dictionary_service import dictionary_service, _is_placeholder

    for attempt in range(5):
        options_data = []

        if use_words:
            options_data.append({"label": correct_word, "value": correct_word})
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT word FROM vocabulary WHERE language=? AND word!=? ORDER BY RANDOM() LIMIT 4",
                    (lang, correct_word),
                )
                for row in cursor.fetchall():
                    w = row[0]
                    if w != correct_word and not any(o["value"] == w for o in options_data):
                        options_data.append({"label": w, "value": w})
                conn.close()
            except Exception:
                pass
            filler_words = {
                "es": ["casa", "agua", "sol", "mesa", "flor", "pan", "leche", "rojo", "azul", "verde"],
                "en": ["house", "water", "sun", "table", "flower", "bread", "milk", "red", "blue", "green"],
                "hi": ["घर", "पानी", "सूरज", "मेज़", "फूल", "रोटी", "दूध", "लाल", "नीला", "हरा"],
            }.get(lang, ["house", "water", "sun", "table", "flower"])
            while len(options_data) < 4:
                w = random.choice(filler_words)
                if not any(o["value"] == w for o in options_data):
                    options_data.append({"label": w, "value": w})
        else:
            options_data.append({"label": correct_meaning, "value": correct_meaning})
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT word FROM vocabulary WHERE language=? AND word!=? ORDER BY RANDOM() LIMIT 6",
                    (lang, correct_word),
                )
                for row in cursor.fetchall():
                    w = row[0]
                    if any(o["value"] == w for o in options_data):
                        continue
                    defn = dictionary_service.get_meaning(w, lang)
                    if defn and defn.get("meaning"):
                        m = defn["meaning"]
                        is_bad = (len(m) > 30 or
                                  m == correct_meaning or
                                  " " in m.strip() or
                                  m.startswith(("A ", "An ", "The ")) or
                                  _is_placeholder(m, w))
                        if not is_bad:
                            options_data.append({"label": m, "value": m})
                conn.close()
            except Exception:
                pass
            filler_meanings = {
                "es": ["house", "water", "sun", "table", "flower", "bread", "milk", "red", "blue", "green",
                       "school", "book", "door", "tree", "river", "mountain", "city", "road", "money", "food"],
                "en": ["casa", "agua", "sol", "mesa", "flor", "pan", "leche", "rojo", "azul", "verde",
                       "escuela", "libro", "puerta", "árbol", "río", "montaña", "ciudad", "camino", "dinero", "comida"],
                "hi": ["house", "water", "sun", "table", "flower", "bread", "milk", "red", "blue", "green",
                       "school", "book", "door", "tree", "river", "mountain"],
            }.get(lang, ["house", "water", "sun", "table", "flower", "bread", "milk", "red", "blue", "green"])
            while len(options_data) < 4:
                m = random.choice(filler_meanings)
                if not any(o["value"] == m for o in options_data):
                    options_data.append({"label": m, "value": m})

        # Trim to 4 while guaranteeing correct answer is kept
        correct_value = correct_word if use_words else correct_meaning
        trimmed = []
        for o in options_data:
            if o["value"] == correct_value:
                trimmed.insert(0, o)
            elif len(trimmed) < 4:
                trimmed.append(o)
        trimmed = trimmed[:4]

        # Validate: exactly 4 unique options, correct answer present
        has_correct = any(o["value"] == correct_value for o in trimmed)
        all_valid = (len(trimmed) == 4 and has_correct and
                     len(set(o["value"] for o in trimmed)) == 4)

        if all_valid:
            random.shuffle(trimmed)
            return trimmed

    # Hard fallback: return just the correct answer as a single option
    label = correct_word if use_words else correct_meaning
    return [{"label": label, "value": label}]


def _generate_distractors(correct_word, lang):
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


def _generate_fill_blank(word, meaning, lang):
    templates = {
        "es": [
            f"Yo _____ todos los días.",
            f"Necesito _____ ahora.",
            f"Ella va a _____ mañana.",
            f"Ellos quieren _____.",
            f"Nosotros vamos a _____ pronto.",
            f"¿Puedes _____ esto?",
        ],
        "en": [
            f"I like to _____ every day.",
            f"Please _____ this for me.",
            f"Can you _____?",
            f"She wants to _____.",
            f"We need to _____ today.",
            f"They will _____ tomorrow.",
        ],
        "hi": [
            f"Main _____ karta hoon.",
            f"Kya aap _____ sakte hain?",
            f"Mujhe _____ hai.",
            f"Hum _____ karenge.",
        ],
    }
    candidates = templates.get(lang, templates["en"])
    sentence = random.choice(candidates)
    display = sentence.replace("_____", "______")
    trans = f"Sentence using: {word}"
    return {"text": display, "answer": word, "translation": trans}


def compose_lesson(user_id, level_id, language):
    """Compose a lesson with naturally interleaved new words and SRS review words."""
    from srs_manager import srs_manager
    from learner_intelligence import LearnerIntelligenceEngine
    from dictionary_service import dictionary_service

    NEW_WORD_STAGES = ["introduction", "recognition", "listening", "speaking", "context", "active_recall"]
    REVIEW_WORD_STAGES = ["recognition", "listening", "speaking", "context", "active_recall"]

    content = level_generator.generate_level_content(level_id, language, [])
    level_words = content.get("words", []) if isinstance(content, dict) else content[:5]
    if not level_words:
        return None

    new_words = []
    for w in level_words:
        if isinstance(w, str):
            new_words.append({"word": w, "language": language})
        elif isinstance(w, dict):
            new_words.append(w)
    new_words = dictionary_service.enrich_words(new_words, language)

    existing_word_set = set(w.get("word", "").lower() for w in new_words if w.get("word"))

    try:
        due = srs_manager.get_due_words(user_id, language) or []
        random.shuffle(due)
    except Exception:
        due = []

    review_words = []
    for rw in due:
        rw_text = rw.get("word", rw) if isinstance(rw, dict) else rw
        if rw_text.lower() not in existing_word_set and len(review_words) < 3:
            review_words.append(rw_text)
            existing_word_set.add(rw_text.lower())

    try:
        lie = LearnerIntelligenceEngine(user_id)
        plan = lie.generate_daily_plan(language)
        if plan and "reviews" in plan:
            for r in plan["reviews"][:2]:
                rword = r.get("word", "") if isinstance(r, dict) else r
                if rword and rword.lower() not in existing_word_set and len(review_words) < 4:
                    review_words.append(rword)
                    existing_word_set.add(rword.lower())
    except Exception:
        pass

    # Build merged word list: interleave new + review naturally
    merged = []
    all_new = list(new_words)
    all_review = list(review_words)
    random.shuffle(all_new)
    random.shuffle(all_review)

    new_idx = 0
    review_idx = 0
    # Pattern: 2 new → 1 review → 1 new → 1 review → remaining new → remaining review
    pattern = [2, 1, 1, 1]
    for p in pattern:
        if p == 2:
            for _ in range(2):
                if new_idx < len(all_new):
                    merged.append(("new", all_new[new_idx]))
                    new_idx += 1
        elif p == 1 and new_idx < len(all_new):
            merged.append(("new", all_new[new_idx]))
            new_idx += 1
        elif p == 1 and review_idx < len(all_review):
            merged.append(("review", {"word": all_review[review_idx], "language": language}))
            review_idx += 1
    while new_idx < len(all_new):
        merged.append(("new", all_new[new_idx]))
        new_idx += 1
        if review_idx < len(all_review):
            merged.append(("review", {"word": all_review[review_idx], "language": language}))
            review_idx += 1
    while review_idx < len(all_review):
        merged.append(("review", {"word": all_review[review_idx], "language": language}))
        review_idx += 1

    all_word_objs = [w for _, w in merged]

    exercises = []
    for wi, (word_type, w) in enumerate(merged):
        word_text = w["word"]
        meaning = w.get("meaning", word_text)
        stages = NEW_WORD_STAGES if word_type == "new" else REVIEW_WORD_STAGES
        for stage in stages:
            idx = len(exercises)
            ex = _make_exercise(word_text, meaning, language, stage, idx, w)
            ex["word_index"] = wi
            ex["word_count"] = len(merged)
            ex["word_type"] = word_type
            exercises.append(ex)

    exercises.append({
        "id": "summary",
        "stage": "summary",
        "type": "summary",
        "stage_name": "Lesson Summary",
        "word_count": len(all_word_objs),
        "xp": 0,
    })

    total_xp = sum(e.get("xp", 0) for e in exercises if e.get("type") != "summary")

    try:
        meta = level_generator.get_level_metadata(level_id)
        title = meta.get("name", f"Level {level_id}")
    except Exception:
        title = f"Level {level_id}"

    from vocabulary_engine import vocabulary_engine
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT total_xp FROM user_progress WHERE user_id=? AND language=?",
                       (user_id, language))
        row = cursor.fetchone()
        user_xp = row[0] if row else 0
        conn.close()
    except Exception:
        user_xp = 0

    try:
        combo = srs_manager.get_combo(user_id, language)
        current_streak = combo.get("current_streak", 0)
    except Exception:
        current_streak = 0

    new_count = sum(1 for t, _ in merged if t == "new")
    review_count = sum(1 for t, _ in merged if t == "review")

    return {
        "title": title,
        "level_id": level_id,
        "language": language,
        "words": all_word_objs,
        "exercises": exercises,
        "total_xp": total_xp,
        "word_count": len(merged),
        "new_word_count": new_count,
        "review_word_count": review_count,
        "exercise_count": len([e for e in exercises if e.get("type") != "summary"]),
        "stage_order": NEW_WORD_STAGES,
        "user_xp": user_xp,
        "current_streak": current_streak,
        "streak_days": current_streak,
    }


def complete_lesson(user_id, level_id, language, score, total, xp_earned, word_progress=None, duration_seconds=0):
    from srs_manager import srs_manager
    from adaptive_chatbot import AdaptiveChatbot
    from datetime import date, timedelta, datetime

    passed = score >= total * 0.6
    accuracy = round((score / total * 100)) if total > 0 else 0

    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT passed FROM user_completed_levels WHERE user_id=? AND level_id=?", (user_id, level_id))
        existing = cursor.fetchone()
        if existing and existing[0]:
            conn.close()
            return {"passed": True, "xp_earned": 0, "score": score, "total": total, "level_id": level_id, "accuracy": accuracy, "new_achievements": [], "already_completed": True}

        # Snapshot user_progress BEFORE SRS operations (which update it via _award_xp)
        # so we can compute streak correctly afterward
        cursor.execute("SELECT streak_days, last_activity FROM user_progress WHERE user_id=? AND language=?", (user_id, language))
        up_row = cursor.fetchone()
        old_streak = up_row[0] if up_row else 0
        old_last_activity_raw = up_row[1] if up_row else None
        if old_last_activity_raw and isinstance(old_last_activity_raw, str):
            old_last_activity = datetime.strptime(old_last_activity_raw, '%Y-%m-%d').date()
        elif old_last_activity_raw:
            old_last_activity = old_last_activity_raw
        else:
            old_last_activity = None

        if word_progress:
            for wp in word_progress:
                word = wp.get("word")
                correct = wp.get("correct", False)
                rt = wp.get("response_time_ms", 1000)
                if not word:
                    continue

                cursor.execute(
                    "SELECT id FROM vocabulary WHERE user_id=? AND word=? AND language=?",
                    (user_id, word, language),
                )
                row = cursor.fetchone()

                if row:
                    word_id = row[0]
                else:
                    from dictionary_service import dictionary_service
                    defn = dictionary_service.get_meaning(word, language)
                    meaning_text = defn["meaning"] if defn else ""
                    cursor.execute("""
                        INSERT INTO vocabulary (user_id, word, language, meaning, first_seen, is_valid)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 1)
                    """, (user_id, word, language, meaning_text))
                    word_id = cursor.lastrowid
                    # Commit vocabulary INSERT so SRS methods (which open their own
                    # connections) can write without SQLite's "database is locked" error
                    conn.commit()
                    srs_manager.schedule_new_word(word_id)

                if correct:
                    srs_manager.handle_correct(word_id, rt)
                else:
                    srs_manager.handle_incorrect(word_id, rt)

        # Begin explicit transaction for lesson-level analytics
        cursor.execute("BEGIN")

        if word_progress:
            for wp in word_progress:
                word = wp.get("word")
                correct = wp.get("correct", False)
                rt = wp.get("response_time_ms", 1000)
                if not word:
                    continue
                cursor.execute("""
                    INSERT INTO performance_analytics (user_id, language, word, lesson_type, response_time, is_correct, timestamp, difficulty_level)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """, (user_id, language, word, "lesson_exercise", rt, 1 if correct else 0, "lesson"))

        xp_to_award = xp_earned
        if passed:
            xp_to_award += 10

        if xp_to_award > 0:
            cursor.execute("""
                INSERT INTO learning_sessions (user_id, session_date, language, xp_earned, words_learned, duration_seconds)
                VALUES (?, CURRENT_DATE, ?, ?, ?, ?)
            """, (user_id, language, xp_to_award, len(word_progress) if word_progress else 0, duration_seconds))

        cursor.execute(
            "INSERT OR REPLACE INTO user_completed_levels (user_id, level_id, xp_earned, score, passed) VALUES (?, ?, ?, ?, ?)",
            (user_id, level_id, xp_to_award, score, 1 if passed else 0),
        )

        conn.commit()

        # These open their own connections — critical that conn has no open transaction
        if xp_to_award > 0:
            try:
                chatbot = AdaptiveChatbot()
                chatbot.update_user_progress(user_id, language, xp_to_award)
            except Exception:
                pass

            # Fix streak: _award_xp (called by handle_correct in the SRS loop) updates
            # user_progress.last_activity to today before update_user_progress can read the
            # old value. This makes the streak-delta calculation always see same-day activity,
            # so streak never increments. We recompute it from the pre-SRS snapshot.
            today = date.today()
            if old_last_activity is not None:
                delta = today - old_last_activity
                if delta == timedelta(days=1):
                    new_streak = old_streak + 1
                elif delta > timedelta(days=1):
                    new_streak = 1
                else:
                    new_streak = old_streak
            else:
                new_streak = 1
            if new_streak != old_streak:
                sc = db.get_connection()
                sc.execute("UPDATE user_progress SET streak_days=? WHERE user_id=? AND language=?", (new_streak, user_id, language))
                sc.commit()
                sc.close()

        try:
            new_achs = srs_manager.check_achievements(user_id, language)
        except Exception:
            new_achs = []

        return {
            "passed": passed,
            "xp_earned": xp_to_award,
            "score": score,
            "total": total,
            "level_id": level_id,
            "accuracy": accuracy,
            "new_achievements": new_achs,
        }

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
