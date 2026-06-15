"""
Learning Level Generator for 100-Level Progressive System
Generates difficulty-appropriate content using OpenAI
"""
import openai_service
import json

class LevelGenerator:
    """Generate learning levels with progressive difficulty"""
    
    def __init__(self):
        self.difficulty_tiers = {
            'beginner': (1, 30),
            'intermediate': (31, 60),
            'mastery': (61, 100)
        }
    
    def get_difficulty_tier(self, level_num):
        """Get difficulty tier for a level"""
        if level_num <= 30:
            return 'beginner'
        elif level_num <= 60:
            return 'intermediate'
        else:
            return 'mastery'
    
    def generate_level_content(self, level_num, target_language='es', exclude_words=None):
        """Generate 5 words for a specific level using AI, avoiding excluded words and concepts"""
        tier = self.get_difficulty_tier(level_num)
        
        exclude_str = ""
        if exclude_words:
            # Limit exclude string to last 100 words to avoid prompt bloat, but prioritize most recent
            subset = exclude_words[-100:] if len(exclude_words) > 100 else exclude_words
            exclude_str = f" CRITICAL: Do NOT use any of these words or their direct translations: {', '.join(subset)}."

        # Create AI prompt based on difficulty
        prompts = {
            'beginner': f"List 5 essential {target_language} words for beginners (Level {level_num}).{exclude_str} Each word must be a common daily object or concept.",
            'intermediate': f"List 5 intermediate {target_language} words (Level {level_num}).{exclude_str} Focus on abstract nouns, emotions, or professional terms.",
            'mastery': f"List 5 advanced {target_language} words (Level {level_num}).{exclude_str} Focus on idioms, academic terms, or nuanced verbs."
        }
        
        try:
            import random
            variations = ["common", "useful", "popular", "essential", "daily", "practical", "interesting", "contextual"]
            variation = random.choice(variations)
            
            final_prompt = f"""{prompts[tier]}
Make them completely unique and different from previous levels. 
Focus on {variation} vocabulary. 
Return exactly 5 UNIQUE objects in JSON format: 
[
  {{"word": "target_word", "pronunciation": "/phonetic/", "meaning": "English meaning", "example": "Sentence using word"}}
]
Ensure the words are distinctly different from children's basic level 1 words unless specifically requested. 
The 'meaning' field should be a concise English translation."""
            
            response = openai_service.openai_service.generate_content(final_prompt)
            if response and response.text:
                text = response.text.strip()
                # Remove markdown
                if text.startswith('```json'): text = text[7:]
                if text.startswith('```'): text = text[3:]
                if text.endswith('```'): text = text[:-3]
                text = text.strip()
                
                # Parse JSON
                words = json.loads(text)
                
                # Double check uniqueness against exclusion list
                unique_words = []
                seen_in_current = set()
                exclude_set = set(w.lower() for w in (exclude_words or []))
                
                for w in words:
                    w_text = w.get('word', '').lower()
                    m_text = w.get('meaning', '').lower().split('(')[0].strip()
                    
                    # Skip if word OR meaning seen before
                    if w_text and w_text not in exclude_set and w_text not in seen_in_current:
                        # Also check if meaning (concept) is already learned
                        if m_text not in exclude_set:
                            unique_words.append(w)
                            seen_in_current.add(w_text)
                
                if len(unique_words) >= 5:
                    return unique_words[:5]
                elif len(unique_words) > 0:
                    # Supplement with fallback if some were filtered
                    fallbacks = self.get_fallback_words(level_num, target_language)
                    for fw in fallbacks:
                        if len(unique_words) >= 5: break
                        if fw['word'].lower() not in exclude_set and fw['word'].lower() not in seen_in_current:
                            unique_words.append(fw)
                    return unique_words[:5]
        except Exception as e:
            print(f"[LEVEL_GEN] Error generating level {level_num}: {e}")
        
        # Fallback Procedural Generation
        return self.get_fallback_words(level_num, target_language)

    def get_fallback_words(self, level_num, lang):
        """Generate deterministic fallback words with a much larger pool to avoid repeats"""
        # Expanded vocabulary for 100 levels (at least 500 words per lang ideally, but let's provide a solid base)
        base_words = {
            'es': [
                'casa', 'perro', 'gato', 'coche', 'playa', 'libro', 'escuela', 'hombre', 'mujer', 'niño', 
                'agua', 'comida', 'tiempo', 'camino', 'dinero', 'familia', 'amigo', 'ciudad', 'mesa', 'silla',
                'ventana', 'puerta', 'teclado', 'raton', 'papel', 'lapiz', 'boligrafo', 'mochila', 'reloj', 'gafas',
                'pantalones', 'camisa', 'zapatos', 'calcetines', 'sombrero', 'abrigos', 'guantes', 'bufanda', 'bolso', 'llaves',
                'sol', 'luna', 'estrellas', 'nubes', 'lluvia', 'nieve', 'viento', 'tormenta', 'trueno', 'relampago',
                'mar', 'rio', 'lago', 'montaña', 'bosque', 'selva', 'desierto', 'valle', 'cerro', 'piedra'
            ],
            'fr': [
                'maison', 'chien', 'chat', 'voiture', 'plage', 'livre', 'école', 'homme', 'femme', 'enfant', 
                'eau', 'nourriture', 'temps', 'chemin', 'argent', 'famille', 'ami', 'ville', 'table', 'chaise',
                'fenêtre', 'porte', 'clavier', 'souris', 'papier', 'crayon', 'stylo', 'sac', 'montre', 'lunettes',
                'pantalon', 'chemise', 'chaussures', 'chaussettes', 'chapeau', 'manteau', 'gants', 'écharpe', 'sac', 'clés',
                'soleil', 'lune', 'étoiles', 'nuages', 'pluie', 'neige', 'vent', 'orage', 'tonnerre', 'éclair',
                'mer', 'rivière', 'lac', 'montagne', 'forêt', 'jungle', 'désert', 'vallée', 'colline', 'pierre'
            ],
            'de': [
                'Haus', 'Hund', 'Katze', 'Auto', 'Strand', 'Buch', 'Schule', 'Mann', 'Frau', 'Kind', 
                'Wasser', 'Essen', 'Zeit', 'Weg', 'Geld', 'Familie', 'Freund', 'Stadt', 'Tisch', 'Stuhl',
                'Fenster', 'Tür', 'Tastatur', 'Maus', 'Papier', 'Bleistift', 'Kuli', 'Rucksack', 'Uhr', 'Brille',
                'Hose', 'Hemd', 'Schuhe', 'Socken', 'Hut', 'Mantel', 'Handschuhe', 'Schal', 'Tasche', 'Schlüssel',
                'Sonne', 'Mond', 'Sterne', 'Wolken', 'Regen', 'Schnee', 'Wind', 'Sturm', 'Donner', 'Blitz',
                'Meer', 'Fluss', 'See', 'Berg', 'Wald', 'Dschungel', 'Wüste', 'Tal', 'Hügel', 'Stein'
            ],
            'hi': [
                'ghar', 'kutta', 'billi', 'gaadi', 'samundar', 'kitab', 'vidyalay', 'aadmi', 'aurat', 'bacha', 
                'paani', 'khana', 'samay', 'rasta', 'paisa', 'parivaar', 'dost', 'shahar', 'mez', 'kursi',
                'khidki', 'darwaza', 'keyboard', 'mouse', 'kaagaz', 'pencil', 'pen', 'bag', 'ghadi', 'chashma',
                'pant', 'shirt', 'jute', 'moze', 'topi', 'coat', ' दस्ताने (dastaane)', 'scary', 'jhola', 'chabi',
                'suraj', 'chaand', 'taare', 'badal', 'baarish', 'barf', 'hawa', 'toofan', 'garaj', 'bijli',
                'samudra', 'nadi', 'jheel', 'pahar', 'jungle', 'van', 'registan', 'ghati', 'tila', 'patthar'
            ]
        }
        
        vocab = base_words.get(lang, base_words['es'])
        
        # Use a better offset to ensure uniqueness across levels
        words = []
        import random
        # Seed with level_num for determinism per level, but offset it
        state = random.getstate()
        random.seed(level_num + hash(lang) % 1000)
        
        # Shuffle a copy
        pool = list(vocab)
        random.shuffle(pool)
        
        for i in range(min(5, len(pool))):
            word = pool[i]
            words.append({
                'word': word, 
                'pronunciation': f'/{word}/', 
                'meaning': f'Meaning of {word}', 
                'example': f'This is {word} in context.'
            })
            
        random.setstate(state) # Restore random state
        return words
    
    def get_level_metadata(self, level_num):
        """Get metadata for a level"""
        tier = self.get_difficulty_tier(level_num)
        
        themes = {
            'beginner': [
                "Greetings & Basics", "Numbers & Counting", "Family & Friends",
                "Food & Drinks", "Colors & Shapes", "Daily Routine",
                "Body Parts", "Weather", "Animals", "Common Objects",
                "Basic Verbs", "Time & Days", "Places", "Clothing",
                "House & Home", "Emotions", "School", "Transportation",
                "Fruits & Vegetables", "Simple Questions", "Directions",
                "Shopping", "Restaurant", "Travel Essentials", "Sports",
                "Music", "Hobbies", "Nature", "Occupations", "Quantities"
            ],
            'intermediate': [
                "Complex Emotions", "Abstract Concepts", "Professional Life",
                "Technology", "Health & Wellness", "Cultural Topics",
                "Politics & Society", "Environment", "Economics",
                "Education System", "Legal Terms", "Psychology",
                "Philosophy", "History", "Science", "Art & Literature",
                "Media & Entertainment", "Social Issues", "Ethics",
                "Religion & Beliefs", "Relationships", "Communication",
                "Business", "Marketing", "Finance", "Innovation",
                "Global Issues", "Sustainability", "Urban Life", "Rural Life"
            ],
            'mastery': [
                "Idiomatic Expressions", "Advanced Grammar", "Literary Devices",
                "Figurative Language", "Regional Dialects", "Formal Writing",
                "Academic Discourse", "Technical Jargon", "Specialized Fields",
                "Nuanced Meanings", "Cultural Idioms", "Historical Terms",
                "Philosophical Concepts", "Scientific Terminology", "Legal Language",
                "Medical Vocabulary", "Poetic Expressions", "Rhetorical Devices",
                "Complex Syntax", "Abstract Theory", "Industry Specific",
                "Research Terminology", "Advanced Composition", "Critical Analysis",
                "Semantic Nuances", "Contextual Usage", "Professional Discourse",
                "Expert Communication", "Specialized Topics", "Mastery Synthesis",
                "Academic Excellence", "Professional Mastery", "Cultural Fluency",
                "Native-Level Expression", "Complete Fluency", "Language Mastery",
                "Expert Proficiency", "Total Command", "Ultimate Mastery", "Certification Ready"
            ]
        }
        
        tier_themes = themes[tier]
        theme_index = (level_num - 1) % len(tier_themes)
        
        return {
            'title': tier_themes[theme_index],
            'xp': 50 + (level_num * 2),  # Progressive XP
            'tier': tier.capitalize(),
            'icon': self._get_level_icon(level_num, tier)
        }
    
    def _get_level_icon(self, level_num, tier):
        """Get appropriate emoji for level"""
        if tier == 'beginner':
            icons = ["👋", "🔢", "👨‍👩‍👧", "🍕", "🌈", "⏰", "💪", "⛅", "🐕", "📱"]
            return icons[(level_num - 1) % len(icons)]
        elif tier == 'intermediate':
            icons = ["🎓", "💼", "🌍", "🏥", "🎨", "📚", "🔬", "🏛️", "🎭", "🎵"]
            return icons[(level_num - 31) % len(icons)]
        else:
            icons = ["🏆", "👑", "💎", "🎖️", "⭐", "🔥", "💫", "🌟", "✨", "👨‍🎓"]
            return icons[(level_num - 61) % len(icons)]

# Global instance
level_generator = LevelGenerator()
