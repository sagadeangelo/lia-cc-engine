import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json

ROOT = Path(__file__).resolve().parents[2]

abort_flags = set()

def abort_pipeline(project_id: str):
    abort_flags.add(project_id)
    # Cancel ComfyUI Generation
    import requests
    comfy_config_path = ROOT / "config" / "comfyui_config.json"
    if comfy_config_path.exists():
        try:
            cfg = json.loads(comfy_config_path.read_text(encoding="utf-8"))
            server_url = cfg.get("server_url", "http://127.0.0.1:8188")
            requests.post(f"{server_url}/interrupt", timeout=5)
            requests.post(f"{server_url}/queue", json={"clear": True}, timeout=5)
        except Exception as e:
            print(f"No se pudo interrumpir ComfyUI: {e}")

def check_abort(project_id: str):
    if project_id in abort_flags:
        abort_flags.discard(project_id)
        raise Exception("Abortado por el usuario")

def get_project_root(project_id: str) -> Path:
    return ROOT / "projects" / project_id


def get_status_path(project_id: str) -> Path:
    return get_project_root(project_id) / "status.json"


def write_status(
    project_id: str,
    stage: str,
    message: str,
    progress: float,
    extra: dict | None = None
) -> None:
    status_path = get_status_path(project_id)
    status_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "project_id": project_id,
        "stage": stage,
        "message": message,
        "progress": progress,
        "total_scenes": 0,
        "completed_scenes": 0,
        "is_running": True,
        "is_aborted": False,
        "error": None,
        "last_update": datetime.now().isoformat(timespec="seconds")
    }

    if status_path.exists():
        try:
            existing = json.loads(status_path.read_text(encoding="utf-8"))
            data["total_scenes"] = existing.get("total_scenes", 0)
            data["completed_scenes"] = existing.get("completed_scenes", 0)
            data["is_aborted"] = existing.get("is_aborted", False)
            # Mantener el error si estamos en estado error y no estamos cambiando a uno exitoso
            if stage == "error":
                 data["error"] = existing.get("error")
        except Exception:
            pass

    # Lógica de estados automáticos
    if stage in ["completed", "error", "aborted", "idle"]:
        data["is_running"] = False
    
    if stage == "aborted":
        data["is_aborted"] = True

    if extra:
        data.update(extra)

    status_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def run_script(script_name: str, project_id: str) -> None:
    script_path = ROOT / "scripts" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"No existe el script: {script_path}")

    result = subprocess.run(
        [sys.executable, str(script_path), project_id],
        cwd=str(ROOT),
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(f"Fallo el script: {script_name}")


def run_full_pipeline(project_id: str) -> None:
    try:
        # Aseguramos que el flag de aborto esté limpio al iniciar
        if project_id in abort_flags:
            abort_flags.discard(project_id)
            
        write_status(project_id, "parse_chapter", "Analizando tu historia...", 0.05, extra={
            "is_aborted": False,
            "completed_scenes": 0,
            "total_scenes": 0,
            "error": None
        })
        check_abort(project_id)
        run_script("01_parse_chapter.py", project_id)

        write_status(project_id, "build_scenes", "Construyendo escenas...", 0.15)
        check_abort(project_id)
        run_script("02_build_scenes.py", project_id)

        write_status(project_id, "build_prompts", "Diseñando prompts artísticos...", 0.30)
        check_abort(project_id)
        run_script("03_build_prompts.py", project_id)

        # 04_prepare_render_queue ahora acepta project_id
        write_status(project_id, "build_prompts", "Preparando cola de renderizado...", 0.40)
        check_abort(project_id)
        run_script("04_prepare_render_queue.py", project_id)

        write_status(project_id, "generate_voices", "Creando narración...", 0.50)
        check_abort(project_id)
        run_script("07_generate_voices.py", project_id)

        write_status(project_id, "waiting_for_render", "Enviando escenas a ComfyUI...", 0.60)
        check_abort(project_id)
        run_script("05_run_comfy_queue.py", project_id)

        write_status(project_id, "waiting_for_render", "Renderizando escenas con inteligencia artificial...", 0.70)

        # Módulo de monitoreo de renders (Ahora enfocado en carpetas de proyecto)
        project_root = get_project_root(project_id)
        queue_path = project_root / "output" / "render_queue.json"
        
        total_scenes = 0
        jobs = []
        if queue_path.exists():
            q = json.loads(queue_path.read_text(encoding="utf-8"))
            jobs = q.get("jobs", [])
            total_scenes = len(jobs)
        
        comfy_config_path = ROOT / "config" / "comfyui_config.json"
        output_dir_base = None
        if comfy_config_path.exists():
            try:
                cfg = json.loads(comfy_config_path.read_text(encoding="utf-8"))
                output_dir_base = cfg.get("output_dir")
            except Exception:
                pass
                
        if not output_dir_base:
            output_dir_base = "C:/ComfyUI_windows_portable/ComfyUI/output" # Fallback
            
        import time
        while total_scenes > 0:
            check_abort(project_id)
            completed = 0
            
            for job in jobs:
                prefix = job.get("output_prefix", "")
                if not prefix:
                    continue
                
                # Check normal path AND nested path (ComfyUI sometimes adds 'output/')
                paths_to_check = [
                    Path(output_dir_base) / prefix,
                    Path(output_dir_base) / "output" / prefix
                ]
                
                has_output = False
                for target_path in paths_to_check:
                    parent_dir = target_path.parent
                    file_prefix = target_path.name
                    
                    if parent_dir.exists():
                        for f in parent_dir.iterdir():
                            if f.is_file() and f.name.startswith(file_prefix):
                                if f.suffix.lower() in [".mp4", ".png", ".jpg", ".webp", ".mov", ".mkv"]:
                                    if f.stat().st_size > 0:
                                        has_output = True
                                        break
                    if has_output: break
                
                if has_output:
                    completed += 1
            
            # Progreso en la etapa de renderizado (del 0.70 al 0.90)
            progress_val = 0.70 + ((completed / total_scenes) * 0.20)
            
            write_status(
                project_id, 
                "waiting_for_render", 
                "Renderizando escenas con inteligencia artificial...", 
                progress_val, 
                extra={"completed_scenes": completed, "total_scenes": total_scenes}
            )
            
            if completed >= total_scenes:
                break
            
            # Check abort flag inside loop
            check_abort(project_id)
            time.sleep(3)

        write_status(project_id, "build_timeline", "Sincronizando audio y video...", 0.92)
        check_abort(project_id)
        run_script("08_build_timeline.py", project_id)

        write_status(project_id, "merge_video", "Creando video final...", 0.96)
        check_abort(project_id)
        run_script("09_merge_audio_video.py", project_id)

        import time
        time.sleep(2) # Dar tiempo para ver el estado final
        write_status(project_id, "completed", "¡Generación completada!", 1.0)

    except Exception as exc:
        is_aborted = (str(exc) == "Abortado por el usuario" or project_id in abort_flags)
        
        if is_aborted:
            write_status(
                project_id,
                "aborted",
                "Generación abortada por el usuario.",
                0.0,
                extra={"is_aborted": True}
            )
        else:
            write_status(
                project_id,
                "error",
                f"Error en pipeline: {exc}",
                0.0,
                extra={"error": str(exc)}
            )
        raise

def check_abort_file(project_id: str):
    """
    Función para que los scripts individuales verifiquen el estado de aborto
    leyendo directamente el status.json.
    """
    status_path = get_status_path(project_id)
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if status.get("is_aborted") is True:
                return True
        except Exception:
            pass
    return False