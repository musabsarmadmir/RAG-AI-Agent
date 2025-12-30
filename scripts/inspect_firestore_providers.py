"""Inspect providers stored in Firestore.

Run from repo root (inside venv):

    python scripts/inspect_firestore_providers.py

Requires FIRESTORE_ENABLED=1 and GOOGLE_APPLICATION_CREDENTIALS set (local.env is already wired
through app.config if you use uvicorn/test_all flows).
"""
from pathlib import Path
import sys

# Ensure project root on sys.path so `app` imports work when running the script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.provider_index_firestore import load_index_map, get_firestore_client
from app.config import BASE_DIR


def main() -> None:
    print(f"Project base dir: {BASE_DIR}")

    # 1) Provider index mappings (index -> provider name)
    index_map = load_index_map() or {}
    print("\nProvider index map (index -> provider):")
    if not index_map:
        print("  (no mappings found)")
    else:
        for k, v in sorted(index_map.items(), key=lambda kv: kv[0]):
            print(f"  {k} -> {v}")
    print(f"Total mappings: {len(index_map)}")

    # 2) Providers present in Firestore `providers` collection
    db = get_firestore_client()
    providers = [doc.id for doc in db.collection("providers").stream()]
    print("\nProviders collection IDs:")
    if not providers:
        print("  (no provider documents found)")
    else:
        for pid in sorted(providers):
            print(f"  {pid}")
    print(f"Total providers in Firestore.providers: {len(providers)}")


if __name__ == "__main__":
    main()
