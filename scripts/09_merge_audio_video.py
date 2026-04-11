from pathlib import Path
import sys
import subprocess
import json
import shutil

sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import BASE_DIR
from scripts.utils.file_utils import load_json


# =========================================================
# CONFIG
# =========================================================
FFMPEG_PRESET = "fast"
CRF = "23"


# =========================================================
# UTILS
# =========================================================

def get_project_id():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/09_merge_audio_video.py <project_id>")
    return sys.argv[1]


def require_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise SystemExit("❌ FFmpeg no está instalado o no está en PATH")


# =========================================================
# BUILD CLIP (VIDEO + AUDIO)
# =========================================================

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

    # =====================================================
    # 🎧 CON AUDIO
    # =====================================================
    if audio_tracks:
        audio_file = audio_tracks[0].get("file")

        # 🔥 buscar en múltiples rutas
        audio_path = project_root / audio_file
        if not audio_path.exists():
            audio_path = project_root / "audio" / Path(audio_file).name

        if not audio_path.exists():
            print(f"⚠️ Audio no encontrado: {audio_file}")
            return None

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", FFMPEG_PRESET,
            "-crf", CRF,
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_clip)
        ]

    # =====================================================
    # 🎞️ SIN AUDIO
    # =====================================================
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", FFMPEG_PRESET,
            "-crf", CRF,
            str(output_clip)
        ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Clip final: {output_clip.name}")
        return output_clip
    except subprocess.CalledProcessError:
        print(f"❌ Error generando clip: {scene_id}")
        return None


# =========================================================
# MERGE FINAL
# =========================================================

def merge_all(clips, output_path, temp_dir):
    if not clips:
        raise SystemExit("❌ No hay clips para unir")

    list_file = temp_dir / "list.txt"

    # 🔥 IMPORTANTE: formato correcto para ffmpeg concat
    content = "\n".join([f"file '{c.as_posix()}'" for c in clips])
    list_file.write_text(content, encoding="utf-8")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_file),

        # 🔥 NO usar copy → causa errores
        "-c:v", "libx264",
        "-preset", FFMPEG_PRESET,
        "-crf", CRF,
        "-c:a", "aac",
        "-b:a", "192k",

        str(output_path)
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        raise SystemExit("❌ Error uniendo clips (FFmpeg falló)")


# =========================================================
# MAIN
# =========================================================

def main():
    require_ffmpeg()

    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id

    timeline_path = project_root / "final" / "timeline.json"
    clips_dir = project_root / "clips"
    temp_dir = project_root / "final" / "temp"
    output_path = project_root / "final" / "final_reel.mp4"

    temp_dir.mkdir(parents=True, exist_ok=True)

    if not timeline_path.exists():
        raise FileNotFoundError(f"No existe timeline.json: {timeline_path}")

    timeline = load_json(str(timeline_path))

    built_clips = []

    print("🎬 Construyendo clips finales...")

    for scene in timeline.get("timeline", []):
        clip = build_scene_clip(scene, project_root, clips_dir, temp_dir)
        if clip:
            built_clips.append(clip)

    print("🔥 Uniendo todo...")

    merge_all(built_clips, output_path, temp_dir)

    print("\n🎉 REEL FINAL CREADO")
    print(f"📁 {output_path}")


if __name__ == "__main__":
    main()