from pathlib import Path
import sys
import subprocess
import shutil
import glob
import os

# Add root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR, COMFY_DIR
from scripts.utils.file_utils import load_json, save_json
from scripts.utils.status_manager import StatusManager
from backend.services.pipeline_service import check_abort_file

def get_project_id() -> str:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/09_merge_audio_video.py <project_id>")
    return sys.argv[1].strip()

def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("FFmpeg no está disponible en PATH")

def load_comfy_output_dir() -> Path:
    return COMFY_DIR / "output"

def find_rendered_video(output_prefix: str) -> Path | None:
    output_dir_base = load_comfy_output_dir()
    target_pattern = str(output_dir_base / f"{output_prefix}*")
    
    candidates = []
    for match in glob.glob(target_pattern):
        p = Path(match)
        if p.is_file() and p.suffix.lower() in [".mp4", ".webm", ".mov", ".mkv"]:
            if p.stat().st_size > 0:
                candidates.append(p)
    
    if not candidates: return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]

def build_scene_clip(scene: dict, project_root: Path, output_dir_base: Path, temp_dir: Path) -> Path | None:
    scene_id = scene.get("scene_id")
    output_prefix = scene.get("output_prefix")
    
    # Intenta encontrar el video en rutas anidadas (awareness de nesting)
    source_video = find_rendered_video(output_prefix)
    if not source_video:
        # Intento secundario: buscar en output/output/renders (casos específicos de ComfyUI)
        nested_prefix = f"output/{output_prefix}"
        source_video = find_rendered_video(nested_prefix)
        
    if not source_video:
        print(f"[WARN] No se encontró video para {output_prefix}")
        return None

    audio_tracks = scene.get("audio_tracks", [])
    if not audio_tracks:
        print(f"[WARN] No hay audio para {scene_id}, usando solo video.")
        return source_video

    # Tomamos el primer audio (narración principal)
    audio_file = audio_tracks[0].get("file")
    audio_path = project_root / "audio" / audio_file
    
    if not audio_path.exists():
        print(f"[WARN] Archivo de audio no encontrado: {audio_path}")
        return source_video

    output_clip = temp_dir / f"{scene_id}_merged.mp4"
    
    # FFmpeg: Escala a 1280x720, ajusta audio y asegura compatibilidad
    cmd = [
        "ffmpeg", "-y",
        "-i", str(source_video),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-profile:v", "main",
        "-level:v", "3.1",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-shortest",
        str(output_clip)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_clip
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Falló el merge de la escena {scene_id}: {e.stderr.decode()}")
        return None

def merge_clips(clips: list[Path], final_output: Path, temp_dir: Path) -> bool:
    if not clips: return False
    
    list_path = temp_dir / "clips.txt"
    content = "\n".join([f"file '{c.absolute()}'" for c in clips])
    list_path.write_text(content, encoding="utf-8")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(final_output)
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return final_output.exists()
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Falló la concatenación final: {e.stderr.decode()}")
        return False

def main() -> None:
    require_ffmpeg()
    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id
    
    status = StatusManager(project_id, project_root)
    status.update_stage("merging", progress=0.1)

    timeline_path = project_root / "final" / "timeline.json"
    final_video_path = project_root / "final" / "lia_cc_final.mp4"
    temp_dir = project_root / "final" / "temp_merge"

    if not timeline_path.exists():
        raise FileNotFoundError(f"No existe timeline.json: {timeline_path}")

    timeline_data = load_json(str(timeline_path))
    scenes = timeline_data.get("timeline", [])

    temp_dir.mkdir(parents=True, exist_ok=True)
    built_clips = []

    print(f"[*] Iniciando ensamblado de {len(scenes)} escenas...")
    for idx, scene in enumerate(scenes, start=1):
        if check_abort_file(project_id):
            print("[ABORT] Proceso de merge abortado.")
            return

        output_prefix = scene.get("output_prefix")
        clip = build_scene_clip(scene, project_root, load_comfy_output_dir(), temp_dir)
        if clip:
            built_clips.append(clip)
            print(f"    [OK] Escena {idx}/{len(scenes)} procesada.")

    if built_clips:
        success = merge_clips(built_clips, final_video_path, temp_dir)
        if success:
            status.update_stage("merging", progress=1.0)
            print(f"[OK] Video final generado exitosamente: {final_video_path}")
            # Limpieza opcional
            try: shutil.rmtree(temp_dir)
            except: pass
        else:
            status.set_error("Merge failed")
            print("[ERROR] No se pudo crear el archivo final concatenado.")
            sys.exit(1)
    else:
        status.set_error("No clips found")
        print("[ERROR] No se pudo procesar ningún clip de video.")
        sys.exit(1)

if __name__ == "__main__":
    main()