import json
from pathlib import Path
from typing import Dict, Any

def ensure_provider_dirs(base: Path, provider: str) -> Dict[str, Path]:
    p = base / provider
    dirs = {
        'root': p,
        'excel': p / 'excel',
        'docs': p / 'docs',
        'parsed': p / 'parsed',
        'chunks': p / 'chunks',
        'db': p / 'db',
        'index': p / 'index',
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs

def write_file(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)

def read_json(path: Path) -> Any:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
