from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()

BASE = Path("D:/LIA-CUENTA_CUENTOS/projects")


# =========================
# LISTAR IMÁGENES
# =========================
@router.get("/{project_id}/images")
def list_images(project_id: str):

    renders_path = BASE / project_id / "renders"

    if not renders_path.exists():
        return {"images": []}

    images = []

    for img in sorted(renders_path.glob("*.png")):
        images.append(f"/assets/{project_id}/image/{img.name}")

    return {"images": images}


# =========================
# SERVIR IMAGEN
# =========================
@router.get("/{project_id}/image/{filename}")
def get_image(project_id: str, filename: str):

    file_path = BASE / project_id / "renders" / filename

    if not file_path.exists():
        return {"error": "not found"}

    return FileResponse(file_path)

@router.get("/{project_id}/images")
def list_images(project_id: str):
    base = Path(f"D:/LIA-CUENTA_CUENTOS/projects/{project_id}/renders")

    if not base.exists():
        return {"images": []}

    files = [f.name for f in base.iterdir() if f.suffix == ".png"]

    return {"images": files}