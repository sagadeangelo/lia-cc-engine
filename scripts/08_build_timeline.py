from pathlib import Path
import sys
import json

sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import BASE_DIR
from scripts.utils.status_manager import StatusManager
from backend.services.pipeline_service import check_abort_file

# 🔥 IMPORT CORRECTO MOVIEPY 2.x
from moviepy.audio.io.AudioFileClip import AudioFileClip


# =========================================================
# CONFIG
# =========================================================
FALLBACK_DURATION = 5.0


# =========================================================
# UTILS
# =========================================================
def get_project_id() -> str:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/08_build_timeline.py <project_id>")
    return sys.argv[1].strip()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def build_audio_index(voice_manifest: dict) -> dict:
    index = {}

    for item in voice_manifest.get("files", []):
        scene_id = item.get("scene_id")
        if not scene_id:
            continue

        index.setdefault(scene_id, []).append({
            "speaker": item.get("speaker"),
            "speaker_display": item.get("speaker_display", ""),
            "file": item.get("file"),
            "text": item.get("text")
        })

    return index


def get_audio_duration(audio_path: Path) -> float:
    try:
        clip = AudioFileClip(str(audio_path))
        duration = clip.duration
        clip.close()
        return duration
    except Exception as e:
        print(f"⚠️ Error leyendo audio: {audio_path} → {e}")
        return FALLBACK_DURATION


# =========================================================
# MAIN
# =========================================================
def main() -> None:

    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id

    status = StatusManager(project_id, project_root)
    status.update_stage("build_timeline", progress=0.1)

    print(f"🧠 Generando timeline REAL para {project_id}")

    # PATHS
    scenes_path = project_root / "scenes" / "scenes.json"
    prompts_path = project_root / "prompts" / "scene_prompts.json"
    voice_manifest_path = project_root / "audio" / "voice_manifest.json"
    render_queue_path = project_root / "output" / "render_queue.json"
    timeline_path = project_root / "final" / "timeline.json"

    # VALIDACIÓN
    if not scenes_path.exists():
        raise FileNotFoundError(f"No existe: {scenes_path}")

    if not voice_manifest_path.exists():
        raise FileNotFoundError(f"No existe: {voice_manifest_path}")

    # LOAD DATA
    scenes_data = load_json(scenes_path)
    prompts_data = load_json(prompts_path)
    voice_manifest = load_json(voice_manifest_path)
    queue_data = load_json(render_queue_path)

    # INDEXES
    prompt_index = {item["scene_id"]: item for item in prompts_data.get("prompts", [])}
    audio_index = build_audio_index(voice_manifest)
    render_index = {item["scene_id"]: item for item in queue_data.get("jobs", [])}

    timeline = {
        "project_id": project_id,
        "title": scenes_data.get("title", project_id),
        "total_duration_sec": 0,
        "timeline": []
    }

    current_start = 0.0

    # =========================================================
    # LOOP ESCENAS
    # =========================================================
    for scene in scenes_data.get("scenes", []):

        if check_abort_file(project_id):
            print("🛑 ABORT detectado")
            return

        scene_id = scene.get("scene_id")

        prompt_data = prompt_index.get(scene_id, {})
        render_data = render_index.get(scene_id, {})
        audio_tracks = audio_index.get(scene_id, [])

        # 🔥 CALCULAR DURACIÓN REAL
        max_duration = 0.0

        for track in audio_tracks:
            audio_file = track.get("file")

            if audio_file:
               audio_path = project_root / audio_file

               # 🔥 FIX rutas duplicadas tipo audio/audio
               if not audio_path.exists():
                  audio_path = project_root / "audio" / Path(audio_file).name

               if audio_path.exists():
                  duration = get_audio_duration(audio_path)
                  max_duration = max(max_duration, duration)

        # 🔥 FALLBACK SI NO HAY AUDIO
        if max_duration == 0:
            max_duration = FALLBACK_DURATION

        # 🔥 CREAR ITEM
        timeline_item = {
            "scene_id": scene_id,
            "start_sec": round(current_start, 2),
            "end_sec": round(current_start + max_duration, 2),
            "duration_sec": round(max_duration, 2),
            "summary": scene.get("summary", ""),
            "positive_prompt": prompt_data.get("positive_prompt", ""),
            "output_image": str(project_root / "output" / f"{scene_id}.png"),
            "audio_tracks": audio_tracks
        }

        print(f"🎬 {scene_id} → {max_duration:.2f}s")

        timeline["timeline"].append(timeline_item)

        current_start += max_duration

    # 🔥 TOTAL
    timeline["total_duration_sec"] = round(current_start, 2)

    # SAVE
    save_json(timeline_path, timeline)

    status.update_stage("build_timeline", progress=1.0)

    print(f"\n✅ Timeline PRO generada:")
    print(f"📁 {timeline_path}")
    print(f"⏱️ Duración total: {timeline['total_duration_sec']}s")


# =========================================================
# ENTRY
# =========================================================
if __name__ == "__main__":
    main()