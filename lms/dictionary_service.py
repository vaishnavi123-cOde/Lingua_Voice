"""
Dictionary Service — Multilingual dictionary with bilingual datasets.
Provides real word meanings, example sentences, and translations.
"""
import random
import json
import re


SPANISH_LEXICON = [
    ("casa", "house", "A building where people live."),
    ("perro", "dog", "A furry animal that barks and is kept as a pet."),
    ("gato", "cat", "A small furry animal that purrs and catches mice."),
    ("coche", "car", "A vehicle with four wheels used for travel."),
    ("playa", "beach", "A sandy or pebbly shore by the ocean."),
    ("libro", "book", "A set of printed pages for reading."),
    ("escuela", "school", "A place where children learn from teachers."),
    ("hombre", "man", "An adult male person."),
    ("mujer", "woman", "An adult female person."),
    ("niño", "child", "A young person below the age of puberty."),
    ("agua", "water", "A clear liquid that all living things need."),
    ("comida", "food", "Anything that people or animals eat."),
    ("tiempo", "time", "The ongoing sequence of events from past to future."),
    ("camino", "road", "A long narrow route for vehicles and people."),
    ("dinero", "money", "Coins or bills used to buy things."),
    ("familia", "family", "A group of related people living together."),
    ("amigo", "friend", "A person you like and enjoy being with."),
    ("ciudad", "city", "A large and important town."),
    ("mesa", "table", "A piece of furniture with a flat top."),
    ("silla", "chair", "A seat with a back for one person."),
    ("ventana", "window", "An opening in a wall with glass."),
    ("puerta", "door", "A movable barrier at the entrance to a room."),
    ("reloj", "clock", "An instrument that shows the time."),
    ("sol", "sun", "The bright star that gives light and heat to Earth."),
    ("luna", "moon", "The natural satellite that orbits Earth at night."),
    ("estrella", "star", "A bright point of light in the night sky."),
    ("nube", "cloud", "A white or gray mass of water vapor in the sky."),
    ("lluvia", "rain", "Water falling in drops from clouds."),
    ("nieve", "snow", "Soft white frozen water falling from clouds."),
    ("mar", "sea", "A large body of salt water."),
    ("río", "river", "A large natural flow of fresh water."),
    ("montaña", "mountain", "A very high natural hill."),
    ("bosque", "forest", "A large area covered with trees."),
    ("rojo", "red", "The color of blood or fire."),
    ("azul", "blue", "The color of the clear sky."),
    ("verde", "green", "The color of grass and leaves."),
    ("amarillo", "yellow", "The color of the sun or a lemon."),
    ("negro", "black", "The darkest color, like the night sky."),
    ("blanco", "white", "The lightest color, like snow."),
    ("grande", "big", "Large in size or extent."),
    ("pequeño", "small", "Little in size."),
    ("bueno", "good", "Of a high quality or standard."),
    ("malo", "bad", "Not good; of poor quality."),
    ("feliz", "happy", "Feeling or showing pleasure."),
    ("triste", "sad", "Feeling unhappy or sorrowful."),
    ("comer", "eat", "To take food into the mouth and swallow it."),
    ("beber", "drink", "To take liquid into the mouth and swallow."),
    ("dormir", "sleep", "To rest with eyes closed and become unconscious."),
    ("caminar", "walk", "To move at a regular pace by lifting each foot."),
    ("correr", "run", "To move faster than walking by springing steps."),
    ("hablar", "speak", "To say words with the mouth."),
    ("leer", "read", "To look at and understand written words."),
    ("escribir", "write", "To mark letters or words on a surface."),
    ("escuchar", "listen", "To pay attention to sound."),
    ("mirar", "look", "To direct eyes toward something."),
    ("pensar", "think", "To use the mind to form ideas."),
    ("saber", "know", "To have information in the mind."),
    ("querer", "want", "To have a desire for something."),
    ("poder", "can", "To be able to do something."),
    ("tener", "have", "To possess or own something."),
    ("hacer", "make", "To create or produce something."),
    ("decir", "say", "To speak words aloud."),
    ("poner", "put", "To place something somewhere."),
    ("salir", "leave", "To go away from a place."),
    ("llegar", "arrive", "To reach a destination."),
    ("trabajar", "work", "To do a job or task for money."),
    ("estudiar", "study", "To learn about a subject."),
    ("enseñar", "teach", "To give knowledge or instruction."),
    ("aprender", "learn", "To gain knowledge or skill."),
    ("jugar", "play", "To take part in games or fun activities."),
    ("cantar", "sing", "To make musical sounds with the voice."),
    ("bailar", "dance", "To move rhythmically to music."),
    ("cocinar", "cook", "To prepare food by heating it."),
    ("viajar", "travel", "To go on a journey."),
    ("comprar", "buy", "To get something by paying money."),
    ("vender", "sell", "To give something in exchange for money."),
    ("ayudar", "help", "To give support or assistance."),
    ("amar", "love", "To have deep affection for someone."),
    ("cabeza", "head", "The top part of the body with the brain and face."),
    ("mano", "hand", "The end part of the arm used for grasping."),
    ("pie", "foot", "The lower part of the leg used for standing."),
    ("brazo", "arm", "The upper limb from shoulder to hand."),
    ("pierna", "leg", "The limb from hip to foot used for walking."),
    ("ojo", "eye", "The organ used for seeing."),
    ("oreja", "ear", "The organ used for hearing."),
    ("boca", "mouth", "The opening used for eating and speaking."),
    ("nariz", "nose", "The organ used for smelling and breathing."),
    ("uno", "one", "The number 1."),
    ("dos", "two", "The number 2."),
    ("tres", "three", "The number 3."),
    ("cuatro", "four", "The number 4."),
    ("cinco", "five", "The number 5."),
    ("seis", "six", "The number 6."),
    ("siete", "seven", "The number 7."),
    ("ocho", "eight", "The number 8."),
    ("nueve", "nine", "The number 9."),
    ("diez", "ten", "The number 10."),
    ("lunes", "Monday", "The first day of the work week."),
    ("martes", "Tuesday", "The second day of the work week."),
    ("miércoles", "Wednesday", "The third day of the work week."),
    ("jueves", "Thursday", "The fourth day of the work week."),
    ("viernes", "Friday", "The fifth day of the work week."),
    ("sábado", "Saturday", "The sixth day of the week; weekend."),
    ("domingo", "Sunday", "The seventh day of the week; rest day."),
    ("amor", "love", "A strong feeling of deep affection."),
    ("paz", "peace", "A state of calm and harmony without conflict."),
    ("vida", "life", "The existence of a living being."),
    ("muerte", "death", "The end of life."),
    ("sueño", "dream", "A series of thoughts during sleep."),
    ("esperanza", "hope", "A feeling that something good will happen."),
    ("miedo", "fear", "An unpleasant feeling caused by danger."),
    ("libertad", "freedom", "The power to act as one wishes."),
    ("verdad", "truth", "That which is true or real."),
    ("belleza", "beauty", "A quality that pleases the senses."),
    ("hombre", "man", "An adult male human being."),
    ("señor", "mister", "A title used before a man's name."),
    ("gracias", "thank you", "An expression of gratitude."),
    ("adiós", "goodbye", "A farewell greeting."),
    ("hola", "hello", "A greeting used when meeting someone."),
    ("por favor", "please", "A polite word used when asking."),
    ("perdón", "sorry", "An apology for a mistake."),
    ("médico", "doctor", "A person trained to treat sick people."),
    ("profesor", "teacher", "A person who teaches in a school."),
    ("estudiante", "student", "A person who studies at school."),
    ("amable", "kind", "Generous and caring toward others."),
    ("inteligente", "intelligent", "Having a sharp and quick mind."),
    ("fuerte", "strong", "Having great physical power."),
    ("débil", "weak", "Lacking physical strength."),
    ("rápido", "fast", "Moving or able to move at high speed."),
    ("lento", "slow", "Moving or able to move only at a low speed."),
    ("nuevo", "new", "Not existing before; recently made."),
    ("viejo", "old", "Having existed for a long time."),
    ("joven", "young", "Having lived for only a short time."),
    ("caliente", "hot", "Having a high temperature."),
    ("frío", "cold", "Having a low temperature."),
    ("bonito", "pretty", "Pleasant to look at; attractive."),
    ("feo", "ugly", "Unpleasant to look at."),
    ("rico", "rich", "Having a lot of money or resources."),
    ("pobre", "poor", "Having little money or resources."),
    ("felicidad", "happiness", "The state of being happy and content."),
    ("tristeza", "sadness", "The state of feeling sorrowful."),
    ("valiente", "brave", "Ready to face and endure danger."),
    ("honesto", "honest", "Truthful and sincere in character."),
    ("orgulloso", "proud", "Feeling deep satisfaction from achievements."),
    ("humilde", "humble", "Having a modest view of one's importance."),
    ("luz", "light", "The natural brightness that makes things visible."),
    ("oscuridad", "darkness", "The absence of light."),
    ("flor", "flower", "The bloom of a plant."),
    ("árbol", "tree", "A tall plant with a trunk and leaves."),
    ("fruta", "fruit", "The sweet product of a tree or plant."),
    ("verdura", "vegetable", "A plant used as food."),
    ("animal", "animal", "A living creature that is not a plant."),
    ("pájaro", "bird", "A warm-blooded animal with wings and feathers."),
    ("pez", "fish", "A cold-blooded aquatic animal."),
    ("mariposa", "butterfly", "An insect with colorful wings."),
    ("abeja", "bee", "An insect that makes honey."),
    ("computadora", "computer", "An electronic device for processing data."),
    ("teléfono", "telephone", "A device for voice communication over distance."),
    ("música", "music", "Sounds arranged to create harmony and expression."),
    ("canción", "song", "A short piece of music with words."),
    ("película", "movie", "A story recorded as moving images."),
    ("deporte", "sport", "A physical activity played for enjoyment."),
    ("juego", "game", "An activity done for fun or competition."),
    ("cultura", "culture", "The customs and beliefs of a group of people."),
    ("historia", "history", "The study of past events."),
    ("ciencia", "science", "The study of the natural world."),
    ("arte", "art", "Creative expression through painting, music, etc."),
    ("naturaleza", "nature", "The physical world and living things."),
    ("montaña", "mountain", "A very high natural elevation of land."),
    ("océano", "ocean", "A very large sea."),
    ("isla", "island", "A piece of land surrounded by water."),
    ("hermano", "brother", "A male sibling."),
    ("hermana", "sister", "A female sibling."),
    ("padre", "father", "A male parent."),
    ("madre", "mother", "A female parent."),
    ("abuelo", "grandfather", "The father of one's parent."),
    ("abuela", "grandmother", "The mother of one's parent."),
    ("hijo", "son", "A male child of a parent."),
    ("hija", "daughter", "A female child of a parent."),
    ("tío", "uncle", "The brother of one's parent."),
    ("tía", "aunt", "The sister of one's parent."),
    ("primo", "cousin", "The child of one's aunt or uncle."),
]

HINDI_LEXICON = [
    ("पानी", "water", "A clear liquid that all living things need."),
    ("किताब", "book", "A set of printed pages for reading."),
    ("दोस्त", "friend", "A person you like and enjoy being with."),
    ("घर", "house", "A building where people live."),
    ("खाना", "food", "Anything that people or animals eat."),
    ("पानी", "water", "A clear liquid essential for life."),
    ("सूरज", "sun", "The bright star that gives light to Earth."),
    ("चाँद", "moon", "The natural satellite that orbits Earth."),
    ("आदमी", "man", "An adult male human being."),
    ("औरत", "woman", "An adult female human being."),
    ("बच्चा", "child", "A young person."),
    ("स्कूल", "school", "A place where children learn."),
    ("कुत्ता", "dog", "A furry animal that barks."),
    ("बिल्ली", "cat", "A small furry animal that purrs."),
    ("हाथ", "hand", "The end part of the arm used for grasping."),
    ("पैर", "foot", "The lower part of the leg used for standing."),
    ("आँख", "eye", "The organ used for seeing."),
    ("कान", "ear", "The organ used for hearing."),
    ("मुँह", "mouth", "The opening used for eating and speaking."),
    ("नाक", "nose", "The organ used for smelling."),
    ("लाल", "red", "The color of blood or fire."),
    ("नीला", "blue", "The color of the clear sky."),
    ("हरा", "green", "The color of grass and leaves."),
    ("पीला", "yellow", "The color of the sun or a lemon."),
    ("काला", "black", "The darkest color, like the night sky."),
    ("सफ़ेद", "white", "The lightest color, like snow."),
    ("एक", "one", "The number 1."),
    ("दो", "two", "The number 2."),
    ("तीन", "three", "The number 3."),
    ("चार", "four", "The number 4."),
    ("पाँच", "five", "The number 5."),
    ("अच्छा", "good", "Of a high quality or standard."),
    ("बुरा", "bad", "Not good; of poor quality."),
    ("खुश", "happy", "Feeling or showing pleasure."),
    ("उदास", "sad", "Feeling unhappy or sorrowful."),
    ("बड़ा", "big", "Large in size or extent."),
    ("छोटा", "small", "Little in size."),
    ("प्यार", "love", "A strong feeling of deep affection."),
    ("शांति", "peace", "A state of calm and harmony."),
    ("सच", "truth", "That which is true or real."),
    ("झूठ", "lie", "A false statement made intentionally."),
    ("सपना", "dream", "A series of thoughts during sleep."),
    ("डर", "fear", "An unpleasant feeling caused by danger."),
    ("आज़ादी", "freedom", "The power to act as one wishes."),
    ("उम्मीद", "hope", "A feeling that something good will happen."),
    ("रोटी", "bread", "A baked food made from flour."),
    ("दूध", "milk", "A white liquid produced by mammals."),
    ("पैसा", "money", "Coins or bills used to buy things."),
    ("समय", "time", "The ongoing sequence of events."),
    ("दिन", "day", "A period of 24 hours."),
    ("रात", "night", "The period of darkness each day."),
    ("पेड़", "tree", "A tall plant with a trunk and leaves."),
    ("फूल", "flower", "The bloom of a plant."),
    ("जानवर", "animal", "A living creature that is not a plant."),
    ("पक्षी", "bird", "A warm-blooded animal with wings."),
    ("मछली", "fish", "A cold-blooded aquatic animal."),
    ("तारा", "star", "A bright point of light in the night sky."),
    ("बादल", "cloud", "A white or gray mass of water vapor."),
    ("हवा", "air", "The invisible gas that surrounds Earth."),
]

ENGLISH_LEXICON = [
    ("apple", "A round fruit that is red, green, or yellow.", "A round fruit that is usually red, green, or yellow with a crisp texture."),
    ("house", "A building where people live.", "A building or structure where people live."),
    ("dog", "A furry pet that barks.", "A domesticated animal with four legs that barks."),
    ("cat", "A small pet that purrs.", "A small domesticated furry animal that purrs."),
    ("car", "A vehicle with four wheels.", "A road vehicle with four wheels powered by an engine."),
    ("book", "Pages bound together for reading.", "A set of written or printed pages bound together."),
    ("water", "A clear liquid we drink.", "A clear colorless liquid essential for life."),
    ("food", "What people and animals eat.", "Any substance consumed to provide nutrition."),
    ("friend", "A person you like.", "A person with whom you share a bond of mutual affection."),
    ("family", "A group of related people.", "A group of people related by blood or marriage."),
    ("school", "A place for learning.", "An institution where children receive education."),
    ("teacher", "A person who teaches.", "A person who helps students learn."),
    ("student", "A person who learns.", "A person who attends school for education."),
    ("happy", "Feeling joy or pleasure.", "Feeling or showing pleasure or contentment."),
    ("sad", "Feeling unhappiness.", "Feeling sorrow or unhappiness."),
    ("big", "Large in size.", "Of considerable size or extent."),
    ("small", "Little in size.", "Of a size that is less than average."),
    ("beautiful", "Very pleasing to look at.", "Having qualities that delight the senses."),
    ("run", "Move faster than walking.", "To move at a speed faster than walking."),
    ("walk", "Move at a regular pace.", "To move at a regular pace by lifting each foot."),
    ("eat", "Take food into the mouth.", "To take food into the mouth and swallow it."),
    ("drink", "Take liquid into the mouth.", "To take a liquid into the mouth and swallow."),
    ("sleep", "Rest with closed eyes.", "To rest with eyes closed in a natural state of rest."),
    ("read", "Look at written words.", "To look at and understand written or printed words."),
    ("write", "Mark letters on paper.", "To mark letters, words, or symbols on a surface."),
    ("speak", "Say words aloud.", "To say words using the voice."),
    ("learn", "Gain knowledge or skill.", "To gain knowledge or skill through study."),
    ("teach", "Give knowledge to others.", "To give knowledge or instruction to others."),
    ("play", "Engage in fun activities.", "To take part in activities for enjoyment."),
    ("love", "Deep affection for someone.", "An intense feeling of deep affection."),
    ("time", "The ongoing sequence of events.", "The indefinite continued progress of existence."),
    ("money", "Coins or bills used to buy.", "A medium of exchange used to buy goods."),
    ("sun", "The star that lights Earth.", "The star around which Earth orbits."),
    ("moon", "Earth's natural satellite.", "The natural satellite of Earth visible at night."),
    ("star", "A bright point in the night sky.", "A fixed luminous point in the night sky."),
    ("rain", "Water falling from clouds.", "Water that falls from clouds in drops."),
    ("snow", "Frozen water from clouds.", "Frozen water vapor falling as white flakes."),
    ("tree", "A tall plant with a trunk.", "A tall plant with a wooden trunk and branches."),
    ("flower", "The bloom of a plant.", "The seed-bearing part of a plant with petals."),
    ("animal", "A living creature.", "A living organism that is not a plant."),
    ("bird", "An animal with wings.", "A warm-blooded animal with feathers and wings."),
    ("fish", "An aquatic animal.", "A cold-blooded animal that lives in water."),
    ("computer", "An electronic device.", "An electronic device for processing data."),
    ("internet", "A global computer network.", "A global network connecting millions of computers."),
    ("phone", "A device for calls.", "A device used for voice communication."),
    ("music", "Arranged sounds and silence.", "Sounds arranged to create harmony and expression."),
    ("song", "A piece of music with words.", "A short musical composition with lyrics."),
    ("color", "A visual property of things.", "The property of objects seen as red, blue, green, etc."),
    ("number", "A mathematical value.", "A count or measurement expressed as a figure."),
    ("city", "A large town.", "A large and important town or urban center."),
    ("country", "A nation.", "A nation with its own government and territory."),
    ("world", "The planet Earth.", "The planet Earth and all its inhabitants."),
    ("ocean", "A vast body of salt water.", "A very large expanse of salt water."),
    ("mountain", "A very high hill.", "A large natural elevation of the earth's surface."),
    ("river", "A natural water flow.", "A large natural stream of water."),
    ("sea", "A large body of salt water.", "A large expanse of salt water part of an ocean."),
    ("hand", "End of the arm for grasping.", "The end part of the arm used for holding."),
    ("eye", "The organ for seeing.", "The organ of sight in humans and animals."),
    ("ear", "The organ for hearing.", "The organ of hearing in humans and animals."),
    ("mouth", "The opening for eating.", "The opening in the face used for eating and speaking."),
    ("nose", "The organ for smelling.", "The organ of smell in humans and animals."),
    ("head", "The top part of the body.", "The upper part of the body containing the brain."),
    ("arm", "Upper limb from shoulder.", "The upper limb of the body from shoulder to hand."),
    ("leg", "Lower limb for walking.", "The lower limb of the body used for walking."),
    ("foot", "Lower part of the leg.", "The lower extremity of the leg below the ankle."),
]

FRENCH_LEXICON = [
    ("maison", "house", "A building where people live."),
    ("chien", "dog", "A furry animal that barks and is kept as a pet."),
    ("chat", "cat", "A small furry animal that purrs and catches mice."),
    ("voiture", "car", "A vehicle with four wheels used for travel."),
    ("livre", "book", "A set of printed pages for reading."),
    ("eau", "water", "A clear liquid that all living things need."),
    ("nourriture", "food", "Anything that people or animals eat."),
    ("ami", "friend", "A person you like and enjoy being with."),
    ("école", "school", "A place where children learn from teachers."),
    ("soleil", "sun", "The bright star that gives light and heat to Earth."),
    ("lune", "moon", "The natural satellite that orbits Earth at night."),
    ("ciel", "sky", "The space above the Earth seen from the ground."),
    ("mer", "sea", "A large body of salt water."),
    ("montagne", "mountain", "A very high natural hill."),
    ("arbre", "tree", "A tall plant with a trunk and leaves."),
    ("fleur", "flower", "The bloom of a plant."),
    ("rouge", "red", "The color of blood or fire."),
    ("bleu", "blue", "The color of the clear sky."),
    ("vert", "green", "The color of grass and leaves."),
    ("jaune", "yellow", "The color of the sun or a lemon."),
    ("noir", "black", "The darkest color, like the night sky."),
    ("blanc", "white", "The lightest color, like snow."),
]

LEXICONS = {
    "es": SPANISH_LEXICON,
    "hi": HINDI_LEXICON,
    "en": ENGLISH_LEXICON,
    "fr": FRENCH_LEXICON,
}

LEXICON_DICT = {}
for lang, entries in LEXICONS.items():
    LEXICON_DICT[lang] = {}
    for entry in entries:
        word = entry[0].lower()
        LEXICON_DICT[lang][word] = {
            "meaning": entry[1],
            "explanation": entry[2] if len(entry) > 2 else entry[1],
        }


class DictionaryService:

    def get_meaning(self, word, language="es", target_language="en"):
        word_lower = word.lower().strip()
        lang_dict = LEXICON_DICT.get(language, {})
        if word_lower in lang_dict:
            return {
                "word": word,
                "meaning": lang_dict[word_lower]["meaning"],
                "explanation": lang_dict[word_lower]["explanation"],
                "language": language,
                "source": "builtin",
            }

        if language == "en":
            api_result = self._try_freedict_api(word_lower)
            if api_result:
                return api_result

        if language != "en":
            en_dict = LEXICON_DICT.get("en", {})
            if word_lower in en_dict:
                return {
                    "word": word,
                    "meaning": en_dict[word_lower]["meaning"],
                    "explanation": en_dict[word_lower]["explanation"],
                    "language": language,
                    "source": "builtin_en",
                    "note": f"Translation from English lexicon for {word}",
                }

        ai_result = self._try_openai(word, language)
        if ai_result:
            return ai_result

        return None

    def _try_openai(self, word, language):
        try:
            from openai import OpenAI
            from config import OPENAI_API_KEY
            if not OPENAI_API_KEY:
                return None
            client = OpenAI(api_key=OPENAI_API_KEY)
            lang_map = {"es": "Spanish", "hi": "Hindi", "en": "English", "fr": "French"}
            lang_name = lang_map.get(language, language)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a bilingual dictionary. Return ONLY valid JSON."},
                    {"role": "user", "content": f'Return JSON for the {lang_name} word "{word}": {{"meaning":"English meaning","explanation":"short learner-friendly explanation","example":"example sentence in {lang_name}","translation":"English translation of example"}}'}
                ],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content
            if text:
                import json
                data = json.loads(text)
                result = {
                    "word": word,
                    "meaning": data.get("meaning", word),
                    "explanation": data.get("explanation", data.get("meaning", word)),
                    "language": language,
                    "source": "openai",
                }
                if data.get("example"):
                    result["example"] = data["example"]
                if data.get("translation"):
                    result["example_translation"] = data["translation"]
                return result
        except Exception:
            pass
        return None

    def generate_rich_definition(self, word, language="es"):
        result = self.get_meaning(word, language)
        if result:
            if not result.get("example"):
                result["example"] = self._generate_example(word, result["meaning"])
            if not result.get("example_translation"):
                result["example_translation"] = self._translate_example(
                    result.get("example", ""), language, result["meaning"]
                )
            return result
        return None

    def ensure_meaning(self, word, language="es"):
        """Get meaning or return None — never generate placeholders."""
        return self.get_meaning(word, language)

    def enrich_words(self, words, language="es"):
        """Take a list of word dicts and fill in real meanings."""
        enriched = []
        for w in words:
            word_text = w.get("word", w) if isinstance(w, dict) else w
            if isinstance(w, dict):
                entry = w.copy()
            else:
                entry = {"word": word_text, "language": language}

            existing_meaning = entry.get("meaning", "")
            if existing_meaning and not _is_placeholder(existing_meaning, word_text):
                enriched.append(entry)
                continue

            definition = self.get_meaning(word_text, language)
            if definition:
                entry["meaning"] = definition["meaning"]
                entry["explanation"] = definition.get("explanation", definition["meaning"])
            else:
                entry["meaning"] = ""
                entry["explanation"] = ""
                entry["meaning_unavailable"] = True

            enriched.append(entry)

        return enriched

    def _try_freedict_api(self, word):
        try:
            import urllib.request
            import json
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            req = urllib.request.Request(url, headers={"User-Agent": "LinguaVoice/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                if data and len(data) > 0:
                    meanings = data[0].get("meanings", [])
                    if meanings:
                        defs = meanings[0].get("definitions", [])
                        if defs:
                            meaning_text = defs[0].get("definition", "")
                            return {
                                "word": word,
                                "meaning": meaning_text,
                                "explanation": meaning_text,
                                "language": "en",
                                "source": "freedict_api",
                            }
        except Exception:
            pass
        return None

    def _generate_example(self, word, meaning):
        templates = [
            f"The word '{word}' is commonly used in daily conversation.",
            f"'{word}' refers to {meaning.lower() if meaning else word}.",
            f"Learning the word '{word}' helps you express yourself better.",
        ]
        return random.choice(templates)

    def _translate_example(self, sentence, lang, meaning):
        return f"Meaning: {meaning}"


def _is_placeholder(text, word=None):
    if not text or not isinstance(text, str):
        return True
    text_lower = text.strip().lower()
    if text_lower in ("", "unknown", "loading...", "definition pending", "none", "null"):
        return True
    if word and f"meaning of {word.lower()}" in text_lower:
        return True
    if word and text_lower == word.lower():
        return True
    return False


dictionary_service = DictionaryService()
