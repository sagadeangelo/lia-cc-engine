import os
import shutil
from pathlib import Path

# ----------------------------------------
# 🔥 CONFIG FIJA (SIN CONFUSIÓN)
# ----------------------------------------

BASE_DIR = Path("D:/lia-cc-engine")
COMFY_DIR = Path("D:/ComfyUI")

print("🔥 BASE_DIR REAL:", BASE_DIR)
print("🔥 COMFY_DIR REAL:", COMFY_DIR)

# ----------------------------------------
# 🧠 VERIFICAR COMFYUI
# ----------------------------------------

def verify_comfy():
    if not COMFY_DIR.exists():
        raise RuntimeError(f"[CRITICAL] No se encontró ComfyUI en: {COMFY_DIR}")
    
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 8188), timeout=1):
            pass
    except (ConnectionRefusedError, socket.timeout):
        print("[WARN] ComfyUI (8188) no está corriendo")

# ----------------------------------------
# 📁 PROJECT LOGIC
# ----------------------------------------

def get_project_dir(project_id: str) -> Path:
    p_dir = BASE_DIR / "projects" / project_id
    p_dir.mkdir(parents=True, exist_ok=True)

    for sub in ["input", "scenes", "prompts", "audio", "output"]:
        (p_dir / sub).mkdir(exist_ok=True)

    return p_dir

# ----------------------------------------
# 📦 PATHS GLOBALES
# ----------------------------------------

INPUT_DIR = BASE_DIR / "input"
ASSETS_DIR = BASE_DIR / "assets"

BASE_DIR.mkdir(parents=True, exist_ok=True)