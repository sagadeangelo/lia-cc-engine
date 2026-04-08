import re
import unicodedata

def normalize_text(text: str) -> str:
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text

def split_into_scene_units(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    sentences = re.split(r"(?<=[\.\!\?])\s+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    scenes = []
    current_chunk = []
    current_length = 0
    break_words = ["entonces", "mientras tanto", "luego", "de repente", "al dia siguiente", "y acontecio"]
    for sentence in sentences:
        sentence_norm = normalize_text(sentence)
        should_split_before = False
        if current_chunk and current_length > 120:
             if any(sentence_norm.startswith(word) for word in break_words):
                 should_split_before = True
        if should_split_before:
            scenes.append(" ".join(current_chunk).strip())
            current_chunk = [sentence]
            current_length = len(sentence)
        else:
            current_chunk.append(sentence)
            current_length += len(sentence) + (1 if current_length > 0 else 0)
            if current_length >= 180:
                scenes.append(" ".join(current_chunk).strip())
                current_chunk = []
                current_length = 0
    if current_chunk:
        scenes.append(" ".join(current_chunk).strip())
    return scenes[:20]

test_text = """
Había una vez un pequeño pueblo en las montañas. La gente vivía feliz y en paz. 
Un día, un gran dragón apareció en el cielo nublado. Todos se asustaron mucho y corrieron a sus casas. 
Entonces, el valiente caballero decidió enfrentar a la bestia. Tomó su espada de plata y subió a la cima más alta. 
Mientras tanto, el pueblo rezaba por su seguridad. De repente, se escuchó un rugido ensordecedor que hizo temblar la tierra. 
Luego, el caballero regresó con una sonrisa, anunciando que el dragón era solo un sueño. 
Al día siguiente, todos celebraron una gran fiesta en la plaza principal. Fue el día más alegre que recordaban.
"""

scenes = split_into_scene_units(test_text)
print(f"Total escenas: {len(scenes)}")
for i, s in enumerate(scenes):
    print(f"Escena {i+1} ({len(s)} chars): {s}")
