from pathlib import Path
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
