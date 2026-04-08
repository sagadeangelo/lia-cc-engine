from fastapi import APIRouter
from threading import Thread
from api.services.pipeline_service import run_pipeline

router = APIRouter()

@router.post("/start")
def start_render(data: dict):
    project_id = data["project_id"]

    thread = Thread(target=run_pipeline, args=(project_id,))
    thread.start()

    return {"status": "started"}
