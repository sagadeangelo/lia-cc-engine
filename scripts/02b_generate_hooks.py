from pathlib import Path
import sys
import json
import random

sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import BASE_DIR


# =========================================================
# CORE
# =========================================================

def get_project_id():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/02b_generate_hooks.py <project_id>")
    return sys.argv[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# =========================================================
# HOOK GENERATOR (PROGRESIVO)
# =========================================================

def generate_hook(text, index=0):
    text = str(text or "").lower()

    progression_hooks = [
        "Todo comenzó aquí...",
        "Algo no estaba bien...",
        "Nadie lo vio venir...",
        "Entonces ocurrió algo inesperado...",
        "Ese momento lo cambió todo...",
        "La situación empeoró...",
        "No había vuelta atrás...",
        "Todo estaba por colapsar...",
        "La verdad salió a la luz...",
        "Nada volvería a ser igual...",
        "Y esto solo era el principio..."
    ]

    # 🔥 PROGRESIÓN (CLAVE)
    if index < len(progression_hooks):
        return progression_hooks[index]

    # 🔥 fallback inteligente
    if "visión" in text:
        return "Tuvo una visión impactante..."
    if "dios" in text:
        return "Algo divino estaba ocurriendo..."
    if "desierto" in text:
        return "Tuvieron que huir..."

    return random.choice([
        "Todo estaba por cambiar...",
        "Algo grande estaba pasando...",
        "Nadie sabía lo que venía..."
    ])


# =========================================================
# MAIN
# =========================================================

def main():
    project_id = get_project_id()
    project_root = BASE_DIR / "projects" / project_id

    scenes_path = project_root / "scenes" / "scenes.json"
    output_path = project_root / "scenes" / "hooks.json"

    if not scenes_path.exists():
        raise FileNotFoundError(f"No existe scenes.json en: {scenes_path}")

    scenes_data = load_json(scenes_path)

    hooks = []

    # 🔥 AQUÍ ESTÁ LA CLAVE → enumerate
    for i, scene in enumerate(scenes_data.get("scenes", [])):
        scene_id = scene.get("scene_id", "unknown")
        summary = scene.get("summary", "")

        hook = generate_hook(summary, index=i)

        hooks.append({
            "scene_id": scene_id,
            "hook": hook
        })

    save_json(output_path, {"hooks": hooks})

    print("🔥 Hooks generados correctamente:")
    print(f"📁 {output_path}")


if __name__ == "__main__":
    main()