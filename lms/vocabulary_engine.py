"""
Incremental Vocabulary Learning Engine
Knowledge Graph, AI Recommendations, Topic Detection, Learning Paths
"""
import json
import random
import re
from datetime import datetime, date, timedelta
from database_manager import db
from srs_manager import srs_manager
from word_validator import is_placeholder

class VocabularyEngine:
    RELATION_TYPES = ['synonym', 'antonym', 'similar', 'associated', 'topic_related',
                      'advanced_form', 'simpler_form', 'compound', 'co_occurring']

    def __init__(self, openai_service=None, api_service=None):
        self.openai = openai_service
        self.api = api_service

    def _today(self):
        return date.today().isoformat()

    # ================================================================
    # KNOWLEDGE GRAPH
    # ================================================================

    def add_relation(self, user_id, word_id_1, word_id_2, relation_type, strength=0.5, difficulty_level=1):
        """Add an edge to the vocabulary knowledge graph."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO vocabulary_relations (user_id, word_id_1, word_id_2, relation_type, strength, difficulty_level)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, word_id_1, word_id_2, relation_type) DO UPDATE SET
                    strength = MAX(strength, ?),
                    difficulty_level = MIN(difficulty_level, ?)
            """, (user_id, word_id_1, word_id_2, relation_type, strength, difficulty_level,
                  strength, difficulty_level))
            conn.commit()
        except Exception as e:
            print(f"[VOCAB_ENGINE] Error adding relation: {e}")
        finally:
            conn.close()

    def get_related_words(self, user_id, word_id, limit=10):
        """Get all related words from the knowledge graph for a given word."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.id, v.word, v.language, v.meaning, v.mastery_level,
                   vr.relation_type, vr.strength, vr.difficulty_level
            FROM vocabulary_relations vr
            JOIN vocabulary v ON v.id = CASE WHEN vr.word_id_1 = ? THEN vr.word_id_2 ELSE vr.word_id_1 END
            WHERE (vr.word_id_1 = ? OR vr.word_id_2 = ?)
              AND vr.user_id = ?
            ORDER BY vr.strength DESC, vr.difficulty_level ASC
            LIMIT ?
        """, (word_id, word_id, word_id, user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': r[0],
            'word': r[1],
            'language': r[2],
            'meaning': r[3],
            'mastery_level': r[4],
            'relation_type': r[5],
            'strength': r[6],
            'difficulty_level': r[7]
        } for r in rows]

    def get_word_graph(self, user_id, language=None, depth=2):
        """Build a full knowledge graph for a user (adjacency list)."""
        conn = db.get_connection()
        cursor = conn.cursor()
        lang_filter = ""
        params = [user_id]
        if language:
            lang_filter = "AND v.language = ?"
            params.append(language)
        cursor.execute(f"""
            SELECT DISTINCT v.id, v.word, v.language, v.meaning, v.mastery_level
            FROM vocabulary v
            WHERE v.user_id = ? {lang_filter}
        """, params)
        words = [{'id': r[0], 'word': r[1], 'language': r[2], 'meaning': r[3], 'mastery_level': r[4]}
                 for r in cursor.fetchall()]

        word_map = {w['id']: w for w in words}
        for w in words:
            w['relations'] = []

        cursor.execute("""
            SELECT word_id_1, word_id_2, relation_type, strength, difficulty_level
            FROM vocabulary_relations
            WHERE user_id = ? AND (word_id_1 IN ({}) OR word_id_2 IN ({}))
        """.format(
            ','.join('?' * len(words)),
            ','.join('?' * (len(words) if words else 1))
        ), params + [w['id'] for w in words] + [w['id'] for w in words])

        for r in cursor.fetchall():
            w1, w2, rel_type, strength, diff = r
            if w1 in word_map:
                word_map[w1]['relations'].append({
                    'word_id': w2,
                    'word': word_map[w2]['word'] if w2 in word_map else 'unknown',
                    'relation_type': rel_type,
                    'strength': strength
                })
            if w2 in word_map:
                word_map[w2]['relations'].append({
                    'word_id': w1,
                    'word': word_map[w1]['word'] if w1 in word_map else 'unknown',
                    'relation_type': rel_type,
                    'strength': strength
                })

        conn.close()
        return words

    # ================================================================
    # TOPIC DETECTION
    # ================================================================

    def detect_topic(self, word, language='en'):
        """Detect the topic/category for a word using AI."""
        if not self.openai:
            return 'General'
        try:
            prompt = f"""Categorize the word "{word}" into ONE of these topics:
        Greetings, Numbers, Colors, Food, Animals, Travel, Weather, Family, Body, Clothing,
        Home, School, Work, Emotions, Nature, Sports, Music, Art, Science, Technology,
        Business, Health, Time, Places, Actions, Descriptions, Relationships, Hobbies,
        Shopping, Money, General

        Return ONLY the topic name, nothing else.
        Language: {language}"""
            resp = self.openai.generate_content(prompt)
            if resp and resp.text:
                topic = resp.text.strip().split('\n')[0].strip()
                if topic and len(topic) < 30:
                    return topic
            return 'General'
        except Exception as e:
            print(f"[VOCAB_ENGINE] Topic detection error: {e}")
            return 'General'

    def assign_topic(self, word_id, topic):
        """Assign a topic to a word."""
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO word_topics (word_id, topic) VALUES (?, ?)
                ON CONFLICT(word_id) DO UPDATE SET topic = ?
            """, (word_id, topic, topic))
            conn.commit()
        except Exception as e:
            print(f"[VOCAB_ENGINE] Topic assign error: {e}")
        finally:
            conn.close()

    def get_word_topic(self, word_id):
        """Get the topic for a word."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT topic FROM word_topics WHERE word_id = ?", (word_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_user_topics(self, user_id, language=None):
        """Get all topics and their word counts for a user."""
        conn = db.get_connection()
        cursor = conn.cursor()
        lang_filter = ""
        params = [user_id]
        if language:
            lang_filter = "AND v.language = ?"
            params.append(language)
        cursor.execute(f"""
            SELECT wt.topic, COUNT(*) as count, GROUP_CONCAT(v.word, ', ') as words
            FROM word_topics wt
            JOIN vocabulary v ON v.id = wt.word_id
            WHERE v.user_id = ? {lang_filter}
            GROUP BY wt.topic
            ORDER BY count DESC
        """, params)
        rows = cursor.fetchall()
        conn.close()
        return [{'topic': r[0], 'count': r[1], 'words': r[2].split(', ')} for r in rows]

    # ================================================================
    # AI WORD EXPANSION
    # ================================================================

    def generate_related_words(self, word, meaning, language='en', mastery_level=0):
        """Generate related words at appropriate difficulty levels using AI or API fallback."""
        # First try OpenAI
        if self.openai:
            try:
                diff_tier = 'beginner'
                if mastery_level >= 3:
                    diff_tier = 'intermediate'
                if mastery_level >= 5:
                    diff_tier = 'advanced'

                prompt = f"""Given the {language} word "{word}" (meaning: {meaning}), generate 7 related vocabulary words at 3 difficulty levels.

    Level 1 (Easy/beginner): 3 simpler or very common related words
    Level 2 (Intermediate): 2 moderately advanced related words
    Level 3 (Advanced): 2 advanced or nuanced related words

    For each word provide:
    - the word
    - brief meaning
    - relation type (synonym, antonym, similar, associated, topic_related, advanced_form, simpler_form)

    The current learner is at {diff_tier} level.

    Return ONLY valid JSON array:
    [
      {{"word": "...", "meaning": "...", "difficulty": 1, "relation": "synonym"}},
      ...
    ]
    """
                resp = self.openai.generate_content(prompt)
                if resp and resp.text:
                    text = resp.text.strip()
                    if text.startswith('```json'):
                        text = text[7:]
                    elif text.startswith('```'):
                        text = text[3:]
                    if text.endswith('```'):
                        text = text[:-3]
                    text = text.strip()
                    words = json.loads(text)
                    if isinstance(words, list) and len(words) > 0:
                        return words[:10]
            except Exception as e:
                print(f"[VOCAB_ENGINE] OpenAI generate error: {e}")

        # Hardcoded fallback for common words (works for any language)
        fallback_pairs = self._get_fallback_pairs()
        word_lower = word.lower()
        for key, words_list in fallback_pairs.items():
            if word_lower == key or word_lower in [w['word'] for w in words_list]:
                return words_list

        # Rule-based fallback: generate word families for unknown words
        result = self._generate_word_family(word, meaning, language, mastery_level)
        if result:
            return result

        # Final fallback: Datamuse API (primarily English, poor for other languages)
        if self.api:
            try:
                similar = self.api.get_similar_words(word)
                if similar:
                    result = []
                    for i, sw in enumerate(similar[:7]):
                        diff = 1 if i < 3 else (2 if i < 5 else 3)
                        rel = 'synonym' if i < 3 else ('similar' if i < 5 else 'advanced_form')
                        result.append({'word': sw, 'meaning': '', 'difficulty': diff, 'relation': rel})
                    return result
            except Exception as e:
                print(f"[VOCAB_ENGINE] Datamuse fallback error: {e}")

        return []

    def _generate_word_family(self, word, meaning, language, mastery_level):
        """Generate related words for any word using rule-based transformations."""
        word_lower = word.lower().strip()
        result = []
        seen = {word_lower}

        if language == 'es':
            # Spanish word families
            patterns = [
                # Nouns → related verbs/nouns
                (lambda w: w[:-1] + 'ar' if w.endswith('o') else None, 1, 'similar', 'related verb form'),
                (lambda w: w[:-1] + 'ación' if w.endswith('ar') else None, 2, 'associated', 'noun form'),
                (lambda w: w + 'mente' if len(w) > 3 and w.endswith('o') else None, 2, 'advanced_form', 'adverb form'),
                (lambda w: w[:-1] + 'ero' if w.endswith('o') and len(w) > 3 and not w.endswith('ero') else None, 2, 'associated', 'person who does'),
                (lambda w: w[:-1] + 'a' if w.endswith('o') and len(w) > 3 else None, 1, 'similar', 'feminine form'),
                (lambda w: w + 's' if len(w) > 2 else None, 1, 'similar', 'plural form'),
                (lambda w: 'pequeño ' + w if len(w) > 3 else None, 1, 'similar', 'diminutive'),
                (lambda w: 'gran ' + w if len(w) > 3 else None, 2, 'similar', 'augmentative'),
            ]
            for fn, diff, rel, desc in patterns:
                try:
                    nw = fn(word_lower)
                    if nw and nw not in seen and len(nw) > 2:
                        result.append({'word': nw, 'meaning': f'{desc} of {word}', 'difficulty': diff, 'relation': rel})
                        seen.add(nw)
                except Exception:
                    pass

        elif language == 'en':
            # English word families
            patterns = [
                (lambda w: w + 'ly' if len(w) > 3 and not w.endswith('ly') else None, 2, 'advanced_form', 'adverb form'),
                (lambda w: w + 'ness' if len(w) > 3 and not w.endswith('ness') else None, 2, 'advanced_form', 'noun form'),
                (lambda w: w + 'ful' if len(w) > 3 and not w.endswith('ful') else None, 2, 'similar', 'full of'),
                (lambda w: w + 'less' if len(w) > 3 and not w.endswith('less') else None, 2, 'antonym', 'without'),
                (lambda w: w + 'er' if len(w) > 3 and not w.endswith('er') else None, 1, 'similar', 'one who does'),
                (lambda w: 'un' + w if len(w) > 3 and not w.startswith('un') else None, 1, 'antonym', 'opposite'),
                (lambda w: w + 'ing' if len(w) > 3 and not w.endswith('ing') else None, 1, 'similar', 'action form'),
                (lambda w: w + 'ed' if len(w) > 3 and not w.endswith('ed') else None, 1, 'similar', 'past tense'),
            ]
            for fn, diff, rel, desc in patterns:
                try:
                    nw = fn(word_lower)
                    if nw and nw not in seen and len(nw) > 2:
                        result.append({'word': nw, 'meaning': f'{desc} of {word}', 'difficulty': diff, 'relation': rel})
                        seen.add(nw)
                except Exception:
                    pass

        # Common: generate opposite/related using simple patterns
        common_prefixes = {
            'en': ('un', 're', 'dis'),
            'es': ('des', 're', 'in'),
        }
        prefixes = common_prefixes.get(language, ('un', 're'))
        for prefix in prefixes:
            nw = prefix + word_lower
            if nw not in seen and len(nw) > 2 and len(nw) < 20:
                result.append({'word': nw, 'meaning': f'related to {word}', 'difficulty': 2, 'relation': 'similar'})
                seen.add(nw)

        if result:
            random.shuffle(result)
            return result[:5]
        return []

    def _get_fallback_pairs(self):
        """Get comprehensive hardcoded word clusters for fallback."""
        return {
            # ========================
            # ENGLISH CLUSTERS
            # ========================
            'happy': [{'word': 'glad', 'meaning': 'feeling pleasure', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'cheerful', 'meaning': 'noticeably happy', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'joyful', 'meaning': 'full of joy', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'delighted', 'meaning': 'very pleased', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'thrilled', 'meaning': 'extremely happy', 'difficulty': 2, 'relation': 'advanced_form'},
                      {'word': 'ecstatic', 'meaning': 'overwhelmingly happy', 'difficulty': 3, 'relation': 'advanced_form'},
                      {'word': 'elated', 'meaning': 'very happy and excited', 'difficulty': 3, 'relation': 'advanced_form'}],
            'sad': [{'word': 'unhappy', 'meaning': 'not happy', 'difficulty': 1, 'relation': 'similar'},
                    {'word': 'upset', 'meaning': 'distressed', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'gloomy', 'meaning': 'dark or sad', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'melancholy', 'meaning': 'deep sadness', 'difficulty': 3, 'relation': 'advanced_form'},
                    {'word': 'sorrow', 'meaning': 'deep distress', 'difficulty': 2, 'relation': 'synonym'}],
            'good': [{'word': 'nice', 'meaning': 'pleasant', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'fine', 'meaning': 'of good quality', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'great', 'meaning': 'very good', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'excellent', 'meaning': 'extremely good', 'difficulty': 2, 'relation': 'advanced_form'},
                     {'word': 'superb', 'meaning': 'of outstanding quality', 'difficulty': 3, 'relation': 'advanced_form'}],
            'bad': [{'word': 'poor', 'meaning': 'not good', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'terrible', 'meaning': 'very bad', 'difficulty': 2, 'relation': 'synonym'},
                    {'word': 'awful', 'meaning': 'extremely bad', 'difficulty': 2, 'relation': 'synonym'},
                    {'word': 'dreadful', 'meaning': 'causing great suffering', 'difficulty': 3, 'relation': 'advanced_form'}],
            'big': [{'word': 'large', 'meaning': 'big in size', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'huge', 'meaning': 'very large', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'enormous', 'meaning': 'extremely large', 'difficulty': 2, 'relation': 'advanced_form'},
                    {'word': 'massive', 'meaning': 'very big and solid', 'difficulty': 2, 'relation': 'advanced_form'},
                    {'word': 'colossal', 'meaning': 'extremely large', 'difficulty': 3, 'relation': 'advanced_form'}],
            'small': [{'word': 'little', 'meaning': 'small in size', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'tiny', 'meaning': 'very small', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'miniature', 'meaning': 'much smaller than usual', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'compact', 'meaning': 'small and neatly arranged', 'difficulty': 3, 'relation': 'advanced_form'}],
            'fast': [{'word': 'quick', 'meaning': 'moving at high speed', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'rapid', 'meaning': 'very fast', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'swift', 'meaning': 'moving quickly', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'speedy', 'meaning': 'characterized by speed', 'difficulty': 2, 'relation': 'synonym'}],
            'slow': [{'word': 'gentle', 'meaning': 'moderate in speed', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'gradual', 'meaning': 'happening slowly', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'leisurely', 'meaning': 'acting without haste', 'difficulty': 2, 'relation': 'similar'}],
            'food': [{'word': 'meal', 'meaning': 'an occasion of eating', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'dish', 'meaning': 'a prepared item of food', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'recipe', 'meaning': 'instructions for cooking', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'cuisine', 'meaning': 'a style of cooking', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'ingredient', 'meaning': 'component of a dish', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'gourmet', 'meaning': 'high-quality food', 'difficulty': 3, 'relation': 'advanced_form'},
                     {'word': 'gastronomy', 'meaning': 'art of good eating', 'difficulty': 3, 'relation': 'topic_related'}],
            'eat': [{'word': 'dine', 'meaning': 'eat a meal', 'difficulty': 2, 'relation': 'synonym'},
                    {'word': 'consume', 'meaning': 'eat or drink', 'difficulty': 2, 'relation': 'synonym'},
                    {'word': 'devour', 'meaning': 'eat hungrily', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'feast', 'meaning': 'large meal', 'difficulty': 2, 'relation': 'associated'}],
            'drink': [{'word': 'water', 'meaning': 'a clear liquid', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'beverage', 'meaning': 'a drink', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'sip', 'meaning': 'drink slowly', 'difficulty': 1, 'relation': 'similar'},
                      {'word': 'gulp', 'meaning': 'swallow quickly', 'difficulty': 2, 'relation': 'similar'}],
            'travel': [{'word': 'trip', 'meaning': 'a journey', 'difficulty': 1, 'relation': 'synonym'},
                       {'word': 'journey', 'meaning': 'travel from one place to another', 'difficulty': 1, 'relation': 'synonym'},
                       {'word': 'destination', 'meaning': 'place to go', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'itinerary', 'meaning': 'planned route', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'excursion', 'meaning': 'short trip', 'difficulty': 3, 'relation': 'similar'},
                       {'word': 'expedition', 'meaning': 'journey with purpose', 'difficulty': 3, 'relation': 'advanced_form'}],
            'learn': [{'word': 'study', 'meaning': 'to learn about', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'practice', 'meaning': 'to repeat to improve', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'understand', 'meaning': 'to comprehend', 'difficulty': 1, 'relation': 'similar'},
                      {'word': 'master', 'meaning': 'to become expert', 'difficulty': 2, 'relation': 'advanced_form'},
                      {'word': 'comprehend', 'meaning': 'to grasp mentally', 'difficulty': 3, 'relation': 'similar'}],
            'teach': [{'word': 'explain', 'meaning': 'make clear', 'difficulty': 1, 'relation': 'similar'},
                      {'word': 'instruct', 'meaning': 'give knowledge', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'educate', 'meaning': 'provide learning', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'train', 'meaning': 'teach skills', 'difficulty': 1, 'relation': 'similar'}],
            'run': [{'word': 'jog', 'meaning': 'run at a steady pace', 'difficulty': 1, 'relation': 'similar'},
                    {'word': 'sprint', 'meaning': 'run fast for short distance', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'dash', 'meaning': 'run quickly', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'race', 'meaning': 'compete in speed', 'difficulty': 2, 'relation': 'associated'},
                    {'word': 'gallop', 'meaning': 'run like a horse', 'difficulty': 3, 'relation': 'advanced_form'}],
            'walk': [{'word': 'stroll', 'meaning': 'walk slowly', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'hike', 'meaning': 'long walk', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'march', 'meaning': 'walk with purpose', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'wander', 'meaning': 'walk without destination', 'difficulty': 2, 'relation': 'similar'}],
            'say': [{'word': 'tell', 'meaning': 'communicate information', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'speak', 'meaning': 'talk out loud', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'mention', 'meaning': 'refer to briefly', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'express', 'meaning': 'convey thoughts', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'declare', 'meaning': 'state formally', 'difficulty': 3, 'relation': 'advanced_form'},
                    {'word': 'articulate', 'meaning': 'speak clearly', 'difficulty': 3, 'relation': 'advanced_form'}],
            'see': [{'word': 'look', 'meaning': 'direct your eyes', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'watch', 'meaning': 'observe carefully', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'view', 'meaning': 'look at something', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'observe', 'meaning': 'watch attentively', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'glimpse', 'meaning': 'a brief look', 'difficulty': 2, 'relation': 'associated'}],
            'hear': [{'word': 'listen', 'meaning': 'pay attention to sound', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'sound', 'meaning': 'vibrations that you hear', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'noise', 'meaning': 'unwanted sound', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'eavesdrop', 'meaning': 'secretly listen', 'difficulty': 3, 'relation': 'advanced_form'}],
            'think': [{'word': 'believe', 'meaning': 'accept as true', 'difficulty': 1, 'relation': 'similar'},
                      {'word': 'consider', 'meaning': 'think carefully', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'ponder', 'meaning': 'think deeply', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'reflect', 'meaning': 'think seriously', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'contemplate', 'meaning': 'view thoughtfully', 'difficulty': 3, 'relation': 'synonym'}],
            'know': [{'word': 'aware', 'meaning': 'having knowledge', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'familiar', 'meaning': 'well known', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'recognize', 'meaning': 'identify from past', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'comprehend', 'meaning': 'understand fully', 'difficulty': 3, 'relation': 'synonym'}],
            'want': [{'word': 'desire', 'meaning': 'strong wish', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'wish', 'meaning': 'hope for something', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'crave', 'meaning': 'intensely desire', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'yearn', 'meaning': 'long for something', 'difficulty': 3, 'relation': 'similar'}],
            'need': [{'word': 'require', 'meaning': 'need something', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'essential', 'meaning': 'absolutely necessary', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'necessary', 'meaning': 'needed, required', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'vital', 'meaning': 'extremely important', 'difficulty': 3, 'relation': 'advanced_form'}],
            'make': [{'word': 'create', 'meaning': 'bring into existence', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'build', 'meaning': 'construct something', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'produce', 'meaning': 'create or make', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'manufacture', 'meaning': 'make on a large scale', 'difficulty': 3, 'relation': 'advanced_form'}],
            'take': [{'word': 'grab', 'meaning': 'take quickly', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'seize', 'meaning': 'take forcefully', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'capture', 'meaning': 'take into control', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'obtain', 'meaning': 'get something', 'difficulty': 2, 'relation': 'synonym'}],
            'give': [{'word': 'provide', 'meaning': 'give what is needed', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'donate', 'meaning': 'give to charity', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'offer', 'meaning': 'present for acceptance', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'contribute', 'meaning': 'give to a common cause', 'difficulty': 2, 'relation': 'similar'}],
            'help': [{'word': 'assist', 'meaning': 'give support', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'aid', 'meaning': 'help or support', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'support', 'meaning': 'give assistance', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'facilitate', 'meaning': 'make easier', 'difficulty': 3, 'relation': 'advanced_form'}],
            'work': [{'word': 'job', 'meaning': 'paid position', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'task', 'meaning': 'piece of work to do', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'labor', 'meaning': 'physical work', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'profession', 'meaning': 'paid occupation', 'difficulty': 2, 'relation': 'similar'}],
            'play': [{'word': 'game', 'meaning': 'activity for fun', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'fun', 'meaning': 'enjoyment', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'sport', 'meaning': 'physical game', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'entertain', 'meaning': 'provide amusement', 'difficulty': 2, 'relation': 'similar'}],
            'love': [{'word': 'like', 'meaning': 'find agreeable', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'adore', 'meaning': 'love deeply', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'cherish', 'meaning': 'hold dear', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'affection', 'meaning': 'fond feelings', 'difficulty': 2, 'relation': 'associated'}],
            'hate': [{'word': 'dislike', 'meaning': 'not like', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'detest', 'meaning': 'strongly dislike', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'loathe', 'meaning': 'intensely hate', 'difficulty': 3, 'relation': 'synonym'},
                     {'word': 'despise', 'meaning': 'feel contempt for', 'difficulty': 3, 'relation': 'synonym'}],
            'beautiful': [{'word': 'pretty', 'meaning': 'attractive', 'difficulty': 1, 'relation': 'synonym'},
                          {'word': 'lovely', 'meaning': 'very beautiful', 'difficulty': 1, 'relation': 'synonym'},
                          {'word': 'gorgeous', 'meaning': 'stunningly beautiful', 'difficulty': 2, 'relation': 'synonym'},
                          {'word': 'magnificent', 'meaning': 'impressively beautiful', 'difficulty': 3, 'relation': 'advanced_form'}],
            'ugly': [{'word': 'plain', 'meaning': 'not attractive', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'unattractive', 'meaning': 'not pleasing to look at', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'hideous', 'meaning': 'extremely ugly', 'difficulty': 3, 'relation': 'advanced_form'}],
            'strong': [{'word': 'powerful', 'meaning': 'having great strength', 'difficulty': 1, 'relation': 'synonym'},
                       {'word': 'mighty', 'meaning': 'very strong', 'difficulty': 2, 'relation': 'synonym'},
                       {'word': 'robust', 'meaning': 'strong and healthy', 'difficulty': 2, 'relation': 'similar'},
                       {'word': 'sturdy', 'meaning': 'strongly built', 'difficulty': 2, 'relation': 'similar'}],
            'weak': [{'word': 'fragile', 'meaning': 'easily broken', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'feeble', 'meaning': 'very weak', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'delicate', 'meaning': 'easily damaged', 'difficulty': 2, 'relation': 'similar'}],
            'old': [{'word': 'ancient', 'meaning': 'very old', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'elderly', 'meaning': 'old person', 'difficulty': 2, 'relation': 'associated'},
                    {'word': 'vintage', 'meaning': 'from the past', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'antique', 'meaning': 'old and valuable', 'difficulty': 2, 'relation': 'similar'}],
            'new': [{'word': 'fresh', 'meaning': 'newly made', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'modern', 'meaning': 'related to present time', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'recent', 'meaning': 'not long ago', 'difficulty': 2, 'relation': 'synonym'},
                    {'word': 'novel', 'meaning': 'new and original', 'difficulty': 2, 'relation': 'similar'}],
            'rich': [{'word': 'wealthy', 'meaning': 'having a lot of money', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'affluent', 'meaning': 'having great wealth', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'prosperous', 'meaning': 'successful and rich', 'difficulty': 3, 'relation': 'synonym'}],
            'poor': [{'word': 'needy', 'meaning': 'lacking money', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'destitute', 'meaning': 'extremely poor', 'difficulty': 3, 'relation': 'advanced_form'},
                     {'word': 'impoverished', 'meaning': 'made poor', 'difficulty': 3, 'relation': 'synonym'}],
            'important': [{'word': 'significant', 'meaning': 'notably important', 'difficulty': 2, 'relation': 'synonym'},
                          {'word': 'crucial', 'meaning': 'very important', 'difficulty': 2, 'relation': 'synonym'},
                          {'word': 'essential', 'meaning': 'absolutely necessary', 'difficulty': 2, 'relation': 'similar'},
                          {'word': 'paramount', 'meaning': 'most important', 'difficulty': 3, 'relation': 'advanced_form'}],
            'easy': [{'word': 'simple', 'meaning': 'not difficult', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'effortless', 'meaning': 'requiring no effort', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'straightforward', 'meaning': 'easy to understand', 'difficulty': 2, 'relation': 'synonym'}],
            'difficult': [{'word': 'hard', 'meaning': 'not easy', 'difficulty': 1, 'relation': 'synonym'},
                          {'word': 'challenging', 'meaning': 'testing one\'s abilities', 'difficulty': 2, 'relation': 'synonym'},
                          {'word': 'complex', 'meaning': 'difficult to understand', 'difficulty': 2, 'relation': 'similar'},
                          {'word': 'arduous', 'meaning': 'very difficult', 'difficulty': 3, 'relation': 'advanced_form'}],
            'hot': [{'word': 'warm', 'meaning': 'moderately hot', 'difficulty': 1, 'relation': 'similar'},
                    {'word': 'boiling', 'meaning': 'very hot', 'difficulty': 2, 'relation': 'advanced_form'},
                    {'word': 'scorching', 'meaning': 'extremely hot', 'difficulty': 3, 'relation': 'advanced_form'}],
            'cold': [{'word': 'cool', 'meaning': 'slightly cold', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'freezing', 'meaning': 'very cold', 'difficulty': 2, 'relation': 'advanced_form'},
                     {'word': 'icy', 'meaning': 'covered with ice', 'difficulty': 2, 'relation': 'similar'}],
            'beautiful': [{'word': 'pretty', 'meaning': 'attractive', 'difficulty': 1, 'relation': 'synonym'},
                          {'word': 'lovely', 'meaning': 'very beautiful', 'difficulty': 1, 'relation': 'synonym'},
                          {'word': 'gorgeous', 'meaning': 'stunningly beautiful', 'difficulty': 2, 'relation': 'synonym'},
                          {'word': 'magnificent', 'meaning': 'impressively beautiful', 'difficulty': 3, 'relation': 'advanced_form'}],

            # ========================
            # SPANISH CLUSTERS
            # ========================
            'hola': [{'word': 'saludo', 'meaning': 'greeting', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'adiós', 'meaning': 'goodbye', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'bienvenido', 'meaning': 'welcome', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'saludar', 'meaning': 'to greet', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'despedirse', 'meaning': 'to say goodbye', 'difficulty': 3, 'relation': 'advanced_form'}],
            'adiós': [{'word': 'saludo', 'meaning': 'greeting', 'difficulty': 1, 'relation': 'similar'},
                      {'word': 'hasta luego', 'meaning': 'see you later', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'nos vemos', 'meaning': 'see you', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'despedida', 'meaning': 'farewell', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'hasta pronto', 'meaning': 'see you soon', 'difficulty': 1, 'relation': 'synonym'}],
            'casa': [{'word': 'hogar', 'meaning': 'home', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'edificio', 'meaning': 'building', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'habitación', 'meaning': 'room', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'vivienda', 'meaning': 'housing', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'residencia', 'meaning': 'residence', 'difficulty': 3, 'relation': 'advanced_form'},
                     {'word': 'cocina', 'meaning': 'kitchen', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'dormitorio', 'meaning': 'bedroom', 'difficulty': 2, 'relation': 'associated'}],
            'comida': [{'word': 'bebida', 'meaning': 'drink', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'cocina', 'meaning': 'kitchen / cooking', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'plato', 'meaning': 'dish / plate', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'receta', 'meaning': 'recipe', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'restaurante', 'meaning': 'restaurant', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'desayuno', 'meaning': 'breakfast', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'almuerzo', 'meaning': 'lunch', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'cena', 'meaning': 'dinner', 'difficulty': 1, 'relation': 'associated'}],
            'bueno': [{'word': 'malo', 'meaning': 'bad', 'difficulty': 1, 'relation': 'antonym'},
                      {'word': 'excelente', 'meaning': 'excellent', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'maravilloso', 'meaning': 'wonderful', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'fantástico', 'meaning': 'fantastic', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'magnífico', 'meaning': 'magnificent', 'difficulty': 3, 'relation': 'advanced_form'},
                      {'word': 'estupendo', 'meaning': 'stupendous', 'difficulty': 2, 'relation': 'synonym'}],
            'malo': [{'word': 'bueno', 'meaning': 'good', 'difficulty': 1, 'relation': 'antonym'},
                     {'word': 'terrible', 'meaning': 'terrible', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'horrible', 'meaning': 'horrible', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'pésimo', 'meaning': 'very bad', 'difficulty': 3, 'relation': 'advanced_form'}],
            'amigo': [{'word': 'amiga', 'meaning': 'friend (female)', 'difficulty': 1, 'relation': 'similar'},
                      {'word': 'compañero', 'meaning': 'companion', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'amistad', 'meaning': 'friendship', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'colega', 'meaning': 'colleague', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'camarada', 'meaning': 'comrade', 'difficulty': 3, 'relation': 'advanced_form'}],
            'libro': [{'word': 'leer', 'meaning': 'to read', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'página', 'meaning': 'page', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'autor', 'meaning': 'author', 'difficulty': 2, 'relation': 'associated'},
                      {'word': 'capítulo', 'meaning': 'chapter', 'difficulty': 2, 'relation': 'associated'},
                      {'word': 'biblioteca', 'meaning': 'library', 'difficulty': 2, 'relation': 'associated'},
                      {'word': 'lectura', 'meaning': 'reading', 'difficulty': 1, 'relation': 'associated'}],
            'agua': [{'word': 'mar', 'meaning': 'sea', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'río', 'meaning': 'river', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'beber', 'meaning': 'to drink', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'líquido', 'meaning': 'liquid', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'océano', 'meaning': 'ocean', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'lluvia', 'meaning': 'rain', 'difficulty': 1, 'relation': 'associated'}],
            'familia': [{'word': 'padre', 'meaning': 'father', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'madre', 'meaning': 'mother', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'hermano', 'meaning': 'brother', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'hijo', 'meaning': 'son / child', 'difficulty': 2, 'relation': 'associated'},
                        {'word': 'pariente', 'meaning': 'relative', 'difficulty': 2, 'relation': 'similar'},
                        {'word': 'abuelo', 'meaning': 'grandfather', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'abuela', 'meaning': 'grandmother', 'difficulty': 1, 'relation': 'associated'}],
            'tiempo': [{'word': 'hora', 'meaning': 'hour', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'día', 'meaning': 'day', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'semana', 'meaning': 'week', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'año', 'meaning': 'year', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'momento', 'meaning': 'moment', 'difficulty': 2, 'relation': 'similar'},
                       {'word': 'reloj', 'meaning': 'clock', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'minuto', 'meaning': 'minute', 'difficulty': 1, 'relation': 'associated'}],
            'gracias': [{'word': 'por favor', 'meaning': 'please', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'de nada', 'meaning': "you're welcome", 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'perdón', 'meaning': 'sorry / excuse me', 'difficulty': 2, 'relation': 'associated'},
                        {'word': 'agradecer', 'meaning': 'to thank', 'difficulty': 2, 'relation': 'similar'},
                        {'word': 'agradecido', 'meaning': 'grateful', 'difficulty': 3, 'relation': 'similar'}],
            'mundo': [{'word': 'tierra', 'meaning': 'earth', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'país', 'meaning': 'country', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'planeta', 'meaning': 'planet', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'global', 'meaning': 'global', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'universo', 'meaning': 'universe', 'difficulty': 3, 'relation': 'advanced_form'}],
            'escuela': [{'word': 'clase', 'meaning': 'class', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'profesor', 'meaning': 'teacher', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'estudiante', 'meaning': 'student', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'estudiar', 'meaning': 'to study', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'universidad', 'meaning': 'university', 'difficulty': 2, 'relation': 'associated'},
                        {'word': 'examen', 'meaning': 'exam', 'difficulty': 2, 'relation': 'associated'}],
            'grande': [{'word': 'pequeño', 'meaning': 'small', 'difficulty': 1, 'relation': 'antonym'},
                       {'word': 'enorme', 'meaning': 'enormous', 'difficulty': 2, 'relation': 'synonym'},
                       {'word': 'gigante', 'meaning': 'giant', 'difficulty': 2, 'relation': 'synonym'},
                       {'word': 'inmenso', 'meaning': 'immense', 'difficulty': 3, 'relation': 'synonym'}],
            'pequeño': [{'word': 'grande', 'meaning': 'big', 'difficulty': 1, 'relation': 'antonym'},
                        {'word': 'diminuto', 'meaning': 'tiny', 'difficulty': 2, 'relation': 'synonym'},
                        {'word': 'minúsculo', 'meaning': 'minuscule', 'difficulty': 3, 'relation': 'synonym'}],
            'hombre': [{'word': 'mujer', 'meaning': 'woman', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'niño', 'meaning': 'child', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'persona', 'meaning': 'person', 'difficulty': 1, 'relation': 'similar'},
                       {'word': 'señor', 'meaning': 'mister / gentleman', 'difficulty': 1, 'relation': 'associated'}],
            'mujer': [{'word': 'hombre', 'meaning': 'man', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'niña', 'meaning': 'girl', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'señora', 'meaning': 'miss / lady', 'difficulty': 1, 'relation': 'associated'}],
            'niño': [{'word': 'niña', 'meaning': 'girl', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'bebé', 'meaning': 'baby', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'joven', 'meaning': 'young person', 'difficulty': 1, 'relation': 'similar'},
                     {'word': 'adolescente', 'meaning': 'teenager', 'difficulty': 2, 'relation': 'similar'}],
            'comer': [{'word': 'beber', 'meaning': 'to drink', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'cocinar', 'meaning': 'to cook', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'desayunar', 'meaning': 'to have breakfast', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'cenar', 'meaning': 'to have dinner', 'difficulty': 2, 'relation': 'similar'}],
            'beber': [{'word': 'comer', 'meaning': 'to eat', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'agua', 'meaning': 'water', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'sed', 'meaning': 'thirst', 'difficulty': 2, 'relation': 'associated'},
                      {'word': 'vaso', 'meaning': 'glass', 'difficulty': 1, 'relation': 'associated'}],
            'hablar': [{'word': 'decir', 'meaning': 'to say', 'difficulty': 1, 'relation': 'synonym'},
                       {'word': 'conversar', 'meaning': 'to converse', 'difficulty': 2, 'relation': 'synonym'},
                       {'word': 'platicar', 'meaning': 'to chat', 'difficulty': 2, 'relation': 'similar'},
                       {'word': 'gritar', 'meaning': 'to shout', 'difficulty': 2, 'relation': 'similar'},
                       {'word': 'susurrar', 'meaning': 'to whisper', 'difficulty': 3, 'relation': 'advanced_form'}],
            'trabajar': [{'word': 'trabajo', 'meaning': 'work (noun)', 'difficulty': 1, 'relation': 'associated'},
                         {'word': 'empleo', 'meaning': 'employment', 'difficulty': 2, 'relation': 'synonym'},
                         {'word': 'oficina', 'meaning': 'office', 'difficulty': 1, 'relation': 'associated'},
                         {'word': 'jefe', 'meaning': 'boss', 'difficulty': 2, 'relation': 'associated'},
                         {'word': 'colega', 'meaning': 'colleague', 'difficulty': 2, 'relation': 'associated'}],
            'jugar': [{'word': 'juego', 'meaning': 'game', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'divertirse', 'meaning': 'to have fun', 'difficulty': 2, 'relation': 'associated'},
                      {'word': 'deporte', 'meaning': 'sport', 'difficulty': 2, 'relation': 'associated'},
                      {'word': 'ganar', 'meaning': 'to win', 'difficulty': 2, 'relation': 'associated'},
                      {'word': 'perder', 'meaning': 'to lose', 'difficulty': 2, 'relation': 'antonym'}],
            'leer': [{'word': 'libro', 'meaning': 'book', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'escritor', 'meaning': 'writer', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'novela', 'meaning': 'novel', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'cuento', 'meaning': 'story', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'poesía', 'meaning': 'poetry', 'difficulty': 2, 'relation': 'associated'}],
            'escribir': [{'word': 'escritura', 'meaning': 'writing', 'difficulty': 2, 'relation': 'associated'},
                         {'word': 'carta', 'meaning': 'letter', 'difficulty': 1, 'relation': 'associated'},
                         {'word': 'nota', 'meaning': 'note', 'difficulty': 1, 'relation': 'associated'},
                         {'word': 'firma', 'meaning': 'signature', 'difficulty': 2, 'relation': 'associated'}],
            'correr': [{'word': 'caminar', 'meaning': 'to walk', 'difficulty': 1, 'relation': 'similar'},
                       {'word': 'saltar', 'meaning': 'to jump', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'nadar', 'meaning': 'to swim', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'moverse', 'meaning': 'to move', 'difficulty': 2, 'relation': 'similar'}],
            'rojo': [{'word': 'azul', 'meaning': 'blue', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'verde', 'meaning': 'green', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'amarillo', 'meaning': 'yellow', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'negro', 'meaning': 'black', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'blanco', 'meaning': 'white', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'color', 'meaning': 'color', 'difficulty': 1, 'relation': 'associated'}],
            'azul': [{'word': 'rojo', 'meaning': 'red', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'verde', 'meaning': 'green', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'azulado', 'meaning': 'bluish', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'cielo', 'meaning': 'sky', 'difficulty': 1, 'relation': 'associated'}],
            'feliz': [{'word': 'contento', 'meaning': 'happy', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'alegre', 'meaning': 'cheerful', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'triste', 'meaning': 'sad', 'difficulty': 1, 'relation': 'antonym'},
                      {'word': 'alegría', 'meaning': 'happiness', 'difficulty': 2, 'relation': 'similar'}],
            'triste': [{'word': 'feliz', 'meaning': 'happy', 'difficulty': 1, 'relation': 'antonym'},
                       {'word': 'deprimido', 'meaning': 'depressed', 'difficulty': 2, 'relation': 'similar'},
                       {'word': 'llorar', 'meaning': 'to cry', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'tristeza', 'meaning': 'sadness', 'difficulty': 2, 'relation': 'similar'}],
            'poder': [{'word': 'fuerza', 'meaning': 'strength', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'capaz', 'meaning': 'capable', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'dominar', 'meaning': 'to dominate', 'difficulty': 3, 'relation': 'advanced_form'}],
            'saber': [{'word': 'conocer', 'meaning': 'to know (someone)', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'conocimiento', 'meaning': 'knowledge', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'sabiduría', 'meaning': 'wisdom', 'difficulty': 3, 'relation': 'advanced_form'}],
            'querer': [{'word': 'amar', 'meaning': 'to love', 'difficulty': 1, 'relation': 'synonym'},
                       {'word': 'desear', 'meaning': 'to desire', 'difficulty': 2, 'relation': 'synonym'},
                       {'word': 'necesitar', 'meaning': 'to need', 'difficulty': 1, 'relation': 'similar'}],
            'abrir': [{'word': 'cerrar', 'meaning': 'to close', 'difficulty': 1, 'relation': 'antonym'},
                      {'word': 'abierto', 'meaning': 'open (adj)', 'difficulty': 1, 'relation': 'similar'},
                      {'word': 'puerta', 'meaning': 'door', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'ventana', 'meaning': 'window', 'difficulty': 1, 'relation': 'associated'}],
            'pensar': [{'word': 'creer', 'meaning': 'to believe', 'difficulty': 1, 'relation': 'similar'},
                       {'word': 'imaginar', 'meaning': 'to imagine', 'difficulty': 2, 'relation': 'similar'},
                       {'word': 'recordar', 'meaning': 'to remember', 'difficulty': 2, 'relation': 'similar'},
                       {'word': 'olvidar', 'meaning': 'to forget', 'difficulty': 2, 'relation': 'antonym'}],
            'poner': [{'word': 'colocar', 'meaning': 'to place', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'quitar', 'meaning': 'to remove', 'difficulty': 2, 'relation': 'antonym'},
                      {'word': 'dejar', 'meaning': 'to leave', 'difficulty': 2, 'relation': 'similar'}],
            'traer': [{'word': 'llevar', 'meaning': 'to carry', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'enviar', 'meaning': 'to send', 'difficulty': 2, 'relation': 'similar'},
                      {'word': 'recibir', 'meaning': 'to receive', 'difficulty': 2, 'relation': 'antonym'}],
            'dar': [{'word': 'recibir', 'meaning': 'to receive', 'difficulty': 1, 'relation': 'antonym'},
                    {'word': 'regalar', 'meaning': 'to gift', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'donar', 'meaning': 'to donate', 'difficulty': 2, 'relation': 'similar'}],
            'ver': [{'word': 'mirar', 'meaning': 'to look at', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'observar', 'meaning': 'to observe', 'difficulty': 2, 'relation': 'similar'},
                    {'word': 'ojeada', 'meaning': 'glance', 'difficulty': 2, 'relation': 'associated'}],
            'oír': [{'word': 'escuchar', 'meaning': 'to listen', 'difficulty': 1, 'relation': 'synonym'},
                    {'word': 'sonido', 'meaning': 'sound', 'difficulty': 1, 'relation': 'associated'},
                    {'word': 'ruido', 'meaning': 'noise', 'difficulty': 1, 'relation': 'associated'}],
            'dormir': [{'word': 'cama', 'meaning': 'bed', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'soñar', 'meaning': 'to dream', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'descansar', 'meaning': 'to rest', 'difficulty': 2, 'relation': 'similar'},
                       {'word': 'despertar', 'meaning': 'to wake up', 'difficulty': 2, 'relation': 'antonym'}],
            'viajar': [{'word': 'viaje', 'meaning': 'trip', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'vuelo', 'meaning': 'flight', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'hotel', 'meaning': 'hotel', 'difficulty': 1, 'relation': 'associated'},
                       {'word': 'turista', 'meaning': 'tourist', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'vacaciones', 'meaning': 'vacation', 'difficulty': 2, 'relation': 'associated'}],
            'comprar': [{'word': 'vender', 'meaning': 'to sell', 'difficulty': 1, 'relation': 'antonym'},
                        {'word': 'tienda', 'meaning': 'store', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'precio', 'meaning': 'price', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'dinero', 'meaning': 'money', 'difficulty': 1, 'relation': 'associated'},
                        {'word': 'gastar', 'meaning': 'to spend', 'difficulty': 2, 'relation': 'associated'}],
            'vender': [{'word': 'comprar', 'meaning': 'to buy', 'difficulty': 1, 'relation': 'antonym'},
                       {'word': 'venta', 'meaning': 'sale', 'difficulty': 2, 'relation': 'associated'},
                       {'word': 'mercado', 'meaning': 'market', 'difficulty': 2, 'relation': 'associated'}],
            'buscar': [{'word': 'encontrar', 'meaning': 'to find', 'difficulty': 1, 'relation': 'similar'},
                       {'word': 'perder', 'meaning': 'to lose', 'difficulty': 2, 'relation': 'antonym'},
                       {'word': 'búsqueda', 'meaning': 'search', 'difficulty': 2, 'relation': 'similar'}],
            'encontrar': [{'word': 'buscar', 'meaning': 'to search', 'difficulty': 1, 'relation': 'similar'},
                          {'word': 'hallar', 'meaning': 'to find (formal)', 'difficulty': 3, 'relation': 'synonym'},
                          {'word': 'descubrir', 'meaning': 'to discover', 'difficulty': 2, 'relation': 'similar'}],

            # ========================
            # HINDI CLUSTERS
            # ========================
            'नमस्ते': [{'word': 'नमस्कार', 'meaning': 'greetings (formal)', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'स्वागत', 'meaning': 'welcome', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'अलविदा', 'meaning': 'goodbye', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'शुभ', 'meaning': 'auspicious', 'difficulty': 2, 'relation': 'similar'}],
            'पानी': [{'word': 'जल', 'meaning': 'water (formal)', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'समुद्र', 'meaning': 'sea', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'नदी', 'meaning': 'river', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'प्यास', 'meaning': 'thirst', 'difficulty': 2, 'relation': 'associated'}],
            'खाना': [{'word': 'भोजन', 'meaning': 'meal (formal)', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'पकाना', 'meaning': 'to cook', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'स्वाद', 'meaning': 'taste', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'रसोई', 'meaning': 'kitchen', 'difficulty': 2, 'relation': 'associated'}],
            'अच्छा': [{'word': 'बुरा', 'meaning': 'bad', 'difficulty': 1, 'relation': 'antonym'},
                      {'word': 'बढ़िया', 'meaning': 'excellent', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'शानदार', 'meaning': 'magnificent', 'difficulty': 3, 'relation': 'advanced_form'}],
            'बड़ा': [{'word': 'छोटा', 'meaning': 'small', 'difficulty': 1, 'relation': 'antonym'},
                     {'word': 'विशाल', 'meaning': 'huge', 'difficulty': 2, 'relation': 'synonym'},
                     {'word': 'लंबा', 'meaning': 'tall / long', 'difficulty': 1, 'relation': 'similar'}],
            'सुंदर': [{'word': 'खूबसूरत', 'meaning': 'beautiful', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'प्यारा', 'meaning': 'lovely', 'difficulty': 1, 'relation': 'synonym'},
                      {'word': 'आकर्षक', 'meaning': 'attractive', 'difficulty': 3, 'relation': 'synonym'}],
            'दोस्त': [{'word': 'मित्र', 'meaning': 'friend (formal)', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'साथी', 'meaning': 'companion', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'दोस्ती', 'meaning': 'friendship', 'difficulty': 2, 'relation': 'similar'}],
            'प्यार': [{'word': 'प्रेम', 'meaning': 'love (formal)', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'मोहब्बत', 'meaning': 'love (Urdu)', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'स्नेह', 'meaning': 'affection', 'difficulty': 3, 'relation': 'similar'}],
            'घर': [{'word': 'मकान', 'meaning': 'house', 'difficulty': 2, 'relation': 'synonym'},
                   {'word': 'भवन', 'meaning': 'building', 'difficulty': 2, 'relation': 'associated'},
                   {'word': 'कमरा', 'meaning': 'room', 'difficulty': 1, 'relation': 'associated'}],
            'स्कूल': [{'word': 'विद्यालय', 'meaning': 'school (formal)', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'शिक्षक', 'meaning': 'teacher', 'difficulty': 2, 'relation': 'associated'},
                      {'word': 'विद्यार्थी', 'meaning': 'student', 'difficulty': 2, 'relation': 'associated'}],
            'किताब': [{'word': 'पुस्तक', 'meaning': 'book (formal)', 'difficulty': 2, 'relation': 'synonym'},
                      {'word': 'पढ़ना', 'meaning': 'to read', 'difficulty': 1, 'relation': 'associated'},
                      {'word': 'लेखक', 'meaning': 'author', 'difficulty': 2, 'relation': 'associated'}],
            'पैसा': [{'word': 'धन', 'meaning': 'wealth', 'difficulty': 2, 'relation': 'similar'},
                     {'word': 'दाम', 'meaning': 'price', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'खरीदना', 'meaning': 'to buy', 'difficulty': 2, 'relation': 'associated'}],
            'जाना': [{'word': 'आना', 'meaning': 'to come', 'difficulty': 1, 'relation': 'antonym'},
                     {'word': 'यात्रा', 'meaning': 'journey', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'चलना', 'meaning': 'to walk', 'difficulty': 1, 'relation': 'similar'}],
            'कहना': [{'word': 'बोलना', 'meaning': 'to speak', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'बताना', 'meaning': 'to tell', 'difficulty': 1, 'relation': 'synonym'},
                     {'word': 'पूछना', 'meaning': 'to ask', 'difficulty': 1, 'relation': 'associated'}],
            'काम': [{'word': 'कार्य', 'meaning': 'work (formal)', 'difficulty': 2, 'relation': 'synonym'},
                    {'word': 'नौकरी', 'meaning': 'job', 'difficulty': 2, 'relation': 'synonym'},
                    {'word': 'व्यवसाय', 'meaning': 'profession', 'difficulty': 3, 'relation': 'similar'}],
            'समय': [{'word': 'घंटा', 'meaning': 'hour', 'difficulty': 1, 'relation': 'associated'},
                    {'word': 'दिन', 'meaning': 'day', 'difficulty': 1, 'relation': 'associated'},
                    {'word': 'सप्ताह', 'meaning': 'week', 'difficulty': 2, 'relation': 'associated'},
                    {'word': 'महीना', 'meaning': 'month', 'difficulty': 2, 'relation': 'associated'}],
            'रंग': [{'word': 'लाल', 'meaning': 'red', 'difficulty': 1, 'relation': 'associated'},
                    {'word': 'नीला', 'meaning': 'blue', 'difficulty': 1, 'relation': 'associated'},
                    {'word': 'हरा', 'meaning': 'green', 'difficulty': 1, 'relation': 'associated'},
                    {'word': 'पीला', 'meaning': 'yellow', 'difficulty': 1, 'relation': 'associated'}],
            'रोटी': [{'word': 'चावल', 'meaning': 'rice', 'difficulty': 1, 'relation': 'associated'},
                     {'word': 'दाल', 'meaning': 'lentils', 'difficulty': 2, 'relation': 'associated'},
                     {'word': 'सब्जी', 'meaning': 'vegetables', 'difficulty': 1, 'relation': 'associated'}],
        }

    def expand_vocabulary(self, user_id, source_word_id):
        """Generate and store related words for a newly learned/validated word."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.word, v.meaning, v.language, v.mastery_level
            FROM vocabulary v WHERE v.id = ? AND v.user_id = ?
        """, (source_word_id, user_id))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return []
        word, meaning, language, mastery = row
        related = self.generate_related_words(word, meaning, language, mastery)
        added_words = []

        for rw in related:
            rw_word = rw.get('word', '').strip()
            rw_meaning = rw.get('meaning', '')
            diff_level = rw.get('difficulty', 1)
            rel_type = rw.get('relation', 'similar')

            if not rw_word:
                continue
            if not rw_meaning or is_placeholder(rw_meaning):
                try:
                    from api_service import api_service
                    info = api_service.get_enhanced_word_info(rw_word, language)
                    if info and info.get('definition') and not is_placeholder(info['definition']):
                        rw_meaning = info['definition']
                except Exception:
                    pass
                if not rw_meaning or is_placeholder(rw_meaning):
                    from dictionary_service import dictionary_service
                    defn = dictionary_service.get_meaning(rw_word, language)
                    if defn:
                        rw_meaning = defn["meaning"]
                    else:
                        rw_meaning = ""

            # See if word already exists for user
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM vocabulary WHERE user_id = ? AND word = ? AND language = ?
            """, (user_id, rw_word, language))
            existing = cursor.fetchone()

            if existing:
                existing_id = existing[0]
                self.add_relation(user_id, source_word_id, existing_id, rel_type, strength=0.8, difficulty_level=diff_level)
                added_words.append({'id': existing_id, 'word': rw_word, 'meaning': rw_meaning, 'new': False})
            else:
                # Insert as a discovery suggestion
                cursor.execute("""
                    INSERT INTO vocabulary_discovery (user_id, word, language, meaning, source_word, difficulty_level, relation_type, topic)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, rw_word, language, rw_meaning, word, diff_level, rel_type, 'General'))
                disc_id = cursor.lastrowid
                added_words.append({'id': disc_id, 'word': rw_word, 'meaning': rw_meaning, 'new': True,
                                    'language': language, 'difficulty_level': diff_level,
                                    'relation_type': rel_type, 'topic': 'General'})

            conn.commit()
            conn.close()

        # Detect and assign topic
        topic = self.detect_topic(word, language)
        self.assign_topic(source_word_id, topic)

        return added_words

    # ================================================================
    # RECOMMENDATION ENGINE
    # ================================================================

    def score_word(self, user_id, candidate_word, source_words, weak_words):
        """Score a candidate word for recommendation."""
        score = 0.0

        # Similarity to learned words base score (40%)
        max_sim = 1.0
        for sw in source_words:
            if candidate_word.lower() in sw.get('related', []):
                max_sim = max(max_sim, 0.8)
        score += max_sim * 0.4

        # Weak word relevance (20%)
        for ww in weak_words:
            if candidate_word.lower() in ww.get('related', []):
                score += 0.15
                break
        score += 0.05  # base interest

        # Frequency / real-world usage (20%)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                        'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                        'would', 'could', 'should', 'may', 'might', 'shall', 'can'}
        if candidate_word.lower() not in common_words:
            score += 0.2

        # Difficulty match (20%)
        known_mastery = sum(sw.get('mastery_level', 0) for sw in source_words) / max(len(source_words), 1)
        difficulty_ratio = 1.0 - (known_mastery / 5.0)
        score += difficulty_ratio * 0.2

        return min(score, 1.0)

    def get_recommendations(self, user_id, language=None, limit=10):
        """Get personalized word recommendations for a user."""
        conn = db.get_connection()
        cursor = conn.cursor()

        # 1. Get all user words sorted by mastery (highest first)
        lang_filter = ""
        params = [user_id]
        if language:
            lang_filter = "AND language = ?"
            params.append(language)
        cursor.execute(f"""
            SELECT id, word, meaning, mastery_level, frequency
            FROM vocabulary WHERE user_id = ? {lang_filter}
            ORDER BY mastery_level DESC, frequency DESC LIMIT 20
        """, params)
        source_words = [{'id': r[0], 'word': r[1], 'meaning': r[2], 'mastery_level': r[3],
                         'frequency': r[4]} for r in cursor.fetchall()]

        # 2. Get weakest words (lowest mastery, most mistakes)
        cursor.execute(f"""
            SELECT v.id, v.word, v.meaning, v.mastery_level
            FROM vocabulary v
            LEFT JOIN review_analytics ra ON v.id = ra.word_id AND ra.user_id = v.user_id
            WHERE v.user_id = ? {lang_filter}
            ORDER BY v.mastery_level ASC, COALESCE(ra.difficulty_score, 0) DESC
            LIMIT 10
        """, params)
        weak_words = [{'id': r[0], 'word': r[1], 'meaning': r[2], 'mastery_level': r[3]}
                      for r in cursor.fetchall()]

        # 3. Get existing discovery suggestions
        cursor.execute("""
            SELECT id, word, language, meaning, source_word, difficulty_level, relation_type, topic
            FROM vocabulary_discovery
            WHERE user_id = ? AND (viewed = 0 OR viewed IS NULL)
            ORDER BY created_date DESC
            LIMIT ?
        """, (user_id, limit))
        discovery = [{'id': r[0], 'word': r[1], 'language': r[2], 'meaning': r[3],
                      'source_word': r[4], 'difficulty_level': r[5], 'relation_type': r[6],
                      'topic': r[7]} for r in cursor.fetchall()]

        # Score discovery words
        for d in discovery:
            d['score'] = self.score_word(user_id, d['word'], source_words, weak_words)

        # If not enough from discovery, generate new recommendations via AI
        if len(discovery) < limit and source_words:
            for sw in source_words[:3]:
                result = self.expand_vocabulary(user_id, sw['id'])
                for rw in result:
                    if rw.get('new') and not any(d['word'] == rw['word'] for d in discovery):
                        discovery.append({
                            'id': rw.get('id'),
                            'word': rw['word'],
                            'meaning': rw['meaning'],
                            'language': rw.get('language', language or 'en'),
                            'source_word': sw['word'],
                            'difficulty_level': rw.get('difficulty_level', 1),
                            'relation_type': rw.get('relation_type', 'similar'),
                            'topic': rw.get('topic', 'General'),
                            'score': self.score_word(user_id, rw['word'], source_words, weak_words)
                        })
                if len(discovery) >= limit:
                    break

        conn.close()

        # Sort by score descending
        discovery.sort(key=lambda x: x.get('score', 0), reverse=True)
        return discovery[:limit]

    def mark_discovery_viewed(self, discovery_id):
        """Mark a discovery suggestion as viewed."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE vocabulary_discovery SET viewed = 1 WHERE id = ?", (discovery_id,))
        conn.commit()
        conn.close()

    def add_discovery_to_vocabulary(self, user_id, discovery_id):
        """Add a discovery word to the user's vocabulary."""
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT word, language, meaning, source_word FROM vocabulary_discovery WHERE id = ?
        """, (discovery_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        word, language, meaning, source = row
        from word_validator import WordValidator
        result = WordValidator().validate_and_store_word(user_id, word, language, meaning)

        # Mark discovery as viewed
        cursor.execute("UPDATE vocabulary_discovery SET viewed = 1 WHERE id = ?", (discovery_id,))
        conn.commit()
        conn.close()
        return result

    # ================================================================
    # LEARNING PATHS
    # ================================================================

    def generate_learning_path(self, user_id, topic, language='en', count=7):
        """Generate a learning path for a specific topic using AI."""
        if not self.openai:
            return []

        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT word FROM vocabulary v
            JOIN word_topics wt ON v.id = wt.word_id
            WHERE v.user_id = ? AND wt.topic = ? AND v.language = ?
            LIMIT 5
        """, (user_id, topic, language))
        known_words = [r[0] for r in cursor.fetchall()]
        conn.close()

        if not known_words:
            return []

        prompt = f"""The user knows these {topic} words: {', '.join(known_words)}.

    Generate {count} new related {topic} vocabulary words for them to learn next.
    Provide them in a logical learning progression (easier first, harder later).

    For each word provide:
    - word
    - brief meaning in English
    - difficulty level (1-5)
    - why it's useful for the learner

    Return ONLY valid JSON array:
    [
      {{"word": "...", "meaning": "...", "difficulty": 1, "reason": "..."}},
    ]
    """
        try:
            resp = self.openai.generate_content(prompt)
            if not resp or not resp.text:
                return []
            text = resp.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            words = json.loads(text)
            if isinstance(words, list):
                return words[:count]
            return []
        except Exception as e:
            print(f"[VOCAB_ENGINE] Learning path error: {e}")
            return []

    # ================================================================
    # DISCOVERY CARD CONTENT
    # ================================================================

    def generate_discovery_card(self, user_id, discovery_word):
        """Generate Duolingo-style discovery card content."""
        if not self.openai:
            return discovery_word

        word = discovery_word.get('word', '')
        source = discovery_word.get('source_word', '')
        meaning = discovery_word.get('meaning', '')

        prompt = f"""Create a friendly learning moment for a language learner.

    The learner already knows the word "{source}".
    Now they are discovering the word "{word}" (meaning: {meaning}).

    Write a short, encouraging explanation like Duolingo's green owl character would say.
    Explain how "{word}" relates to "{source}" and why it's useful.
    Keep it to 2-3 sentences. Be warm and encouraging.

    Return as JSON:
    {{"message": "...", "tip": "...", "example": "...", "fun_fact": "..."}}
    """
        try:
            resp = self.openai.generate_content(prompt)
            if not resp or not resp.text:
                return discovery_word
            text = resp.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            elif text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            card_data = json.loads(text)
            discovery_word.update(card_data)
            return discovery_word
        except Exception as e:
            print(f"[VOCAB_ENGINE] Card generation error: {e}")
            return discovery_word

    # ================================================================
    # REVIEW PRIORITIZATION INTEGRATION
    # ================================================================

    def get_prioritized_words(self, user_id, language=None, limit=20):
        """Get words ranked for review priority using the recommendation engine."""
        conn = db.get_connection()
        cursor = conn.cursor()

        # Words ranked by: forgotten frequently, recently learned, related to mastered, high-frequency
        lang_filter = ""
        params = [user_id]
        if language:
            lang_filter = "AND v.language = ?"
            params.append(language)

        cursor.execute(f"""
            SELECT v.id, v.word, v.meaning, v.mastery_level, v.review_count,
                   v.frequency, v.last_practiced,
                   COALESCE(ra.incorrect_count, 0) as wrong_count,
                   COALESCE(ra.difficulty_score, 0) as difficulty,
                   COUNT(vr.id) as relation_count
            FROM vocabulary v
            LEFT JOIN review_analytics ra ON v.id = ra.word_id AND ra.user_id = v.user_id
            LEFT JOIN vocabulary_relations vr ON (v.id = vr.word_id_1 OR v.id = vr.word_id_2) AND vr.user_id = v.user_id
            WHERE v.user_id = ? {lang_filter}
            GROUP BY v.id
            ORDER BY
                difficulty DESC,
                v.mastery_level ASC,
                v.last_practiced ASC NULLS FIRST,
                relation_count DESC,
                v.frequency DESC
            LIMIT ?
        """, params + [limit])
        rows = cursor.fetchall()
        conn.close()
        return [{
            'id': r[0], 'word': r[1], 'meaning': r[2], 'mastery_level': r[3],
            'review_count': r[4], 'frequency': r[5], 'last_practiced': r[6],
            'wrong_count': r[7], 'difficulty': r[8], 'relation_count': r[9]
        } for r in rows]


vocabulary_engine = VocabularyEngine()
