from datetime import datetime, timedelta, date
from database_manager import db

class SRSManager:
    INITIAL_INTERVAL = 1
    INITIAL_EASE = 2.5
    MIN_EASE = 1.3
    MAX_INTERVAL = 365
    CORRECT_XP = 5
    BONUS_THRESHOLD = 10
    BONUS_XP = 25
    PERFECT_BONUS_XP = 15

    def _today_str(self):
        return date.today().isoformat()

    def _tomorrow_str(self):
        return (date.today() + timedelta(days=1)).isoformat()

    def _award_xp_impl(self, user_id, language, xp):
        conn = db.get_connection()
        cursor = conn.cursor()
        self._award_xp(cursor, user_id, language, xp)
        conn.commit()
        conn.close()

    def _schedule_initial(self, word_id):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vocabulary
            SET next_review = ?,
                review_interval = ?,
                ease_factor = ?,
                review_count = 0
            WHERE id = ?
        """, (self._tomorrow_str(), self.INITIAL_INTERVAL, self.INITIAL_EASE, word_id))
        conn.commit()
        conn.close()

    def schedule_new_word(self, word_id):
        self._schedule_initial(word_id)

    def handle_correct(self, word_id, response_time_ms=0):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT review_interval, ease_factor, review_count, mastery_level, user_id, language
            FROM vocabulary WHERE id = ?
        """, (word_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        interval, ease, count, mastery, user_id, lang = row
        if interval is None:
            interval = self.INITIAL_INTERVAL
        if ease is None:
            ease = self.INITIAL_EASE

        new_interval = min(int(interval * ease), self.MAX_INTERVAL)
        new_count = (count or 0) + 1
        new_mastery = min(5, (mastery or 0) + 1)
        new_ease = max(self.MIN_EASE, ease + 0.1)
        next_review = (date.today() + timedelta(days=new_interval)).isoformat()

        cursor.execute("""
            UPDATE vocabulary
            SET review_interval = ?, ease_factor = ?, review_count = ?,
                next_review = ?, mastery_level = ?, last_practiced = CURRENT_TIMESTAMP,
                correct_attempts = correct_attempts + 1
            WHERE id = ?
        """, (new_interval, new_ease, new_count, next_review, new_mastery, word_id))

        self._record_review(cursor, user_id, word_id, True, response_time_ms, ease, new_ease, interval, new_interval)

        # Track combo
        combo_info = self._update_combo(cursor, user_id, lang, True)
        current_combo = combo_info.get('current_streak', 0)

        # Award XP with combo bonus
        xp_awarded = self.CORRECT_XP
        if current_combo >= 5:
            xp_awarded += 2  # +2 for 5+ combo
        if current_combo >= 10:
            xp_awarded += 3  # +3 more for 10+ combo
        self._award_xp(cursor, user_id, lang, xp_awarded)

        # Original bonus at threshold
        bonus_awarded = 0
        if new_count > 0 and new_count % self.BONUS_THRESHOLD == 0:
            self._award_xp(cursor, user_id, lang, self.BONUS_XP)
            bonus_awarded = self.BONUS_XP

        # Update review analytics
        self._update_review_analytics(cursor, user_id, word_id, True, response_time_ms)

        conn.commit()
        conn.close()
        return {
            'xp': xp_awarded,
            'mastery': new_mastery,
            'interval': new_interval,
            'combo': current_combo,
            'bonus_xp': bonus_awarded,
            'total_xp': xp_awarded + bonus_awarded
        }

    def handle_incorrect(self, word_id, response_time_ms=0):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT review_interval, ease_factor, review_count, mastery_level, user_id, language
            FROM vocabulary WHERE id = ?
        """, (word_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        interval, ease, count, mastery, user_id, lang = row
        if ease is None:
            ease = self.INITIAL_EASE

        new_interval = 1
        new_ease = max(self.MIN_EASE, ease - 0.2)
        new_mastery = max(0, (mastery or 0) - 1)
        next_review = self._tomorrow_str()

        cursor.execute("""
            UPDATE vocabulary
            SET review_interval = ?, ease_factor = ?, next_review = ?,
                mastery_level = ?, last_practiced = CURRENT_TIMESTAMP,
                incorrect_attempts = incorrect_attempts + 1
            WHERE id = ?
        """, (new_interval, new_ease, next_review, new_mastery, word_id))

        self._record_review(cursor, user_id, word_id, False, response_time_ms, ease, new_ease, interval, new_interval)

        # Reset combo
        combo_info = self._update_combo(cursor, user_id, lang, False)

        # Update review analytics
        self._update_review_analytics(cursor, user_id, word_id, False, response_time_ms)

        conn.commit()
        conn.close()
        return {'mastery': new_mastery, 'interval': new_interval, 'combo': combo_info.get('current_streak', 0)}

    def _update_combo(self, cursor, user_id, language, is_correct):
        today = self._today_str()
        cursor.execute("""
            INSERT INTO review_streaks (user_id, language, current_streak, longest_streak, last_review_date)
            VALUES (?, ?, 0, 0, ?)
            ON CONFLICT(user_id, language) DO NOTHING
        """, (user_id, language, today))
        cursor.execute("""
            SELECT current_streak, longest_streak FROM review_streaks
            WHERE user_id = ? AND language = ?
        """, (user_id, language))
        row = cursor.fetchone()
        current = row[0] if row else 0
        longest = row[1] if row else 0

        if is_correct:
            current += 1
            if current > longest:
                longest = current
        else:
            current = 0

        cursor.execute("""
            UPDATE review_streaks
            SET current_streak = ?, longest_streak = ?, last_review_date = ?
            WHERE user_id = ? AND language = ?
        """, (current, longest, today, user_id, language))

        # Update daily summary combo_count
        cursor.execute("""
            UPDATE srs_daily_summary SET combo_count = ?
            WHERE user_id = ? AND date = ?
        """, (current, user_id, today))

        return {'current_streak': current, 'longest_streak': longest}

    def _update_review_analytics(self, cursor, user_id, word_id, is_correct, response_time_ms):
        cursor.execute("""
            SELECT word, language FROM vocabulary WHERE id = ?
        """, (word_id,))
        row = cursor.fetchone()
        if not row:
            return
        word, language = row

        cursor.execute("""
            INSERT INTO review_analytics (user_id, word_id, word, language, total_reviews, correct_count, incorrect_count, avg_response_time, last_reviewed)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(user_id, word_id) DO UPDATE SET
                total_reviews = total_reviews + 1,
                correct_count = correct_count + ?,
                incorrect_count = incorrect_count + ?,
                avg_response_time = (avg_response_time * (total_reviews - 1) + ?) / total_reviews,
                last_reviewed = ?,
                difficulty_score = CAST(incorrect_count AS REAL) / MAX(total_reviews, 1)
        """, (
            user_id, word_id, word, language,
            1 if is_correct else 0,
            0 if is_correct else 1,
            response_time_ms,
            self._today_str(),
            1 if is_correct else 0,
            0 if is_correct else 1,
            response_time_ms,
            self._today_str()
        ))

    def get_due_words(self, user_id, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()
        params = [user_id, self._today_str()]
        lang_filter = ""
        if language:
            lang_filter = "AND language=?"
            params.append(language)
        cursor.execute(f"""
            SELECT v.id, v.word, v.language, v.meaning, v.mastery_level, v.next_review,
                   v.review_interval, v.ease_factor, v.review_count,
                   COALESCE(ra.incorrect_count, 0) as incorrect_count,
                   COALESCE(ra.difficulty_score, 0) as difficulty_score
            FROM vocabulary v
            LEFT JOIN review_analytics ra ON v.id = ra.word_id AND ra.user_id = v.user_id
            WHERE v.user_id = ?
              AND (v.next_review IS NULL OR v.next_review <= ?)
              {lang_filter}
            ORDER BY
                CASE WHEN v.next_review IS NULL THEN 0 ELSE 1 END,
                difficulty_score DESC,
                v.ease_factor ASC,
                v.next_review ASC
        """, params)
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(r) for r in rows]

    def get_due_count(self, user_id, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()
        params = [user_id, self._today_str()]
        lang_filter = ""
        if language:
            lang_filter = "AND language=?"
            params.append(language)
        cursor.execute(f"""
            SELECT COUNT(*) FROM vocabulary
            WHERE user_id = ?
              AND (next_review IS NULL OR next_review <= ?)
              {lang_filter}
        """, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_srs_stats(self, user_id):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(reviews_completed), 0),
                   COALESCE(SUM(correct_count), 0),
                   COALESCE(SUM(incorrect_count), 0),
                   COALESCE(SUM(total_xp_earned), 0),
                   COALESCE(MAX(combo_count), 0)
            FROM srs_daily_summary WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        total_reviews, correct, incorrect, xp, max_combo = row
        accuracy = (correct / total_reviews * 100) if total_reviews > 0 else 0
        retention = accuracy
        conn.close()
        return {
            'total_reviews': total_reviews,
            'correct': correct,
            'incorrect': incorrect,
            'accuracy': round(accuracy, 1),
            'retention_rate': round(retention, 1),
            'xp_earned': xp,
            'max_combo': max_combo
        }

    def get_combo(self, user_id, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()
        params = [user_id]
        lang_filter = ""
        if language:
            lang_filter = "AND language = ?"
            params.append(language)
        cursor.execute(f"""
            SELECT current_streak, longest_streak FROM review_streaks
            WHERE user_id = ? {lang_filter}
        """, params)
        row = cursor.fetchone()
        conn.close()
        if row:
            return {'current_streak': row[0], 'longest_streak': row[1]}
        return {'current_streak': 0, 'longest_streak': 0}

    def get_achievements(self, user_id, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, a.name, a.description, a.icon, a.requirement_type, a.requirement_value,
                   CASE WHEN ua.id IS NOT NULL THEN 1 ELSE 0 END as earned,
                   ua.earned_date
            FROM achievements a
            LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
            ORDER BY a.id
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': r[0],
            'name': r[1],
            'description': r[2],
            'icon': r[3],
            'requirement_type': r[4],
            'requirement_value': r[5],
            'earned': bool(r[6]),
            'earned_date': r[7]
        } for r in rows]

    def check_achievements(self, user_id, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()
        new_achievements = []

        # Get user stats
        stats = self.get_srs_stats(user_id)
        combo = self.get_combo(user_id, language)

        # Get mastered words count
        cursor.execute("""
            SELECT COUNT(*) FROM vocabulary
            WHERE user_id = ? AND mastery_level >= 5
        """, (user_id,))
        mastered_count = cursor.fetchone()[0]

        # Check each unearned achievement
        cursor.execute("""
            SELECT a.id, a.name, a.description, a.icon, a.requirement_type, a.requirement_value
            FROM achievements a
            WHERE a.id NOT IN (
                SELECT achievement_id FROM user_achievements WHERE user_id = ?
            )
        """, (user_id,))
        for row in cursor.fetchall():
            aid, name, desc, icon, req_type, req_val = row
            earned = False
            if req_type == 'total_reviews' and stats['total_reviews'] >= req_val:
                earned = True
            elif req_type == 'streak_days':
                cursor.execute("SELECT streak_days FROM user_progress WHERE user_id = ? LIMIT 1", (user_id,))
                up = cursor.fetchone()
                if up and (up[0] or 0) >= req_val:
                    earned = True
            elif req_type == 'perfect_session':
                earned = False  # Checked separately via API
            elif req_type == 'combo_streak' and combo['current_streak'] >= req_val:
                earned = True
            elif req_type == 'speed_demon':
                cursor.execute("""
                    SELECT AVG(response_time_ms) FROM srs_reviews
                    WHERE user_id = ? AND review_date = ?
                """, (user_id, self._today_str()))
                avg_time = cursor.fetchone()[0]
                if avg_time and avg_time < 3000:
                    earned = True
            elif req_type == 'mastered_words' and mastered_count >= req_val:
                earned = True

            if earned:
                cursor.execute("""
                    INSERT INTO user_achievements (user_id, achievement_id)
                    VALUES (?, ?)
                """, (user_id, aid))
                new_achievements.append({'id': aid, 'name': name, 'icon': icon, 'description': desc})

        conn.commit()
        conn.close()
        return new_achievements

    def get_analytics(self, user_id):
        conn = db.get_connection()
        cursor = conn.cursor()

        # Weekly progress
        weekly = []
        for i in range(7, -1, -1):
            day = (date.today() - timedelta(days=i)).isoformat()
            cursor.execute("""
                SELECT COALESCE(SUM(reviews_completed), 0),
                       COALESCE(SUM(correct_count), 0),
                       COALESCE(SUM(total_xp_earned), 0)
                FROM srs_daily_summary
                WHERE user_id = ? AND date = ?
            """, (user_id, day))
            r = cursor.fetchone()
            weekly.append({
                'date': day,
                'reviews': r[0],
                'correct': r[1],
                'xp': r[2]
            })

        # Most difficult words (highest incorrect ratio)
        cursor.execute("""
            SELECT word, meaning, total_reviews, correct_count, incorrect_count,
                   CAST(incorrect_count AS REAL) / MAX(total_reviews, 1) as difficulty
            FROM review_analytics
            WHERE user_id = ? AND total_reviews >= 2
            ORDER BY difficulty DESC
            LIMIT 10
        """, (user_id,))
        difficult = [{
            'word': r[0],
            'meaning': r[1],
            'total': r[2],
            'correct': r[3],
            'incorrect': r[4],
            'difficulty': round(r[5] * 100, 1)
        } for r in cursor.fetchall()]

        # Most improved words
        cursor.execute("""
            SELECT v.word, v.meaning, v.mastery_level,
                   COALESCE(ra.incorrect_count, 0) as incorrect_count,
                   COALESCE(ra.difficulty_score, 0) as difficulty
            FROM vocabulary v
            LEFT JOIN review_analytics ra ON v.id = ra.word_id AND ra.user_id = v.user_id
            WHERE v.user_id = ? AND v.mastery_level >= 3 AND ra.total_reviews >= 2
            ORDER BY v.mastery_level DESC, difficulty ASC
            LIMIT 10
        """, (user_id,))
        improved = [{
            'word': r[0],
            'meaning': r[1],
            'mastery': r[2],
            'incorrect_count': r[3],
            'difficulty': round(r[4] * 100, 1)
        } for r in cursor.fetchall()]

        # Retention rate (overall)
        cursor.execute("""
            SELECT COALESCE(SUM(correct_count), 0), COALESCE(SUM(incorrect_count), 0)
            FROM srs_daily_summary WHERE user_id = ?
        """, (user_id,))
        total_correct, total_incorrect = cursor.fetchone()
        total_attempts = total_correct + total_incorrect
        retention = round(total_correct / total_attempts * 100, 1) if total_attempts > 0 else 0

        # Review consistency (days with reviews in past 7 days)
        consistency_days = sum(1 for d in weekly if d['reviews'] > 0)

        conn.close()
        return {
            'weekly': weekly,
            'difficult_words': difficult,
            'improved_words': improved,
            'retention_rate': retention,
            'consistency': consistency_days,
            'total_analytics': len(difficult) + len(improved)
        }

    def get_weak_words(self, user_id, limit=10, language=None):
        """Get words that need more practice - prioritized by difficulty score."""
        conn = db.get_connection()
        cursor = conn.cursor()
        params = [user_id]
        lang_filter = ""
        if language:
            lang_filter = "AND v.language = ?"
            params.append(language)
        cursor.execute(f"""
            SELECT v.id, v.word, v.language, v.meaning, v.mastery_level,
                   COALESCE(ra.incorrect_count, 0) as wrong_count,
                   COALESCE(ra.difficulty_score, 0) as difficulty
            FROM vocabulary v
            LEFT JOIN review_analytics ra ON v.id = ra.word_id AND ra.user_id = v.user_id
            WHERE v.user_id = ? AND v.mastery_level < 3 {lang_filter}
            ORDER BY difficulty DESC, v.mastery_level ASC
            LIMIT ?
        """, params + [limit])
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': r[0],
            'word': r[1],
            'language': r[2],
            'meaning': r[3],
            'mastery': r[4],
            'incorrect_count': r[5],
            'difficulty': round(r[6] * 100, 1)
        } for r in rows]

    def _record_review(self, cursor, user_id, word_id, is_correct, response_time_ms,
                       ef_before, ef_after, int_before, int_after):
        cursor.execute("""
            INSERT INTO srs_reviews
                (user_id, word_id, is_correct, response_time_ms,
                 ease_factor_before, ease_factor_after,
                 interval_before, interval_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, word_id, int(is_correct), response_time_ms,
              ef_before, ef_after, int_before, int_after))
        today = self._today_str()
        cursor.execute("""
            INSERT INTO srs_daily_summary (user_id, date, reviews_completed, correct_count, incorrect_count, total_xp_earned)
            VALUES (?, ?, 1, ?, ?, 0)
            ON CONFLICT(user_id, date) DO UPDATE SET
                reviews_completed = reviews_completed + 1,
                correct_count = correct_count + ?,
                incorrect_count = incorrect_count + ?
        """, (user_id, today, int(is_correct), int(not is_correct),
              int(is_correct), int(not is_correct)))

    def _award_xp(self, cursor, user_id, language, xp):
        today = self._today_str()
        cursor.execute("""
            INSERT INTO learning_sessions (user_id, session_date, language, xp_earned)
            VALUES (?, ?, ?, ?)
        """, (user_id, today, language, xp))
        cursor.execute("""
            INSERT INTO user_progress (user_id, language, total_xp, last_activity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, language) DO UPDATE SET
                total_xp = total_xp + ?,
                last_activity = ?
        """, (user_id, language, xp, today, xp, today))
        cursor.execute("""
            UPDATE srs_daily_summary SET total_xp_earned = total_xp_earned + ?
            WHERE user_id = ? AND date = ?
        """, (xp, user_id, today))

    def _row_to_dict(self, r):
        return {
            'id': r[0],
            'word': r[1],
            'language': r[2],
            'meaning': r[3],
            'mastery_level': r[4],
            'next_review': r[5],
            'review_interval': r[6],
            'ease_factor': r[7],
            'review_count': r[8]
        }

srs_manager = SRSManager()
