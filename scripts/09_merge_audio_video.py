from pathlib import Path
import sys
import subprocess
import json
import shutil

sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import BASE_DIR
from scripts.utils.file_utils import load_json


def get_project_id():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/09_merge_audio_video.py <project_id>")
    return sys.argv[1]


def require_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise SystemExit("❌ FFmpeg no está instalado o no está en PATH")


def build_scene_clip(scene, project_root, clips_dir, temp_dir):
    scene_id = scene["scene_id"]
    duration = scene["duration_sec"]

    clip_index = int(scene_id.replace("s", "")) - 1
    video_path = clips_dir / f"clip_{clip_index:03}.mp4"

    if not video_path.exists():
        print(f"⚠️ No existe clip: {video_path}")
        return None

    audio_tracks = scene.get("audio_tracks", [])

    output_clip = temp_dir / f"{scene_id}.mp4"

    if audio_tracks:
        audio_file = audio_tracks[0]["file"]
        audio_path = project_root / audio_file

        if not audio_path.exists():
            audio_path = project_root / "audio" / Path(audio_file).name

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            str(output_clip)
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-t", str(duration),
            "-c:v", "libx264",
            str(output_clip)
        ]

    subprocess.run(cmd, check=True)

    return output_clip


def merge_all(clips, output_path, temp_dir):
    list_file = temp_dir / "list.txt"

    content = "\n".join([f"file '{c.absolute()}'" for c in clips])
    list_file.write_text(content, encoding="utf-8")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path)
    ]

    subprocess.run(cmd, check=True)


def main():
    require_ffmpeg()

    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id

    timeline_path = project_root / "final" / "timeline.json"
    clips_dir = project_root / "clips"
    temp_dir = project_root / "final" / "temp"
    output_path = project_root / "final" / "final_reel.mp4"

    temp_dir.mkdir(parents=True, exist_ok=True)

    timeline = load_json(str(timeline_path))

    built = []

    print("🎬 Construyendo clips finales...")

    for scene in timeline["timeline"]:
        clip = build_scene_clip(scene, project_root, clips_dir, temp_dir)
        if clip:
            built.append(clip)

    print("🔥 Uniendo todo...")

    merge_all(built, output_path, temp_dir)

    print(f"✅ FINAL: {output_path}")


if __name__ == "__main__":
    main()