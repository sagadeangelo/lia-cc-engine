from pathlib import Path
import sys
import subprocess

sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import BASE_DIR

VIDEO_FORMAT = "vertical"  # "horizontal"
FPS = 25
DURATION_BASE = 5


def get_project_id():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/06_create_clips.py <project_id>")
    return sys.argv[1]


def main():
    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id

    renders_dir = project_root / "renders"
    clips_dir = project_root / "clips"

    clips_dir.mkdir(exist_ok=True)

    images = sorted(renders_dir.glob("*.png"))

    if not images:
        print("❌ No hay imágenes en renders/")
        return

    print(f"🎬 Creando clips para {len(images)} escenas...")

    for i, img in enumerate(images):
        output_clip = clips_dir / f"clip_{i:03}.mp4"

        scale = "1080:1920" if VIDEO_FORMAT == "vertical" else "1920:1080"

        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", str(img),
            "-t", str(DURATION_BASE),
            "-vf", f"scale={scale},zoompan=z='if(lte(zoom,1.0),1.1,zoom-0.0005)'",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            str(output_clip)
      ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f"✅ {output_clip.name}")

    print("🔥 Clips creados correctamente")


if __name__ == "__main__":
    main()