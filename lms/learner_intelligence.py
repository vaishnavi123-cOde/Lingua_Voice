import json
import math
from datetime import datetime, date, timedelta
from database_manager import db

class LearnerIntelligenceEngine:
    FORGETTING_THRESHOLD = 0.6
    MAX_NEW_WORDS_PER_DAY = 10
    MIN_REVIEWS_PER_DAY = 5

    def __init__(self, user_id):
        self.user_id = user_id
        self._today = date.today()
        self._today_str = self._today.isoformat()

    def generate_daily_plan(self, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()

        words = self._load_words(cursor, language)
        if not words:
            conn.close()
            return self._empty_plan()

        profile = self._build_profile(cursor, language)
        forgetting = self._compute_forgetting_risk(words)
        weak_areas = self._analyze_weaknesses(cursor, words, language)
        graph_gaps = self._find_knowledge_gaps(cursor, words, language)
        goals = self._compute_daily_goals(profile, forgetting)
        reviews = self._prioritize_reviews(forgetting, weak_areas)
        new_words = self._recommend_new_words(graph_gaps, profile, language)
        insights = self._generate_insights(profile, forgetting, weak_areas)

        plan = {
            'date': self._today_str,
            'language': language or 'es',
            'goals': goals,
            'reviews': reviews[:goals.get('review_target', 20)],
            'new_words': new_words[:goals.get('new_word_target', 5)],
            'focus_skills': weak_areas['skills'],
            'forgetting_curve': [{'word': w['word'], 'retention': round(r, 3)} for w, r in forgetting[:10]],
            'weak_topics': weak_areas['topics'][:5],
            'streak_days': profile.get('streak_days', 0),
            'insights': insights,
        }

        self._cache_plan(conn, cursor, plan)
        conn.commit()
        conn.close()

        return plan

    def _empty_plan(self):
        return {
            'date': self._today_str,
            'language': 'es',
            'goals': {'review_target': 0, 'new_word_target': 0, 'practice_minutes': 5},
            'reviews': [],
            'new_words': [],
            'focus_skills': ['vocabulary'],
            'forgetting_curve': [],
            'weak_topics': [],
            'streak_days': 0,
            'insights': {'message': 'Learn your first words to get personalized recommendations!', 'level': 'info'},
        }

    def _load_words(self, cursor, language):
        params = [self.user_id]
        lang_clause = ''
        if language:
            lang_clause = 'AND v.language = ?'
            params.append(language)
        cursor.execute(f"""
            SELECT v.id, v.word, v.language, v.meaning, v.mastery_level,
                   v.review_interval, v.ease_factor, v.next_review,
                   v.review_count, v.correct_attempts, v.incorrect_attempts,
                   v.last_practiced, v.frequency,
                   COALESCE(ra.incorrect_count, 0) as total_incorrect,
                   COALESCE(ra.difficulty_score, 0) as difficulty,
                   COALESCE(ra.avg_response_time, 0) as avg_response,
                   (SELECT COUNT(*) FROM vocabulary_relations vr
                    WHERE (vr.word_id_1 = v.id OR vr.word_id_2 = v.id)
                    AND vr.user_id = v.user_id) as relation_count
            FROM vocabulary v
            LEFT JOIN review_analytics ra ON v.id = ra.word_id AND ra.user_id = v.user_id
            WHERE v.user_id = ? {lang_clause}
            ORDER BY v.last_practiced DESC
        """, params)
        cols = ['id', 'word', 'language', 'meaning', 'mastery_level',
                'review_interval', 'ease_factor', 'next_review',
                'review_count', 'correct_attempts', 'incorrect_attempts',
                'last_practiced', 'frequency',
                'total_incorrect', 'difficulty', 'avg_response', 'relation_count']
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _build_profile(self, cursor, language):
        cursor.execute("""
            SELECT COALESCE(SUM(total_xp), 0) FROM user_progress WHERE user_id=?
        """, (self.user_id,))
        total_xp = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT COALESCE(SUM(xp_earned), 0) FROM user_completed_levels WHERE user_id=? AND passed=1
        """, (self.user_id,))
        level_xp = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT streak_days FROM user_progress WHERE user_id=? ORDER BY last_activity DESC LIMIT 1
        """, (self.user_id,))
        row = cursor.fetchone()
        streak_days = row[0] if row else 0

        cursor.execute("""
            SELECT COUNT(*) FROM vocabulary WHERE user_id=?
        """, (self.user_id,))
        total_words = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM vocabulary WHERE user_id=? AND mastery_level >= 4
        """, (self.user_id,))
        mastered_words = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM learning_sessions WHERE user_id=?
        """, (self.user_id,))
        total_sessions = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(duration_seconds), 0) FROM learning_sessions WHERE user_id=?
        """, (self.user_id,))
        total_seconds = cursor.fetchone()[0]

        return {
            'total_xp': total_xp + level_xp,
            'streak_days': streak_days,
            'total_words': total_words,
            'mastered_words': mastered_words,
            'total_sessions': total_sessions,
            'total_practice_hours': round(total_seconds / 3600, 1),
        }

    def _compute_forgetting_risk(self, words):
        scored = []
        for w in words:
            retention = self._estimate_retention(w)
            max_mastery = w['mastery_level'] or 0
            overdue = 0
            if w['next_review']:
                try:
                    nxt = datetime.strptime(w['next_review'], '%Y-%m-%d').date()
                    overdue = (self._today - nxt).days
                except (ValueError, TypeError):
                    overdue = 0

            if overdue > 0:
                risk = 100 + overdue * 15
            elif retention < self.FORGETTING_THRESHOLD:
                risk = 80 + (1 - retention / self.FORGETTING_THRESHOLD) * 20
            else:
                risk = max(0, (1 - retention) * 100)

            if max_mastery < 2:
                risk *= 2.0
            elif max_mastery < 4:
                risk *= 1.3

            if w['total_incorrect'] > w['correct_attempts'] and w['correct_attempts'] > 0:
                risk *= 1.5

            days_since = 999
            if w['last_practiced']:
                try:
                    lp = datetime.strptime(w['last_practiced'][:10], '%Y-%m-%d').date()
                    days_since = (self._today - lp).days
                except (ValueError, TypeError):
                    pass
            if days_since > 30:
                risk *= 1.2

            relation_boost = 1 + (w['relation_count'] or 0) * 0.05
            risk *= relation_boost

            scored.append((w, min(risk, 999)))

        scored.sort(key=lambda x: -x[1])
        return scored

    def _estimate_retention(self, word):
        ease = word['ease_factor'] or 2.5
        interval = word['review_interval'] or 1

        stability = interval * (ease - 1)
        if stability <= 0:
            stability = 1

        days_since = 999
        if word['last_practiced']:
            try:
                lp = datetime.strptime(word['last_practiced'][:10], '%Y-%m-%d').date()
                days_since = (self._today - lp).days
            except (ValueError, TypeError):
                pass

        retention = math.exp(-days_since / stability) if stability > 0 else 0
        return max(0, min(1, retention))

    def _analyze_weaknesses(self, cursor, words, language):
        topic_errors = {}
        for w in words:
            cursor.execute("SELECT topic FROM word_topics WHERE word_id=?", (w['id'],))
            row = cursor.fetchone()
            topic = row[0] if row else 'General'
            if topic not in topic_errors:
                topic_errors[topic] = {'total': 0, 'incorrect': 0, 'avg_time': 0, 'count': 0}
            t = topic_errors[topic]
            t['total'] += 1
            t['incorrect'] += w['total_incorrect'] or 0
            t['avg_time'] += w['avg_response'] or 0
            t['count'] += 1

        topics = []
        for topic, data in topic_errors.items():
            error_rate = data['incorrect'] / max(data['total'], 1)
            avg_time = data['avg_time'] / max(data['count'], 1)
            topics.append({
                'topic': topic, 'word_count': data['total'],
                'error_rate': round(error_rate, 3),
                'avg_response_ms': round(avg_time),
            })
        topics.sort(key=lambda t: -t['error_rate'])

        slow_words = [w for w in words if w['avg_response'] and w['avg_response'] > 5000 and w['mastery_level'] < 3]
        high_error_words = [w for w in words if w['total_incorrect'] > max(w['correct_attempts'], 1)]

        weak_skills = []
        if any(w['total_incorrect'] > w['correct_attempts'] * 1.5 for w in words if w['correct_attempts'] > 2):
            weak_skills.append('recall')
        if any(w['avg_response'] and w['avg_response'] > 8000 for w in words):
            weak_skills.append('processing_speed')
        if len(slow_words) > len(words) * 0.3:
            weak_skills.append('fluency')
        if not weak_skills:
            weak_skills.append('vocabulary')

        return {
            'topics': topics,
            'slow_words': [{'word': w['word'], 'avg_response_ms': w['avg_response']} for w in slow_words[:5]],
            'high_error_words': [{'word': w['word'], 'errors': w['total_incorrect']} for w in high_error_words[:5]],
            'skills': weak_skills,
        }

    def _find_knowledge_gaps(self, cursor, words, language):
        mastered_ids = [w['id'] for w in words if (w['mastery_level'] or 0) >= 4]
        if not mastered_ids:
            return []

        placeholders = ','.join(['?'] * len(mastered_ids))
        cursor.execute(f"""
            SELECT v.id, v.word, v.language, v.meaning, v.mastery_level,
                   vr.relation_type, vr.strength, vr.word_id_1, vr.word_id_2
            FROM vocabulary_relations vr
            JOIN vocabulary v ON (v.id = CASE WHEN vr.word_id_1 IN ({placeholders}) THEN vr.word_id_2 ELSE vr.word_id_1 END)
            WHERE vr.user_id = ? AND (vr.word_id_1 IN ({placeholders}) OR vr.word_id_2 IN ({placeholders}))
              AND v.mastery_level < 3
            ORDER BY vr.strength DESC
            LIMIT 30
        """, mastered_ids + [self.user_id] + mastered_ids)

        cols = ['id', 'word', 'language', 'meaning', 'mastery_level',
                'relation_type', 'strength', 'word_id_1', 'word_id_2']
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def _compute_daily_goals(self, profile, forgetting):
        urgent_count = sum(1 for _, risk in forgetting if risk >= 80)
        due_today = sum(1 for _, risk in forgetting if risk >= 50)

        review_target = max(self.MIN_REVIEWS_PER_DAY, min(due_today + 5, 30))
        if urgent_count > 10:
            review_target = min(urgent_count + 5, 30)

        avg_daily_words = max(1, profile['total_words'] // max(profile['total_sessions'], 1) if profile['total_sessions'] > 0 else 3)
        new_word_target = min(avg_daily_words, self.MAX_NEW_WORDS_PER_DAY)
        if urgent_count > 15:
            new_word_target = max(1, new_word_target // 2)

        practice_minutes = max(5, min(profile.get('total_practice_hours', 0) * 10, 30))

        return {
            'review_target': review_target,
            'new_word_target': new_word_target,
            'practice_minutes': int(practice_minutes),
            'urgent_words': urgent_count,
        }

    def _prioritize_reviews(self, forgetting, weak_areas):
        reviews = []
        weak_words_set = {w['word'] for w in weak_areas.get('high_error_words', [])}
        slow_words_set = {w['word'] for w in weak_areas.get('slow_words', [])}

        for w, risk in forgetting:
            priority = 'critical' if risk >= 80 else 'high' if risk >= 50 else 'normal' if risk >= 20 else 'low'
            reason = []
            if risk >= 80:
                reason.append('overdue')
            if w['word'] in weak_words_set:
                reason.append('high_error_rate')
            if w['word'] in slow_words_set:
                reason.append('slow_response')
            if (w['mastery_level'] or 0) < 2:
                reason.append('new_word')
            if not reason:
                reason.append('scheduled')

            reviews.append({
                'word_id': w['id'],
                'word': w['word'],
                'language': w['language'],
                'meaning': w['meaning'],
                'mastery_level': w['mastery_level'],
                'forgetting_risk': round(risk, 1),
                'priority': priority,
                'reasons': reason,
                'retention': round(self._estimate_retention(w), 3),
            })

        reviews.sort(key=lambda r: (
            {'critical': 0, 'high': 1, 'normal': 2, 'low': 3}[r['priority']],
            -r['forgetting_risk'],
        ))
        return reviews

    def _recommend_new_words(self, graph_gaps, profile, language):
        if not graph_gaps:
            return []
        seen = set()
        recommendations = []
        for gap in graph_gaps:
            if gap['word'] in seen:
                continue
            seen.add(gap['word'])
            recommendations.append({
                'word': gap['word'],
                'language': gap['language'],
                'meaning': gap['meaning'],
                'relation_type': gap['relation_type'],
                'source': 'knowledge_graph',
            })
        return recommendations

    def _generate_insights(self, profile, forgetting, weak_areas):
        insights = []
        urgent = sum(1 for _, r in forgetting if r >= 80)
        if urgent > 10:
            insights.append({'message': f'{urgent} words are overdue. Prioritize review today.', 'level': 'warning'})
        elif urgent == 0 and profile['total_words'] > 0:
            insights.append({'message': 'All caught up! Great consistency.', 'level': 'success'})

        high_error_topics = [t for t in weak_areas['topics'] if t['error_rate'] > 0.3]
        if high_error_topics:
            topics_str = ', '.join(t['topic'] for t in high_error_topics[:3])
            insights.append({'message': f'Focus on {topics_str} — highest error rates.', 'level': 'info'})

        if profile['total_words'] > 0:
            mastery_pct = round(profile['mastered_words'] / profile['total_words'] * 100)
            insights.append({'message': f'You have mastered {mastery_pct}% of your vocabulary.', 'level': 'success'})

        if profile['streak_days'] > 0:
            insights.append({'message': f'{profile["streak_days"]}-day streak! Keep it going.', 'level': 'motivation'})

        if profile['total_practice_hours'] > 0:
            insights.append({'message': f'{profile["total_practice_hours"]} hours of total practice.', 'level': 'info'})

        if not insights:
            insights.append({'message': 'Learn your first words to get started!', 'level': 'info'})

        return insights

    def _cache_plan(self, conn, cursor, plan):
        cursor.execute("""
            INSERT OR REPLACE INTO learner_daily_plans
                (user_id, plan_date, review_words, new_words, focus_skills, goals, insights)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            self.user_id,
            self._today_str,
            json.dumps([{
                'word_id': r['word_id'], 'word': r['word'],
                'priority': r['priority'], 'reasons': r['reasons'],
                'forgetting_risk': r['forgetting_risk'],
            } for r in plan['reviews']]),
            json.dumps([{
                'word': r['word'], 'language': r['language'],
                'meaning': r['meaning'], 'relation_type': r['relation_type'],
            } for r in plan['new_words']]),
            json.dumps(plan['focus_skills']),
            json.dumps(plan['goals']),
            json.dumps(plan['insights']),
        ))

    def get_cached_plan(self, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT review_words, new_words, focus_skills, goals, insights, created_at
            FROM learner_daily_plans
            WHERE user_id = ? AND plan_date = ?
            ORDER BY created_at DESC LIMIT 1
        """, (self.user_id, self._today_str))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                'reviews': json.loads(row[0]) if row[0] else [],
                'new_words': json.loads(row[1]) if row[1] else [],
                'focus_skills': json.loads(row[2]) if row[2] else [],
                'goals': json.loads(row[3]) if row[3] else {},
                'insights': json.loads(row[4]) if row[4] else [],
                'cached': True,
                'date': self._today_str,
            }
        return None


learner_intelligence = LearnerIntelligenceEngine
