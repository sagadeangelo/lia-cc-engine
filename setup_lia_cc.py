from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(r"D:\LIA-CUENTA_CUENTOS")


DIRS = [
    "input",
    "input/chapters",
    "input/reference_images",
    "input/voices",
    "input/music",
    "input/templates",
    "projects",
    "projects/demo_project",
    "projects/demo_project/scenes",
    "projects/demo_project/renders",
    "projects/demo_project/audio",
    "projects/demo_project/subtitles",
    "projects/demo_project/final",
    "config",
    "schemas",
    "prompts",
    "prompts/masters",
    "prompts/generated",
    "scripts",
    "scripts/utils",
    "workflows",
    "workflows/image",
    "workflows/animation",
    "workflows/upscale",
    "output",
    "output/logs",
    "output/cache",
    "output/temp",
    "output/previews",
    "output/renders",
    "output/videos",
    "assets",
    "assets/fonts",
    "assets/branding",
    "docs",
]


FILES = {
    "README.md": """# LIA-CC

LIA-CC (Cuenta Cuentos) es un pipeline para convertir capítulos o textos narrativos
en escenas, prompts, renders, clips, subtítulos y video final.

## Flujo base
1. Pegar capítulo en `input/chapters/chapter_input.txt`
2. Ejecutar parser de escenas
3. Generar prompts positivos y negativos
4. Mandar prompts a ComfyUI
5. Generar clips / imágenes
6. Agregar voz, subtítulos y música
7. Exportar video final
""",

    "config/app_config.json": json.dumps({
        "project_name": "LIA-CC",
        "root_path": str(ROOT),
        "default_language": "es",
        "default_aspect_ratio": "9:16",
        "default_style": "semi_realistic_3d",
        "default_fps": 24,
        "default_scene_duration_sec": 3,
        "log_level": "INFO"
    }, ensure_ascii=False, indent=2),

    "config/comfyui_config.json": json.dumps({
        "server_url": "http://127.0.0.1:8188",
        "prompt_endpoint": "/prompt",
        "history_endpoint": "/history",
        "ws_endpoint": "/ws",
        "image_workflow_path": "workflows/image/base_image_workflow.json",
        "animation_workflow_path": "workflows/animation/base_animation_workflow.json",
        "upscale_workflow_path": "workflows/upscale/base_upscale_workflow.json"
    }, ensure_ascii=False, indent=2),

    "config/render_profiles.json": json.dumps({
        "draft": {
            "width": 512,
            "height": 896,
            "steps": 20,
            "cfg": 4.5
        },
        "standard": {
            "width": 576,
            "height": 1024,
            "steps": 28,
            "cfg": 5.0
        },
        "premium": {
            "width": 768,
            "height": 1344,
            "steps": 32,
            "cfg": 5.5
        }
    }, ensure_ascii=False, indent=2),

    "schemas/scene_schema.json": json.dumps({
        "project_id": "string",
        "title": "string",
        "source": "Biblia o Libro de Mormón",
        "style": "semi_realistic_3d",
        "scenes": [
            {
                "scene_id": "s01",
                "summary": "Resumen corto de la escena",
                "characters": ["Personaje 1"],
                "dialogue": "",
                "location": "desierto",
                "mood": "solemne",
                "shot_type": "medium",
                "duration_sec": 3,
                "positive_prompt": "",
                "negative_prompt": ""
            }
        ]
    }, ensure_ascii=False, indent=2),

    "input/chapters/chapter_input.txt": """Pega aquí el capítulo completo de la Biblia o del Libro de Mormón.
""",

    "input/templates/chapter_metadata.json": json.dumps({
        "project_id": "demo_project",
        "title": "Capítulo de prueba",
        "source": "Libro de Mormón",
        "book": "1 Nefi",
        "chapter": 1,
        "language": "es",
        "style": "semi_realistic_3d"
    }, ensure_ascii=False, indent=2),

    "projects/demo_project/project.json": json.dumps({
        "project_id": "demo_project",
        "title": "Proyecto Demo",
        "source": "Libro de Mormón",
        "style": "semi_realistic_3d",
        "status": "draft"
    }, ensure_ascii=False, indent=2),

    "projects/demo_project/scenes/scenes.json": json.dumps({
        "project_id": "demo_project",
        "title": "Proyecto Demo",
        "source": "Libro de Mormón",
        "style": "semi_realistic_3d",
        "scenes": []
    }, ensure_ascii=False, indent=2),

    "prompts/masters/positive_master.txt": """cinematic 3D character, semi-realistic animated style, subtle Pixar influence, single subject, centered composition, clean framing, expressive eyes, simple ancient scriptural clothing, natural lighting, cinematic atmosphere, global illumination, unreal engine style render, depth of field, emotional storytelling, 9:16 vertical composition, masterpiece
""",

    "prompts/masters/negative_master.txt": """multiple people, extra person, duplicate face, extra head, bad anatomy, extra arms, extra hands, extra fingers, malformed hands, armor, fantasy outfit, excessive ornaments, cartoon, anime, blurry, low quality, watermark, text, logo
""",

    "workflows/image/base_image_workflow.json": json.dumps({
        "note": "Pega aquí después tu workflow base de imagen de ComfyUI en formato API."
    }, ensure_ascii=False, indent=2),

    "workflows/animation/base_animation_workflow.json": json.dumps({
        "note": "Pega aquí después tu workflow base de animación de ComfyUI en formato API."
    }, ensure_ascii=False, indent=2),

    "workflows/upscale/base_upscale_workflow.json": json.dumps({
        "note": "Pega aquí después tu workflow base de upscale de ComfyUI en formato API."
    }, ensure_ascii=False, indent=2),

    "scripts/__init__.py": "",

    "scripts/utils/__init__.py": "",

    "scripts/utils/file_utils.py": """from pathlib import Path
import json

def load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def save_text(path: str, content: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def save_json(path: str, data) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
""",

    "scripts/01_parse_chapter.py": """from pathlib import Path
from scripts.utils.file_utils import load_text, save_json

ROOT = Path(__file__).resolve().parents[1]
chapter_path = ROOT / "input" / "chapters" / "chapter_input.txt"
output_path = ROOT / "projects" / "demo_project" / "scenes" / "parsed_chapter.json"

text = load_text(str(chapter_path))

data = {
    "title": "Capítulo pendiente de análisis",
    "raw_text": text,
    "notes": "Este archivo será usado por el siguiente paso para dividir escenas."
}

save_json(str(output_path), data)
print(f"Archivo generado: {output_path}")
""",

    "scripts/02_build_scenes.py": """from pathlib import Path
from scripts.utils.file_utils import load_json, save_json

ROOT = Path(__file__).resolve().parents[1]
parsed_path = ROOT / "projects" / "demo_project" / "scenes" / "parsed_chapter.json"
scenes_path = ROOT / "projects" / "demo_project" / "scenes" / "scenes.json"

parsed = load_json(str(parsed_path))

# Placeholder simple. Aquí después meteremos el analizador real.
scenes = {
    "project_id": "demo_project",
    "title": parsed.get("title", "Proyecto Demo"),
    "source": "Libro de Mormón",
    "style": "semi_realistic_3d",
    "scenes": [
        {
            "scene_id": "s01",
            "summary": "Escena inicial generada como ejemplo",
            "characters": ["Personaje principal"],
            "dialogue": "",
            "location": "desierto",
            "mood": "solemne",
            "shot_type": "medium",
            "duration_sec": 3,
            "positive_prompt": "",
            "negative_prompt": ""
        }
    ]
}

save_json(str(scenes_path), scenes)
print(f"Escenas generadas: {scenes_path}")
""",

    "scripts/03_build_prompts.py": """from pathlib import Path
from scripts.utils.file_utils import load_json, load_text, save_json

ROOT = Path(__file__).resolve().parents[1]
scenes_path = ROOT / "projects" / "demo_project" / "scenes" / "scenes.json"
positive_master_path = ROOT / "prompts" / "masters" / "positive_master.txt"
negative_master_path = ROOT / "prompts" / "masters" / "negative_master.txt"
output_path = ROOT / "prompts" / "generated" / "scene_prompts.json"

scenes_data = load_json(str(scenes_path))
positive_master = load_text(str(positive_master_path)).strip()
negative_master = load_text(str(negative_master_path)).strip()

result = {
    "project_id": scenes_data["project_id"],
    "prompts": []
}

for scene in scenes_data["scenes"]:
    positive = f"{positive_master}, {scene['summary']}, location: {scene['location']}, mood: {scene['mood']}, shot: {scene['shot_type']}"
    negative = negative_master
    result["prompts"].append({
        "scene_id": scene["scene_id"],
        "positive_prompt": positive,
        "negative_prompt": negative
    })

save_json(str(output_path), result)
print(f"Prompts generados: {output_path}")
""",

    "scripts/04_prepare_render_queue.py": """from pathlib import Path
from scripts.utils.file_utils import load_json, save_json

ROOT = Path(__file__).resolve().parents[1]
prompts_path = ROOT / "prompts" / "generated" / "scene_prompts.json"
queue_path = ROOT / "output" / "render_queue.json"

prompts_data = load_json(str(prompts_path))

queue = {
    "project_id": prompts_data["project_id"],
    "jobs": []
}

for item in prompts_data["prompts"]:
    queue["jobs"].append({
        "scene_id": item["scene_id"],
        "workflow": "workflows/image/base_image_workflow.json",
        "positive_prompt": item["positive_prompt"],
        "negative_prompt": item["negative_prompt"],
        "output_prefix": f"output/renders/{item['scene_id']}"
    })

save_json(str(queue_path), queue)
print(f"Render queue creada: {queue_path}")
""",

    "scripts/05_run_comfy_queue.py": """from pathlib import Path
from scripts.utils.file_utils import load_json

ROOT = Path(__file__).resolve().parents[1]
queue_path = ROOT / "output" / "render_queue.json"
queue = load_json(str(queue_path))

print("Pendiente conectar con la API de ComfyUI.")
print("Jobs encontrados:", len(queue.get("jobs", [])))
for job in queue.get("jobs", []):
    print(job["scene_id"], "->", job["workflow"])
""",

    "scripts/06_assemble_video.py": """print("Pendiente: ensamblar imágenes, audio, subtítulos y exportar video final.")""",

    "docs/pipeline_notes.md": """# Pipeline LIA-CC

## Módulos
- Parser de capítulo
- Generador de escenas
- Generador de prompts
- Render con ComfyUI
- Animación
- Audio / subtítulos
- Ensamblado final

## Próximos pasos
1. Conectar parser real
2. Conectar ComfyUI API
3. Añadir TTS
4. Añadir FFmpeg
"""
}


def ensure_dirs(root: Path) -> None:
    for d in DIRS:
        (root / d).mkdir(parents=True, exist_ok=True)


def ensure_files(root: Path) -> None:
    for rel_path, content in FILES.items():
        full_path = root / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_path.exists():
            full_path.write_text(content, encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    ensure_dirs(ROOT)
    ensure_files(ROOT)

    print("\\nLIA-CC base creada correctamente en:")
    print(ROOT)
    print("\\nSiguientes pasos recomendados:")
    print("1. Pega tu capítulo en input/chapters/chapter_input.txt")
    print("2. Ejecuta scripts/01_parse_chapter.py")
    print("3. Ejecuta scripts/02_build_scenes.py")
    print("4. Ejecuta scripts/03_build_prompts.py")
    print("5. Ejecuta scripts/04_prepare_render_queue.py")


if __name__ == "__main__":
    main()