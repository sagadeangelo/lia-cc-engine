from fastapi import APIRouter
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
