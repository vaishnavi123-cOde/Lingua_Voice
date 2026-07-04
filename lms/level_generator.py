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
        """Generate deterministic fallback words with a large pool and real meanings"""
        from dictionary_service import dictionary_service
        
        base_words = self._build_large_word_pool()
        
        vocab = base_words.get(lang, base_words['es'])
        
        words = []
        pool_size = len(vocab)
        if pool_size == 0:
            return words
        
        start_idx = ((level_num - 1) * 5) % pool_size
        
        for i in range(5):
            idx = (start_idx + i) % pool_size
            word_text = vocab[idx]
            definition = dictionary_service.get_meaning(word_text, lang)
            if definition:
                meaning = definition["meaning"]
                example = definition.get("explanation", meaning)
            else:
                meaning = word_text
                example = f"A word in {lang}."
            words.append({
                'word': word_text,
                'pronunciation': f'/{word_text}/',
                'meaning': meaning,
                'example': example,
            })
            
        return words
    
    def _build_large_word_pool(self):
        """Build a large word pool (500+ words per language) for fallback generation."""
        return {
            'es': [
                # Nivel 1-20: Objetos cotidianos, saludos, colores, números
                'casa', 'perro', 'gato', 'coche', 'playa', 'libro', 'escuela', 'hombre', 'mujer', 'niño',
                'agua', 'comida', 'tiempo', 'camino', 'dinero', 'familia', 'amigo', 'ciudad', 'mesa', 'silla',
                'ventana', 'puerta', 'teclado', 'ratón', 'papel', 'lápiz', 'bolígrafo', 'mochila', 'reloj', 'gafas',
                'pantalones', 'camisa', 'zapatos', 'calcetines', 'sombrero', 'abrigo', 'guantes', 'bufanda', 'bolso', 'llaves',
                'sol', 'luna', 'estrella', 'nube', 'lluvia', 'nieve', 'viento', 'tormenta', 'trueno', 'relámpago',
                'mar', 'río', 'lago', 'montaña', 'bosque', 'selva', 'desierto', 'valle', 'cerro', 'piedra',
                'rojo', 'azul', 'verde', 'amarillo', 'negro', 'blanco', 'gris', 'marrón', 'naranja', 'violeta',
                'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez',
                'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo', 'mes', 'año', 'siglo',
                # Nivel 21-40: Partes del cuerpo, emociones, acciones básicas
                'cabeza', 'mano', 'pie', 'brazo', 'pierna', 'ojo', 'oreja', 'boca', 'nariz', 'dedo',
                'feliz', 'triste', 'enojado', 'asustado', 'cansado', 'enfermo', 'nervioso', 'tranquilo', 'orgulloso', 'avergonzado',
                'comer', 'beber', 'dormir', 'caminar', 'correr', 'saltar', 'nadar', 'volar', 'sentarse', 'pararse',
                'hablar', 'decir', 'gritar', 'susurrar', 'cantar', 'reír', 'llorar', 'sonreír', 'bailar', 'jugar',
                'pensar', 'saber', 'creer', 'recordar', 'olvidar', 'entender', 'aprender', 'enseñar', 'estudiar', 'leer',
                'escribir', 'dibujar', 'pintar', 'cocinar', 'limpiar', 'lavar', 'planchar', 'coser', 'tejer', 'cultivar',
                # Nivel 41-60: Profesiones, viajes, comida
                'médico', 'enfermero', 'profesor', 'ingeniero', 'abogado', 'policía', 'bombero', 'cartero', 'panadero', 'cocinero',
                'piloto', 'conductor', 'actor', 'cantante', 'pintor', 'escritor', 'periodista', 'fotógrafo', 'arquitecto', 'dentista',
                'avión', 'tren', 'barco', 'bicicleta', 'autobús', 'taxi', 'moto', 'camión', 'helicóptero', 'metro',
                'hotel', 'restaurante', 'hospital', 'banco', 'museo', 'teatro', 'iglesia', 'parque', 'plaza', 'mercado',
                'manzana', 'naranja', 'plátano', 'uva', 'fresa', 'sandía', 'limón', 'cereza', 'pera', 'melocotón',
                'pan', 'leche', 'huevo', 'queso', 'carne', 'pescado', 'arroz', 'frijoles', 'ensalada', 'sopa',
                # Nivel 61-80: Conceptos abstractos, tecnología, naturaleza
                'amor', 'odio', 'paz', 'guerra', 'vida', 'muerte', 'sueño', 'esperanza', 'miedo', 'valor',
                'libertad', 'justicia', 'verdad', 'mentira', 'belleza', 'fealdad', 'riqueza', 'pobreza', 'sabiduría', 'ignorancia',
                'computadora', 'internet', 'teléfono', 'pantalla', 'teclado', 'ratón', 'cámara', 'vídeo', 'música', 'canción',
                'película', 'programa', 'aplicación', 'correo', 'mensaje', 'red', 'datos', 'archivo', 'imagen', 'sonido',
                'árbol', 'flor', 'hierba', 'semilla', 'raíz', 'hoja', 'rama', 'tronco', 'fruta', 'verdura',
                'animal', 'pájaro', 'pez', 'insecto', 'mariposa', 'abeja', 'hormiga', 'araña', 'serpiente', 'tortuga',
                # Nivel 81-100: Cultura, sociedad, expresiones avanzadas
                'cultura', 'idioma', 'costumbre', 'tradición', 'historia', 'leyenda', 'mito', 'cuento', 'poema', 'novela',
                'gobierno', 'presidente', 'ministro', 'senador', 'juez', 'ley', 'derecho', 'voto', 'elección', 'democracia',
                'educación', 'ciencia', 'arte', 'música', 'deporte', 'literatura', 'filosofía', 'religión', 'política', 'economía',
                'amable', 'generoso', 'honesto', 'humilde', 'valiente', 'leal', 'sincero', 'paciente', 'responsable', 'respetuoso',
                'inteligente', 'hábil', 'rápido', 'fuerte', 'sabio', 'creativo', 'curioso', 'audaz', 'ágil', 'eficiente',
                'profundo', 'amplio', 'duro', 'suave', 'ligero', 'pesado', 'ancho', 'estrecho', 'alto', 'bajo',
                'hermoso', 'horrible', 'extraño', 'maravilloso', 'peligroso', 'seguro', 'dulce', 'amargo', 'salado', 'ácido',
                # Más palabras nivel 81-100
                'felicidad', 'tristeza', 'bondad', 'maldad', 'honestidad', 'lealtad', 'humildad', 'paciencia', 'tolerancia', 'perseverancia',
                'agricultura', 'industria', 'comercio', 'turismo', 'minería', 'pesca', 'ganadería', 'construcción', 'transporte', 'comunicación',
                'matemáticas', 'física', 'química', 'biología', 'geografía', 'astronomía', 'geología', 'ecología', 'botánica', 'zoología',
                'democracia', 'monarquía', 'dictadura', 'república', 'federación', 'imperio', 'colonia', 'territorio', 'nación', 'estado',
                'pintura', 'escultura', 'arquitectura', 'literatura', 'poesía', 'teatro', 'cine', 'fotografía', 'dibujo', 'grabado',
                'energía', 'petróleo', 'carbón', 'gas', 'solar', 'eólica', 'nuclear', 'hidráulica', 'biomasa', 'geotérmica',
                'enfermedad', 'medicina', 'cirugía', 'terapia', 'diagnóstico', 'prevención', 'vacuna', 'epidemia', 'pandemia', 'salud',
                'desarrollo', 'crecimiento', 'progreso', 'innovación', 'invención', 'descubrimiento', 'investigación', 'exploración', 'experimento', 'teoría',
                'derechos', 'deberes', 'obligaciones', 'responsabilidades', 'privilegios', 'libertades', 'garantías', 'protección', 'seguridad', 'defensa',
                'reunión', 'conferencia', 'congreso', 'asamblea', 'consejo', 'comité', 'comisión', 'junta', 'panel', 'foro',
                'celebración', 'festival', 'ceremonia', 'rito', 'tradición', 'costumbre', 'conmemoración', 'homenaje', 'tributo', 'ofrenda',
                'conocimiento', 'sabiduría', 'inteligencia', 'razón', 'lógica', 'análisis', 'síntesis', 'deducción', 'inducción', 'abstracción',
                'valentía', 'coraje', 'audacia', 'determinación', 'persistencia', 'disciplina', 'voluntad', 'decisión', 'iniciativa', 'liderazgo',
                'compasión', 'empatía', 'solidaridad', 'generosidad', 'altruismo', 'bondad', 'amabilidad', 'cortesía', 'respeto', 'tolerancia',
                'admiración', 'aprecio', 'estimación', 'reconocimiento', 'gratitud', 'agradecimiento', 'respeto', 'veneración', 'devoción', 'lealtad',
                'maravilloso', 'espectacular', 'impresionante', 'fascinante', 'asombroso', 'extraordinario', 'increíble', 'magnífico', 'espléndido', 'soberbio',
                'delicado', 'sutil', 'refinado', 'elegante', 'distinguido', 'fino', 'exquisito', 'selecto', 'privilegiado', 'exclusivo',
                'abundante', 'copioso', 'numeroso', 'múltiple', 'diverso', 'variado', 'extenso', 'amplio', 'inmenso', 'infinito',
                'urgente', 'apremiante', 'impostergable', 'inaplazable', 'crítico', 'decisivo', 'fundamental', 'esencial', 'vital', 'primordial',
                'apacible', 'sereno', 'tranquilo', 'plácido', 'sosegado', 'calmado', 'pacífico', 'armonioso', 'equilibrado', 'estable',
            ],
            'fr': [
                'maison', 'chien', 'chat', 'voiture', 'plage', 'livre', 'école', 'homme', 'femme', 'enfant',
                'eau', 'nourriture', 'temps', 'chemin', 'argent', 'famille', 'ami', 'ville', 'table', 'chaise',
                'fenêtre', 'porte', 'clavier', 'souris', 'papier', 'crayon', 'stylo', 'sac', 'montre', 'lunettes',
                'pantalon', 'chemise', 'chaussures', 'chaussettes', 'chapeau', 'manteau', 'gants', 'écharpe', 'sac', 'clés',
                'soleil', 'lune', 'étoile', 'nuage', 'pluie', 'neige', 'vent', 'orage', 'tonnerre', 'éclair',
                'mer', 'rivière', 'lac', 'montagne', 'forêt', 'jungle', 'désert', 'vallée', 'colline', 'pierre',
                'rouge', 'bleu', 'vert', 'jaune', 'noir', 'blanc', 'gris', 'marron', 'orange', 'violet',
                'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix',
                'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche', 'mois', 'an', 'siècle',
                'tête', 'main', 'pied', 'bras', 'jambe', 'œil', 'oreille', 'bouche', 'nez', 'doigt',
                'heureux', 'triste', 'fâché', 'effrayé', 'fatigué', 'malade', 'nerveux', 'calme', 'fier', 'timide',
                'manger', 'boire', 'dormir', 'marcher', 'courir', 'sauter', 'nager', 'voler', 'asseoir', 'lever',
                'parler', 'dire', 'crier', 'chuchoter', 'chanter', 'rire', 'pleurer', 'sourire', 'danser', 'jouer',
                'penser', 'savoir', 'croire', 'se souvenir', 'oublier', 'comprendre', 'apprendre', 'enseigner', 'étudier', 'lire',
                'écrire', 'dessiner', 'peindre', 'cuisiner', 'nettoyer', 'laver', 'repasser', 'coudre', 'tricoter', 'cultiver',
                'médecin', 'infirmier', 'professeur', 'ingénieur', 'avocat', 'policier', 'pompier', 'facteur', 'boulanger', 'cuisinier',
                'pilote', 'conducteur', 'acteur', 'chanteur', 'peintre', 'écrivain', 'journaliste', 'photographe', 'architecte', 'dentiste',
                'avion', 'train', 'bateau', 'vélo', 'bus', 'taxi', 'moto', 'camion', 'hélicoptère', 'métro',
                'hôtel', 'restaurant', 'hôpital', 'banque', 'musée', 'théâtre', 'église', 'parc', 'place', 'marché',
                'pomme', 'orange', 'banane', 'raisin', 'fraise', 'pastèque', 'citron', 'cerise', 'poire', 'pêche',
                'pain', 'lait', 'œuf', 'fromage', 'viande', 'poisson', 'riz', 'haricots', 'salade', 'soupe',
                'amour', 'haine', 'paix', 'guerre', 'vie', 'mort', 'rêve', 'espoir', 'peur', 'courage',
                'liberté', 'justice', 'vérité', 'mensonge', 'beauté', 'laideur', 'richesse', 'pauvreté', 'sagesse', 'ignorance',
                'ordinateur', 'internet', 'téléphone', 'écran', 'clavier', 'souris', 'caméra', 'vidéo', 'musique', 'chanson',
                'film', 'programme', 'application', 'courrier', 'message', 'réseau', 'données', 'fichier', 'image', 'son',
                'arbre', 'fleur', 'herbe', 'graine', 'racine', 'feuille', 'branche', 'tronc', 'fruit', 'légume',
                'animal', 'oiseau', 'poisson', 'insecte', 'papillon', 'abeille', 'fourmi', 'araignée', 'serpent', 'tortue',
                'culture', 'langue', 'coutume', 'tradition', 'histoire', 'légende', 'mythe', 'conte', 'poème', 'roman',
                'gouvernement', 'président', 'ministre', 'sénateur', 'juge', 'loi', 'droit', 'vote', 'élection', 'démocratie',
                'éducation', 'science', 'art', 'musique', 'sport', 'littérature', 'philosophie', 'religion', 'politique', 'économie',
                'gentil', 'généreux', 'honnête', 'humble', 'courageux', 'loyal', 'sincère', 'patient', 'responsable', 'respectueux',
                'intelligent', 'habile', 'rapide', 'fort', 'sage', 'créatif', 'curieux', 'audacieux', 'agile', 'efficace',
                'profond', 'large', 'dur', 'doux', 'léger', 'lourd', 'étroit', 'haut', 'bas', 'beau',
            ],
            'de': [
                'Haus', 'Hund', 'Katze', 'Auto', 'Strand', 'Buch', 'Schule', 'Mann', 'Frau', 'Kind',
                'Wasser', 'Essen', 'Zeit', 'Weg', 'Geld', 'Familie', 'Freund', 'Stadt', 'Tisch', 'Stuhl',
                'Fenster', 'Tür', 'Tastatur', 'Maus', 'Papier', 'Bleistift', 'Kuli', 'Rucksack', 'Uhr', 'Brille',
                'Hose', 'Hemd', 'Schuhe', 'Socken', 'Hut', 'Mantel', 'Handschuhe', 'Schal', 'Tasche', 'Schlüssel',
                'Sonne', 'Mond', 'Stern', 'Wolke', 'Regen', 'Schnee', 'Wind', 'Sturm', 'Donner', 'Blitz',
                'Meer', 'Fluss', 'See', 'Berg', 'Wald', 'Dschungel', 'Wüste', 'Tal', 'Hügel', 'Stein',
                'rot', 'blau', 'grün', 'gelb', 'schwarz', 'weiß', 'grau', 'braun', 'orange', 'lila',
                'eins', 'zwei', 'drei', 'vier', 'fünf', 'sechs', 'sieben', 'acht', 'neun', 'zehn',
                'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag', 'Monat', 'Jahr', 'Jahrhundert',
                'Kopf', 'Hand', 'Fuß', 'Arm', 'Bein', 'Auge', 'Ohr', 'Mund', 'Nase', 'Finger',
                'glücklich', 'traurig', 'wütend', 'verängstigt', 'müde', 'krank', 'nervös', 'ruhig', 'stolz', 'schüchtern',
                'essen', 'trinken', 'schlafen', 'gehen', 'laufen', 'springen', 'schwimmen', 'fliegen', 'sitzen', 'stehen',
                'sprechen', 'sagen', 'schreien', 'flüstern', 'singen', 'lachen', 'weinen', 'lächeln', 'tanzen', 'spielen',
                'denken', 'wissen', 'glauben', 'erinnern', 'vergessen', 'verstehen', 'lernen', 'lehren', 'studieren', 'lesen',
                'schreiben', 'zeichnen', 'malen', 'kochen', 'putzen', 'waschen', 'bügeln', 'nähen', 'stricken', 'gärtnern',
                'Arzt', 'Krankenschwester', 'Lehrer', 'Ingenieur', 'Anwalt', 'Polizist', 'Feuerwehrmann', 'Briefträger', 'Bäcker', 'Koch',
                'Pilot', 'Fahrer', 'Schauspieler', 'Sänger', 'Maler', 'Schriftsteller', 'Journalist', 'Fotograf', 'Architekt', 'Zahnarzt',
                'Flugzeug', 'Zug', 'Schiff', 'Fahrrad', 'Bus', 'Taxi', 'Motorrad', 'LKW', 'Hubschrauber', 'U-Bahn',
                'Hotel', 'Restaurant', 'Krankenhaus', 'Bank', 'Museum', 'Theater', 'Kirche', 'Park', 'Platz', 'Markt',
                'Apfel', 'Orange', 'Banane', 'Traube', 'Erdbeere', 'Wassermelone', 'Zitrone', 'Kirsche', 'Birne', 'Pfirsich',
                'Brot', 'Milch', 'Ei', 'Käse', 'Fleisch', 'Fisch', 'Reis', 'Bohnen', 'Salat', 'Suppe',
                'Liebe', 'Hass', 'Frieden', 'Krieg', 'Leben', 'Tod', 'Traum', 'Hoffnung', 'Angst', 'Mut',
                'Freiheit', 'Gerechtigkeit', 'Wahrheit', 'Lüge', 'Schönheit', 'Hässlichkeit', 'Reichtum', 'Armut', 'Weisheit', 'Unwissenheit',
                'Computer', 'Internet', 'Telefon', 'Bildschirm', 'Tastatur', 'Maus', 'Kamera', 'Video', 'Musik', 'Lied',
                'Film', 'Programm', 'Anwendung', 'Post', 'Nachricht', 'Netzwerk', 'Daten', 'Datei', 'Bild', 'Klang',
                'Baum', 'Blume', 'Gras', 'Samen', 'Wurzel', 'Blatt', 'Ast', 'Stamm', 'Frucht', 'Gemüse',
                'Tier', 'Vogel', 'Fisch', 'Insekt', 'Schmetterling', 'Biene', 'Ameise', 'Spinne', 'Schlange', 'Schildkröte',
                'Kultur', 'Sprache', 'Brauch', 'Tradition', 'Geschichte', 'Legende', 'Mythos', 'Märchen', 'Gedicht', 'Roman',
                'Regierung', 'Präsident', 'Minister', 'Senator', 'Richter', 'Gesetz', 'Recht', 'Wahl', 'Demokratie',
                'Bildung', 'Wissenschaft', 'Kunst', 'Musik', 'Sport', 'Literatur', 'Philosophie', 'Religion', 'Politik', 'Wirtschaft',
                'freundlich', 'großzügig', 'ehrlich', 'bescheiden', 'mutig', 'treu', 'aufrichtig', 'geduldig', 'verantwortungsvoll', 'respektvoll',
                'intelligent', 'geschickt', 'schnell', 'stark', 'weise', 'kreativ', 'neugierig', 'kühn', 'wendig', 'effizient',
                'tief', 'breit', 'hart', 'weich', 'leicht', 'schwer', 'eng', 'schmal', 'groß', 'klein',
            ],
            'hi': [
                'घर', 'कुत्ता', 'बिल्ली', 'गाड़ी', 'समुद्र', 'किताब', 'विद्यालय', 'आदमी', 'औरत', 'बच्चा',
                'पानी', 'खाना', 'समय', 'रास्ता', 'पैसा', 'परिवार', 'दोस्त', 'शहर', 'मेज़', 'कुर्सी',
                'खिड़की', 'दरवाज़ा', 'कीबोर्ड', 'माउस', 'कागज़', 'पेंसिल', 'पेन', 'बैग', 'घड़ी', 'चश्मा',
                'पैंट', 'शर्ट', 'जूते', 'मोज़े', 'टोपी', 'कोट', 'दस्ताने', 'स्कार्फ़', 'थैला', 'चाबी',
                'सूरज', 'चाँद', 'तारा', 'बादल', 'बारिश', 'बर्फ़', 'हवा', 'तूफ़ान', 'गरज', 'बिजली',
                'समुद्र', 'नदी', 'झील', 'पहाड़', 'जंगल', 'वन', 'रेगिस्तान', 'घाटी', 'टीला', 'पत्थर',
                'लाल', 'नीला', 'हरा', 'पीला', 'काला', 'सफ़ेद', 'भूरा', 'नारंगी', 'बैंगनी', 'गुलाबी',
                'एक', 'दो', 'तीन', 'चार', 'पाँच', 'छह', 'सात', 'आठ', 'नौ', 'दस',
                'सोमवार', 'मंगलवार', 'बुधवार', 'गुरुवार', 'शुक्रवार', 'शनिवार', 'रविवार', 'महीना', 'साल', 'सदी',
                'सिर', 'हाथ', 'पैर', 'बाँह', 'टाँग', 'आँख', 'कान', 'मुँह', 'नाक', 'उँगली',
                'खुश', 'उदास', 'गुस्सा', 'डरा', 'थका', 'बीमार', 'घबराया', 'शांत', 'गर्व', 'शर्मीला',
                'खाना', 'पीना', 'सोना', 'चलना', 'दौड़ना', 'कूदना', 'तैरना', 'उड़ना', 'बैठना', 'खड़ा होना',
                'बोलना', 'कहना', 'चिल्लाना', 'फुसफुसाना', 'गाना', 'हँसना', 'रोना', 'मुस्कुराना', 'नाचना', 'खेलना',
                'सोचना', 'जानना', 'मानना', 'याद रखना', 'भूलना', 'समझना', 'सीखना', 'सिखाना', 'पढ़ना', 'लिखना',
                'डॉक्टर', 'नर्स', 'शिक्षक', 'इंजीनियर', 'वकील', 'पुलिस', 'फायरमैन', 'डाकिया', 'नानबाई', 'रसोइया',
                'पायलट', 'ड्राइवर', 'अभिनेता', 'गायक', 'चित्रकार', 'लेखक', 'पत्रकार', 'फ़ोटोग्राफ़र', 'वास्तुकार', 'दंत चिकित्सक',
                'हवाई जहाज़', 'रेल', 'जहाज़', 'साइकिल', 'बस', 'टैक्सी', 'मोटरसाइकिल', 'ट्रक', 'हेलीकॉप्टर', 'मेट्रो',
                'होटल', 'रेस्तरां', 'अस्पताल', 'बैंक', 'संग्रहालय', 'थिएटर', 'चर्च', 'पार्क', 'चौक', 'बाज़ार',
                'सेब', 'संतरा', 'केला', 'अंगूर', 'स्ट्रॉबेरी', 'तरबूज़', 'नींबू', 'चेरी', 'नाशपाती', 'आड़ू',
                'रोटी', 'दूध', 'अंडा', 'पनीर', 'मांस', 'मछली', 'चावल', 'दाल', 'सलाद', 'सूप',
                'प्यार', 'नफरत', 'शांति', 'युद्ध', 'जीवन', 'मृत्यु', 'सपना', 'उम्मीद', 'डर', 'साहस',
                'आज़ादी', 'न्याय', 'सच', 'झूठ', 'सुंदरता', 'बदसूरती', 'अमीरी', 'गरीबी', 'ज्ञान', 'अज्ञान',
                'कंप्यूटर', 'इंटरनेट', 'फ़ोन', 'स्क्रीन', 'कीबोर्ड', 'माउस', 'कैमरा', 'वीडियो', 'संगीत', 'गाना',
                'फ़िल्म', 'प्रोग्राम', 'ऐप', 'डाक', 'संदेश', 'नेटवर्क', 'डेटा', 'फ़ाइल', 'तस्वीर', 'आवाज़',
                'पेड़', 'फूल', 'घास', 'बीज', 'जड़', 'पत्ती', 'शाखा', 'तना', 'फल', 'सब्जी',
                'जानवर', 'पक्षी', 'मछली', 'कीड़ा', 'तितली', 'मधुमक्खी', 'चींटी', 'मकड़ी', 'साँप', 'कछुआ',
                'संस्कृति', 'भाषा', 'रिवाज', 'परंपरा', 'इतिहास', 'किंवदंती', 'मिथक', 'कहानी', 'कविता', 'उपन्यास',
                'सरकार', 'राष्ट्रपति', 'मंत्री', 'सीनेटर', 'न्यायाधीश', 'कानून', 'अधिकार', 'वोट', 'चुनाव', 'लोकतंत्र',
                'शिक्षा', 'विज्ञान', 'कला', 'संगीत', 'खेल', 'साहित्य', 'दर्शन', 'धर्म', 'राजनीति', 'अर्थव्यवस्था',
                'दयालु', 'उदार', 'ईमानदार', 'विनम्र', 'बहादुर', 'वफादार', 'सच्चा', 'धैर्यवान', 'जिम्मेदार', 'सम्मानजनक',
                'बुद्धिमान', 'कुशल', 'तेज़', 'मजबूत', 'ज्ञानी', 'रचनात्मक', 'जिज्ञासु', 'साहसी', 'फुर्तीला', 'कुशल',
                'गहरा', 'चौड़ा', 'कठोर', 'नरम', 'हल्का', 'भारी', 'संकीर्ण', 'ऊँचा', 'नीचा', 'सुंदर',
            ],
        }

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
