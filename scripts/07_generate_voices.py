from pathlib import Path
import sys
import json
import re
import asyncio
import unicodedata

# =========================================================
# 🎙️ VOICE MAP BASE (fallback inteligente)
# =========================================================
VOICE_MAP = {
    "male": "es-MX-JorgeNeural",
    "female": "es-MX-DaliaNeural",
    "narrator": "es-MX-DaliaNeural"
}

# =========================================================
# PATH SETUP
# =========================================================
sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import BASE_DIR
from scripts.utils.file_utils import load_json
from scripts.utils.status_manager import StatusManager
from backend.services.pipeline_service import check_abort_file

try:
    import edge_tts
except ImportError as exc:
    raise SystemExit("edge-tts no está instalado. Ejecuta: pip install edge-tts") from exc

VOICE_CONFIG_PATH = BASE_DIR / "config" / "voice_profiles.json"

# =========================================================
# 🧠 UTILIDADES
# =========================================================

def get_project_id():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/07_generate_voices.py <project_id>")
    return sys.argv[1].strip()


def normalize_text(text: str) -> str:
    text = str(text or "").strip()
    text = text.replace("—", ", ")
    text = text.replace("...", ". ")
    text = re.sub(r"\s+", " ", text)
    return text


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def safe_speaker_key(name: str) -> str:
    cleaned = str(name or "").strip().lower()
    cleaned = strip_accents(cleaned)
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_")


def infer_gender_from_name(name: str) -> str:
    name = name.lower()

    female = ["sariah", "maria", "ana", "eve"]
    male = ["nefi", "lehi", "laman", "sam"]

    if any(n in name for n in female):
        return "female"
    if any(n in name for n in male):
        return "male"

    return "narrator"


# =========================================================
# 🎙️ EDGE TTS
# =========================================================

async def list_installed_voices():
    return await edge_tts.list_voices()


def only_spanish_voices(voices):
    return [
        v for v in voices
        if v.get("ShortName", "").startswith("es-")
    ]


def pick_voice_name(installed_voices, preferred_contains):
    spanish = only_spanish_voices(installed_voices)

    if not spanish:
        raise RuntimeError("No hay voces en español.")

    if preferred_contains:
        for v in spanish:
            blob = f"{v.get('ShortName','')} {v.get('FriendlyName','')}".lower()
            if preferred_contains.lower() in blob:
                return v["ShortName"]

    return spanish[0]["ShortName"]


async def synthesize(text, path, voice, rate, pitch, volume):
    path.parent.mkdir(parents=True, exist_ok=True)

    tts = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume=volume
    )

    await tts.save(str(path))


# =========================================================
# 🚀 MAIN
# =========================================================

async def main_async():
    project_id = get_project_id()

    project_root = BASE_DIR / "projects" / project_id
    scenes_path = project_root / "scenes" / "scenes.json"
    audio_dir = project_root / "audio"
    manifest_path = audio_dir / "voice_manifest.json"

    status = StatusManager(project_id, project_root)
    status.update_stage("voices", progress=0.1)

    scenes_data = load_json(str(scenes_path))
    voice_cfg = load_json(str(VOICE_CONFIG_PATH))

    installed = await list_installed_voices()

    default_rate = voice_cfg.get("default_rate", "+0%")
    default_pitch = voice_cfg.get("default_pitch", "+0Hz")
    default_volume = voice_cfg.get("default_volume", "+0%")
    voice_roles = voice_cfg.get("voices", {})

    manifest = {
        "project_id": project_id,
        "files": []
    }

    scenes = scenes_data.get("scenes", [])

    print(f"🎙️ Generando voces para {len(scenes)} escenas...")

    for scene in scenes:
        scene_id = scene.get("scene_id")

        if check_abort_file(project_id):
            print("⛔ Abortado")
            break

        # =====================================================
        # 🎧 NARRACIÓN
        # =====================================================
        narration = normalize_text(scene.get("narration", ""))

        if narration:
            narrator_voice = VOICE_MAP["narrator"]

            file_path = audio_dir / f"{scene_id}_narrator.mp3"

            await synthesize(
                narration,
                file_path,
                narrator_voice,
                default_rate,
                default_pitch,
                default_volume
            )

            manifest["files"].append({
                "scene_id": scene_id,
                "speaker": "narrator",
                "file": file_path.name,
                "voice": narrator_voice
            })

            print(f"✅ Narrador: {file_path.name}")

        # =====================================================
        # 🗣️ DIÁLOGOS
        # =====================================================
        for i, dialogue in enumerate(scene.get("dialogues", []), 1):

            speaker = safe_speaker_key(dialogue.get("speaker", "narrator"))
            text = normalize_text(dialogue.get("text", ""))

            if not text:
                continue

            # 🔥 CONFIG O AUTO-DETECCIÓN
            cfg = voice_roles.get(speaker)

            if not cfg:
                gender = infer_gender_from_name(speaker)
                voice = VOICE_MAP[gender]
            else:
                voice = pick_voice_name(installed, cfg.get("voice_name_contains", ""))

            file_path = audio_dir / f"{scene_id}_{speaker}_{i:02}.mp3"

            await synthesize(
                text,
                file_path,
                voice,
                default_rate,
                default_pitch,
                default_volume
            )

            manifest["files"].append({
                "scene_id": scene_id,
                "speaker": speaker,
                "file": file_path.name,
                "voice": voice
            })

            print(f"🎤 {speaker}: {file_path.name}")

    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    status.update_stage("voices", progress=1.0)

    print(f"\n🔥 VOCES COMPLETAS → {manifest_path}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()