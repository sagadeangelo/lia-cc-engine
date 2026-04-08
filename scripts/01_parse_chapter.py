from pathlib import Path
import sys

# Add root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from env_config import BASE_DIR
from scripts.utils.file_utils import load_text, save_json
from scripts.utils.status_manager import StatusManager

def get_project_id() -> str:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Falta project_id.\n"
            "Uso: python scripts/01_parse_chapter.py <project_id>\n"
            "Ejemplo: python scripts/01_parse_chapter.py 1nefi_cap_01"
        )
    return sys.argv[1].strip()

def get_paths(project_id: str) -> dict:
    project_root = BASE_DIR / "projects" / project_id

    return {
        "chapter_path": project_root / "input" / "script.txt",
        "output_path": project_root / "scenes" / "parsed_chapter.json",
        "project_root": project_root
    }


def main():
    project_id = get_project_id()
    paths = get_paths(project_id)

    chapter_path = paths["chapter_path"]
    output_path = paths["output_path"]

    if not chapter_path.exists():
        # Fallback only for generic input
        fallback_path = BASE_DIR / "input" / "chapters" / "chapter_input.txt"
        if fallback_path.exists():
            print(f"[WARN] No se encontró {chapter_path}. Usando fallback global.")
            chapter_path = fallback_path
        else:
            raise FileNotFoundError(f"No existe script de entrada: {chapter_path}")

    text = load_text(str(chapter_path)).strip()

    if not text:
        raise ValueError(f"El archivo está vacío: {chapter_path}")

    data = {
        "project_id": project_id,
        "title": f"Capítulo {project_id}",
        "raw_text": text,
        "notes": "Archivo base para división en escenas (02_build_scenes)."
    }

    save_json(str(output_path), data)

    status = StatusManager(project_id, paths["project_root"])
    status.update_stage("parse_chapter", progress=1.0)

    print(f"[OK] Proyecto creado: {project_id}")
    print(f"[OK] Archivo generado: {output_path}")


if __name__ == "__main__":
    main()