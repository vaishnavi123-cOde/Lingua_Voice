"""
AI Tutor Chat API using OpenAI GPT-4o-mini
"""
import json
from openai import OpenAI
from config import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY)
_MODEL = "gpt-4o-mini"

def _chat(system: str, user: str, json_mode: bool = False) -> str | None:
    """Helper: call OpenAI chat completions and return the text content."""
    try:
        kwargs = {
            "model": _MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["temperature"] = 0.3
        response = _client.chat.completions.create(**kwargs)
        if response and response.choices:
            return response.choices[0].message.content
    except Exception as e:
        print(f"[AI_TUTOR] OpenAI error: {e}")
    return None

def get_ai_tutor_response(message, base_language, target_language, history, weak_words=None):
    """Get AI tutor response using OpenAI, optionally focusing on weak vocabulary"""

    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'hi': 'Hindi'
    }

    base_lang_name = language_names.get(base_language, 'English')
    target_lang_name = language_names.get(target_language, 'Spanish')

    # Build context from history
    context = ""
    if history:
        for exchange in history[-5:]:  # Last 5 exchanges
            context += f"Student: {exchange['user']}\nTutor: {exchange['ai']}\n"

    weak_words_str = ""
    if weak_words:
        weak_words_str = f"Try to naturally use some of these words the student is currently learning: {', '.join(weak_words)}."

    system_msg = (
        f"You are not just a tutor, but a close, supportive friend helping the student learn {target_lang_name}. "
        f"The student speaks {base_lang_name}. {weak_words_str} "
        "Be warm, conversational, and encouraging. "
        f"Use {target_lang_name} naturally but always provide the {base_lang_name} translation. "
        "Gently correct mistakes and ask friendly follow-up questions."
    )
    user_msg = f"Previous conversation:\n{context}\nFriend's message: {message}\n\nRespond as a warm, interactive friend."

    result = _chat(system_msg, user_msg)
    if result:
        return result.strip()
    return "Hey! I'm having a little glitch in my system. Let's try again in a moment, friend!"

def get_note_translation(text, target_language):
    """Translate a recorded note into English and provide explanation"""

    system_msg = "You are a helpful language translator. Always respond with valid JSON only."
    user_msg = f"""Translate the following text from {target_language} to English.
Provide a clear translation and a brief, friendly explanation of any interesting words or grammar points.

Text: {text}

Return JSON:
{{"translation": "English translation", "explanation": "Brief friendly explanation", "original": "{text}"}}"""

    try:
        raw = _chat(system_msg, user_msg, json_mode=True)
        if raw:
            return json.loads(raw)
    except Exception as e:
        print(f"[NOTES_TRANS] Error: {e}")

    return {
        "translation": "Could not translate right now.",
        "explanation": "Translation service is temporarily unavailable.",
        "original": text
    }

def get_practice_phrase(base_language, target_language, exclude=None, focus_word=None):
    """Get a practice phrase for voice conversation, focusing on vocabulary if provided"""

    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'hi': 'Hindi'
    }

    target_lang_name = language_names.get(target_language, 'Spanish')
    base_lang_name = language_names.get(base_language, 'English')

    exclude_str = ""
    if exclude:
        if focus_word and focus_word.lower() in [e.lower() for e in exclude]:
            exclude = [e for e in exclude if e.lower() != focus_word.lower()]
        exclude_str = f" Do NOT use any of these: {', '.join(exclude)}."

    focus_str = ""
    if focus_word:
        focus_str = f"\nCRITICAL: You MUST use the word '{focus_word}' in the phrase. Create a natural context for this word."

    system_msg = "You are a language learning assistant. Always respond with valid JSON only."
    user_msg = f"""Generate a simple, common {target_lang_name} phrase for a beginner to practice speaking.{exclude_str}{focus_str}
Make it practical and useful for everyday conversation.
CRITICAL: Do not repeat any concepts, words, or meanings mentioned in the exclusion list.
Ensure the phrase is different from very basic greetings like 'Hello' or 'How are you' if they are already in the list.

Return JSON: {{"phrase": "the {target_lang_name} phrase", "translation": "{base_lang_name} translation", "context": "when to use this phrase"}}"""

    try:
        raw = _chat(system_msg, user_msg, json_mode=True)
        if raw:
            return json.loads(raw)
    except Exception as e:
        print(f"[AI_TUTOR] Phrase error: {e}")

    return {
        "phrase": "Hola",
        "translation": "Hello",
        "context": "Basic greeting"
    }

def check_pronunciation(expected, actual, language):
    """Check if user's speech matches expected phrase"""
    
    # Simple similarity check (can be enhanced)
    expected_lower = expected.lower().strip()
    actual_lower = actual.lower().strip()
    
    # Calculate similarity
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, expected_lower, actual_lower).ratio()
    
    if similarity > 0.7:
        return {
            "correct": True,
            "message": "Excellent! Perfect pronunciation! 🎉",
            "similarity": similarity
        }
    elif similarity > 0.4:
        return {
            "correct": False,
            "message": f"Almost there! Try again. Expected: '{expected}'",
            "similarity": similarity
        }
    else:
        return {
            "correct": False,
            "message": f"Let's try again. Listen carefully and repeat: '{expected}'",
            "similarity": similarity
        }

def generate_quiz_questions(level_id, tier='beginner', target_language='es', words=None):
    """Generate 5 quiz questions for a specific level using OpenAI"""

    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'hi': 'Hindi'
    }

    lang_name = language_names.get(target_language, 'Spanish')
    system_msg = "You are a language quiz generator. Always respond with valid JSON only — a JSON array of questions."

    if words:
        word_list = [w.get('word', '') for w in words]
        word_list_str = ", ".join(word_list)
        user_msg = f"""Generate 5 multiple-choice quiz questions using these specific {lang_name} words: {word_list_str}.
Each question should test one of these words. Level {level_id}.

Return a JSON array:
[{{"type":"multiple_choice","question":"What does 'XXXX' mean?","word":"XXXX","options":["A","B","C","D"],"correct":"A","language":"{target_language}"}}]"""
    else:
        tier_detail = {
            'beginner': f"absolute beginners, focus on basic vocabulary like greetings, numbers, food, family",
            'intermediate': f"intermediate learners, focus on descriptive and action words",
            'mastery': f"advanced learners, focus on complex vocabulary and idioms",
        }.get(tier, "absolute beginners")
        user_msg = f"""Generate 5 multiple-choice {lang_name} quiz questions for {tier_detail}. Level {level_id}.

Return a JSON array:
[{{"type":"multiple_choice","question":"...","word":"...","options":["A","B","C","D"],"correct":"A","language":"{target_language}"}}]"""

    try:
        raw = _chat(system_msg, user_msg, json_mode=True)
        if raw:
            questions = json.loads(raw)
            # Handle both array root and object wrapper like {"questions": [...]}
            if isinstance(questions, dict):
                questions = questions.get('questions', list(questions.values())[0])
            for q in questions:
                q['language'] = target_language
            return questions[:5]
    except Exception as e:
        print(f"[QUIZ_GEN] Error: {e}")

    return get_fallback_quiz(level_id, target_language, words)

def get_fallback_quiz(level_id, lang, words=None):
    """Generate deterministic fallback quiz"""
    
    # If words are provided, generate quiz from them
    if words and len(words) >= 4:
        questions = []
        all_meanings = [w.get('meaning', 'Unknown') for w in words]
        
        import random
        
        for w in words:
            word_str = w.get('word', '')
            correct_meaning = w.get('meaning', 'Unknown')
            
            # Pick distractors from other words
            distractors = [m for m in all_meanings if m != correct_meaning]
            if len(distractors) < 3:
                distractors += ["Option A", "Option B", "Option C"] # Ensure enough
            
            random.shuffle(distractors)
            opts = [correct_meaning] + distractors[:3]
            random.shuffle(opts)
            
            questions.append({
                "type": "multiple_choice", 
                "question": f"What does '{word_str}' mean?", 
                "word": word_str, 
                "options": opts, 
                "correct": correct_meaning, 
                "language": lang
            })
        return questions[:5]

    base_data = {
        'es': [
            {"q": "What is 'House'?", "w": "Casa", "o": ["Casa", "Perro", "Gato", "Agua"], "c": "Casa"},
            {"q": "Translate 'Hello'", "w": "Hola", "o": ["Hola", "Adiós", "Gracias", "Por favor"], "c": "Hola"},
            {"q": "What is 'Cat'?", "w": "Gato", "o": ["Gato", "Perro", "Casa", "Coche"], "c": "Gato"},
            {"q": "Translate 'Water'", "w": "Agua", "o": ["Agua", "Comida", "Aire", "Fuego"], "c": "Agua"},
            {"q": "What is 'Friend'?", "w": "Amigo", "o": ["Amigo", "Enemigo", "Padre", "Madre"], "c": "Amigo"}
        ],
        'fr': [
            {"q": "What is 'House'?", "w": "Maison", "o": ["Maison", "Chien", "Chat", "Eau"], "c": "Maison"},
            {"q": "Translate 'Hello'", "w": "Bonjour", "o": ["Bonjour", "Au revoir", "Merci", "S'il vous plaît"], "c": "Bonjour"},
            {"q": "What is 'Cat'?", "w": "Chat", "o": ["Chat", "Chien", "Maison", "Voiture"], "c": "Chat"},
            {"q": "Translate 'Water'", "w": "Eau", "o": ["Eau", "Nourriture", "Air", "Feu"], "c": "Eau"},
            {"q": "What is 'Friend'?", "w": "Ami", "o": ["Ami", "Ennemi", "Père", "Mère"], "c": "Ami"}
        ],
        # Add others as needed, default to ES
    }
    
    data = base_data.get(lang, base_data['es'])
    questions = []
    
    # Procedurally generate slightly different questions per level if possible, 
    # but for now just rotate the mapping or use static list
    # To avoid "same every level", we can rotate based on level_id
    
    for i in range(5):
        item = data[(level_id + i) % len(data)]
        questions.append({
            "type": "multiple_choice", 
            "question": f"{item['q']} (L{level_id})", # Add level to visual to prove it changes
            "word": item['w'], 
            "options": item['o'], 
            "correct": item['c'], 
            "language": lang
        })
        
    return questions
