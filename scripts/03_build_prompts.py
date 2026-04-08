from __future__ import annotations

from pathlib import Path
import sys
import unicodedata

# Add root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR
from scripts.utils.file_utils import load_json, load_text, save_json
from scripts.utils.status_manager import StatusManager

POSITIVE_MASTER_PATH = BASE_DIR / "prompts" / "masters" / "positive_master.txt"
NEGATIVE_MASTER_PATH = BASE_DIR / "prompts" / "masters" / "negative_master.txt"

# Paths se manejan por proyecto


def get_project_id() -> str:
    """
    Uso:
        python scripts/03_build_prompts.py demo_project
        python scripts/03_build_prompts.py 1nefi_cap_01
    """
    if len(sys.argv) < 2:
        raise SystemExit(
            "Falta project_id.\n"
            "Uso: python scripts/03_build_prompts.py <project_id>\n"
            "Ejemplo: python scripts/03_build_prompts.py 1nefi_cap_01"
        )
    return sys.argv[1].strip()


def get_project_paths(project_id: str) -> dict[str, Path]:
    project_root = BASE_DIR / "projects" / project_id
    scenes_path = project_root / "scenes" / "scenes.json"
    local_output_path = project_root / "prompts" / "scene_prompts.json"

    return {
        "project_root": project_root,
        "scenes_path": scenes_path,
        "local_output_path": local_output_path,
    }


def normalize_text(text: str) -> str:
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


def build_character_block(characters: list[str]) -> str:
    if not characters:
        return ""

    known_map = {
        "Nefi": "young man (Nephi), faithful young prophet, calm but determined expression, simple ancient scriptural clothing",
        "Lehi": "older man (Lehi), wise prophet, solemn expression, ancient biblical robes",
        "Sariah": "woman (Sariah), warm but strong presence, modest ancient clothing, gentle expression",
        "Laman": "young adult man (Laman), strong build, skeptical expression, rough desert clothing",
        "Lemuel": "young adult man (Lemuel), doubtful expression, modest ancient clothing",
        "Sam": "young man (Sam), kind face, peaceful expression, simple biblical clothing",
        "Laban": "man (Laban), powerful and arrogant expression, authority presence, rich ancient clothing",
        "Ismael": "older biblical man (Ishmael), desert traveler, ancient robes, serious expression",
        "Zoram": "young adult biblical man (Zoram), alert expression, servant clothing, ancient setting",
        "Jacob": "young biblical boy (Jacob), thoughtful expression, simple ancient clothing",
        "Jose": "young biblical boy (Joseph), soft expression, simple ancient clothing",
        "Benjamin": "elderly biblical king (Benjamin), noble presence, sacred robes, wise expression",
        "Mosiah": "biblical king (Mosiah), calm authority, sacred robes, noble expression",
        "Alma": "biblical prophet (Alma), intense spiritual expression, modest ancient robes",
        "Amulek": "biblical man (Amulek), serious expression, modest ancient robes",
        "Mormon": "mature biblical prophet (Mormon), solemn expression, record keeper presence, ancient robes",
        "Moroni": "young adult biblical prophet (Moroni), determined expression, sacred ancient robes",
    }

    blocks = []
    for name in characters:
        blocks.append(known_map.get(name, f"{name}, biblical character, ancient clothing"))

    return ", ".join(blocks)


def build_location_block(location: str) -> str:
    mapping = {
        "desierto": "desert environment, sand, rocks, warm natural sunlight",
        "ciudad antigua": "ancient city environment, stone architecture, historical atmosphere",
        "interior doméstico antiguo": "ancient interior, stone walls, modest house, dim warm light",
        "exterior rocoso": "rocky exterior, desert stone, dramatic natural light",
        "visión celestial": "heavenly vision, glowing sky, divine light, celestial atmosphere",
        "visión sagrada": "sacred vision scene, glowing light, spiritual atmosphere, divine symbolism",
        "templo": "temple environment, sacred interior, reverent mood",
        "palacio": "ancient royal hall, stone columns, dramatic interior lighting",
        "río": "ancient riverbank, natural environment, biblical landscape",
        "costa o mar": "biblical seashore, ancient coastal atmosphere, natural dramatic light",
        "entorno bíblico": "biblical environment, ancient atmosphere"
    }
    return mapping.get(location, "biblical environment, ancient atmosphere")


def build_mood_block(mood: str) -> str:
    mood_n = normalize_text(mood)

    if "profetico" in mood_n:
        return "prophetic tone, spiritual intensity, dramatic atmosphere"
    if "emocional" in mood_n:
        return "emotional tone, solemn atmosphere, expressive storytelling"
    if "reflexivo" in mood_n:
        return "reflective spiritual tone, contemplative atmosphere"
    if "sagrado" in mood_n or "sobrecogedor" in mood_n:
        return "sacred overwhelming atmosphere, divine presence, spiritual intensity"

    return "solemn biblical atmosphere, cinematic storytelling"


def build_shot_block(shot_type: str, visual_focus: str) -> str:
    shot_n = normalize_text(shot_type)
    focus_n = normalize_text(visual_focus)

    if focus_n == "environment":
        return "wide cinematic shot, environmental storytelling, no face focus"
    if focus_n == "vision":
        return "wide cinematic composition, dramatic divine scale, environmental storytelling"

    if "wide" in shot_n:
        return "wide cinematic shot, strong environmental storytelling"
    if "close" in shot_n:
        return "medium close-up, expressive face, character focus"

    return "medium shot, centered composition, cinematic framing"


def build_camera_motion(shot_type: str, mood: str, visual_focus: str) -> str:
    shot_n = normalize_text(shot_type)
    mood_n = normalize_text(mood)
    focus_n = normalize_text(visual_focus)

    if focus_n == "environment":
        return "slow cinematic drift"
    if focus_n == "vision":
        return "slow dramatic push in"

    if "wide" in shot_n:
        return "slow forward push"
    if "profetico" in mood_n:
        return "slow dramatic push in"
    if "emocional" in mood_n:
        return "gentle cinematic push"

    return "subtle cinematic movement"


def build_animation_hint(mood: str, visual_focus: str) -> str:
    mood_n = normalize_text(mood)
    focus_n = normalize_text(visual_focus)

    if focus_n == "environment":
        return "subtle environmental motion, moving light, drifting atmosphere, gentle cinematic motion"
    if focus_n == "vision":
        return "glowing particles, soft divine movement, spiritual atmosphere, subtle cinematic motion"

    base = "subtle facial animation, slight blinking, gentle breathing, slight head movement"

    if "profetico" in mood_n:
        return base + ", quiet intensity, slight body sway"
    if "emocional" in mood_n:
        return base + ", emotional eye focus, soft expression changes"
    if "reflexivo" in mood_n:
        return base + ", contemplative expression, calm body posture"

    return base + ", natural idle motion"


def build_environment_focus(summary: str, location: str, mood: str, visual_focus: str) -> str:
    location_block = build_location_block(location)
    mood_block = build_mood_block(mood)

    if visual_focus == "vision":
        return (
            f"scene action: {summary}, "
            f"{location_block}, "
            f"{mood_block}, "
            "divine vision, celestial light, sacred environment, no single character portrait, environmental storytelling"
        )

    return (
        f"scene action: {summary}, "
        f"{location_block}, "
        f"{mood_block}, "
        "ancient biblical environment, no single character portrait, environmental storytelling"
    )


def build_positive_prompt(scene: dict, positive_master: str) -> str:
    summary = scene.get("summary", "")
    characters = scene.get("characters", [])
    location = scene.get("location", "entorno bíblico")
    mood = scene.get("mood", "solemne")
    shot_type = scene.get("shot_type", "medium")
    visual_focus = scene.get("visual_focus", "character")

    shot_block = build_shot_block(shot_type, visual_focus)
    animation_hint = build_animation_hint(mood, visual_focus)

    if characters:
        character_block = build_character_block(characters)
        location_block = build_location_block(location)
        mood_block = build_mood_block(mood)

        parts = [
            positive_master.strip(),
            character_block,
            f"scene action: {summary}",
            location_block,
            mood_block,
            shot_block,
            animation_hint,
            "Pixar style animated realism, cinematic 3D animation, expressive face, soft skin shading, clean anatomy, correct hands, stable face, consistent facial identity, depth of field, global illumination, masterpiece"
        ]
    else:
        env_block = build_environment_focus(summary, location, mood, visual_focus)

        parts = [
            positive_master.strip(),
            env_block,
            shot_block,
            animation_hint,
            "cinematic biblical environment, dramatic composition, volumetric light, depth of field, global illumination, masterpiece"
        ]

    return ", ".join([p for p in parts if p])


def build_negative_prompt(scene: dict, negative_master: str) -> str:
    visual_focus = scene.get("visual_focus", "character")

    common_extras = [
        "multiple people",
        "extra person",
        "duplicate face",
        "extra head",
        "bad anatomy",
        "extra arms",
        "extra hands",
        "extra fingers",
        "malformed hands",
        "blurry",
        "low quality",
        "watermark",
        "text",
        "logo"
    ]

    if visual_focus in {"environment", "vision"}:
        extras = common_extras + [
            "random portrait",
            "single face close-up",
            "unwanted character portrait",
            "modern objects",
            "urban elements",
            "sci-fi technology"
        ]
    else:
        extras = common_extras + [
            "frozen face",
            "stiff face",
            "emotionless",
            "robotic face",
            "lifeless eyes",
            "static pose",
            "extra limbs"
        ]

    base = negative_master.strip()
    if base:
        return base + ", " + ", ".join(extras)
    return ", ".join(extras)


def choose_render_profile(scene: dict) -> str:
    visual_focus = normalize_text(scene.get("visual_focus", "character"))
    shot = normalize_text(scene.get("shot_type", ""))

    if visual_focus == "vision":
        return "vision"
    if visual_focus == "environment":
        return "environment"
    if "wide" in shot:
        return "wide"

    return "standard"


def main() -> None:
    project_id = get_project_id()
    paths = get_project_paths(project_id)

    scenes_path = paths["scenes_path"]
    local_output_path = paths["local_output_path"]

    if not scenes_path.exists():
        raise FileNotFoundError(f"No existe scenes.json: {scenes_path}")

    if not POSITIVE_MASTER_PATH.exists():
        raise FileNotFoundError(f"No existe positive_master.txt: {POSITIVE_MASTER_PATH}")

    if not NEGATIVE_MASTER_PATH.exists():
        raise FileNotFoundError(f"No existe negative_master.txt: {NEGATIVE_MASTER_PATH}")

    scenes_data = load_json(str(scenes_path))
    positive_master = load_text(str(POSITIVE_MASTER_PATH)).strip()
    negative_master = load_text(str(NEGATIVE_MASTER_PATH)).strip()

    result = {
        "project_id": scenes_data.get("project_id", project_id),
        "title": scenes_data.get("title", project_id),
        "prompts": []
    }

    for scene in scenes_data.get("scenes", []):
        positive_prompt = build_positive_prompt(scene, positive_master)
        negative_prompt = build_negative_prompt(scene, negative_master)
        camera_motion = build_camera_motion(
            scene.get("shot_type", ""),
            scene.get("mood", ""),
            scene.get("visual_focus", "character")
        )
        animation_hint = build_animation_hint(
            scene.get("mood", ""),
            scene.get("visual_focus", "character")
        )

        result["prompts"].append({
            "scene_id": scene["scene_id"],
            "summary": scene.get("summary", ""),
            "characters": scene.get("characters", []),
            "visual_focus": scene.get("visual_focus", "character"),
            "narration": scene.get("narration", ""),
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "camera_motion": camera_motion,
            "animation_hint": animation_hint,
            "render_profile": choose_render_profile(scene)
        })

    status = StatusManager(project_id, paths["project_root"])
    status.update_stage("build_prompts", progress=0.1)

    # 1) Guardado por proyecto
    save_json(str(local_output_path), result)
    
    status.update_stage("build_prompts", progress=1.0)

    print(f"[OK] Proyecto: {project_id}")
    print(f"[OK] Prompts generados (local): {local_output_path}")


if __name__ == "__main__":
    main()