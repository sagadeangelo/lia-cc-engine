from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from pydantic import BaseModel
from pathlib import Path
from backend.services.project_service import (
    list_projects,
    get_project_status,
    get_project_files,
    get_project_renders,
    create_project,
    delete_project,
    get_project_script,
    save_project_script,
    list_characters,
    add_character,
    delete_character,
    save_character_reference,
)
from backend.services.pipeline_service import run_full_pipeline, abort_pipeline
import subprocess
import sys
import requests
import time
import uuid
import shutil

app = FastAPI(title="LIA-CC Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
ROOT = Path(__file__).resolve().parents[1]

# Montar carpeta de renders estática
RENDERS_DIR = os.path.join(ROOT, "output", "renders")
os.makedirs(RENDERS_DIR, exist_ok=True)
app.mount("/renders", StaticFiles(directory=RENDERS_DIR), name="renders")

# Servir proyectos enteros de manera estática
PROJECTS_DIR = os.path.join(ROOT, "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)
app.mount("/api/projects_static", StaticFiles(directory=PROJECTS_DIR), name="projects_static")

# NUEVO: Servir assets para Flutter
app.mount("/assets", StaticFiles(directory=PROJECTS_DIR), name="assets")

# NUEVO: Servir fotos temporales
TEMP_PHOTO_DIR = os.path.join(ROOT, "temp", "photo")
os.makedirs(TEMP_PHOTO_DIR, exist_ok=True)
app.mount("/temp/photo", StaticFiles(directory=TEMP_PHOTO_DIR), name="temp_photo")

running_projects = set()


class CreateProjectReq(BaseModel):
    project_id: str

class SaveScriptReq(BaseModel):
    script: str

class CharacterReq(BaseModel):
    char_id: str
    display_name: str

class PhotoPromptReq(BaseModel):
    prompt: str
    style: str | None = None


@app.get("/")
def root():
    return {
        "ok": True,
        "app": "LIA-CC Backend",
        "status": "running"
    }


@app.get("/health")
def health():
    from env_config import IS_COLAB
    return {
        "ok": True,
        "status": "healthy",
        "env": "colab" if IS_COLAB else "local"
    }


@app.get("/projects")
def projects():
    return {
        "ok": True,
        "projects": list_projects()
    }


@app.post("/projects")
def api_create_project(req: CreateProjectReq):
    try:
        new_proj = create_project(req.project_id)
        return {
            "ok": True,
            "project": new_proj
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/projects/{project_id}/status")
def project_status(project_id: str):
    data = get_project_status(project_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Proyecto no encontrado: {project_id}")
    return {
        "ok": True,
        "project_id": project_id,
        "status": data
    }


@app.get("/projects/{project_id}/files")
def project_files(project_id: str):
    data = get_project_files(project_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Proyecto no encontrado: {project_id}")
    return {
        "ok": True,
        "project_id": project_id,
        "files": data
    }


@app.get("/projects/{project_id}/renders")
def project_renders(project_id: str):
    renders = get_project_renders(project_id)
    return {
        "ok": True,
        "project_id": project_id,
        "renders": renders
    }


def _run_pipeline_task(project_id: str):
    try:
        run_full_pipeline(project_id)
    finally:
        if project_id in running_projects:
            running_projects.remove(project_id)


@app.post("/projects/{project_id}/run-all")
def run_all(project_id: str, background_tasks: BackgroundTasks):
    script_content = get_project_script(project_id)
    if not script_content or not script_content.strip():
        raise HTTPException(
            status_code=400, 
            detail="No se puede ejecutar el pipeline. El script del proyecto está vacío o no existe."
        )

    if project_id in running_projects:
        return {
            "ok": False,
            "project_id": project_id,
            "status": "already_running"
        }
        
    running_projects.add(project_id)
    background_tasks.add_task(_run_pipeline_task, project_id)
    
    return {
        "ok": True,
        "project_id": project_id,
        "status": "started"
    }

# ==========================================
# PART 1 — VIDEO PIPELINE (NON-BLOCKING)
# ==========================================
def run_pipeline_worker(project_id: str):
    print("API HIT: run-pipeline")
    print("PROJECT:", project_id)
    
    scripts = [
        "01_parse_chapter.py",
        "02_build_scenes.py",
        "03_build_prompts.py",
        "04_prepare_render_queue.py",
        "05_run_comfy_queue.py"
    ]
    
    python_exe = sys.executable
    for script in scripts:
        print("STEP:", script)
        script_path = os.path.join(ROOT, "scripts", script)
        # Requisito: subprocess.Popen + wait
        try:
            p = subprocess.Popen([python_exe, script_path, project_id], cwd=ROOT)
            p.wait()
        except Exception as e:
            print(f"Error running step {script}: {e}")
            break

@app.post("/projects/{project_id}/run-pipeline")
async def api_run_pipeline(project_id: str, background_tasks: BackgroundTasks):
    print("API HIT: run-pipeline")
    print("PROJECT:", project_id)
    background_tasks.add_task(run_pipeline_worker, project_id)
    return {"status": "pipeline_started"}

@app.post("/projects/{project_id}/abort")
def api_abort_project(project_id: str):
    try:
        from backend.services.pipeline_service import write_status
        # Set persistent abort flag in status.json so scripts can see it
        write_status(project_id, "aborted", "Abortado por el usuario", 0, extra={"is_aborted": True, "is_running": False})
        
        # Also signal the running orchestrator if it's in the same process memory
        abort_pipeline(project_id)
        
        if project_id in running_projects:
            running_projects.discard(project_id)
            
        return {"ok": True, "project_id": project_id, "status": "aborted"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/projects/{project_id}/sync")
def api_sync_project(project_id: str):
    try:
        from backend.services.pipeline_service import write_status, get_status_path
        import json
        status_path = get_status_path(project_id)
        if status_path.exists():
            data = json.loads(status_path.read_text(encoding="utf-8"))
            stage = data.get("stage", "")
            if stage not in ["completed", "error", "unknown", "not_started"] and project_id not in running_projects:
                write_status(project_id, "error", "Proceso interrumpido (backend reiniciado)", 0)
                return {"ok": True, "status": "fixed_orphan"}
        return {"ok": True, "status": "synced"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/projects/{project_id}/reset")
def api_reset_project(project_id: str):
    try:
        from backend.services.pipeline_service import abort_pipeline, write_status, get_project_root
        import shutil
        
        # 1. Abortar cualquier ejecución activa
        abort_pipeline(project_id)
        if project_id in running_projects:
            running_projects.discard(project_id)
            
        # 2. Deep Clean de carpetas de procesamiento
        project_root = get_project_root(project_id)
        folders_to_clean = ["scenes", "prompts", "audio", "output", "final"]
        
        for folder in folders_to_clean:
            folder_path = project_root / folder
            if folder_path.exists():
                try:
                    shutil.rmtree(str(folder_path))
                    # Re-create mostly empty folders if needed for system stability
                    folder_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"[WARN] No se pudo limpiar {folder}: {e}")
                    
        # 3. Eliminar renders publicos (ROOT/output/renders)
        renders_project_dir = Path(RENDERS_DIR) / project_id
        if renders_project_dir.exists():
            try:
                shutil.rmtree(str(renders_project_dir))
            except Exception as e:
                print(f"[WARN] No se pudo limpiar renders publicos: {e}")

        # 4. Eliminar renders internos de ComfyUI (C:/.../ComfyUI/output/renders/{project_id})
        try:
            comfy_config_path = ROOT / "config" / "comfyui_config.json"
            if comfy_config_path.exists():
                comfy_cfg = json.loads(comfy_config_path.read_text(encoding="utf-8"))
                comfy_output_dir = comfy_cfg.get("output_dir")
                if comfy_output_dir:
                    comfy_project_renders = Path(comfy_output_dir) / "renders" / project_id
                    if comfy_project_renders.exists():
                        print(f"[RESET] Limpiando carpeta interna de ComfyUI: {comfy_project_renders}")
                        shutil.rmtree(str(comfy_project_renders))
        except Exception as e:
            print(f"[WARN] No se pudo limpiar carpeta interna de ComfyUI: {e}")
            
        # 5. Resetear el estado a 'idle'
        write_status(project_id, "idle", "Proyecto reiniciado completamente", 0.0, extra={
            "completed_scenes": 0,
            "total_scenes": 0,
            "is_aborted": False,
            "is_running": False,
            "error": None
        })
        
        return {
            "ok": True, 
            "project_id": project_id, 
            "status": "reset",
            "message": "Limpieza profunda completada."
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/projects/{project_id}")
def api_delete_project(project_id: str):
    try:
        delete_project(project_id)
        if project_id in running_projects:
            running_projects.remove(project_id)
        return {"ok": True, "project_id": project_id, "status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.get("/projects/{project_id}/script")
def api_get_script(project_id: str):
    try:
        content = get_project_script(project_id)
        return {"ok": True, "project_id": project_id, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/projects/{project_id}/script")
def api_save_script(project_id: str, req: SaveScriptReq):
    print("Saving script for:", project_id)
    print("Payload:", req.dict())
    try:
        save_project_script(project_id, req.script)
        return {"status": "saved"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ==========================================
# ENDPOINTS CHARACTERS (FIXED)
# ==========================================

@app.get("/projects/{project_id}/characters")
def api_get_characters(project_id: str):
    print("API HIT: get-characters")
    print("PROJECT:", project_id)
    try:
        # Requisito: Return [{ "name": "...", "image": "/assets/...png" }]
        chars_dir = Path(ROOT) / "projects" / project_id / "characters"
        results = []
        if chars_dir.exists():
            for f in chars_dir.glob("*.png"):
                results.append({
                    "name": f.stem,
                    "image": f"/assets/{project_id}/characters/{f.name}"
                })
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/projects/{project_id}/characters")
async def api_add_character(project_id: str, name: str = Form(...), image: UploadFile = File(...)):
    print("API HIT: create-character")
    print("PROJECT:", project_id)
    try:
        chars_dir = Path(ROOT) / "projects" / project_id / "characters"
        chars_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = chars_dir / f"{name}.png"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            
        return {"status": "saved", "name": name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ==========================================
# PART 4 — ASSETS ENDPOINT
# ==========================================
@app.get("/assets/{project_id}/images")
async def get_assets_images(project_id: str):
    print("API HIT: get-assets")
    print("PROJECT:", project_id)
    try:
        renders_dir = Path(ROOT) / "projects" / project_id / "renders"
        if not renders_dir.exists():
            # Intentar fallback a output/renders/{project_id} si es necesario
            renders_dir = Path(ROOT) / "output" / "renders" / project_id
            
        results = []
        if renders_dir.exists():
            for f in renders_dir.iterdir():
                if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".webp"]:
                    results.append(f.name)
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.delete("/projects/{project_id}/characters/{char_id}")
def api_delete_character(project_id: str, char_id: str):
    try:
        delete_character(project_id, char_id)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/projects/{project_id}/characters/{char_id}/reference/upload")
async def api_upload_character_ref(project_id: str, char_id: str, file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        filename = save_character_reference(project_id, char_id, file_bytes, file.filename)
        return {"ok": True, "filename": filename}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ==========================================
# ENDPOINTS FOTO REAL
# ==========================================
import importlib.util
import json
import uuid

import shutil
import time

# ==========================================
# PART 2 — PHOTO MODE (COMFY SAFE)
# ==========================================
class SimplePhotoReq(BaseModel):
    prompt: str
    negative_prompt: str = ""
    style: str = "cinematic"

@app.post("/generate/photo")
async def api_generate_photo_simple(req: SimplePhotoReq):
    print("API HIT: generate-photo")
    try:
        # 1. Load basic workflow
        workflow_path = Path(ROOT) / "workflows" / "image" / "photo_workflow.json"
        if not workflow_path.exists():
            raise HTTPException(status_code=404, detail="Workflow photo_workflow.json not found")
        
        with open(workflow_path, "r", encoding="utf-8") as f:
            wf = json.load(f)
            
        # 2. Inject prompts (Node 10 for pos, 11 for neg)
        if "10" in wf: wf["10"]["inputs"]["text"] = req.prompt
        if "11" in wf: wf["11"]["inputs"]["text"] = req.negative_prompt
        
        # 3. Send to ComfyUI
        server_url = "http://127.0.0.1:8188"
        response = requests.post(f"{server_url}/prompt", json={"prompt": wf, "client_id": str(uuid.uuid4())})
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Error encolando en ComfyUI")
            
        prompt_id = response.json().get("prompt_id")
        
        # 4. Poll /history/{prompt_id}
        start_time = time.time()
        timeout = 60 # Requisito
        image_name = None
        
        while time.time() - start_time < timeout:
            hist_res = requests.get(f"{server_url}/history/{prompt_id}")
            if hist_res.status_code == 200:
                history = hist_res.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    # Buscar outputs de SaveImage (típicamente nodo 14 en nuestro flujo)
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            image_name = node_output["images"][0].get("filename")
                            break
                    if image_name: break
            time.sleep(2)
            
        if not image_name:
            raise HTTPException(status_code=504, detail="Timeout generando imagen en ComfyUI")
            
        # 5. Extract and save to /temp/photo/
        comfy_out_dir = "C:/ComfyUI_windows_portable/ComfyUI/output" # Default path
        # Try to find comfy_dir from existing config
        try:
            config_path = Path(ROOT) / "config" / "comfyui_config.json"
            if config_path.exists():
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                comfy_out_dir = cfg.get("output_dir", comfy_out_dir)
        except: pass
        
        source_path = Path(comfy_out_dir) / image_name
        dest_filename = f"generated_{int(time.time())}.png"
        dest_path = Path(ROOT) / "temp" / "photo" / dest_filename
        
        if source_path.exists():
            shutil.copy(source_path, dest_path)
            return {"image_url": f"/temp/photo/{dest_filename}"}
        else:
            raise HTTPException(status_code=500, detail=f"Imagen no encontrada en ComfyUI: {source_path}")

    except Exception as exc:
        return {"ok": False, "error": str(exc)}

@app.get("/projects/{project_id}/photo/results")
def api_get_photo_results(project_id: str):
    import shutil
    root_dir = Path(__file__).resolve().parents[1]
    config_path = root_dir / "config" / "comfyui_config.json"
    
    photos_dir = root_dir / "output" / "renders" / project_id / "photos"
    photos_dir.mkdir(parents=True, exist_ok=True)

    try:
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            comfy_out = Path(config.get("output_dir", "C:/ComfyUI_windows_portable/ComfyUI/output"))
            
            if comfy_out.exists():
                # 1. ComfyUI might have respected the nested folder prefix
                nested_folder = comfy_out / "output" / "renders" / project_id / "photos"
                if nested_folder.exists():
                    for f in nested_folder.glob("*.[pm][np][g4]"):
                        try:
                            shutil.move(str(f), str(photos_dir / f.name))
                        except Exception:
                            pass
                
                # 2. ComfyUI might have flattened it to root folder
                for f in comfy_out.glob("photo_*.[pm][np][g4]"):
                    try:
                        shutil.move(str(f), str(photos_dir / f.name))
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error copying comfy output: {e}")

    results = []
    if photos_dir.exists():
        for f in photos_dir.glob("*.[pm][np][g4]"):
            if f.suffix in ['.png', '.mp4'] and f.stat().st_size > 1024:
                results.append(f.name)
    return {
        "ok": True,
        "results": results
    }