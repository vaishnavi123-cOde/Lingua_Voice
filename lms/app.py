from flask import Flask, render_template, jsonify, request, redirect, session, url_for, flash
import os
import transcriber
import threading
import sqlite3
import random
from database_manager import db
from adaptive_chatbot import AdaptiveChatbot
from word_validator import WordValidator
from language_detector import OfflineLanguageDetector
from conversation_engine import conversation_engine
from api_service import api_service
from srs_manager import srs_manager
from vocabulary_engine import vocabulary_engine
from learner_intelligence import learner_intelligence

# Initialize OpenAI Service
try:
    from config import OPENAI_API_KEY
    from openai_service import OpenAIWordService, openai_service as os_svc
    import openai_service
    openai_service.openai_service = OpenAIWordService(OPENAI_API_KEY)
    vocabulary_engine.openai = openai_service.openai_service
    from api_service import api_service
    vocabulary_engine.api = api_service
    print("[APP] OpenAI API initialized successfully")
except Exception as e:
    print(f"[APP] Warning: Could not initialize OpenAI API: {e}")
    print("[APP] Word meanings will use fallback dictionary APIs")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY environment variable is required")
chatbot = AdaptiveChatbot()
word_validator = WordValidator()
lang_detector = OfflineLanguageDetector()
transcriber.start_transcriber()

def get_current_user_id():
    return session.get("user_id")

def is_logged_in():
    return "user_id" in session

# --- Routes: Auth ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = db.login_user(email, password)
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            transcriber.set_active_user(user["id"]) # Connect audio to this user
            return redirect("/dashboard")
        else:
            flash("Invalid email or password", "error")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        if db.register_user(email, password, name):
            flash("Account created! Please log in.", "success")
            return redirect("/login")
        else:
            flash("Email already registered.", "error")
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    transcriber.set_active_user(None)
    return redirect("/login")

@app.route("/health")
def health_check():
    health = {"status": "ok", "database": "unknown"}
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        health["database"] = "connected"
        health["tables"] = tables
        conn.close()
    except Exception as e:
        health["status"] = "error"
        health["database"] = f"error: {str(e)}"
    return jsonify(health)

# --- Routes: Main App ---
@app.route("/")
def index():
    if is_logged_in():
        return redirect("/dashboard")
    return redirect("/landing")

@app.route("/landing")
def landing():
    return render_template("landing_new.html")

@app.route("/dashboard")
def dashboard():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("dashboard_modern.html", user_name=user_name)

@app.route("/transcription")
def transcription_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("transcription_modern.html", user_name=user_name)

@app.route("/tutor")
def tutor_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    user_id = get_current_user_id()
    
    # Get target language
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row and row[0] else 'es'
    
    # Get current level to fetch appropriate content
    cursor.execute("SELECT level_id FROM user_completed_levels WHERE user_id=? AND passed=1", (user_id,))
    completed = [r[0] for r in cursor.fetchall()]
    current_level = max(completed) + 1 if completed else 1
    conn.close()
    
    return render_template("tutor.html", user_name=user_name, target_language=target_language, current_level=current_level)

@app.route("/api/tutor/get_content")
def get_tutor_content():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    
    user_id = get_current_user_id()
    level_id = int(request.args.get('level', 1))
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row and row[0] else 'es'
    
    # Get used words and meanings to exclude them (avoids repeat concepts across languages)
    cursor.execute("SELECT word, meaning FROM vocabulary WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    exclude_words = set()
    for word, meaning in rows:
        if word: exclude_words.add(word.lower())
        if meaning:
            # Add the English keyword if it's a simple meaning
            simple_meaning = meaning.split('|')[0].split('(')[0].strip().lower()
            if len(simple_meaning) < 20: # Only exclude short concept words
                exclude_words.add(simple_meaning)
    
    exclude_list = list(exclude_words)
    conn.close()
    
    from level_generator import level_generator
    words = level_generator.generate_level_content(level_id, target_language, exclude_words=exclude_list)
    
    # Track these words so they aren't repeated
    for w in words:
        try:
            word_validator.validate_and_store_word(
                user_id, 
                w['word'], 
                target_language, 
                source_context='ai_tutor',
                meaning=w.get('meaning')
            )
        except Exception as e:
            print(f"[API] Error tracking tutor word {w['word']}: {e}")
    
    # Store in session for quiz consistency if they switch to quiz mode in tutor
    session[f'level_{level_id}_words'] = words
    
    return jsonify({"words": words, "level": level_id})

@app.route("/vocabulary")
def vocabulary_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("vocabulary_modern.html", user_name=user_name)
@app.route("/learning_path")
def learning_path_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    user_id = get_current_user_id()
    
    # Fetch progress from DB
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Table creation moved to database_manager.py

    
    # Fetch completed levels
    cursor.execute("SELECT level_id FROM user_completed_levels WHERE user_id=? AND passed=1", (user_id,))
    completed_levels = [row[0] for row in cursor.fetchall()]
    
    # Fetch target language
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row else None
    
    # If not set, check if we can infer from user_progress (legacy)
    if not target_language:
        cursor.execute("SELECT language FROM user_progress WHERE user_id=? ORDER BY last_activity DESC LIMIT 1", (user_id,))
        row = cursor.fetchone()
        if row:
             target_language = row[0]
             # Backfill
             cursor.execute("UPDATE users SET target_language=? WHERE id=?", (target_language, user_id))
             conn.commit()

    conn.close()
    
    # Determine current level (max completed + 1)
    current_level = max(completed_levels) + 1 if completed_levels else 1
    
    return render_template("learning_path.html", user_name=user_name, completed_levels=completed_levels, current_level=current_level, target_language=target_language)

@app.route("/api/set_target_language", methods=["POST"])
def set_target_language():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    lang = data.get("language")
    
    if not lang:
        return jsonify({"error": "No language provided"}), 400
        
    user_id = get_current_user_id()
    conn = db.get_connection()
    try:
        conn.execute("UPDATE users SET target_language=? WHERE id=?", (lang, user_id))
        conn.commit()
    except Exception as e:
        print(f"[API] Error setting language: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
        
    return jsonify({"success": True})

@app.route("/learning/level/<int:level_id>/flashcards")
def level_flashcards(level_id):
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    user_id = get_current_user_id()
    
    # Get user's target language
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row and row[0] else 'es'
    
    # Get user's existing vocabulary words to exclude duplicates
    cursor.execute("SELECT word, meaning FROM vocabulary WHERE user_id=? AND language=?", (user_id, target_language))
    rows = cursor.fetchall()
    conn.close()
    
    exclude_words = set()
    for word, meaning in rows:
        if word: exclude_words.add(word.lower())
        if meaning and len(meaning) < 20:
            exclude_words.add(meaning.lower().split('|')[0].split('(')[0].strip())
    
    # Also exclude words from previously completed levels
    for l in range(1, level_id):
        prev_words = session.get(f'level_{l}_words', [])
        for w in prev_words:
            if isinstance(w, dict) and w.get('word'):
                exclude_words.add(w['word'].lower())
    
    from level_generator import level_generator
    words = level_generator.generate_level_content(level_id, target_language, exclude_words=list(exclude_words))
    
    # Store words in session for quiz consistency
    session[f'level_{level_id}_words'] = words
    
    print(f"[DEBUG] Level {level_id} words ({target_language}): {[w.get('word') for w in words]}")
    
    return render_template("flashcards.html", user_name=user_name, level_id=level_id, words=words)
@app.route("/learning/level/<int:level_id>/quiz")
def level_quiz(level_id):
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("quiz.html", user_name=user_name, level_id=level_id)

@app.route("/lesson/continue")
def lesson_continue():
    if not is_logged_in(): return redirect("/login")
    user_id = get_current_user_id()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT level_id FROM user_completed_levels WHERE user_id=? AND passed=1", (user_id,))
    completed = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    lang = row[0] if row and row[0] else 'es'
    next_level = max(completed) + 1 if completed else 1
    return redirect(f"/lesson/{next_level}")

@app.route("/lesson/<int:level_id>")
def lesson_page(level_id):
    if not is_logged_in(): return redirect("/login")
    user_id = get_current_user_id()
    user_name = session.get("user_name", "User")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    lang = row[0] if row and row[0] else 'es'

    from lesson_service import compose_lesson
    lesson_data = compose_lesson(user_id, level_id, lang)
    if not lesson_data:
        return redirect("/learning_path")

    return render_template("lesson.html",
                         user_name=user_name,
                         lesson_data=lesson_data,
                         title=lesson_data.get("title", f"Level {level_id}"))

@app.route("/api/lesson/complete", methods=["POST"])
def lesson_complete():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    data = request.get_json()
    level_id = data.get("level_id")
    language = data.get("language")
    score = data.get("score", 0)
    total = data.get("total", 1)
    xp_earned = data.get("xp_earned", 0)
    word_progress = data.get("word_progress")

    stage_stats = data.get("stage_stats", {})
    duration_seconds = data.get("duration_seconds", 0)

    from lesson_service import complete_lesson
    result = complete_lesson(user_id, level_id, language, score, total, xp_earned, word_progress, duration_seconds)

    new_ach = result.get("new_achievements", [])
    if new_ach:
        result["new_achievements"] = new_ach

    return jsonify(result)

@app.route("/api/lesson/coach_message", methods=["POST"])
def lesson_coach_message():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    message = data.get("message", "")
    word = data.get("word", "")
    try:
        from ai_tutor_service import get_ai_tutor_response
        reply = get_ai_tutor_response(message, "en", "es", [], weak_words=[])
        return jsonify({"message": reply or "Keep going!"})
    except Exception:
        encouragements = [
            "Great work! Keep practicing!",
            "You're making excellent progress!",
            "Don't give up! Consistency is key.",
            "Fantastic effort! Keep it up!",
            "You're doing great! Every word counts!",
        ]
        import random
        return jsonify({"message": random.choice(encouragements)})

@app.route("/learning")
def learning_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("learning_modern.html", user_name=user_name)

@app.route("/reviews")
def review_center():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("review_center.html", user_name=user_name)

@app.route("/analytics")
def analytics_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("analytics_modern.html", user_name=user_name)


@app.route("/notes")
@app.route("/public/notes")
def notes_page():
    # If explicitly public or not logged in, show as guest
    is_public = request.path.startswith('/public')
    user_id = get_current_user_id() if is_logged_in() else None
    
    target_language = 'es'
    if user_id:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        target_language = row[0] if row and row[0] else 'es'
        conn.close()
    
    return render_template("notes.html", target_language=target_language, is_public=is_public)

@app.route("/api/notes/translate", methods=["POST"])
def api_translate_note():
    # Allow public access for translation
    data = request.json
    text = data.get("text")
    lang = data.get("lang", "es")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    from ai_tutor_service import get_note_translation
    result = get_note_translation(text, lang)
    return jsonify(result)

@app.route("/test")
@app.route("/public/test")
def test_page():
    is_public = request.path.startswith('/public')
    user_name = session.get("user_name", "Guest") if is_logged_in() else "Explorer"
    user_id = get_current_user_id() if is_logged_in() else None
    
    target_language = 'es'
    current_level = 1
    
    if user_id:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        target_language = row[0] if row and row[0] else 'es'
        
        cursor.execute("SELECT level_id FROM user_completed_levels WHERE user_id=? AND passed=1", (user_id,))
        completed = [r[0] for r in cursor.fetchall()]
        current_level = max(completed) + 1 if completed else 1
        conn.close()
    
    return render_template("test.html", user_name=user_name, target_language=target_language, current_level=current_level, is_public=is_public)

@app.route("/api/public/tutor/get_content")
def api_public_tutor_content():
    """Public version of tutor content for guests"""
    level = request.args.get('level', 1, type=int)
    from level_generator import generate_level_content
    content = generate_level_content(level, 'es') # Default to Spanish for guests
    return jsonify(content)

@app.route("/word_validation")
def word_validation_page():
    if not is_logged_in(): return redirect("/login")
    return render_template("word_validation_enhanced.html")

@app.route("/ai_tutor")
def ai_tutor_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("ai_tutor_modern.html", user_name=user_name)

@app.route("/certificate")
def certificate_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    user_id = get_current_user_id()
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get target language
    cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
    row = cursor.fetchone()
    target_language = row[0] if row and row[0] else 'en'
    
    # Get actual total XP from user_progress
    cursor.execute("""
        SELECT COALESCE(SUM(total_xp), 0) FROM user_progress WHERE user_id=?
    """, (user_id,))
    total_xp = cursor.fetchone()[0]
    if not total_xp:
        # Fallback: sum XP from completed levels
        cursor.execute("""
            SELECT COALESCE(SUM(xp_earned), 0) FROM user_completed_levels WHERE user_id=? AND passed=1
        """, (user_id,))
        total_xp = cursor.fetchone()[0] or 0
    
    conn.close()
    
    language_names = {'en': 'English', 'es': 'Spanish', 'hi': 'Hindi', 'fr': 'French', 'de': 'German'}
    language_name = language_names.get(target_language, target_language.capitalize())
    
    return render_template("certificate.html", user_name=user_name, language_name=language_name, total_xp=total_xp)

@app.route("/api/save_level_progress", methods=["POST"])
def save_level_progress():
    """Save user's level completion progress"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    level_id = data.get('level_id')
    score = data.get('score')
    xp_earned = data.get('xp_earned')
    passed = data.get('passed')
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Insert or replace execution
        cursor.execute("""
            INSERT OR REPLACE INTO user_completed_levels (user_id, level_id, xp_earned, score, passed)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, level_id, xp_earned, score, passed))
        
        conn.commit()
        conn.close()
        
        if level_id == 100 and passed:
            return jsonify({"success": True, "certificate": True, "redirect": "/certificate"})
        
        return jsonify({"success": True, "next_level": level_id + 1 if passed else level_id})
        
    except Exception as e:
        print(f"[API] Save progress error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
@app.route("/validation")
def validation_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("validation_modern.html", user_name=user_name)
@app.route("/update_meanings")
def update_meanings_page():
    if not is_logged_in(): return redirect("/login")
    return render_template("update_meanings.html")

@app.route("/community")
def community_page():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("community.html", user_name=user_name)


# --- Routes: API ---
@app.route("/api/update_all_meanings")
def update_all_meanings():
    """Fetch meanings for all words using OpenAI API"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT word, language, meaning 
            FROM vocabulary 
            WHERE user_id = ?
        """, (user_id,))
        
        words = cursor.fetchall()
        updated_count = 0
        
        for word, language, current_meaning in words:
            if current_meaning and len(current_meaning) > 20 and 'pending' not in current_meaning.lower() and 'uplabdh' not in current_meaning:
                continue
            
            print(f"[API] Fetching: {word} ({language})")
            new_meaning = word_validator.get_word_meaning(word, language)
            
            if new_meaning:
                cursor.execute("""
                    UPDATE vocabulary 
                    SET meaning = ? 
                    WHERE user_id = ? AND word = ? AND language = ?
                """, (new_meaning, user_id, word, language))
                updated_count += 1
                print(f"[API] ✓ {word}: {new_meaning[:50]}...")
        
        conn.commit()
        conn.close()
        
        return jsonify({"success": True, "updated": updated_count, "total": len(words)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_transcripts")

def get_transcripts():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, language, text, audio_file FROM transcripts WHERE user_id=? ORDER BY id DESC LIMIT 50", (user_id,))
    data = [{"timestamp": r[0], "language": r[1], "text": r[2], "audio_file": r[3]} for r in cursor.fetchall()]
    conn.close()
    return jsonify(data)

@app.route("/api/start_recording", methods=["POST"])
def start_recording():
    """Initialize recording session for the user"""
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    
    # Ensure transcriber knows who is recording
    transcriber.set_active_user(user_id)
    
    # Also default the language if provided in body, else keep current
    data = request.get_json()
    if data and 'language' in data:
        lang = data.get('language')
        if lang in ['en', 'es', 'hi']:
            transcriber.set_active_language(lang)
            
    return jsonify({"success": True})

@app.route("/api/set_language", methods=["POST"])
def set_language():
    """Set the active transcription language"""
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    
    data = request.get_json()
    lang = data.get('language')
    
    if lang not in ['en', 'es', 'hi']:
        return jsonify({"error": "Invalid language"}), 400
        
    transcriber.set_active_language(lang)
    transcriber.set_active_user(user_id) # Ensure user is also refreshed
    return jsonify({"success": True, "language": lang})

@app.route("/api/save_transcript", methods=["POST"])
def save_manual_transcript():
    """Manually save a transcript from frontend"""
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        text = data.get('text')
        language = data.get('language')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        # Use existing logic
        transcriber.set_active_user(user_id)
        transcriber.save_transcript(text, language, audio_path="manual_entry")
        
        # Trigger vocabulary expansion for each transcribed word
        try:
            words = text.lower().split()
            conn = db.get_connection()
            cursor = conn.cursor()
            for word in words:
                cursor.execute("SELECT id FROM vocabulary WHERE user_id = ? AND word = ? AND language = ?",
                               (user_id, word.strip('.,!?;:\'"()[]{}'), language))
                row = cursor.fetchone()
                if row:
                    vocabulary_engine.expand_vocabulary(user_id, row[0])
            conn.close()
        except Exception as e2:
            print(f"[VOCAB] Expansion error on transcript: {e2}")
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"[API] Error saving transcript: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/get_live_transcripts")
def get_live_transcripts():
    """Get transcripts from the last 5 seconds for live display"""
    user_id = get_current_user_id()
    if not user_id: return jsonify([])
    
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        # Fetch transcripts from the last 10 seconds (allow some buffer)
        cursor.execute("""
            SELECT text, language, timestamp 
            FROM transcripts 
            WHERE user_id=? AND timestamp >= datetime('now', '-10 seconds', 'localtime')
            ORDER BY timestamp ASC
        """, (user_id,))
        
        data = [{"text": r[0], "language": r[1], "id": str(r[2])} for r in cursor.fetchall()]
        conn.close()
        return jsonify({"transcripts": data})
    except Exception as e:
        print(f"[API] Error fetching live transcripts: {e}")
        return jsonify({"transcripts": []})

@app.route("/api/reviews/today")
def api_reviews_today():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    words = srs_manager.get_due_words(user_id, language)
    return jsonify({"due_count": len(words), "words": words})

@app.route("/api/reviews/submit", methods=["POST"])
def api_reviews_submit():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    data = request.get_json()
    word_id = data.get("word_id")
    correct = data.get("correct")
    response_time_ms = data.get("response_time_ms", 0)
    if not word_id:
        return jsonify({"error": "word_id required"}), 400
    if correct:
        result = srs_manager.handle_correct(word_id, response_time_ms)
    else:
        result = srs_manager.handle_incorrect(word_id, response_time_ms)
    if result is None:
        return jsonify({"error": "Word not found"}), 404

    # Record performance analytics
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT word, language FROM vocabulary WHERE id = ?", (word_id,))
        row = cursor.fetchone()
        if row:
            word, lang = row
            chatbot.record_performance(user_id, lang, word, 'review', response_time_ms, correct, 'srs')
        conn.close()
    except Exception as e:
        print(f"[ANALYTICS] Error recording performance: {e}")

    # Auto-expand vocabulary when word is answered correctly (mastery 1+)
    if correct and result and result.get('mastery', 0) >= 1:
        try:
            expansion = vocabulary_engine.expand_vocabulary(get_current_user_id(), word_id)
            if expansion:
                result['new_discoveries'] = len(expansion)
        except Exception as e:
            print(f"[VOCAB] Expansion error: {e}")

    return jsonify({"success": True, "result": result})

@app.route("/api/reviews/stats")
def api_reviews_stats():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    stats = srs_manager.get_srs_stats(user_id)
    due_count = srs_manager.get_due_count(user_id)
    stats['due_count'] = due_count
    return jsonify(stats)

@app.route("/api/reviews/combo")
def api_reviews_combo():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    combo = srs_manager.get_combo(user_id, language)
    return jsonify(combo)

@app.route("/api/reviews/achievements")
def api_reviews_achievements():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    achievements = srs_manager.get_achievements(user_id)
    return jsonify({"achievements": achievements})

@app.route("/api/reviews/check_achievements", methods=["POST"])
def api_reviews_check_achievements():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    new_achievements = srs_manager.check_achievements(user_id)
    return jsonify({"new_achievements": new_achievements})

@app.route("/api/reviews/analytics")
def api_reviews_analytics():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    analytics = srs_manager.get_analytics(user_id)
    return jsonify(analytics)

@app.route("/api/reviews/weak_words")
def api_reviews_weak_words():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    limit = request.args.get('limit', 10, type=int)
    words = srs_manager.get_weak_words(user_id, limit, language)
    return jsonify({"words": words})

@app.route("/api/reviews/complete_session", methods=["POST"])
def api_reviews_complete_session():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    data = request.get_json() or {}
    perfect = data.get('perfect', False)
    new_achievements = srs_manager.check_achievements(user_id)

    # Check perfect session achievement separately
    if perfect:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM achievements WHERE requirement_type = 'perfect_session'
        """)
        ach_row = cursor.fetchone()
        if ach_row:
            ach_id = ach_row[0]
            cursor.execute("""
                INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
                VALUES (?, ?)
            """, (user_id, ach_id))
            if cursor.rowcount > 0:
                cursor.execute("SELECT name, description, icon FROM achievements WHERE id = ?", (ach_id,))
                a = cursor.fetchone()
                new_achievements.append({'id': ach_id, 'name': a[0], 'icon': a[2], 'description': a[1]})
        conn.commit()
        conn.close()

    return jsonify({"new_achievements": new_achievements, "perfect_bonus": srs_manager.PERFECT_BONUS_XP if perfect else 0})

# ============================================================
# VOCABULARY ENGINE API
# ============================================================

@app.route("/api/vocab/recommendations")
def api_vocab_recommendations():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    limit = request.args.get('limit', 10, type=int)
    recommendations = vocabulary_engine.get_recommendations(user_id, language, limit)
    return jsonify({"recommendations": recommendations})

@app.route("/api/vocab/graph")
def api_vocab_graph():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    depth = request.args.get('depth', 2, type=int)
    graph = vocabulary_engine.get_word_graph(user_id, language, depth)
    return jsonify({"graph": graph})

@app.route("/api/vocab/topics")
def api_vocab_topics():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    topics = vocabulary_engine.get_user_topics(user_id, language)
    return jsonify({"topics": topics})

@app.route("/api/vocab/related/<int:word_id>")
def api_vocab_related(word_id):
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    related = vocabulary_engine.get_related_words(user_id, word_id)
    return jsonify({"related": related})

@app.route("/api/vocab/expand/<int:word_id>", methods=["POST"])
def api_vocab_expand(word_id):
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    result = vocabulary_engine.expand_vocabulary(user_id, word_id)
    return jsonify({"expanded": result})

@app.route("/api/vocab/discovery/<int:discovery_id>/add", methods=["POST"])
def api_vocab_discovery_add(discovery_id):
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    result = vocabulary_engine.add_discovery_to_vocabulary(user_id, discovery_id)
    return jsonify({"success": result is not None, "result": result})

@app.route("/api/vocab/discovery/<int:discovery_id>/view", methods=["POST"])
def api_vocab_discovery_view(discovery_id):
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    vocabulary_engine.mark_discovery_viewed(discovery_id)
    return jsonify({"success": True})

@app.route("/api/vocab/discovery_card/<int:discovery_id>")
def api_vocab_discovery_card(discovery_id):
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, word, language, meaning, source_word, difficulty_level, relation_type, topic
        FROM vocabulary_discovery WHERE id = ? AND user_id = ?
    """, (discovery_id, user_id))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    word_data = {
        'id': row[0], 'word': row[1], 'language': row[2], 'meaning': row[3],
        'source_word': row[4], 'difficulty_level': row[5], 'relation_type': row[6], 'topic': row[7]
    }
    card = vocabulary_engine.generate_discovery_card(user_id, word_data)
    return jsonify({"card": card})

@app.route("/api/vocab/learning_path/<path:topic>")
def api_vocab_learning_path(topic):
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language', 'en')
    count = request.args.get('count', 7, type=int)
    path = vocabulary_engine.generate_learning_path(user_id, topic, language, count)
    return jsonify({"learning_path": path})

@app.route("/api/vocab/prioritized_reviews")
def api_vocab_prioritized_reviews():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    limit = request.args.get('limit', 20, type=int)
    try:
        words = vocabulary_engine.get_prioritized_words(user_id, language, limit)
        return jsonify({"words": words})
    except Exception as e:
        print(f"[API] Error in prioritized_reviews: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": True, "recommendations": []})

# ============================================================
# LEARNER INTELLIGENCE ENGINE API
# ============================================================

@app.route("/api/learner/daily_plan")
def api_learner_daily_plan():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    force_refresh = request.args.get('refresh', '').lower() == 'true'

    if not force_refresh:
        engine = learner_intelligence(user_id)
        cached = engine.get_cached_plan(language)
        if cached:
            return jsonify(cached)

    engine = learner_intelligence(user_id)
    plan = engine.generate_daily_plan(language)
    return jsonify(plan)

@app.route("/api/learner/insights")
def api_learner_insights():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    engine = learner_intelligence(user_id)
    plan = engine.generate_daily_plan(language)
    return jsonify({"insights": plan.get('insights', []), "goals": plan.get('goals', {})})

@app.route("/api/learner/forgetting_curve")
def api_learner_forgetting_curve():
    if not is_logged_in(): return jsonify({"error": "Not logged in"}), 401
    user_id = get_current_user_id()
    language = request.args.get('language')
    limit = request.args.get('limit', 10, type=int)
    engine = learner_intelligence(user_id)
    plan = engine.generate_daily_plan(language)
    return jsonify({"forgetting_curve": plan.get('forgetting_curve', [])[:limit]})

@app.route("/api/stats")
def get_stats():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    conn = db.get_connection()
    cursor = conn.cursor()
    stats = {}
    try:
        cursor.execute("SELECT SUM(total_xp), SUM(streak_days) FROM user_progress WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        stats['total_xp'] = row[0] or 0
        stats['streak_days'] = row[1] or 0

        cursor.execute("SELECT COUNT(*) FROM vocabulary WHERE user_id=?", (user_id,))
        stats['words_learned'] = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COALESCE(SUM(duration_seconds), 0) FROM learning_sessions WHERE user_id=? AND session_date >= date('now', '-7 days')", (user_id,))
        total_secs = cursor.fetchone()[0]
        stats['practice_hours'] = round(total_secs / 3600, 1) if total_secs else 0

        stats['due_words_today'] = srs_manager.get_due_count(user_id)
    except Exception as e:
        stats = {'total_xp': 0, 'streak_days': 0, 'words_learned': 0, 'practice_hours': 0, 'due_words_today': 0}
    finally:
        conn.close()
    return jsonify({"stats": stats})

@app.route("/api/validate_word_manual")
def validate_manual():
    user_id = get_current_user_id()
    word = request.args.get("word")
    lang = request.args.get("lang", "en")
    if user_id and word:
        res = word_validator.validate_and_store_word(user_id, word, lang)
        # Expand vocabulary for validated word
        if res and res.get('is_valid'):
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM vocabulary WHERE user_id = ? AND word = ? AND language = ?",
                               (user_id, word.lower(), lang))
                row = cursor.fetchone()
                conn.close()
                if row:
                    vocabulary_engine.expand_vocabulary(user_id, row[0])
            except Exception as e:
                print(f"[VOCAB] Expansion error on validate: {e}")
        return jsonify(res)
    return jsonify({"error": "Missing params"})

@app.route("/api/get_my_spoken_words")
def get_my_spoken_words():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    words = word_validator.get_user_words(user_id)
    return jsonify(words)

@app.route("/api/get_vocabulary_bank_full")
def get_vocab_bank_full():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    words = word_validator.get_user_words(user_id)
    # Enrich with topic data
    conn = db.get_connection()
    cursor = conn.cursor()
    for w in words:
        wid = w.get('id')
        if wid:
            cursor.execute("SELECT topic FROM word_topics WHERE word_id = ?", (wid,))
            row = cursor.fetchone()
            w['topic'] = row[0] if row else None
    conn.close()
    return jsonify(words)

@app.route("/api/get_oov_words")
def get_oov_words_route():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    oov_words = chatbot.get_oov_words(user_id)
    return jsonify(oov_words)
@app.route("/validate_word")
def validate_word_route():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    word = request.args.get("word")
    lang = request.args.get("lang", "en")
    
    if user_id and word:
        res = word_validator.validate_and_store_word(user_id, word, lang)
        return jsonify(res)
    return jsonify({"error": "Missing params"})

@app.route("/api/auto_generate_vocab")
def auto_gen_vocab():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Not logged in"}), 401
    
    import random
    
    # Get language from query parameter, default to English
    lang = request.args.get('lang', 'en')
    
    # Get user's existing vocabulary to avoid duplicates
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT word, meaning FROM vocabulary WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    existing_words = set()
    for word, meaning in rows:
        if word: existing_words.add(word.lower())
        if meaning:
            simple_meaning = meaning.split('|')[0].split('(')[0].strip().lower()
            if len(simple_meaning) < 20: existing_words.add(simple_meaning)
    conn.close()
    
    # Load offline vocabulary for the language
    offline_vocab = chatbot.load_offline_vocab(lang)
    if not offline_vocab:
        return jsonify([])
    
    # Collect all words from all levels
    all_words = []
    for level, words in offline_vocab.items():
        all_words.extend(words)
    
    # Filter out words user already has
    available_words = [w for w in all_words if w.lower() not in existing_words]
    
    # If all words are learned, reset and use all words
    if not available_words:
        available_words = all_words
    
    # Generate 1-N new words based on count param
    try:
        count_param = int(request.args.get('count', 1))
    except (ValueError, TypeError):
        count_param = 1
        
    num_words = min(count_param, len(available_words))
    selected_words = random.sample(available_words, num_words)
    
    new_suggestions = []
    for word in selected_words:
        # Validate and store the word
        res = word_validator.validate_and_store_word(user_id, word, lang)
        new_suggestions.append({
            "word": word,
            "language": lang,
            "source": "Incremental Learning",
            "meaning": res.get('meaning') or None
        })
    
    return jsonify(new_suggestions)

@app.route("/api/ai_tutor_chat", methods=["POST"])
def ai_tutor_chat():
    """AI Tutor chat endpoint"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        message = data.get('message')
        base_language = data.get('base_language')
        target_language = data.get('target_language')
        history = data.get('history', [])
        
        from ai_tutor_service import get_ai_tutor_response
        
        # Get weak words to encourage their use in conversation
        user_id = get_current_user_id()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT word FROM vocabulary 
            WHERE user_id = ? AND language = ? AND mastery_level < 3
            LIMIT 5
        """, (user_id, target_language))
        weak_words = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        reply = get_ai_tutor_response(message, base_language, target_language, history, weak_words=weak_words)
        
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"[API] AI Tutor error: {e}")
        return jsonify({"error": str(e)}), 500
@app.route("/api/ai_voice_phrase", methods=["POST"])
def ai_voice_phrase():
    """Get a practice phrase from AI"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        base_language = data.get('base_language')
        target_language = data.get('target_language')
        
        user_id = get_current_user_id()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all words for this user/language to decide what to practice vs exclude
        cursor.execute("""
            SELECT word, meaning, mastery_level, last_practiced 
            FROM vocabulary 
            WHERE user_id=? AND language=?
            ORDER BY mastery_level ASC, last_practiced ASC
        """, (user_id, target_language))
        vocab_rows = cursor.fetchall()
        
        # Strategy: 
        # 1. Focus on words with low mastery or long time since practice
        # 2. Exclude words that are already mastered (>80% or level 5)
        
        focus_word = None
        excludeset = set()
        
        # Candidate words for focus (mastery < 5)
        candidates = [r[0] for r in vocab_rows if r[2] < 5]
        
        if candidates:
            import random
            # Pick from the bottom half of mastered words or just random from candidates
            focus_word = random.choice(candidates[:10] if len(candidates) > 10 else candidates)
        
        # Also exclude very mastered concepts from the phrase logic to keep variety
        for word, meaning, mastery, last_p in vocab_rows:
            if word: 
                # If it's the focus word, don't exclude it!
                if focus_word and word.lower() == focus_word.lower():
                    continue
                # Exclude if mastered or just to keep things fresh
                if mastery >= 4:
                    excludeset.add(word.lower())
            
            if meaning:
                simple_meaning = meaning.split('|')[0].split('(')[0].strip().lower()
                if len(simple_meaning) < 20: 
                    # Only exclude if not related to focus word
                    excludeset.add(simple_meaning)
        
        exclude = list(excludeset)
        conn.close()
        
        from ai_tutor_service import get_practice_phrase
        phrase_data = get_practice_phrase(base_language, target_language, exclude=exclude, focus_word=focus_word)
        
        # Add focus word and ID to response so we can track practice success
        phrase_data['focus_word'] = focus_word
        
        return jsonify(phrase_data)
    except Exception as e:
        print(f"[API] AI Voice error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai_check_pronunciation", methods=["POST"])
def ai_check_pronunciation():
    """Check user's pronunciation"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        expected = data.get('expected')
        actual = data.get('actual')
        language = data.get('language')
        focus_word = data.get('focus_word') # Optional focused vocabulary word
        
        from ai_tutor_service import check_pronunciation
        result = check_pronunciation(expected, actual, language)
        
        # If correct and we have a focus_word, update vocabulary stats
        if result.get('correct') and focus_word:
            user_id = get_current_user_id()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Update last_practiced, frequency and correct_attempts
            # If multiple correct attempts, increase mastery
            cursor.execute("""
                UPDATE vocabulary 
                SET last_practiced = CURRENT_TIMESTAMP,
                    frequency = frequency + 1,
                    correct_attempts = correct_attempts + 1
                WHERE user_id = ? AND word = ? AND language = ?
            """, (user_id, focus_word, language))
            
            # Logic: If correct_attempts > 3 AND frequency > 5 (or similar), increment mastery_level
            cursor.execute("""
                UPDATE vocabulary
                SET mastery_level = MIN(5, mastery_level + 1)
                WHERE user_id = ? AND word = ? AND language = ?
                  AND (correct_attempts * 1.0 / frequency) > 0.8
            """, (user_id, focus_word, language))
            
            conn.commit()
            conn.close()
            print(f"[PREFORMANCE] Updated mastery for '{focus_word}' after AI practice")
            
        return jsonify(result)
    except Exception as e:
        print(f"[API] Pronunciation check error: {e}")
        return jsonify({"error": str(e)}), 500
@app.route("/api/get_level_quiz", methods=["POST"])
def get_level_quiz():
    """Generate quiz questions for a specific level using OpenAI"""
    if not is_logged_in():
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        data = request.get_json()
        level_id = data.get('level_id', 1)
        user_id = get_current_user_id()
        
        # Get target language
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT target_language FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        target_language = row[0] if row and row[0] else 'es'
        conn.close()
        
        from level_generator import level_generator
        from ai_tutor_service import generate_quiz_questions
        
        # Try to get words from session to ensure quiz matches flashcards
        words = session.get(f'level_{level_id}_words')
        
        # Get level metadata
        metadata = level_generator.get_level_metadata(level_id)
        
        # Generate questions using OpenAI
        questions = generate_quiz_questions(level_id, metadata['tier'], target_language, words)
        
        return jsonify({"questions": questions})
    except Exception as e:
        print(f"[API] Quiz generation error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== OOV / VALIDATION ====================

@app.route("/api/check_grammar")
def check_grammar():
    """Check grammar using LanguageTool API"""
    from api_service import api_service
    
    text = request.args.get("text", "")
    language = request.args.get("lang", "en")
    
    if not text:
        return jsonify({"error": "No text provided"})
    
    result = api_service.check_grammar(text, language)
    return jsonify(result)

@app.route("/api/get_word_info")
def get_word_info():
    """Get enhanced word information"""
    from api_service import api_service
    
    word = request.args.get("word", "")
    language = request.args.get("lang", "en")
    
    if not word:
        return jsonify({"error": "No word provided"})
    
    info = api_service.get_enhanced_word_info(word, language)
    return jsonify(info)

@app.route("/api/get_similar_words")
def get_similar_words():
    """Get similar words using Datamuse API"""
    from api_service import api_service
    
    word = request.args.get("word", "")
    
    if not word:
        return jsonify({"error": "No word provided"})
    
    similar = api_service.get_similar_words(word, max_results=10)
    return jsonify({"similar_words": similar})

@app.route("/api/chat_response", methods=["POST"])
def chat_response():
    """Get AI response for the Tutor"""
    data = request.json
    user_text = data.get("text", "")
    language = data.get("language", "en")
    
    if not user_text:
        return jsonify({"response": "", "correction": None})
        
    result = conversation_engine.get_response(user_text, language)
    return jsonify(result)

# --- SQL Training ---
@app.route("/sql-training")
def sql_training():
    if not is_logged_in(): return redirect("/login")
    user_name = session.get("user_name", "User")
    return render_template("sql_training.html", user_name=user_name)

# --- Audio Serving ---
from flask import send_from_directory
@app.route('/audio_clips/<path:filename>')
def serve_audio(filename):
    return send_from_directory('audio_clips', filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=True)
