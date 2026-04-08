import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# =========================
# ESTRUCTURA
# =========================

folders = [
    "api",
    "api/routes",
    "api/services",
    "api/models",
    "projects"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)

# =========================
# MAIN
# =========================

create_file("api/main.py", """from fastapi import FastAPI
from api.routes import projects, render, status, assets

app = FastAPI(title="LIA-CC Engine API")

app.include_router(projects.router, prefix="/projects")
app.include_router(render.router, prefix="/render")
app.include_router(status.router, prefix="/status")
app.include_router(assets.router, prefix="/assets")

@app.get("/")
def root():
    return {"message": "LIA-CC Backend Running 🚀"}
""")

# =========================
# PROJECTS
# =========================

create_file("api/routes/projects.py", """from fastapi import APIRouter
import uuid, os, json

router = APIRouter()

BASE = "projects"

@router.post("/create")
def create_project(data: dict):
    project_id = str(uuid.uuid4())
    path = f"{BASE}/{project_id}"
    
    os.makedirs(path, exist_ok=True)

    with open(f"{path}/input.json", "w") as f:
        json.dump(data, f)

    return {"project_id": project_id}
""")

# =========================
# RENDER
# =========================

create_file("api/routes/render.py", """from fastapi import APIRouter
from threading import Thread
from api.services.pipeline_service import run_pipeline

router = APIRouter()

@router.post("/start")
def start_render(data: dict):
    project_id = data["project_id"]

    thread = Thread(target=run_pipeline, args=(project_id,))
    thread.start()

    return {"status": "started"}
""")

# =========================
# STATUS
# =========================

create_file("api/routes/status.py", """from fastapi import APIRouter
import json, os

router = APIRouter()

@router.get("/{project_id}")
def get_status(project_id: str):
    path = f"projects/{project_id}/status.json"
    
    if not os.path.exists(path):
        return {"state": "not_started"}

    with open(path) as f:
        return json.load(f)
""")

# =========================
# ASSETS
# =========================

create_file("api/routes/assets.py", """from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/{project_id}/video")
def get_video(project_id: str):
    path = f"projects/{project_id}/final.mp4"
    
    if not os.path.exists(path):
        return {"error": "video not ready"}

    return FileResponse(path, media_type="video/mp4")
""")

# =========================
# PIPELINE SERVICE
# =========================

create_file("api/services/pipeline_service.py", """import os, json

def update_status(project_id, data):
    path = f"projects/{project_id}/status.json"

    if os.path.exists(path):
        with open(path) as f:
            current = json.load(f)
    else:
        current = {}

    current.update(data)

    with open(path, "w") as f:
        json.dump(current, f, indent=2)


def run_pipeline(project_id):
    update_status(project_id, {"state": "running", "progress": 0})

    os.system(f"python 01_parse_chapter.py --project {project_id}")
    update_status(project_id, {"progress": 20})

    os.system(f"python 02_build_scenes.py --project {project_id}")
    update_status(project_id, {"progress": 40})

    os.system(f"python 03_build_prompts.py --project {project_id}")
    update_status(project_id, {"progress": 60})

    os.system(f"python 05_run_comfy_queue.py --project {project_id}")
    update_status(project_id, {"progress": 80})

    os.system(f"python 09_merge_audio_video.py --project {project_id}")
    update_status(project_id, {"progress": 100, "state": "done"})
""")

print("✅ Backend base creado correctamente")