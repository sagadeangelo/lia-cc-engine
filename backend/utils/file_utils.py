from pathlib import Path
import json

def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
