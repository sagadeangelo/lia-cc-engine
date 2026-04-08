from pathlib import Path
import sys
import json

# Add root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR
from scripts.utils.status_manager import StatusManager
from backend.services.pipeline_service import check_abort_file

# =========================================================
# CONFIG
# =========================================================
TARGET_SCENE_DURATION = 5.0

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

def build_audio_index(voice_manifest: dict) -> dict[str, list[dict]]:
    index = {}
    for item in voice_manifest.get("files", []):
        scene_id = item.get("scene_id")
        if not scene_id: continue
        index.setdefault(scene_id, []).append({
            "speaker": item.get("speaker"),
            "speaker_display": item.get("speaker_display", ""),
            "file": item.get("file"),
            "text": item.get("text")
        })
    return index

def main() -> None:
    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id
    
    status = StatusManager(project_id, project_root)
    status.update_stage("build_timeline", progress=0.1)

    # Paths específicos por proyecto (Strict Isolation)
    scenes_path = project_root / "scenes" / "scenes.json"
    prompts_path = project_root / "prompts" / "scene_prompts.json"
    voice_manifest_path = project_root / "audio" / "voice_manifest.json"
    render_queue_path = project_root / "output" / "render_queue.json"
    timeline_path = project_root / "final" / "timeline.json"

    if not scenes_path.exists():
        raise FileNotFoundError(f"No existe scenes.json en {scenes_path}")

    scenes_data = load_json(scenes_path)
    prompts_data = load_json(prompts_path)
    voice_manifest = load_json(voice_manifest_path)
    queue_data = load_json(render_queue_path)

    prompt_index = {item["scene_id"]: item for item in prompts_data.get("prompts", [])}
    audio_index = build_audio_index(voice_manifest)
    render_index = {item["scene_id"]: item for item in queue_data.get("jobs", [])}

    timeline = {
        "project_id": project_id,
        "title": scenes_data.get("title", project_id),
        "target_scene_duration_sec": TARGET_SCENE_DURATION,
        "timeline": []
    }

    current_start = 0.0
    for scene in scenes_data.get("scenes", []):
        # ABORT CHECK
        if check_abort_file(project_id):
            print("[ABORT] Proceso de timeline abortado.")
            return

        scene_id = scene.get("scene_id")
        prompt_data = prompt_index.get(scene_id, {})
        render_data = render_index.get(scene_id, {})
        audio_tracks = audio_index.get(scene_id, [])

        duration_sec = TARGET_SCENE_DURATION
        timeline_item = {
            "scene_id": scene_id,
            "start_sec": round(current_start, 2),
            "end_sec": round(current_start + duration_sec, 2),
            "duration_sec": duration_sec,
            "summary": scene.get("summary", ""),
            "positive_prompt": prompt_data.get("positive_prompt", ""),
            "output_prefix": render_data.get("output_prefix", ""),
            "audio_tracks": audio_tracks
        }
        timeline["timeline"].append(timeline_item)
        current_start += duration_sec

    save_json(timeline_path, timeline)
    status.update_stage("build_timeline", progress=1.0)
    print(f"[OK] Timeline generada: {timeline_path}")

if __name__ == "__main__":
    main()