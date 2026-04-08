from pathlib import Path
import sys
import uuid
import unicodedata
import os

# Add root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR
from scripts.utils.file_utils import load_json, save_json
from scripts.utils.status_manager import StatusManager
# Importamos helper de aborto
from backend.services.pipeline_service import check_abort_file

def get_project_id() -> str:
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/04_prepare_render_queue.py <project_id>")
    return sys.argv[1].strip()

def normalize_text(text: str) -> str:
    if not text: return ""
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

def load_character_references(project_id: str) -> dict:
    ref_map = {}
    chars_dir = BASE_DIR / "projects" / project_id / "characters"
    if not chars_dir.exists():
        return ref_map

    for d in chars_dir.iterdir():
        if d.is_dir():
            meta_path = d / "meta.json"
            if meta_path.exists():
                try:
                    meta = load_json(str(meta_path))
                    ref_img = meta.get("reference_image")
                    if ref_img:
                        d_name = normalize_text(meta.get("display_name", d.name))
                        ref_path = str((d / ref_img).resolve())
                        # Validate exists and not empty
                        if os.path.exists(ref_path) and os.path.getsize(ref_path) > 0:
                            ref_map[d_name] = ref_path
                except Exception:
                    pass
    return ref_map

def get_character_reference(characters, ref_map):
    for c in characters:
        n_c = normalize_text(c)
        if n_c in ref_map:
            return ref_map[n_c]
    return None

def choose_workflow(render_profile, characters):
    base_wf = "workflows/image/base_image_workflow.json"
    
    choice = base_wf
    if render_profile == "wide":
        choice = "workflows/image/wide_workflow.json"
    elif render_profile == "vision":
        choice = "workflows/image/vision_workflow.json"
        
    if not (BASE_DIR / choice).exists() or "environment_workflow" in choice:
        return base_wf
        
    return choice

def build_output_prefix(project_id, scene_id):
    return f"renders/{project_id}/{scene_id}"

def main():
    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id
    
    status = StatusManager(project_id, project_root)
    status.update_stage("prepare_queue", progress=0.1)

    prompts_path = project_root / "prompts" / "scene_prompts.json"
    output_queue_path = project_root / "output" / "render_queue.json"
    default_ref_path = str((BASE_DIR / "assets" / "default_reference.png").resolve())

    if not prompts_path.exists():
        status.set_error(f"No existe scene_prompts.json")
        raise FileNotFoundError(f"No existe scene_prompts.json: {prompts_path}")

    data = load_json(str(prompts_path))
    ref_map = load_character_references(project_id)
    
    # Obtener el primer personaje del proyecto como ancla de estilo global
    first_project_char_ref = None
    if ref_map:
        first_project_char_ref = list(ref_map.values())[0]

    prompts = data.get("prompts", [])
    if not prompts:
        print("[WARN] No hay prompts en scene_prompts.json")
        return

    jobs = []
    for scene in prompts:
        # Abort check
        if check_abort_file(project_id):
            print("[ABORT] Proceso abortado por el usuario.")
            return

        scene_id = scene["scene_id"]
        characters = scene.get("characters", [])
        render_profile = scene.get("render_profile", "standard")
        
        workflow = choose_workflow(render_profile, characters)
        output_prefix = build_output_prefix(project_id, scene_id)
        
        # CADENA DE FALLBACK DE REFERENCIA:
        # 1. Personaje de la escena
        # 2. Primer personaje del proyecto (Style Anchor)
        # 3. Imagen por defecto del sistema
        reference_image = get_character_reference(characters, ref_map) if characters else None
        ip_weight = 0.8 # Por defecto para personajes
        
        if not reference_image:
            if first_project_char_ref:
                reference_image = first_project_char_ref
                ip_weight = 0.45 # Peso bajo para ancla de estilo en paisajes
            else:
                reference_image = default_ref_path
                ip_weight = 0.35 # Peso mínimo para backup genérico

        job = {
            "scene_id": scene_id,
            "workflow": workflow,
            "prompt_id": str(uuid.uuid4()),
            "status": "queued",
            "output_prefix": output_prefix,
            "positive_prompt": scene["positive_prompt"],
            "negative_prompt": scene["negative_prompt"],
            "camera_motion": scene.get("camera_motion", ""),
            "animation_hint": scene.get("animation_hint", ""),
            "render_profile": render_profile,
            "characters": characters,
            "reference_image": reference_image,
            "ip_weight": ip_weight
        }
        jobs.append(job)

    result = {
        "project_id": project_id,
        "jobs": jobs
    }

    output_queue_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(str(output_queue_path), result)
    status.update_stage("prepare_queue", progress=1.0)

    print(f"\n[OK] Render queue creada con Failsafe de Referencias para {project_id}")

if __name__ == "__main__":
    main()