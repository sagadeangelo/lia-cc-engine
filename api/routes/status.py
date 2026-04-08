from fastapi import APIRouter
import json, os

router = APIRouter()

@router.get("/{project_id}")
def get_status(project_id: str):
    path = f"projects/{project_id}/status.json"
    
    if not os.path.exists(path):
        return {"state": "not_started"}

    with open(path) as f:
        return json.load(f)
