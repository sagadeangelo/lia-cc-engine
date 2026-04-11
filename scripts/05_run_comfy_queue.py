from pathlib import Path
import sys
import json
import uuid
import requests
import random
import time
import os

sys.path.append(str(Path(__file__).resolve().parents[1]))

from env_config import BASE_DIR, COMFY_DIR, verify_comfy
from scripts.utils.file_utils import load_json
from scripts.utils.status_manager import StatusManager
from scripts.utils.resume_manager import ResumeManager

print("🔥 COMFY USADO:", COMFY_DIR)


def get_project_id():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/05_run_comfy_queue.py <project_id>")
    return sys.argv[1]


def log(msg):
    print(msg)


def wait_for_result(server_url, prompt_id):
    for _ in range(60):
        time.sleep(1)
        history = requests.get(f"{server_url}/history/{prompt_id}").json()
        if prompt_id in history:
            return history[prompt_id]
    return None


def main():
    project_id = get_project_id()

    project_root = BASE_DIR / "projects" / project_id
    queue_path = project_root / "output" / "render_queue.json"

    output_dir = project_root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    server_url = "http://127.0.0.1:8188"

    log(f"🔥 INICIANDO PIPELINE: {project_id}")

    verify_comfy()

    queue_data = load_json(str(queue_path))
    jobs = queue_data.get("jobs", [])

    for index, job in enumerate(jobs):

        scene_id = job["scene_id"]
        prompt = job["positive_prompt"]
        negative = job.get("negative_prompt", "")

        log(f"\n🎬 Escena {scene_id}")
        log(f"🧠 Prompt: {prompt[:80]}...")

        workflow_file = BASE_DIR / "workflows" / "image" / "photo_workflow.json"
        workflow = load_json(str(workflow_file))

        # 🔥 INYECTAR PROMPTS
        workflow["10"]["inputs"]["text"] = prompt
        workflow["11"]["inputs"]["text"] = negative

        # 🔥 SEED RANDOM REAL
        workflow["12"]["inputs"]["seed"] = random.randint(1, 999999999)

        try:
            log("🚀 Enviando a ComfyUI...")

            res = requests.post(
                f"{server_url}/prompt",
                json={"prompt": workflow, "client_id": str(uuid.uuid4())}
            )

            prompt_id = res.json()["prompt_id"]

            log(f"🆔 Prompt ID: {prompt_id}")

            result = wait_for_result(server_url, prompt_id)

            if not result or "outputs" not in result:
                raise Exception("No result")

            images = []

            for node in result["outputs"].values():
                if "images" in node:
                    images.extend(node["images"])

            if not images:
                raise Exception("No images")

            for img in images:
                filename = img["filename"]
                sub = img.get("subfolder", "")

                url = f"{server_url}/view?filename={filename}&subfolder={sub}&type=output"

                # 🔥 GUARDAR ORDENADO EN OUTPUT
                save_path = output_dir / f"{scene_id}.png"

                data = requests.get(url).content

                with open(save_path, "wb") as f:
                    f.write(data)

                log(f"✅ Guardado: {save_path}")

        except Exception as e:
            log(f"❌ Error en escena {scene_id}: {e}")

    log("🔥 PIPELINE TERMINADO")


if __name__ == "__main__":
    main()