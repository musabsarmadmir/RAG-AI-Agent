from pathlib import Path
import os
import json
from typing import Dict, Iterable, Tuple

from google.cloud import firestore

from .config import BASE_DIR, RAG_DATA


DEFAULT_SA = BASE_DIR / "rag-agent-firestore.json"


def _ensure_credentials_env():
    # If env var not set and default service account exists in repo root, set it.
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and DEFAULT_SA.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(DEFAULT_SA)


def get_firestore_client():
    _ensure_credentials_env()
    return firestore.Client()


def load_index_map() -> Dict[str, str]:
    """Load provider index mapping from Firestore metadata document.

    Returns a dict mapping index (as string) -> provider name.
    """
    db = get_firestore_client()
    doc_ref = db.collection("metadata").document("providers_index")
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict() or {}
        return data.get("map", {})
    return {}


def save_index_map(m: dict):
    db = get_firestore_client()
    doc_ref = db.collection("metadata").document("providers_index")
    doc_ref.set({"map": m})
    return True


def set_provider_index(provider: str, index: int, overwrite: bool = False):
    m = load_index_map()
    s_index = str(index)
    for k, v in list(m.items()):
        if v == provider:
            if k == s_index:
                return True
            if not overwrite:
                raise RuntimeError(f"Provider {provider} already assigned to index {k}")
    if s_index in m and m[s_index] != provider:
        raise RuntimeError(f"Index {index} already assigned to provider {m[s_index]}")
    m[s_index] = provider
    save_index_map(m)
    return True


def save_chunk(db, provider_id: str, chunk_id: str, chunk_data: dict):
    doc_ref = db.collection("providers").document(provider_id).collection("chunks").document(chunk_id)
    # Ensure JSON-serializable types
    doc_ref.set(chunk_data)


def load_chunks(db, provider_id: str, page_size: int = 500) -> Iterable[Tuple[str, dict]]:
    coll = db.collection("providers").document(provider_id).collection("chunks")
    for doc in coll.stream():
        yield doc.id, doc.to_dict()


def batch_write_chunks(db, provider_id: str, chunks: Iterable[Tuple[str, dict]], batch_size: int = 400):
    batch = db.batch()
    counter = 0
    for chunk_id, chunk_data in chunks:
        doc_ref = db.collection("providers").document(provider_id).collection("chunks").document(chunk_id)
        batch.set(doc_ref, chunk_data)
        counter += 1
        if counter >= batch_size:
            batch.commit()
            batch = db.batch()
            counter = 0
    if counter > 0:
        batch.commit()


def ensure_provider_metadata(db, provider_id: str, meta: dict):
    doc_ref = db.collection("providers").document(provider_id).collection("metadata").document("meta")
    doc_ref.set(meta)


def _local_chunks_from_path(provider_path: Path):
    chunks_dir = provider_path / "chunks"
    if not chunks_dir.exists():
        return
    for p in sorted(chunks_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        yield p.stem, data


def migrate_provider_from_local(provider_path: Path, dry_run: bool = True):
    db = get_firestore_client()
    provider_id = provider_path.name
    chunks = list(_local_chunks_from_path(provider_path))
    if dry_run:
        return {"provider": provider_id, "chunks_found": len(chunks)}
    batch_write_chunks(db, provider_id, chunks)
    return {"provider": provider_id, "chunks_written": len(chunks)}
"""Firestore-backed provider index mapping.

This module provides the same functions as `app.provider_index` but uses
Google Firestore as the persistent store. It's a lightweight scaffold: to enable
it, set `FIRESTORE_ENABLED=1` in the env and provide a service account key
pointed to by `GOOGLE_APPLICATION_CREDENTIALS`.

Functions:
 - load_index_map()
 - save_index_map(m)
 - get_provider_by_index(index)
 - get_index_by_provider(provider)
 - set_provider_index(provider, index, overwrite=False)

Note: Firestore operations are synchronous here for simplicity.
"""
from google.cloud import firestore
import os


def _get_client():
    # The environment variable GOOGLE_APPLICATION_CREDENTIALS must point
    # to the service account JSON file, or the client will use ADC.
    return firestore.Client()


def _collection():
    return _get_client().collection('provider_index_mappings')


def load_index_map():
    coll = _collection()
    docs = coll.stream()
    out = {}
    for d in docs:
        # document id is the index
        out[d.id] = d.to_dict().get('provider')
    return out


def save_index_map(m: dict):
    coll = _collection()
    # Upsert each mapping
    for k, v in m.items():
        coll.document(str(k)).set({'provider': v})
    # Also delete any docs not present in m
    existing = {d.id for d in coll.stream()}
    for k in existing:
        if k not in m:
            coll.document(k).delete()
    return True


def get_provider_by_index(index: int):
    doc = _collection().document(str(index)).get()
    if not doc.exists:
        return None
    return doc.to_dict().get('provider')


def get_index_by_provider(provider: str):
    coll = _collection()
    q = coll.where('provider', '==', provider).limit(1).stream()
    for d in q:
        try:
            return int(d.id)
        except Exception:
            return None
    return None


def set_provider_index(provider: str, index: int, overwrite: bool = False):
    coll = _collection()
    idx_doc = coll.document(str(index))
    existing = idx_doc.get()
    if existing.exists and existing.to_dict().get('provider') != provider and not overwrite:
        raise RuntimeError(f"Index {index} already assigned to provider {existing.to_dict().get('provider')}")
    # remove any other doc that references this provider
    q = coll.where('provider', '==', provider).stream()
    for d in q:
        if d.id != str(index):
            coll.document(d.id).delete()
    idx_doc.set({'provider': provider})
    return True
