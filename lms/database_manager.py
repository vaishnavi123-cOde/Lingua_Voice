import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = os.environ.get("DB_NAME", "linguavoice.db")

class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def init_db(self):
        # Create directory if it doesn't exist (useful for persistent volumes like /app/data)
        db_dir = os.path.dirname(self.db_name)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                target_language TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Transcripts Table (Linked to User)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp TEXT,
                language TEXT,
                text TEXT,
                audio_file TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 3. Vocabulary / Words Table (Consolidates validated_words & user_vocabulary)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                language TEXT,
                meaning TEXT,
                is_valid INTEGER DEFAULT 0,
                mastery_level INTEGER DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_practiced TIMESTAMP,
                frequency INTEGER DEFAULT 1,
                source_context TEXT,
                correct_attempts INTEGER DEFAULT 0,
                incorrect_attempts INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, word, language)
            )
        """)

    # ... (existing imports will be handled by context if I don't touch them, but since I need 'json', checking the top is better. The tool replaces blocks by line numbers)

    # 4. Learning Sessions / Stats (Keep existing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_date DATE,
                language TEXT,
                words_learned INTEGER DEFAULT 0,
                xp_earned INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # -- SRS migration: add columns safely
        for col, col_def in [
            ('next_review', 'DATE'),
            ('review_interval', 'INTEGER DEFAULT 1'),
            ('ease_factor', 'REAL DEFAULT 2.5'),
            ('review_count', 'INTEGER DEFAULT 0')
        ]:
            try:
                cursor.execute(f"ALTER TABLE vocabulary ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError:
                pass  # column already exists

        # 9. SRS Analytics (review tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS srs_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word_id INTEGER,
                word TEXT,
                language TEXT,
                review_date DATE DEFAULT CURRENT_DATE,
                is_correct BOOLEAN,
                response_time_ms INTEGER DEFAULT 0,
                ease_factor_before REAL,
                ease_factor_after REAL,
                interval_before INTEGER,
                interval_after INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (word_id) REFERENCES vocabulary (id)
            )
        """)

        # 10. SRS Daily Summary (for analytics dashboard)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS srs_daily_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE DEFAULT CURRENT_DATE,
                reviews_completed INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                incorrect_count INTEGER DEFAULT 0,
                total_xp_earned INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, date)
            )
        """)

        # 11. Review Streaks (for combo tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_streaks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                language TEXT,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_review_date DATE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, language)
            )
        """)

        # 12. Achievements Catalog
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                icon TEXT,
                requirement_type TEXT,
                requirement_value INTEGER
            )
        """)

        # 13. User Achievements (earned badges)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                achievement_id INTEGER,
                earned_date DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (achievement_id) REFERENCES achievements (id),
                UNIQUE(user_id, achievement_id)
            )
        """)

        # 14. Review Analytics (detailed per-word performance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word_id INTEGER,
                word TEXT,
                language TEXT,
                total_reviews INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                incorrect_count INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                last_reviewed DATE,
                difficulty_score REAL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (word_id) REFERENCES vocabulary (id),
                UNIQUE(user_id, word_id)
            )
        """)

        # Add combo_count column to srs_daily_summary if not exists
        try:
            cursor.execute("ALTER TABLE srs_daily_summary ADD COLUMN combo_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # Seed achievements if empty
        cursor.execute("SELECT COUNT(*) FROM achievements")
        if cursor.fetchone()[0] == 0:
            achievements_data = [
                ('First Review', 'Complete your first review', '🌟', 'total_reviews', 1),
                ('Dedicated Learner', 'Complete 10 reviews', '🔥', 'total_reviews', 10),
                ('Word Collector', 'Complete 50 reviews', '📚', 'total_reviews', 50),
                ('Centurion', 'Complete 100 reviews', '💪', 'total_reviews', 100),
                ('Week Warrior', '7-day review streak', '📅', 'streak_days', 7),
                ('Month Master', '30-day review streak', '👑', 'streak_days', 30),
                ('Perfect Session', 'Get 100% accuracy in a session (10+ reviews)', '✨', 'perfect_session', 1),
                ('Combo King', 'Get a 10-word combo streak', '🔥', 'combo_streak', 10),
                ('Speed Demon', 'Average response time under 3 seconds', '⚡', 'speed_demon', 1),
                ('Vocabulary Master', 'Master 50 words (mastery level 5)', '🏆', 'mastered_words', 50),
            ]
            cursor.executemany(
                "INSERT INTO achievements (name, description, icon, requirement_type, requirement_value) VALUES (?, ?, ?, ?, ?)",
                achievements_data
            )

        # 15. Vocabulary Knowledge Graph (word relations)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word_id_1 INTEGER,
                word_id_2 INTEGER,
                relation_type TEXT,
                strength REAL DEFAULT 0.5,
                difficulty_level INTEGER DEFAULT 1,
                created_date DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (word_id_1) REFERENCES vocabulary (id),
                FOREIGN KEY (word_id_2) REFERENCES vocabulary (id),
                UNIQUE(user_id, word_id_1, word_id_2, relation_type)
            )
        """)

        # 16. Word Topics / Categories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS word_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER,
                topic TEXT,
                FOREIGN KEY (word_id) REFERENCES vocabulary (id),
                UNIQUE(word_id)
            )
        """)

        # 17. Vocabulary Discovery Queue (AI-generated suggestions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary_discovery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                language TEXT,
                meaning TEXT,
                source_word TEXT,
                difficulty_level INTEGER DEFAULT 1,
                relation_type TEXT,
                topic TEXT DEFAULT 'General',
                viewed INTEGER DEFAULT 0,
                created_date DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 5. User Global Progress (Keep existing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                language TEXT,
                total_xp INTEGER DEFAULT 0,
                current_level TEXT DEFAULT 'Beginner',
                streak_days INTEGER DEFAULT 0,
                last_activity DATE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, language)
            )
        """)

        # 6. OOV Words
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oov_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                word TEXT,
                language TEXT,
                first_seen DATE,
                last_seen DATE,
                occurrences INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, word, language)
            )
        """)

        # NEW: User Completed Levels (Content Map 1-100)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_completed_levels (
                user_id INTEGER, 
                level_id INTEGER, 
                xp_earned INTEGER, 
                score INTEGER, 
                passed BOOLEAN, 
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                PRIMARY KEY (user_id, level_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # 7. Performance Analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                language TEXT,
                word TEXT,
                lesson_type TEXT,
                response_time REAL,
                is_correct BOOLEAN,
                timestamp DATETIME,
                difficulty_level TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        # -- Performance indexes for hot query paths
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocabulary_user_language ON vocabulary(user_id, language)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocabulary_user_review ON vocabulary(user_id, next_review)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_user ON transcripts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_srs_reviews_user_word ON srs_reviews(user_id, word_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_relations_u1 ON vocabulary_relations(user_id, word_id_1)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_relations_u2 ON vocabulary_relations(user_id, word_id_2)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_learning_sessions_user_date ON learning_sessions(user_id, session_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_progress(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_review_analytics_user_word ON review_analytics(user_id, word_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocab_discovery_user_viewed ON vocabulary_discovery(user_id, viewed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_word_topics_word ON word_topics(word_id)")

        # 18. Learner Daily Plans (cached intelligence engine output)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learner_daily_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_date DATE,
                review_words TEXT,
                new_words TEXT,
                focus_skills TEXT,
                goals TEXT,
                insights TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, plan_date)
            )
        """)

        # 8. Lessons
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                language TEXT,
                level TEXT,
                section INTEGER,
                lesson_type TEXT,
                content TEXT,
                difficulty_score INTEGER DEFAULT 1
            )
        """)
        
        # Populate initial lessons if empty
        cursor.execute("SELECT COUNT(*) FROM lessons")
        if cursor.fetchone()[0] == 0:
            import json
            lessons_data = [
                ('en', 'beginner', 1, 'vocabulary', json.dumps({
                    'title': 'Basic Greetings',
                    'words': ['hello', 'goodbye', 'please', 'thank you'],
                    'exercises': [
                        {'type': 'match', 'pairs': [['hello', 'hola'], ['goodbye', 'adiós']]},
                        {'type': 'listen_repeat', 'audio_prompts': ['hello', 'goodbye']},
                        {'type': 'translate', 'sentences': ['Hello, how are you?']}
                    ]
                }), 1),
                ('en', 'intermediate', 2, 'grammar', json.dumps({
                    'title': 'Present Perfect Tense',
                    'concepts': ['have/has + past participle'],
                    'examples': ['I have eaten', 'She has worked'],
                    'exercises': [
                        {'type': 'fill_blank', 'sentence': 'I ___ (eat) breakfast', 'answer': 'have eaten'},
                        {'type': 'correct_mistake', 'wrong': 'I have ate', 'correct': 'I have eaten'}
                    ]
                }), 3),
                ('es', 'beginner', 1, 'vocabulary', json.dumps({
                    'title': 'Saludos Básicos',
                    'words': ['hola', 'adiós', 'por favor', 'gracias'],
                    'exercises': [
                        {'type': 'match', 'pairs': [['hola', 'hello'], ['adiós', 'goodbye']]},
                        {'type': 'pronunciation', 'words': ['hola', 'gracias']}
                    ]
                }), 1),
            ]
            cursor.executemany(
                "INSERT INTO lessons (language, level, section, lesson_type, content, difficulty_score) VALUES (?, ?, ?, ?, ?, ?)",
                lessons_data
            )

        # -- FK integrity cleanup: remove orphaned records
        cursor.execute("DELETE FROM transcripts WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM vocabulary WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM srs_reviews WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM srs_reviews WHERE word_id IS NOT NULL AND word_id NOT IN (SELECT id FROM vocabulary)")
        cursor.execute("DELETE FROM srs_daily_summary WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM review_streaks WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM user_achievements WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM user_achievements WHERE achievement_id IS NOT NULL AND achievement_id NOT IN (SELECT id FROM achievements)")
        cursor.execute("DELETE FROM vocabulary_relations WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM vocabulary_relations WHERE word_id_1 IS NOT NULL AND word_id_1 NOT IN (SELECT id FROM vocabulary)")
        cursor.execute("DELETE FROM vocabulary_relations WHERE word_id_2 IS NOT NULL AND word_id_2 NOT IN (SELECT id FROM vocabulary)")
        cursor.execute("DELETE FROM word_topics WHERE word_id IS NOT NULL AND word_id NOT IN (SELECT id FROM vocabulary)")
        cursor.execute("DELETE FROM vocabulary_discovery WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM learning_sessions WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM user_progress WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM oov_words WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM user_completed_levels WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM review_analytics WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users)")
        cursor.execute("DELETE FROM review_analytics WHERE word_id IS NOT NULL AND word_id NOT IN (SELECT id FROM vocabulary)")

        conn.commit()
        conn.close()

    # --- User Management Methods ---
    def register_user(self, email, password, name, target_language="es"):
        conn = self.get_connection()
        try:
            # Use pbkdf2:sha256 for compatibility with environments that lack hashlib.scrypt
            password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
            conn.execute("INSERT INTO users (email, password_hash, name, target_language) VALUES (?, ?, ?, ?)", 
                         (email, password_hash, name, target_language))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def login_user(self, email, password):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Add target_language to selection
        try:
            cursor.execute("SELECT id, password_hash, name, target_language FROM users WHERE email=?", (email,))
        except sqlite3.OperationalError:
            cursor.execute("SELECT id, password_hash, name FROM users WHERE email=?", (email,))
            
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[1], password):
            lang = user[3] if len(user) > 3 else None
            return {"id": user[0], "name": user[2], "email": email, "target_language": lang}
        return None

    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, name, email, target_language FROM users WHERE id=?", (user_id,))
        except sqlite3.OperationalError:
             cursor.execute("SELECT id, name, email FROM users WHERE id=?", (user_id,))
             
        user = cursor.fetchone()
        conn.close()
        if user:
            lang = user[3] if len(user) > 3 else None
            return {"id": user[0], "name": user[1], "email": user[2], "target_language": lang}
        return None

db = DatabaseManager()
