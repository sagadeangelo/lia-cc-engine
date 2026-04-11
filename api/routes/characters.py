import os
from fastapi import APIRouter, UploadFile, File, Form

router = APIRouter()

PROJECTS_DIR = "projects"

# =========================
# CREATE CHARACTER
# =========================
@router.post("/projects/{project_id}/characters")
async def create_character(
    project_id: str,
    name: str = Form(...),
    image: UploadFile = File(...)
):
    print("🔥 ENDPOINT HIT: CREATE CHARACTER")
    print("PROJECT:", project_id)
    print("NAME:", name)
    print("FILENAME:", image.filename)

    try:
        # 1. SANITIZE NAME
        safe_name = name.lower().replace(" ", "_")

        # 2. CREATE FOLDER
        char_dir = os.path.join(PROJECTS_DIR, project_id, "characters")
        os.makedirs(char_dir, exist_ok=True)

        # 3. FILE PATH
        file_path = os.path.join(char_dir, f"{safe_name}.png")

        # 4. SAVE FILE
        content = await image.read()

        with open(file_path, "wb") as f:
            f.write(content)

        print("✅ CHARACTER SAVED:", file_path)

        return {
            "status": "success",
            "name": safe_name,
            "path": file_path
        }

    except Exception as e:
        print("❌ ERROR:", str(e))
        return {"error": str(e)}


# =========================
# LIST CHARACTERS
# =========================
@router.get("/projects/{project_id}/characters")
def list_characters(project_id: str):

    print("📦 LIST CHARACTERS:", project_id)

    char_dir = os.path.join(PROJECTS_DIR, project_id, "characters")

    if not os.path.exists(char_dir):
        return []

    characters = []

    for file in os.listdir(char_dir):
        if file.endswith(".png"):
            name = file.replace(".png", "")

            characters.append({
                "name": name,
                "image_url": f"/assets_root/{project_id}/characters/{file}"
            })

    return characters