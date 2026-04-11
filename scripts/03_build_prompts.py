from __future__ import annotations

from pathlib import Path
import sys
import unicodedata

sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import BASE_DIR
from scripts.utils.file_utils import load_json, load_text, save_json
from scripts.utils.status_manager import StatusManager


NEGATIVE_MASTER_PATH = BASE_DIR / "prompts" / "masters" / "negative_master.txt"


# =========================================================
# 🔥 EMOTION SYSTEM
# =========================================================

EMOTION_MAP = [
    "peaceful, calm, soft light, hopeful atmosphere",
    "uneasy tension, subtle darkness",
    "mysterious, dramatic shadows",
    "shock, emotional intensity rising",
    "high tension, dramatic cinematic lighting",
    "chaos, fear, intense emotion",
    "dark atmosphere, conflict, struggle",
    "epic tension, powerful cinematic lighting",
    "revelation moment, divine light rays",
    "climax, ultra dramatic cinematic scene",
    "emotional resolution, soft cinematic glow"
]


# =========================================================
# 🧠 NORMALIZATION
# =========================================================

def normalize_text(text: str) -> str:
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


# =========================================================
# 🎭 BLOCK BUILDERS (MEJORADOS)
# =========================================================

def build_character_block(characters: list[str]) -> str:
    if not characters:
        return "biblical character, ancient clothing"
    return ", ".join([f"{c}, biblical character, ancient clothing" for c in characters])


def build_location_block(location: str) -> str:
    if not location or "entorno" in location.lower():
        return "ancient desert landscape, biblical environment"
    return f"{location}, ancient biblical environment"


def build_shot_block(shot_type: str) -> str:
    shot = normalize_text(shot_type)

    if "wide" in shot:
        return "wide cinematic shot, epic scale, cinematic framing"
    if "close" in shot:
        return "close-up shot, emotional face detail, shallow depth of field"

    return "medium cinematic shot, balanced composition"


# =========================================================
# 🎥 COMPOSICIÓN DINÁMICA
# =========================================================

def build_composition_block(index: int) -> str:
    if index % 3 == 0:
        return "single subject, centered composition"
    elif index % 3 == 1:
        return "two characters interaction, cinematic framing"
    else:
        return "dynamic composition, multiple elements, depth"


# =========================================================
# 🔥 ACCIÓN VISUAL
# =========================================================

def build_action_block(summary: str, index: int) -> str:
    text = summary.lower()

    if index < 3:
        base = "subtle movement, calm posture"
    elif index < 6:
        base = "tense posture, emotional intensity"
    elif index < 9:
        base = "dynamic movement, high tension"
    else:
        base = "powerful stance, cinematic climax"

    if "vision" in text or "visión" in text:
        return "character looking upward, divine light descending"
    if "pray" in text or "oró" in text:
        return "kneeling, praying, emotional intensity"
    if "fear" in text or "miedo" in text:
        return "tense posture, worried expression"

    return base


def build_emotion_block(index: int) -> str:
    if index < len(EMOTION_MAP):
        return EMOTION_MAP[index]
    return "cinematic lighting, emotional scene"


# =========================================================
# 🎬 PROMPT BUILDER FINAL
# =========================================================

def build_positive_prompt(scene: dict, hook: str, index: int) -> str:

    characters = scene.get("characters", [])
    location = scene.get("location", "")
    shot_type = scene.get("shot_type", "")
    summary = scene.get("summary", "")

    parts = [
        # 🎬 ESCENA
        f"biblical cinematic scene, {hook}",

        # 🎭 CONTEXTO
        build_character_block(characters),
        build_location_block(location),

        # 🎥 ACCIÓN
        build_action_block(summary, index),

        # 🔥 EMOCIÓN
        build_emotion_block(index),

        # 📸 CÁMARA
        build_composition_block(index),
        build_shot_block(shot_type),

        # 🎨 ESTILO
        "pixar-style realism",
        "cinematic lighting",
        "depth of field",
        "volumetric light",
        "high detail",
        "masterpiece"
    ]

    return ", ".join([p for p in parts if p])


def build_negative_prompt(negative_master: str) -> str:
    base = [x.strip() for x in negative_master.split(",")]

    extras = [
        "bad anatomy",
        "extra arms",
        "extra fingers",
        "blurry",
        "low quality",
        "text",
        "watermark",
        "deformed face",
        "ugly"
    ]

    final = list(dict.fromkeys(base + extras))  # 🔥 elimina duplicados respetando orden

    return ", ".join(final)


# =========================================================
# 🚀 MAIN
# =========================================================

def main():

    project_id = sys.argv[1]
    project_root = BASE_DIR / "projects" / project_id

    scenes_path = project_root / "scenes" / "scenes.json"
    hooks_path = project_root / "scenes" / "hooks.json"
    output_path = project_root / "prompts" / "scene_prompts.json"

    scenes = load_json(str(scenes_path))
    negative_master = load_text(str(NEGATIVE_MASTER_PATH))

    hook_map = {}
    if hooks_path.exists():
        hooks_data = load_json(str(hooks_path))
        hook_map = {h["scene_id"]: h["hook"] for h in hooks_data.get("hooks", [])}

    result = {
        "project_id": project_id,
        "title": scenes.get("title", project_id),
        "prompts": []
    }

    for i, scene in enumerate(scenes.get("scenes", [])):

        scene_id = scene["scene_id"]
        summary = scene.get("summary", "")

        hook = hook_map.get(scene_id, summary)

        positive_prompt = build_positive_prompt(scene, hook, i)
        negative_prompt = build_negative_prompt(negative_master)

        result["prompts"].append({
            "scene_id": scene_id,
            "summary": hook,
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt
        })

    status = StatusManager(project_id, project_root)
    status.update_stage("build_prompts", progress=0.1)

    save_json(str(output_path), result)

    status.update_stage("build_prompts", progress=1.0)

    print("🔥 PROMPTS FINAL DIOS++ GENERADOS")
    print(f"📁 {output_path}")


if __name__ == "__main__":
    main()