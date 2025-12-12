from pathlib import Path
import json
from .config import RAG_DATA, FIRESTORE_ENABLED

_INDEX_FILE = RAG_DATA / 'providers_index.json'


def _ensure_index_file():
    _INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not _INDEX_FILE.exists():
        _INDEX_FILE.write_text(json.dumps({}))


def _use_firestore():
    return bool(FIRESTORE_ENABLED)


def load_index_map():
    # Prefer Firestore-backed store if enabled
    if _use_firestore():
        try:
            from .provider_index_firestore import load_index_map as _f

            return _f()
        except Exception:
            pass
    _ensure_index_file()
    try:
        return json.loads(_INDEX_FILE.read_text())
    except Exception:
        return {}


def save_index_map(m: dict):
    if _use_firestore():
        try:
            from .provider_index_firestore import save_index_map as _f

            return _f(m)
        except Exception:
            pass
    _ensure_index_file()
    _INDEX_FILE.write_text(json.dumps(m, indent=2))


def get_provider_by_index(index: int):
    m = load_index_map()
    return m.get(str(index))


def get_index_by_provider(provider: str):
    m = load_index_map()
    for k, v in m.items():
        if v == provider:
            try:
                return int(k)
            except Exception:
                return None
    return None


def set_provider_index(provider: str, index: int, overwrite: bool = False):
    if _use_firestore():
        try:
            from .provider_index_firestore import set_provider_index as _f

            return _f(provider, index, overwrite=overwrite)
        except Exception:
            pass
    m = load_index_map()
    s_index = str(index)
    # ensure uniqueness unless overwrite is True
    for k, v in list(m.items()):
        if v == provider:
            if k == s_index:
                return True
            if not overwrite:
                raise RuntimeError(f"Provider {provider} already assigned to index {k}")
    # ensure index not used by other provider
    if s_index in m and m[s_index] != provider:
        raise RuntimeError(f"Index {index} already assigned to provider {m[s_index]}")
    m[s_index] = provider
    save_index_map(m)
    return True


def list_mappings():
    return load_index_map()
