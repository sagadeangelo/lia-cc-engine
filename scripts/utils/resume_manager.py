import os
from pathlib import Path

class ResumeManager:
    def __init__(self, project_id: str, comfy_dir: Path):
        self.project_id = project_id
        # Standard output location for LIA-CC in ComfyUI
        self.render_dir = comfy_dir / "output" / "renders" / project_id

    def get_completed_scenes(self) -> set:
        """Retorna un conjunto de scene_ids que ya tienen un render válido."""
        if not self.render_dir.exists():
            return set()
        
        completed = set()
        for f in self.render_dir.glob("*.png"):
            if f.stat().st_size > 0:
                # El nombre suele ser scene_id.png o similar
                scene_id = f.stem
                completed.add(scene_id)
            else:
                # Si está vacío (0 bytes), está corrupto o falló
                print(f"[WARN] Detectado render corrupto (0 bytes): {f.name}. Se re-renderizará.")
                
        return completed

    def is_scene_complete(self, scene_id: str) -> bool:
        return scene_id in self.get_completed_scenes()
