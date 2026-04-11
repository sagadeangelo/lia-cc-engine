from fastapi import APIRouter
from pydantic import BaseModel
import requests
import json
import time
import os
import shutil

router = APIRouter()


# =========================
# REQUEST MODEL
# =========================
class PhotoRequest(BaseModel):
    prompt: str
    project_id: str = None
    character_name: str = None


# =========================
# CONFIG
# =========================
COMFY_URL = "http://127.0.0.1:8188"
COMFY_INPUT = "ComfyUI/input"


# =========================
# HELPER: copiar imagen a comfy
# =========================
def copy_character_to_comfy(project_id, character_name):
    src = f"projects/{project_id}/characters/{character_name}.png"
    dst_folder = os.path.join(COMFY_INPUT, "characters")

    os.makedirs(dst_folder, exist_ok=True)

    dst = os.path.join(dst_folder, f"{character_name}.png")

    if not os.path.exists(src):
        raise Exception(f"Character image not found: {src}")

    shutil.copy(src, dst)

    print("🧠 IMAGE COPIED TO COMFY:", dst)

    return f"characters/{character_name}.png"


# =========================
# ENDPOINT
# =========================
@router.post("/generate/photo")
def generate_photo(req: PhotoRequest):

    print("\n🔥 PHOTO ENDPOINT HIT")
    print("PROMPT:", req.prompt)
    print("PROJECT:", req.project_id)
    print("CHARACTER:", req.character_name)

    try:
        # =========================
        # 1. seleccionar workflow
        # =========================
        if req.character_name:
            workflow_path = "workflows/image/photo_character_workflow.json"
        else:
            workflow_path = "workflows/image/photo_workflow_sdxl.json"

        print("🧠 WORKFLOW:", workflow_path)

        # =========================
        # 2. cargar workflow
        # =========================
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        # =========================
        # 3. inyectar prompt
        # =========================
        workflow["2"]["inputs"]["text"] = req.prompt

        # =========================
        # 4. si hay personaje → usar imagen
        # =========================
        if req.character_name and req.project_id:

            comfy_path = copy_character_to_comfy(
                req.project_id,
                req.character_name
            )

            # 🔥 este nodo debe coincidir con tu workflow
            workflow["4"]["inputs"]["image"] = comfy_path

            print("🧠 USING CHARACTER IMAGE:", comfy_path)

        # =========================
        # 5. enviar a comfy
        # =========================
        res = requests.post(
            f"{COMFY_URL}/prompt",
            json={"prompt": workflow}
        )

        data = res.json()

        print("🧠 COMFY RESPONSE:", data)

        if "prompt_id" not in data:
            return {
                "status": "error",
                "detail": data
            }

        prompt_id = data["prompt_id"]

        print("🧠 PROMPT ID:", prompt_id)

        # =========================
        # 6. polling
        # =========================
        for i in range(60):
            time.sleep(1)

            history = requests.get(
                f"{COMFY_URL}/history/{prompt_id}"
            ).json()

            if prompt_id in history:

                outputs = history[prompt_id]["outputs"]

                for node in outputs.values():
                    if "images" in node:

                        filename = node["images"][0]["filename"]

                        print("✅ IMAGE GENERATED:", filename)

                        return {
                            "status": "success",
                            "image_url": f"{COMFY_URL}/view?filename={filename}"
                        }

        print("⏰ TIMEOUT")
        return {"status": "timeout"}

    except Exception as e:
        print("❌ PHOTO ERROR:", str(e))
        return {
            "status": "error",
            "detail": str(e)
        }