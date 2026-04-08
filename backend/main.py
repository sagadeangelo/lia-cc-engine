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

running_projects = set()


class CreateProjectReq(BaseModel):
    project_id: str

class SaveScriptReq(BaseModel):
    content: str

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
    try:
        save_project_script(project_id, req.content)
        return {"ok": True, "project_id": project_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# ==========================================
# ENDPOINTS CHARACTERS
# ==========================================

@app.get("/projects/{project_id}/characters")
def api_get_characters(project_id: str):
    try:
        chars = list_characters(project_id)
        return {"ok": True, "characters": chars}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/projects/{project_id}/characters")
def api_add_character(project_id: str, req: CharacterReq):
    try:
        meta = add_character(project_id, req.char_id, req.display_name)
        return {"ok": True, "character": meta}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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

@app.post("/projects/{project_id}/photo/generate")
def api_generate_photo(
    project_id: str, 
    prompt: str = Form(...),
    style: str = Form("cinematic_realistic"),
    similarity: str = Form("muy_parecido"),
    reference_image: UploadFile = File(None)
):
    try:
        root_dir = Path(__file__).resolve().parents[1]
        script_path = root_dir / "scripts" / "05_run_comfy_queue.py"
        
        spec = importlib.util.spec_from_file_location("run_comfy", str(script_path))
        run_comfy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(run_comfy)

        config_path = root_dir / "config" / "comfyui_config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        server_url = config.get("server_url", "http://127.0.0.1:8188")
        
        photo_id = "photo_" + str(uuid.uuid4())[:8]
        output_prefix = f"output/renders/{project_id}/photos/{photo_id}"
        
        style_map = {
            # SDXL WORKFLOWS
            "pixar_3d": {
                "ckpt": "realistas\\sd_xl_base_1.0.safetensors",
                "lora": "pixarStyleModel_lora128.safetensors",
                "workflow": "workflows/image/photo_workflow_sdxl.json"
            },
            "cinematic_realistic": {
                "ckpt": "realistas\\xxmix9realisticsdxl_v10.safetensors",
                "lora": None,
                "workflow": "workflows/image/photo_workflow_sdxl.json"
            },
            "ultra_realistic": {
                "ckpt": "realistas\\epicphotogasm_ultimateFidelity.safetensors",
                "lora": None,
                "workflow": "workflows/image/photo_workflow_sdxl.json"
            },
            
            # SD 1.5 WORKFLOWS
            "anime": {
                "ckpt": "infantiles\\cornflowerStylizedAnime_12.safetensors",
                "lora": None,
                "workflow": "workflows/image/photo_workflow.json"
            },
            "kawaii": {
                "ckpt": "infantiles\\kawaiiRealistic_v06.safetensors",
                "lora": None,
                "workflow": "workflows/image/photo_workflow.json"
            },
            "stylized": {
                "ckpt": "infantiles\\tekakutli-kiki-v10.safetensors",
                "lora": None,
                "workflow": "workflows/image/photo_workflow.json"
            }
        }
        
        
        selected_style = style_map.get(style, style_map["cinematic_realistic"])
        ckpt_name = selected_style["ckpt"]
        lora_name = selected_style["lora"]
        workflow_rel_path = selected_style["workflow"]
        
        # Handle Reference Image Upload
        denoise_val = 1.0
        ref_image_name = None
        if reference_image and reference_image.filename:
            try:
                from PIL import Image
                import io
                
                # 1. Save locally in project
                ref_dir = root_dir / "projects" / project_id / "input" / "references"
                ref_dir.mkdir(parents=True, exist_ok=True)
                timestamp = int(time.time() * 1000)
                safe_filename = f"lia_cc_{timestamp}.png"
                local_save_path = ref_dir / safe_filename
                
                # Redimensionar la imagen para evitar 'Ran out of memory when regular VAE encoding'
                image_data = reference_image.file.read()
                img = Image.open(io.BytesIO(image_data)).convert("RGB")
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                img.save(local_save_path, format="PNG")
                    
                # Copy to ComfyUI input directory
                comfy_dir = config.get("comfyui_dir", "C:/ComfyUI_windows_portable/ComfyUI")
                comfy_input_dir = Path(comfy_dir) / "input"
                comfy_input_dir.mkdir(parents=True, exist_ok=True)
                comfy_save_path = comfy_input_dir / safe_filename
                shutil.copy(local_save_path, comfy_save_path)
                    
                # 2. Change workflow to img2img version
                workflow_rel_path = workflow_rel_path.replace(".json", "_img2img.json")
                ref_image_name = safe_filename
                
                # 3. Apply Denoise mapping
                denoise_map = {
                    "identico": 0.35,
                    "muy_parecido": 0.55,
                    "algo_parecido": 0.75
                }
                denoise_val = denoise_map.get(similarity, 0.55)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error cargando la imagen de referencia: {str(e)}")

        wf = run_comfy.load_workflow(workflow_rel_path)
        wf = run_comfy.inject_job_data(
            workflow=wf,
            workflow_rel_path=workflow_rel_path,
            positive_prompt=prompt,
            negative_prompt="bad quality, ugly, blurry, deformed, watermark, extra people, bad anatomy",
            output_prefix=output_prefix,
            reference_image=ref_image_name,
            characters=[],
            ckpt_name=ckpt_name,
            lora_name=lora_name,
            denoise=denoise_val
        )
        
        result = run_comfy.queue_prompt(server_url, wf)
        prompt_id = result.get("prompt_id")
        
        return {
            "ok": True, 
            "message": "Solicitud enviada a ComfyUI exitosamente.",
            "prompt_id": prompt_id,
            "photo_id": photo_id
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

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