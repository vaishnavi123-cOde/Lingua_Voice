"""
OpenAI API Service for Word Meanings and Definitions
Uses OpenAI's GPT models for comprehensive word information in multiple languages
"""
from openai import OpenAI
from typing import Dict, Optional
import json

class ContentResponse:
    """Wrapper class for OpenAI content response"""
    def __init__(self, text):
        self.text = text

class OpenAIWordService:
    """Service to get word meanings using OpenAI API"""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI API"""
        self.client = OpenAI(api_key=api_key)
        self.model = 'gpt-4o-mini'
        print("[OPENAI] Using model: gpt-4o-mini")
    
    def generate_content(self, prompt: str) -> Optional[ContentResponse]:
        """Generate content using OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful language learning assistant. Respond with valid JSON when requested."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            if response and response.choices:
                text = response.choices[0].message.content
                return ContentResponse(text)
            return None
        except Exception as e:
            print(f"[OPENAI] Error in generate_content: {e}")
            return None
        
    def get_word_meaning(self, word: str, language: str = 'en') -> Optional[Dict]:
        """
        Get comprehensive word meaning using OpenAI API
        
        Args:
            word: The word to get meaning for
            language: Language code (en, es, hi)
            
        Returns:
            Dictionary with word information or None
        """
        try:
            # Create language-specific prompt
            language_names = {
                'en': 'English',
                'es': 'Spanish',
                'hi': 'Hindi'
            }
            
            lang_name = language_names.get(language, 'English')
            
            # Simpler prompt that works better
            prompt = f"""Define the {lang_name} word "{word}" in one clear sentence.
Then provide:
- Part of speech
- Example sentence
- 2-3 synonyms

Format as JSON:
{{
  "definition": "your definition here",
  "partOfSpeech": "noun/verb/etc",
  "example": "example sentence",
  "synonyms": ["syn1", "syn2"]
}}"""
            
            print(f"[OPENAI] Requesting meaning for: {word} ({lang_name})")
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful language learning assistant. Respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            if not response or not response.choices:
                print(f"[OPENAI] No response for {word}")
                return None
            
            # Clean the response text
            text = response.choices[0].message.content.strip()
            print(f"[OPENAI] Raw response: {text[:150]}...")
            
            # Remove markdown code blocks if present
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            text = text.strip()
            
            # Try to parse JSON
            try:
                word_data = json.loads(text)
                
                formatted = {
                    'word': word,
                    'definition': word_data.get('definition', ''),
                    'partOfSpeech': word_data.get('partOfSpeech', ''),
                    'example': word_data.get('example', ''),
                    'synonyms': word_data.get('synonyms', [])[:5],
                    'translation': '',
                    'pronunciation': '',
                    'source': 'openai'
                }
                
                print(f"[OPENAI] ✓ Success: {formatted['definition'][:50]}...")
                return formatted
                
            except json.JSONDecodeError:
                # If JSON fails, extract definition from text
                print(f"[OPENAI] JSON parse failed, using text fallback")
                
                # Extract first sentence as definition
                sentences = text.split('.')
                definition = sentences[0].strip() if sentences else text[:150]
                
                return {
                    'word': word,
                    'definition': definition,
                    'partOfSpeech': '',
                    'example': '',
                    'synonyms': [],
                    'translation': '',
                    'pronunciation': '',
                    'source': 'openai_text'
                }
        
        except Exception as e:
            print(f"[OPENAI] Error for {word} ({language}): {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def validate_word(self, word: str, language: str = 'en') -> bool:
        """Check if a word is valid in the given language"""
        try:
            lang_names = {
                'en': 'English',
                'es': 'Spanish',
                'hi': 'Hindi'
            }
            
            lang_name = lang_names.get(language, 'English')
            
            prompt = f"""
            Is "{word}" a valid {lang_name} word?
            
            Answer with ONLY "YES" or "NO".
            - Answer YES if it's a real word (including slang, informal, or archaic)
            - Answer YES if it's a proper noun
            - Answer NO if it's gibberish, random characters, or not a word
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a language validator. Respond with only YES or NO."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            if response and response.choices:
                answer = response.choices[0].message.content.strip().upper()
                return 'YES' in answer
            
            return False
            
        except Exception as e:
            print(f"[OPENAI] Error validating {word}: {e}")
            return False

# Will be initialized in app.py
openai_service = None
