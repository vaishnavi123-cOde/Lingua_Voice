import sqlite3
import requests
import json
import re
import time
from threading import Lock
from database_manager import db
from api_service import api_service
from srs_manager import srs_manager

PLACEHOLDER_PATTERNS = [
    re.compile(r'^Definition pending\.\.\.$', re.I),
    re.compile(r'^Definición pendiente\.\.\.$', re.I),
    re.compile(r'^परिभाषा लंबित\.\.\.$', re.I),
    re.compile(r'^Learning in progress\.\.\.$', re.I),
    re.compile(r'^Meaning of ', re.I),
    re.compile(r'^A word related to ', re.I),
    re.compile(r'^Definition currently unavailable', re.I),
    re.compile(r'^Unknown$', re.I),
    re.compile(r'^Loading\.\.\.$', re.I),
]

def is_placeholder(text):
    if not text:
        return True
    text = text.strip()
    if len(text) < 3:
        return True
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            return True
    return False

class WordValidator:
    def __init__(self):
        self.lock = Lock()
    
    def is_online(self):
        return api_service.is_online()
    
    def get_word_meaning(self, word, language):
        """Get enhanced word information using the API service"""
        if not self.is_online():
            return None
        
        try:
            word_info = api_service.get_enhanced_word_info(word, language)
            
            if word_info and word_info.get('definition'):
                definition = word_info['definition']
                if is_placeholder(definition):
                    return None
                parts = []
                parts.append(definition)
                if word_info.get('phonetic'):
                    parts[0] = f"({word_info['phonetic']}) " + parts[0]
                if word_info.get('examples'):
                    parts.append(f"Example: {word_info['examples'][0]}")
                if word_info.get('synonyms'):
                    syn_list = ', '.join(word_info['synonyms'][:5])
                    parts.append(f"Synonyms: {syn_list}")
                return ' | '.join(parts)
            
            return None
            
        except Exception as e:
            print(f"[VALIDATOR] Error fetching meaning for {word} ({language}): {e}")
            return None

    def validate_and_store_word(self, user_id, word, language, source_context=None, meaning=None):
        with self.lock:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, meaning, is_valid FROM vocabulary WHERE user_id=? AND word=? AND language=?",
                (user_id, word.lower(), language)
            )
            result = cursor.fetchone()
            
            existing_id = result[0] if result else None
            existing_meaning = result[1] if result else None
            existing_valid = bool(result[2]) if result else False

            if result and not is_placeholder(existing_meaning):
                conn.close()
                return {'cached': True, 'meaning': existing_meaning, 'is_valid': existing_valid}

            if meaning and is_placeholder(meaning):
                meaning = None

            if not meaning:
                if self.is_online():
                    meaning = self.get_word_meaning(word, language)
                else:
                    meaning = None

            is_valid = meaning is not None and not is_placeholder(meaning)

            if meaning and is_placeholder(meaning):
                meaning = None
                is_valid = False

            store_meaning = meaning if meaning else ''
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                if existing_id:
                    update_fields = ["meaning=?", "is_valid=?", "last_practiced=?"]
                    params = [store_meaning, int(is_valid), timestamp]
                    if source_context:
                        update_fields.append("source_context=?")
                        params.append(source_context)
                    params.extend([user_id, word.lower(), language])
                    cursor.execute(
                        f"UPDATE vocabulary SET {', '.join(update_fields)} WHERE user_id=? AND word=? AND language=?",
                        tuple(params)
                    )
                    print(f"[VALIDATOR] Updated: {word} ({language}) - {store_meaning[:50] if store_meaning else 'No meaning'}", flush=True)
                else:
                    cursor.execute(
                        """INSERT INTO vocabulary 
                           (user_id, word, language, meaning, is_valid, first_seen, last_practiced, source_context) 
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (user_id, word.lower(), language, store_meaning, int(is_valid), timestamp, timestamp, source_context)
                    )
                    new_id = cursor.lastrowid
                    try:
                        srs_manager.schedule_new_word(new_id)
                    except Exception as e:
                        print(f"[VALIDATOR] Error scheduling SRS for new word: {e}", flush=True)
                    print(f"[VALIDATOR] Inserted: {word} ({language}) - {store_meaning[:50] if store_meaning else 'No meaning'}", flush=True)
                conn.commit()
            except Exception as e:
                print(f"DB Error in validator: {e}", flush=True)
            finally:
                conn.close()
            
            return {'cached': False, 'meaning': meaning, 'is_valid': is_valid}
    
    def get_user_words(self, user_id, language=None):
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """SELECT word, language, meaning, is_valid, last_practiced, source_context, 
                          frequency, mastery_level 
                   FROM vocabulary WHERE user_id=?"""
        params = [user_id]
        
        if language:
            query += " AND language=?"
            params.append(language)
            
        query += " ORDER BY last_practiced DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'word': r[0], 
            'language': r[1], 
            'meaning': r[2], 
            'is_valid': bool(r[3]), 
            'timestamp': r[4], 
            'source': r[5],
            'frequency': r[6] or 1,
            'mastery_level': r[7] or 0
        } for r in results]
