import json
import time
from pathlib import Path

class StatusManager:
    def __init__(self, project_id: str, project_dir: Path):
        self.project_id = project_id
        self.status_file = project_dir / "status.json"
        self.data = self._load()

    def _load(self):
        if self.status_file.exists():
            try:
                with open(self.status_file, "r") as f:
                    return json.load(f)
            except:
                pass
        
        # Default status
        return {
            "project_id": self.project_id,
            "stage": "init",
            "progress": 0.0,
            "total_scenes": 0,
            "completed_scenes": 0,
            "is_running": False,
            "is_aborted": False,
            "error": None,
            "last_update": time.time()
        }

    def save(self):
        self.data["last_update"] = time.time()
        with open(self.status_file, "w") as f:
            json.dump(self.data, f, indent=2)

    def update_stage(self, stage: str, progress: float = None):
        self.data["stage"] = stage
        if progress is not None:
            self.data["progress"] = progress
        self.save()

    def set_running(self, running: bool):
        self.data["is_running"] = running
        self.save()

    def set_error(self, error_msg: str):
        self.data["error"] = error_msg
        self.data["is_running"] = False
        self.save()

    def mark_scene_complete(self, scene_id: str, total_scenes: int):
        self.data["total_scenes"] = total_scenes
        self.data["completed_scenes"] += 1
        self.data["progress"] = (self.data["completed_scenes"] / total_scenes) * 100
        self.save()
