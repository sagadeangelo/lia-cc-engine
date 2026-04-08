from pathlib import Path
import sys
import json
import uuid
import requests
import random
import copy
import time
import shutil
import os

# Add root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR, COMFY_DIR, verify_comfy
from scripts.utils.file_utils import load_json, save_json
from scripts.utils.status_manager import StatusManager
from scripts.utils.resume_manager import ResumeManager
from backend.services.pipeline_service import check_abort_file

# Mapeo de nodos por tipo de workflow
WORKFLOW_NODE_MAPS = {
    "workflows/image/environment_workflow.json": {
        "positive": ("10", "text"),
        "negative": ("11", "text"),
        "seed": ("12", "seed"),
        "output_prefix": ("14", "filename_prefix")
    },
    "default": { # Base, Wide, Vision
        "positive": ("10", "text"),
        "negative": ("11", "text"),
        "seed": ("12", "seed"),
        "reference_image": ("6", "image"),
        "output_prefix": ("14", "filename_prefix")
    }
}

def get_project_id() -> str:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/05_run_comfy_queue.py <project_id>")
    return sys.argv[1].strip()

def stage_image_for_comfy(project_id: str, local_path: str) -> str:
    """Copia la imagen a ComfyUI/input y devuelve el nombre de archivo."""
    p = Path(local_path)
    if not p.exists():
        return ""
    
    timestamp = int(time.time())
    new_name = f"lia_cc_{project_id}_{timestamp}.png"
    dest = COMFY_DIR / "input" / new_name
    
    # Asegurar que el directorio existe
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    # Validar antes de copiar
    if p.stat().st_size == 0:
        return ""
        
    shutil.copy2(p, dest)
    return new_name

def inject_data(workflow: dict, mapping: dict, job_data: dict) -> dict:
    wf = copy.deepcopy(workflow)
    
    # Inyectar Prompts
    pos_id, pos_field = mapping["positive"]
    wf[pos_id]["inputs"][pos_field] = job_data["positive_prompt"]
    
    neg_id, neg_field = mapping["negative"]
    wf[neg_id]["inputs"][neg_field] = job_data["negative_prompt"]
    
    # Inyectar Seed
    seed_id, seed_field = mapping["seed"]
    wf[seed_id]["inputs"][seed_field] = random.randint(10**8, 10**11)
    
    # Inyectar Output Prefix
    out_id, out_field = mapping["output_prefix"]
    wf[out_id]["inputs"][out_field] = job_data["output_prefix"]
    
    # Inyectar Referencia de Imagen
    if "reference_image" in mapping and job_data.get("reference_image"):
        ref_id, ref_field = mapping["reference_image"]
        wf[ref_id]["inputs"][ref_field] = job_data["reference_image"]

    # Inyectar Peso de IPAdapter (Estilo) - Usualmente nodo 7 en nuestros flujos
    # Si el mapeo no especifica el nodo de peso, intentamos el nodo 7 por defecto si existe
    ip_weight = job_data.get("ip_weight", 0.8)
    if "7" in wf and "weight" in wf["7"]["inputs"]:
        wf["7"]["inputs"]["weight"] = ip_weight
        
    return wf

def main() -> None:
    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id
    queue_path = project_root / "output" / "render_queue.json"
    run_results_path = project_root / "output" / "last_comfy_run.json"
    debug_log_path = project_root / "pipeline_debug.log"

    status = StatusManager(project_id, project_root)
    resume = ResumeManager(project_id, COMFY_DIR)

    def log_debug(msg):
        with open(debug_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        print(msg)

    log_debug(f"=== INICIANDO PIPELINE DE RENDER: {project_id} ===")
    status.set_running(True)
    status.update_stage("rendering", progress=0.0)

    try:
        verify_comfy()
    except Exception as e:
        log_debug(f"[CRITICAL] ComfyUI Error: {e}")
        status.set_error(str(e))
        return

    if not queue_path.exists():
        log_debug(f"[CRITICAL] No existe render_queue.json: {queue_path}")
        status.set_error("No existe render_queue.json")
        return

    queue_data = load_json(str(queue_path))
    server_url = "http://127.0.0.1:8188"
    jobs = queue_data.get("jobs", [])

    results = {"project_id": project_id, "server_url": server_url, "jobs": []}
    
    for job in jobs:
        if check_abort_file(project_id):
            log_debug(f"[ABORT] Deteniendo pipeline por solicitud del usuario.")
            status.set_error("Aborted by user")
            break

        scene_id = job["scene_id"]
        output_prefix = job["output_prefix"]

        if resume.is_scene_complete(scene_id):
            log_debug(f"[SKIP] Escena {scene_id} ya renderizada.")
            results["jobs"].append({**job, "status": "skipped_already_exists"})
            status.mark_scene_complete(scene_id, len(jobs))
            continue

        # TRANFERENCIA DE IMAGEN Y VALIDACIÓN
        local_ref = job.get("reference_image", "")
        staged_name = stage_image_for_comfy(project_id, local_ref)
        if not staged_name:
            log_debug(f"[WARN] Escena {scene_id} saltada: Error al preparar imagen {local_ref}")
            continue

        # Inyectar el nombre del archivo en el input de Comfy, no el path local
        job_for_wf = copy.deepcopy(job)
        job_for_wf["reference_image"] = staged_name

        workflow_path = BASE_DIR / job["workflow"]
        if not workflow_path.exists():
            log_debug(f"[WARN] Escena {scene_id} saltada: Workflow no encontrado en {workflow_path}")
            continue
            
        workflow_json = load_json(str(workflow_path))
        mapping = WORKFLOW_NODE_MAPS.get(job["workflow"], WORKFLOW_NODE_MAPS["default"])
        final_workflow = inject_data(workflow_json, mapping, job_for_wf)
        
        # MECANISMO DE REINTENTO (2 reintentos + 1 intento inicial)
        success = False
        for attempt in range(3):
            try:
                log_debug(f"[INFO] Escena {scene_id}: Intento {attempt + 1}/3...")
                response = requests.post(
                    f"{server_url}/prompt",
                    json={"prompt": final_workflow, "client_id": str(uuid.uuid4())},
                    timeout=30
                )
                response.raise_for_status()
                prompt_id = response.json().get("prompt_id")
                log_debug(f"       [OK] Encolado en ComfyUI: {prompt_id}")
                results["jobs"].append({**job, "status": "enqueued", "comfy_prompt_id": prompt_id})
                status.mark_scene_complete(scene_id, len(jobs))
                success = True
                break
            except Exception as exc:
                log_debug(f"       [ERROR] Fallo en intento {attempt + 1}: {exc}")
                if attempt < 2:
                    time.sleep(1.0) # Espera solicitada de 1s
                else:
                    results["jobs"].append({**job, "status": "error", "error": str(exc)})

        # Pausa obligatoria entre envíos para estabilidad
        time.sleep(1.0)

    save_json(str(run_results_path), results)
    status.update_stage("rendering", progress=1.0)
    status.set_running(False)
    log_debug(f"=== PIPELINE FINALIZADO: {project_id} ===")

if __name__ == "__main__":
    main()