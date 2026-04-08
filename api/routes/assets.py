from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/{project_id}/video")
def get_video(project_id: str):
    path = f"projects/{project_id}/final.mp4"
    
    if not os.path.exists(path):
        return {"error": "video not ready"}

    return FileResponse(path, media_type="video/mp4")
