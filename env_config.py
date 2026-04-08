import os
import shutil
import sys
from pathlib import Path

# ----------------------------------------
# 1. ENVIRONMENT DETECTION
# ----------------------------------------
IS_COLAB = os.path.exists("/content")
IS_WINDOWS = os.name == "nt"

# ----------------------------------------
# 2. BASE PATH LOGIC
# ----------------------------------------
if IS_COLAB:
    BASE_DIR = Path("/content/LIA-CUENTA_CUENTOS")
else:
    # Default for local development
    BASE_DIR = Path("D:/LIA-CUENTA_CUENTOS")

# ----------------------------------------
# 3. GOOGLE DRIVE DETECTION & MIGRATION
# ----------------------------------------
DRIVE_DIR = Path("/content/drive/MyDrive/LIA-CC")

if IS_COLAB and DRIVE_DIR.exists():
    COLAB_PROJECTS = BASE_DIR / "projects"
    DRIVE_PROJECTS = DRIVE_DIR / "projects"
    
    # Switch BASE_DIR to Drive
    OLD_BASE = BASE_DIR
    BASE_DIR = DRIVE_DIR
    
    # AUTO MIGRATION (SAFE)
    if COLAB_PROJECTS.exists() and COLAB_PROJECTS.resolve() != DRIVE_PROJECTS.resolve():
        print(f"[ENV] Detectada migración necesaria: {COLAB_PROJECTS} -> {DRIVE_PROJECTS}")
        DRIVE_PROJECTS.mkdir(parents=True, exist_ok=True)
        
        for item in COLAB_PROJECTS.iterdir():
            if item.is_dir():
                target = DRIVE_PROJECTS / item.name
                if not target.exists():
                    print(f"[ENV] Migrando proyecto: {item.name}")
                    try:
                        shutil.move(str(item), str(target))
                    except Exception as e:
                        print(f"[ERROR] No se pudo migrar {item.name}: {e}")
                else:
                    print(f"[ENV] Proyecto {item.name} ya existe en Drive. Saltando.")

# ----------------------------------------
# 4. COMFYUI CONFIG (SAFE + FLEXIBLE)
# ----------------------------------------
# Prioritize Environment Variable
env_comfy = os.environ.get("COMFYUI_PATH")
if env_comfy:
    COMFY_DIR = Path(env_comfy)
else:
    if IS_COLAB:
        COMFY_DIR = Path("/content/ComfyUI")
    else:
        COMFY_DIR = Path("D:/ComfyUI")

def verify_comfy():
    """Verifica que ComfyUI exista y el servidor responda."""
    if not COMFY_DIR.exists():
        raise RuntimeError(f"[CRITICAL] No se encontró ComfyUI en: {COMFY_DIR}")
    
    # Quick check for server (requires requests or similar, using socket for zero-dep check)
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 8188), timeout=1):
            pass
    except (ConnectionRefusedError, socket.timeout):
        print(f"[WARN] El servidor ComfyUI (8188) no responde. Asegúrate de iniciarlo.")
        # We don't raise error here yet as user might start it later, 
        # but scripts calling this will know.

# ----------------------------------------
# 5. PROJECT LOGIC
# ----------------------------------------
def get_project_dir(project_id: str) -> Path:
    p_dir = BASE_DIR / "projects" / project_id
    p_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure structure
    for sub in ["input", "scenes", "prompts", "audio", "output"]:
        (p_dir / sub).mkdir(exist_ok=True)
        
    return p_dir

# Export commonly used paths
INPUT_DIR = BASE_DIR / "input"
ASSETS_DIR = BASE_DIR / "assets"

# Ensure BASE_DIR exists
BASE_DIR.mkdir(parents=True, exist_ok=True)
