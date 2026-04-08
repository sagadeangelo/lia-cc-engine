from pathlib import Path
import json
import shutil
import uuid
from typing import List, Dict, Any

ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT / "projects"


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_status(project_id: str, status_data: dict | None, project_root: Path) -> dict:
    """Helper to ensure status.json always returns a consistent schema."""
    has_final_video = (project_root / "final" / "lia_cc_final.mp4").exists()
    
    base = {
        "project_id": project_id,
        "stage": "idle",
        "message": "N/A",
        "progress": 0.0,
        "total_scenes": 0,
        "completed_scenes": 0,
        "is_running": False,
        "is_aborted": False,
        "has_final_video": has_final_video,
        "error": None,
        "last_update": ""
    }
    
    if status_data:
        base.update({
            "stage": status_data.get("stage", "idle"),
            "message": status_data.get("message", ""),
            "progress": status_data.get("progress", 0.0),
            "total_scenes": status_data.get("total_scenes", 0),
            "completed_scenes": status_data.get("completed_scenes", 0),
            "is_running": status_data.get("is_running", False),
            "is_aborted": status_data.get("is_aborted", False),
            "error": status_data.get("error", None),
            "last_update": status_data.get("last_update", status_data.get("updated_at", ""))
        })
        base["has_final_video"] = has_final_video or status_data.get("has_final_video", False)
    else:
        base["message"] = "Proyecto encontrado, pero aún sin status.json"
        
    return base


def list_projects() -> list[dict]:
    if not PROJECTS_DIR.exists():
        return []

    items = []
    for path in sorted(PROJECTS_DIR.iterdir()):
        if not path.is_dir():
            continue

        status_path = path / "status.json"
        status_data = None
        if status_path.exists():
            try:
                status_data = _load_json(status_path)
            except Exception:
                pass

        normalized_status = _normalize_status(path.name, status_data, path)

        items.append({
            "project_id": path.name,
            "path": str(path),
            "status": normalized_status
        })

    return items


def get_project_status(project_id: str) -> dict | None:
    project_root = PROJECTS_DIR / project_id
    if not project_root.exists():
        return None

    status_path = project_root / "status.json"
    status_data = None
    if status_path.exists():
        try:
            status_data = _load_json(status_path)
        except Exception:
            pass

    return _normalize_status(project_id, status_data, project_root)


def get_project_files(project_id: str) -> dict | None:
    project_root = PROJECTS_DIR / project_id
    if not project_root.exists():
        return None

    def exists(rel_path: str) -> bool:
        return (project_root / rel_path).exists()

    return {
        "project_root": str(project_root),
        "parsed_chapter": exists("scenes/parsed_chapter.json"),
        "scenes": exists("scenes/scenes.json"),
        "prompts": exists("prompts/scene_prompts.json"),
        "voice_manifest": exists("audio/voice_manifest.json"),
        "timeline": exists("final/timeline.json"),
        "final_video": exists("final/lia_cc_final.mp4"),
        "status": exists("status.json"),
    }


def create_project(project_id: str) -> dict:
    project_root = PROJECTS_DIR / project_id
    if project_root.exists():
        raise ValueError(f"Proyecto {project_id} ya existe")
        
    (project_root / "scenes").mkdir(parents=True, exist_ok=True)
    (project_root / "prompts").mkdir(parents=True, exist_ok=True)
    (project_root / "audio").mkdir(parents=True, exist_ok=True)
    (project_root / "final").mkdir(parents=True, exist_ok=True)
    (project_root / "config").mkdir(parents=True, exist_ok=True)
    (project_root / "input").mkdir(parents=True, exist_ok=True)
    (project_root / "characters").mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    status_data = {
        "project_id": project_id,
        "stage": "idle",
        "message": "Proyecto inicializado",
        "progress": 0.0,
        "total_scenes": 0,
        "completed_scenes": 0,
        "is_running": False,
        "is_aborted": False,
        "has_final_video": False,
        "error": None,
        "last_update": datetime.now().isoformat(timespec="seconds")
    }
    
    (project_root / "status.json").write_text(json.dumps(status_data, indent=2), encoding="utf-8")
    
    return get_project_status(project_id)


def get_project_renders(project_id: str) -> list[str]:
    renders_dir = ROOT / "output" / "renders" / project_id
    if not renders_dir.exists():
        return []
    
    files = []
    for f in renders_dir.iterdir():
        if f.is_file() and f.suffix.lower() in [".png", ".jpg", ".mp4", ".webp"]:
            files.append(f.name)
            
    return sorted(files)


def delete_project(project_id: str) -> None:
    project_root = PROJECTS_DIR / project_id
    if not project_root.exists():
        raise ValueError(f"Proyecto no encontrado: {project_id}")
    import shutil
    shutil.rmtree(project_root)


def get_project_script(project_id: str) -> str:
    script_path = PROJECTS_DIR / project_id / "input" / "script.txt"
    if script_path.exists():
        return script_path.read_text(encoding="utf-8")
    return ""


def save_project_script(project_id: str, content: str) -> None:
    project_root = PROJECTS_DIR / project_id
    if not project_root.exists():
        raise ValueError(f"Proyecto no encontrado: {project_id}")
    
    input_dir = project_root / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    script_path = input_dir / "script.txt"
    script_path.write_text(content, encoding="utf-8")


# ==================================================
# CHARACTERS CRUD
# ==================================================

def list_characters(project_id: str) -> List[Dict[str, Any]]:
    chars_dir = PROJECTS_DIR / project_id / "characters"
    if not chars_dir.exists():
        return []
    
    results = []
    for d in chars_dir.iterdir():
        if d.is_dir():
            meta_path = d / "meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    results.append(meta)
                except Exception:
                    pass
    return sorted(results, key=lambda x: x.get("display_name", ""))

def add_character(project_id: str, char_id: str, display_name: str) -> Dict[str, Any]:
    chars_dir = PROJECTS_DIR / project_id / "characters"
    chars_dir.mkdir(parents=True, exist_ok=True)
    
    char_dir = chars_dir / char_id
    if char_dir.exists():
        raise ValueError(f"El personaje '{char_id}' ya existe.")
        
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / "variations").mkdir(parents=True, exist_ok=True)
    
    meta = {
        "character_id": char_id,
        "display_name": display_name,
        "reference_image": None,
        "source": "manual",
        "label": ""
    }
    
    meta_path = char_dir / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta

def delete_character(project_id: str, char_id: str) -> None:
    char_dir = PROJECTS_DIR / project_id / "characters" / char_id
    if char_dir.exists():
        shutil.rmtree(char_dir)

def save_character_reference(project_id: str, char_id: str, file_data: bytes, original_filename: str) -> str:
    """ Guarda un archivo en character variaciones y/o ref directo y actualiza meta. """
    char_dir = PROJECTS_DIR / project_id / "characters" / char_id
    if not char_dir.exists():
        raise ValueError(f"Personaje '{char_id}' no encontrado.")
        
    ext = Path(original_filename).suffix
    if not ext:
        ext = ".png"
        
    # Siempre guardamos como reference + extension
    safe_filename = f"reference{ext}"
    out_path = char_dir / safe_filename
    out_path.write_bytes(file_data)
    
    # Actualizar metadata
    meta_path = char_dir / "meta.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        
    meta["reference_image"] = safe_filename
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    
    return safe_filename