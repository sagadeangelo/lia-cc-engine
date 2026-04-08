import shutil
import sys
import os
from pathlib import Path

# Add root to sys.path for env_config import
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR

def get_project_id() -> str:
    if len(sys.argv) < 2:
        print("Uso: python scripts/reset_project.py <project_id>")
        sys.exit(1)
    return sys.argv[1].strip()

def reset_project(project_id: str):
    project_dir = BASE_DIR / "projects" / project_id
    
    if not project_dir.exists():
        print(f"[WARN] No se encontró el proyecto: {project_id}")
        return

    # Carpetas a eliminar (transeúntes)
    to_delete = ["scenes", "prompts", "audio", "output"]
    
    print(f"[INFO] Reseteando proyecto: {project_id}")
    for sub in to_delete:
        path = project_dir / sub
        if path.exists():
            print(f"       -> Eliminando: {sub}/")
            shutil.rmtree(path)
        # Re-crear limpia
        path.mkdir()

    # Archivos de estado
    status_file = project_dir / "status.json"
    if status_file.exists():
        print(f"       -> Eliminando status.json")
        status_file.unlink()

    print(f"[OK] Proyecto {project_id} reseteado (input/ y characters/ preservados).")

if __name__ == "__main__":
    p_id = get_project_id()
    reset_project(p_id)
