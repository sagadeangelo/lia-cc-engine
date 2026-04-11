import os, json, time

def update_status(project_id, data):
    path = f"projects/{project_id}/status.json"

    if os.path.exists(path):
        with open(path) as f:
            current = json.load(f)
    else:
        current = {}

    current.update(data)

    with open(path, "w") as f:
        json.dump(current, f, indent=2)


def run_pipeline(project_id):
    print(f"🚀 Pipeline start: {project_id}")

    update_status(project_id, {
        "state": "running",
        "progress": 0,
        "current_step": "parse"
    })

    os.system(f"python scripts/01_parse_chapter.py --project {project_id}")
    update_status(project_id, {"progress": 10})

    os.system(f"python scripts/02_build_scenes.py --project {project_id}")
    update_status(project_id, {
        "progress": 25,
        "current_step": "scenes"
    })

    os.system(f"python scripts/03_build_prompts.py --project {project_id}")
    update_status(project_id, {
        "progress": 40,
        "current_step": "prompts"
    })

    # 🔥 LOOP DE ESCENAS (PRO)
    scenes_path = f"projects/{project_id}/scenes"

    if os.path.exists(scenes_path):
        scenes = sorted(os.listdir(scenes_path))
    else:
        scenes = []

    total = len(scenes)

    for i, scene in enumerate(scenes):
        print(f"🎬 Generando {scene}")

        update_status(project_id, {
            "current_scene": scene,
            "current_step": "rendering",
            "progress": 40 + int((i / max(total,1)) * 40)
        })

        os.system(f"python scripts/05_run_comfy_queue.py --project {project_id} --scene {scene}")

    update_status(project_id, {
        "progress": 85,
        "current_step": "audio"
    })

    os.system(f"python scripts/07_generate_voices.py --project {project_id}")

    update_status(project_id, {
        "progress": 95,
        "current_step": "merge"
    })

    os.system(f"python scripts/09_merge_audio_video.py --project {project_id}")

    update_status(project_id, {
        "state": "done",
        "progress": 100,
        "current_step": "complete"
    })

    print(f"✅ Pipeline finished: {project_id}")