from __future__ import annotations

from pathlib import Path
import sys
import re
import unicodedata

# Add root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR
from scripts.utils.file_utils import load_json, save_json
from scripts.utils.status_manager import StatusManager

CHAR_REF_PATH = BASE_DIR / "assets" / "character_references.json"


def get_project_id() -> str:
    """
    Uso:
        python scripts/02_build_scenes.py demo_project
        python scripts/02_build_scenes.py 1nefi_cap_01
    """
    if len(sys.argv) < 2:
        raise SystemExit(
            "Falta project_id.\n"
            "Uso: python scripts/02_build_scenes.py <project_id>\n"
            "Ejemplo: python scripts/02_build_scenes.py 1nefi_cap_01"
        )
    return sys.argv[1].strip()


def get_project_paths(project_id: str) -> dict[str, Path]:
    project_root = BASE_DIR / "projects" / project_id
    parsed_path = project_root / "scenes" / "parsed_chapter.json"
    scenes_path = project_root / "scenes" / "scenes.json"

    return {
        "project_root": project_root,
        "parsed_path": parsed_path,
        "scenes_path": scenes_path,
    }


def normalize_text(text: str) -> str:
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def split_into_scene_units(text: str, target_count: int = 12) -> list[str]:
    """
    Split text into approximately target_count scenes.
    Logic:
    1. Split into sentences (., !, ?).
    2. Group sentences until reaching target_chunk (total_len / target_count).
    3. Allow ±20% variation.
    4. If a sentence is still too long, split by comma.
    """
    text = re.sub(r"\s+", " ", text.strip())
    # Split by strong punctuation, preserving it
    sentences = [s.strip() for s in re.split(r"(?<=[\.\!\?])\s+", text) if s.strip()]
    
    if not sentences:
        return []

    total_len = len(text)
    target_size = total_len / target_count
    
    # Process long sentences (fallback to comma)
    processed_sentences = []
    limit = target_size * 1.2
    
    for s in sentences:
        if len(s) > limit:
            # Fallback to commas
            subs = [p.strip() for p in re.split(r"(?<=,)\s+", s) if p.strip()]
            current_sub = ""
            for sub in subs:
                if len(current_sub) + len(sub) < limit:
                    current_sub += (" " if current_sub else "") + sub
                else:
                    if current_sub: processed_sentences.append(current_sub)
                    current_sub = sub
            if current_sub: processed_sentences.append(current_sub)
        else:
            processed_sentences.append(s)

    scenes = []
    current_chunk = []
    current_length = 0

    for s in processed_sentences:
        current_chunk.append(s)
        current_length += len(s)
        
        # Check if we should close the scene (within ±20% range)
        if current_length >= target_size * 0.8:
            # If current scene is near target, or taking next sentence would overshoot too much
            scenes.append(" ".join(current_chunk).strip())
            current_chunk = []
            current_length = 0

    # Add remainder
    if current_chunk:
        rem_str = " ".join(current_chunk).strip()
        if scenes and len(rem_str) < target_size * 0.3:
            scenes[-1] += " " + rem_str
        else:
            scenes.append(rem_str)

    return scenes


def load_known_character_names(project_id: str, project_root: Path) -> list[str]:
    """
    Toma personajes desde character_references.json o configuración por proyecto.
    """
    names: list[str] = []

    project_char_path = project_root / "config" / "characters.json"
    if project_char_path.exists():
        try:
            cfg = load_json(str(project_char_path))
            if isinstance(cfg, list):
                return cfg
            if isinstance(cfg, dict) and "characters" in cfg:
                return cfg["characters"]
            if isinstance(cfg, dict):
                return list(cfg.keys())
        except Exception as exc:
            print(f"[WARN] No se pudo leer characters.json del proyecto: {exc}")

    if CHAR_REF_PATH.exists():
        try:
            ref_map = load_json(str(CHAR_REF_PATH))
            if isinstance(ref_map, dict):
                names.extend(ref_map.keys())
        except Exception as exc:
            print(f"[WARN] No se pudo leer character_references.json: {exc}")

    # Fallbacks útiles si aún no están en el archivo de referencias
    fallback_names = [
        "Nefi", "Lehi", "Laman", "Lemuel", "Sam", "Sariah", "Laban", 
        "Ismael", "Zoram", "Jacob", "Jose", "Benjamin", "Mosiah", 
        "Alma", "Amulek", "Mormon", "Moroni"
    ]

    for name in fallback_names:
        if name not in names:
            names.append(name)

    return names


def detect_characters(text: str, project_id: str, project_root: Path) -> list[str]:
    """
    Detecta personajes conocidos apoyándose en character_references.json o overrides.
    """
    text_norm = normalize_text(text)
    known_names = load_known_character_names(project_id, project_root)

    # términos que suelen ser lugares o conceptos, no personajes visuales
    excluded = {
        "Jerusalen", "Jerusalem", "Desierto", "Templo", "Palacio", "Sedequias"
    }

    found: list[str] = []

    for canonical in known_names:
        if canonical in excluded:
            continue

        alias = normalize_text(canonical)

        # boundary estricto
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        if re.search(pattern, text_norm):
            if canonical == "Alma":
                if re.search(r"\b(mi|su|el|tu|nuestra|toda)(\s+)alma\b", text_norm):
                    continue
                if "Alma" not in text and "ALMA" not in text:
                    continue
            
            found.append(canonical)

    return found


def detect_location(text: str) -> str:
    lower = normalize_text(text)

    if "jerusalen" in lower or "jerusalem" in lower:
        return "ciudad antigua"
    if "desierto" in lower:
        return "desierto"
    if "casa" in lower or "cama" in lower:
        return "interior doméstico antiguo"
    if "roca" in lower or "monte" in lower:
        return "exterior rocoso"
    if "cielos abiertos" in lower or "trono" in lower or "angeles" in lower:
        return "visión celestial"
    if "libro" in lower and ("leyo" in lower or "leer" in lower):
        return "visión sagrada"
    if "palacio" in lower:
        return "palacio"
    if "templo" in lower:
        return "templo"
    if "rio" in lower:
        return "río"
    if "mar" in lower:
        return "costa o mar"

    return "entorno bíblico"


def detect_mood(text: str) -> str:
    lower = normalize_text(text)

    if any(x in lower for x in ["temblo", "se estremecio", "aflicciones", "afligido", "anonadado"]):
        return "solemne, emocional"
    if any(x in lower for x in ["profetizando", "profetizo", "destruida", "destruccion", "ay ay de jerusalen"]):
        return "profético, intenso"
    if any(x in lower for x in ["vision", "cielos abiertos", "trono", "angeles", "espiritu del senor"]):
        return "sagrado, sobrecogedor"
    if any(x in lower for x in ["bondad", "misterios de dios", "misericordia"]):
        return "espiritual, reflexivo"

    return "solemne"


def detect_shot_type(text: str, location: str, characters: list[str]) -> str:
    lower = normalize_text(text)

    if location in {"visión celestial", "visión sagrada"}:
        return "wide cinematic"
    if any(x in lower for x in ["rostro", "vio", "leyo", "oraba", "temblo", "se estremecio"]):
        return "medium close-up"
    if not characters:
        return "wide cinematic"
    if any(x in lower for x in ["camino", "viajo", "salio", "partio"]):
        return "wide cinematic"

    return "medium"


def estimate_duration(text: str) -> int:
    words = len(text.split())

    if words < 12:
        return 3
    if words < 28:
        return 4
    if words < 45:
        return 5
    return 6


def infer_visual_focus(characters: list[str], location: str) -> str:
    if characters:
        return "character"
    if location in {"visión celestial", "visión sagrada"}:
        return "vision"
    return "environment"


def main() -> None:
    project_id = get_project_id()
    paths = get_project_paths(project_id)

    project_root = paths["project_root"]
    parsed_path = paths["parsed_path"]
    scenes_path = paths["scenes_path"]

    if not parsed_path.exists():
        raise FileNotFoundError(f"No existe parsed_chapter.json: {parsed_path}")

    parsed = load_json(str(parsed_path))
    raw_text = str(parsed.get("raw_text", "")).strip()

    if not raw_text:
        raise ValueError("parsed_chapter.json no contiene raw_text válido.")

    scene_units = split_into_scene_units(raw_text)

    scenes = {
        "project_id": parsed.get("project_id", project_id),
        "title": parsed.get("title", f"Capítulo {project_id}"),
        "source": "Libro de Mormón",
        "style": "semi_realistic_3d",
        "scenes": []
    }

    for idx, unit in enumerate(scene_units, start=1):
        scene_id = f"s{idx:02d}"

        characters = detect_characters(unit, project_id, project_root)
        location = detect_location(unit)
        mood = detect_mood(unit)
        shot_type = detect_shot_type(unit, location, characters)
        visual_focus = infer_visual_focus(characters, location)

        scene = {
            "scene_id": scene_id,
            "summary": unit,
            "characters": characters,
            "dialogues": [],
            "narration": unit,
            "location": location,
            "mood": mood,
            "shot_type": shot_type,
            "duration_sec": estimate_duration(unit),
            "visual_focus": visual_focus,
            "positive_prompt": "",
            "negative_prompt": ""
        }

        scenes["scenes"].append(scene)

    status = StatusManager(project_id, project_root)
    status.update_stage("build_scenes", progress=0.1)

    save_json(str(scenes_path), scenes)
    
    total_scenes = len(scenes["scenes"])
    status.data["total_scenes"] = total_scenes
    status.update_stage("build_scenes", progress=1.0)
    
    print(f"[OK] Proyecto: {project_id}")
    print(f"[OK] Escenas generadas: {total_scenes} -> {scenes_path}")


if __name__ == "__main__":
    main()