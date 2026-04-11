from fastapi import APIRouter
import subprocess
import os

router = APIRouter()


@router.post("/projects/{project_id}/run-pipeline")
def run_pipeline(project_id: str):

    print("\n🔥 PIPELINE START:", project_id)

    # 🔥 BASE REAL DEL ENGINE (MUY IMPORTANTE)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    steps = [
        "scripts/01_parse_chapter.py",
        "scripts/02_build_scenes.py",
        "scripts/03_build_prompts.py",
        "scripts/04_prepare_render_queue.py",
        "scripts/05_run_comfy_queue.py"
    ]

    for step in steps:

        # 🔥 CONSTRUIR PATH ABSOLUTO
        script_path = os.path.join(BASE_DIR, step)

        print("\n🚀 RUNNING STEP:", step)
        print("📂 SCRIPT PATH:", script_path)

        # 🔥 VALIDACIÓN CRÍTICA
        if not os.path.exists(script_path):
            print("❌ SCRIPT NO EXISTE:", script_path)

            return {
                "status": "error",
                "step": step,
                "error": f"Script no encontrado: {script_path}"
            }

        # 🔥 EJECUCIÓN REAL
        result = subprocess.run(
            ["python", script_path, project_id],
            capture_output=True,
            text=True
        )

        print("\n📤 STDOUT:\n", result.stdout)
        print("\n📥 STDERR:\n", result.stderr)

        if result.returncode != 0:
            print("❌ ERROR EN:", step)

            return {
                "status": "error",
                "step": step,
                "error": result.stderr,
                "script": script_path
            }

    print("\n✅ PIPELINE COMPLETADO\n")

    return {
        "status": "completed",
        "project_id": project_id
    }