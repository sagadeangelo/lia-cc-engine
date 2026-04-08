import os, json

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
    update_status(project_id, {"state": "running", "progress": 0})

    os.system(f"python 01_parse_chapter.py --project {project_id}")
    update_status(project_id, {"progress": 20})

    os.system(f"python 02_build_scenes.py --project {project_id}")
    update_status(project_id, {"progress": 40})

    os.system(f"python 03_build_prompts.py --project {project_id}")
    update_status(project_id, {"progress": 60})

    os.system(f"python 05_run_comfy_queue.py --project {project_id}")
    update_status(project_id, {"progress": 80})

    os.system(f"python 09_merge_audio_video.py --project {project_id}")
    update_status(project_id, {"progress": 100, "state": "done"})
