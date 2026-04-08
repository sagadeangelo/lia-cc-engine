from pathlib import Path
import sys
import json
import re
import asyncio
import unicodedata

# Add root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR
from scripts.utils.file_utils import load_json
from scripts.utils.status_manager import StatusManager
from backend.services.pipeline_service import check_abort_file

try:
    import edge_tts
except ImportError as exc:
    raise SystemExit(
        "edge-tts no está instalado. Ejecuta: pip install edge-tts"
    ) from exc


VOICE_CONFIG_PATH = BASE_DIR / "config" / "voice_profiles.json"


def get_project_id() -> str:
    """
    Uso:
        python scripts/06_generate_voices.py demo_project
        python scripts/06_generate_voices.py 1nefi_cap_01
    """
    if len(sys.argv) < 2:
        raise SystemExit(
            "Falta project_id.\n"
            "Uso: python scripts/06_generate_voices.py <project_id>\n"
            "Ejemplo: python scripts/06_generate_voices.py 1nefi_cap_01"
        )
    return sys.argv[1].strip()


def get_project_paths(project_id: str) -> dict[str, Path]:
    project_root = BASE_DIR / "projects" / project_id
    scenes_path = project_root / "scenes" / "scenes.json"
    audio_dir = project_root / "audio"
    manifest_path = audio_dir / "voice_manifest.json"
    available_voices_path = audio_dir / "available_voices.json"

    return {
        "project_root": project_root,
        "scenes_path": scenes_path,
        "audio_dir": audio_dir,
        "manifest_path": manifest_path,
        "available_voices_path": available_voices_path,
    }


def normalize_text(text: str) -> str:
    text = str(text or "").strip()
    text = text.replace("—", ", ")
    text = text.replace("...", ". ")
    text = re.sub(r"\s+", " ", text)
    return text


def strip_accents(text: str) -> str:
    """
    Convierte caracteres acentuados a su forma simple:
    Labán -> Laban
    Lamán -> Laman
    """
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def safe_speaker_key(name: str) -> str:
    """
    Convierte nombre visible a clave segura para voice_profiles.json.
    Ejemplos:
      "Labán" -> "laban"
      "Lamán" -> "laman"
      "Sam" -> "sam"
      "Nephi 1" -> "nephi_1"
    """
    cleaned = str(name or "").strip().lower()
    cleaned = strip_accents(cleaned)
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"[^a-z0-9_]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_")


async def list_installed_voices() -> list[dict]:
    return await edge_tts.list_voices()


def only_spanish_voices(installed_voices: list[dict]) -> list[dict]:
    spanish = []
    for voice in installed_voices:
        short_name = voice.get("ShortName", "")
        locale = voice.get("Locale", "")
        if short_name.startswith("es-") or locale.startswith("es-"):
            spanish.append(voice)
    return spanish


def pick_voice_name(installed_voices: list[dict], preferred_contains: str) -> str:
    spanish_voices = only_spanish_voices(installed_voices)

    if not spanish_voices:
        raise RuntimeError("No se encontraron voces en español en edge-tts.")

    # 1) Si config pidió una voz exacta o parcial, buscar solo en español
    if preferred_contains:
        needle = preferred_contains.lower()
        for voice in spanish_voices:
            blob = f"{voice.get('ShortName', '')} {voice.get('FriendlyName', '')} {voice.get('Locale', '')}".lower()
            if needle in blob:
                return voice["ShortName"]

    # 2) Prioridad de voces favoritas
    preferred_order = [
        "es-MX-DaliaNeural",
        "es-MX-JorgeNeural",
        "es-ES-ElviraNeural",
        "es-ES-AlvaroNeural",
    ]
    for preferred in preferred_order:
        for voice in spanish_voices:
            if voice.get("ShortName") == preferred:
                return preferred

    # 3) Fallback
    return spanish_voices[0]["ShortName"]


async def synthesize_to_file(
    text: str,
    out_path: Path,
    voice_name: str,
    rate: str,
    pitch: str,
    volume: str
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice_name,
        rate=rate,
        pitch=pitch,
        volume=volume
    )
    await communicate.save(str(out_path))


async def main_async() -> None:
    project_id = get_project_id()
    paths = get_project_paths(project_id)

    project_root = paths["project_root"]
    scenes_path = paths["scenes_path"]
    audio_dir = paths["audio_dir"]
    manifest_path = paths["manifest_path"]
    available_voices_path = paths["available_voices_path"]

    status = StatusManager(project_id, project_root)
    status.update_stage("voices", progress=0.1)

    if not scenes_path.exists():
        raise FileNotFoundError(f"No existe scenes.json: {scenes_path}")

    if not VOICE_CONFIG_PATH.exists():
        raise FileNotFoundError(f"No existe voice_profiles.json: {VOICE_CONFIG_PATH}")

    audio_dir.mkdir(parents=True, exist_ok=True)

    scenes_data = load_json(str(scenes_path))
    voice_cfg = load_json(str(VOICE_CONFIG_PATH))
    installed_voices = await list_installed_voices()

    available_voices_path.write_text(
        json.dumps(installed_voices, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    default_rate = voice_cfg.get("default_rate", "+0%")
    default_pitch = voice_cfg.get("default_pitch", "+0Hz")
    default_volume = voice_cfg.get("default_volume", "+0%")
    voice_roles = voice_cfg.get("voices", {})

    manifest = {
        "project_id": scenes_data.get("project_id", project_id),
        "audio_dir": "audio",
        "available_voices_file": "audio/available_voices.json",
        "files": []
    }

    scenes = scenes_data.get("scenes", [])
    if not scenes:
        print("[WARN] No hay escenas en scenes.json")
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"Manifest vacío generado: {manifest_path}")
        return

    print(f"[INFO] Proyecto: {project_id}")
    print(f"[INFO] Escenas encontradas: {len(scenes)}")

    for scene in scenes:
        scene_id = scene.get("scene_id", "unknown_scene")

        # Abort check
        if check_abort_file(project_id):
            print(f"[ABORT] Generación de voces abortada por el usuario.")
            break

        narration = normalize_text(scene.get("narration", ""))
        if narration:
            narrator_cfg = voice_roles.get("narrator", {})
            narrator_voice = pick_voice_name(
                installed_voices,
                narrator_cfg.get("voice_name_contains", "")
            )

            narration_file = audio_dir / f"{scene_id}_narrator.mp3"
            await synthesize_to_file(
                text=narration,
                out_path=narration_file,
                voice_name=narrator_voice,
                rate=narrator_cfg.get("rate", default_rate),
                pitch=narrator_cfg.get("pitch", default_pitch),
                volume=narrator_cfg.get("volume", default_volume),
            )

            manifest["files"].append({
                "scene_id": scene_id,
                "speaker": "narrator",
                "speaker_display": "Narrator",
                "text": narration,
                "file": narration_file.name,
                "voice": narrator_voice
            })

            print(f"[OK] Narración generada: {narration_file.name} -> {narrator_voice}")

        dialogues = scene.get("dialogues", [])
        for idx, dialogue in enumerate(dialogues, start=1):
            speaker_display = normalize_text(dialogue.get("speaker", "narrator"))
            speaker_key = safe_speaker_key(speaker_display)
            text = normalize_text(dialogue.get("text", ""))

            if not text:
                continue

            speaker_cfg = voice_roles.get(speaker_key, voice_roles.get("narrator", {}))
            speaker_voice = pick_voice_name(
                installed_voices,
                speaker_cfg.get("voice_name_contains", "")
            )

            dialogue_file = audio_dir / f"{scene_id}_{speaker_key}_{idx:02d}.mp3"
            await synthesize_to_file(
                text=text,
                out_path=dialogue_file,
                voice_name=speaker_voice,
                rate=speaker_cfg.get("rate", default_rate),
                pitch=speaker_cfg.get("pitch", default_pitch),
                volume=speaker_cfg.get("volume", default_volume),
            )

            manifest["files"].append({
                "scene_id": scene_id,
                "speaker": speaker_key,
                "speaker_display": speaker_display,
                "text": text,
                "file": dialogue_file.name,
                "voice": speaker_voice
            })

            print(f"[OK] Diálogo generado: {dialogue_file.name} -> {speaker_voice}")

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    status.update_stage("voices", progress=1.0)
    print(f"\n[OK] Manifest generado: {manifest_path}")
    print(f"[OK] Lista de voces disponibles: {available_voices_path}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()