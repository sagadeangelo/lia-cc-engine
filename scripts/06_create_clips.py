from pathlib import Path
import sys
import time

sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import get_project_dir
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from PIL import Image


def main():
    project_id = sys.argv[1]
    project_dir = get_project_dir(project_id)

    images_dir = project_dir / "output"
    images = sorted(images_dir.glob("*.png"))
    temp_dir = project_dir / "temp_frames"
    temp_dir.mkdir(exist_ok=True)

    print(f"🎬 Generando video para {project_id}")

    # 🔥 filtrar imágenes recientes (últimos 5 minutos)
    now = time.time()
    last_minutes = 60 * 60  # 1 hora

    images = sorted(comfy_output.glob("*.png"), key=lambda x: x.stat().st_mtime)

    # 🔥 tomar solo las últimas 20 imágenes (ajusta según tus escenas)
    images = images[-20:]

    if not images:
        print("❌ No hay imágenes recientes en ComfyUI")
        return

    print(f"📸 Imágenes detectadas: {len(images)}")

    # 🔥 tamaño base
    base_size = Image.open(images[0]).size

    processed_paths = []

    for i, img_path in enumerate(images):
        img = Image.open(img_path).convert("RGB")

        # 🔥 normalizar tamaño
        img = img.resize(base_size)

        new_path = temp_dir / f"frame_{i:03}.png"
        img.save(new_path)

        processed_paths.append(str(new_path))

    print("🎞️ Construyendo video...")

    clip = ImageSequenceClip(processed_paths, fps=2)

    output_video = project_dir / "output" / "video.mp4"
    clip.write_videofile(str(output_video), codec="libx264")

    print(f"✅ Video generado en: {output_video}")


if __name__ == "__main__":
    main()