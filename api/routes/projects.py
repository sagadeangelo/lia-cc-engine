from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from threading import Thread
import subprocess
import json
from pathlib import Path
import uuid

class SaveScriptReq(BaseModel):
    content: str | None = None
    script: str | None = None

router = APIRouter()

# 🔥 RUTA BASE DE PROYECTOS
BASE = Path("D:/LIA-CUENTA_CUENTOS/projects")


# =========================================
# CREATE PROJECT
# =========================================
@router.post("/projects")
def create_project(data: dict):

    project_id = str(uuid.uuid4())
    project_path = BASE / project_id

    # Crear estructura de carpetas
    (project_path / "input").mkdir(parents=True, exist_ok=True)
    (project_path / "scenes").mkdir(parents=True, exist_ok=True)
    (project_path / "prompts").mkdir(parents=True, exist_ok=True)
    (project_path / "renders").mkdir(parents=True, exist_ok=True)
    (project_path / "audio").mkdir(parents=True, exist_ok=True)
    (project_path / "final").mkdir(parents=True, exist_ok=True)

    # Guardar script
    script_path = project_path / "input" / "script.txt"
    script_path.write_text(data.get("script", ""), encoding="utf-8")

    # Crear status inicial
    status_path = project_path / "status.json"
    with open(status_path, "w") as f:
        json.dump({
            "state": "created",
            "progress": 0
        }, f)

    return {"project_id": project_id}


# =========================================
# RUN FULL PIPELINE
# =========================================
@router.post("/projects/{project_id}/run-all")
def run_all(project_id: str):

    def update(status_path, state, progress):
        with open(status_path, "w") as f:
            json.dump({
                "state": state,
                "progress": progress
            }, f)

    def pipeline():

        project_path = BASE / project_id
        status_path = project_path / "status.json"

        try:
            print(f"\n🚀 START PIPELINE {project_id}\n")

            update(status_path, "starting", 0)

            steps = [
                ("01_parse", "scripts/01_parse_chapter.py"),
                ("02_scenes", "scripts/02_build_scenes.py"),
                ("03_prompts", "scripts/03_build_prompts.py"),
                ("04_queue", "scripts/04_prepare_render_queue.py"),
                ("05_comfy", "scripts/05_run_comfy_queue.py"),
                ("07_audio", "scripts/07_generate_voices.py"),
                ("08_timeline", "scripts/08_build_timeline.py"),
                ("09_merge", "scripts/09_merge_audio_video.py"),
            ]

            total = len(steps)

            for i, (name, script) in enumerate(steps):

                print(f"\n🔥 STEP: {name}")

                subprocess.run(
                    ["python", script, project_id],
                    check=True
                )

                progress = int(((i + 1) / total) * 100)
                update(status_path, name, progress)

            update(status_path, "done", 100)

            print("\n✅ PIPELINE COMPLETO\n")

        except Exception as e:
            update(status_path, "error", 0)
            print(f"\n❌ ERROR: {e}\n")

    Thread(target=pipeline).start()

    return {"status": "started"}


# =========================================
# GET STATUS
# =========================================
@router.get("/status/{project_id}")
def get_status(project_id: str):

    status_path = BASE / project_id / "status.json"

    if not status_path.exists():
        return {"state": "not_found"}

    return json.loads(status_path.read_text())


# =========================================
# GET IMAGES
# =========================================
@router.get("/projects/{project_id}/images")
def get_images(project_id: str):

    renders_path = BASE / project_id / "renders"

    if not renders_path.exists():
        return {"images": []}

    images = []

    for img in sorted(renders_path.glob("*.png")):
        images.append(str(img))

    return {"images": images}


# =========================================
# GET VIDEO
# =========================================
@router.get("/projects/{project_id}/video")
def get_video(project_id: str):

    video_path = BASE / project_id / "final" / "final_video.mp4"

    if not video_path.exists():
        return {"error": "video_not_ready"}

    return {"video": str(video_path)}


@router.post("/projects/{project_id}/script")
def save_script(project_id: str, req: SaveScriptReq):
    project_id = project_id.strip()
    project_path = BASE / project_id
    
    # 1. Validar que el proyecto existe
    if not project_path.exists():
        print(f"[SAVE SCRIPT] ERROR: Proyecto no encontrado {project_id}")
        raise HTTPException(status_code=404, detail=f"Proyecto no encontrado: {project_id}")
    
    # 2. Normalizar e Validar que o conteúdo não esteja vazio
    text = req.content or req.script
    
    if not text or not text.strip():
        print(f"[SAVE SCRIPT] ERROR: Contenido vacío para {project_id}")
        raise HTTPException(status_code=400, detail="El contenido del script no puede estar vacío")
    
    # 3. Asegurar carpeta input/
    input_dir = project_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    script_path = input_dir / "script.txt"
    
    # 4. Logging PRO
    used_field = "content" if req.content else "script"
    print(f"[SAVE SCRIPT] project_id={project_id}")
    print(f"[SAVE SCRIPT] field_used={used_field}")
    print(f"[SAVE SCRIPT] content_length={len(text)}")
    print(f"[SAVE SCRIPT] path={script_path}")
    
    # 5. Guardar archivo
    script_path.write_text(text, encoding="utf-8")
    
    return {
        "status": "success",
        "message": "Script saved"
    }


@router.get("/projects")
def list_projects():
    projects = []
    
    # Usamos BASE consistentemente
    if BASE.exists():
        for folder in BASE.iterdir():
            if folder.is_dir():
                projects.append({
                    "project_id": folder.name,
                    "status": "created"
                })

    return {"projects": projects}