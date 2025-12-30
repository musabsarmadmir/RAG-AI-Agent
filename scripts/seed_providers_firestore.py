#!/usr/bin/env python3
"""Seed multiple test providers and register them in Firestore-backed index.

Usage (from repo root, inside venv):

    python scripts/seed_providers_firestore.py \
        --providers Fatima Alpha Beta \
        --start-client-id 200 \
        --start-index 60

This will, for each provider name:
  - create local test provider data (metadata.xlsx + sample doc)
  - build the local FAISS + sqlite index
  - migrate chunks to Firestore
  - set Firestore provider index mapping (index -> provider)
  - assign client_id -> provider_index in the local app DB

Assumes:
  - FIRESTORE_ENABLED=1 and GOOGLE_APPLICATION_CREDENTIALS are set
    (e.g. via local.env + app.config)
  - FastAPI app can later use these mappings via /v1/query
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import RAG_DATA, PROVIDERS_DIR  # type: ignore
from app.pipeline import build_index_for_provider  # type: ignore
from app.app_db import set_client_provider_index  # type: ignore
from app import provider_index  # type: ignore
from app.provider_index_firestore import migrate_provider_from_local  # type: ignore


def load_local_env(path: Path = Path("local.env")) -> None:
    """Minimal local.env loader so Firestore credentials/env are available."""
    if not path.exists():
        print("local.env not found, skipping env load")
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            os.environ[k.strip()] = v
    print("Loaded env from local.env (FIRESTORE_ENABLED={}, GOOGLE_APPLICATION_CREDENTIALS set={})".format(
        os.environ.get("FIRESTORE_ENABLED"), bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    ))


def create_local_provider(provider: str, client_id: int) -> None:
    """Call existing create_test_provider script to generate local test data."""
    print(f"[provider {provider}] Creating local test data and mapping client {client_id} -> {provider} (name)")
    subprocess.check_call([
        sys.executable,
        str(ROOT / "scripts" / "create_test_provider.py"),
        provider,
        str(client_id),
    ])


def seed_providers(providers, start_client_id: int, start_index: int) -> None:
    load_local_env()

    base_providers = RAG_DATA / "providers"
    summary = []

    for offset, provider in enumerate(providers):
        client_id = start_client_id + offset
        index = start_index + offset

        print(f"\n=== Seeding provider '{provider}' (client_id={client_id}, index={index}) ===")

        # 1) Create local test provider data and client->provider (name) mapping
        create_local_provider(provider, client_id)

        # 2) Build local FAISS + sqlite index
        print(f"[provider {provider}] Building index locally")
        build_index_for_provider(provider, PROVIDERS_DIR)

        # 3) Migrate chunks to Firestore
        provider_path = base_providers / provider
        print(f"[provider {provider}] Migrating chunks from {provider_path} to Firestore")
        res = migrate_provider_from_local(provider_path, dry_run=False)
        print(f"[provider {provider}] Firestore migration result: {res}")

        # 4) Set Firestore provider index mapping
        print(f"[provider {provider}] Setting provider index mapping {index} -> {provider}")
        provider_index.set_provider_index(provider, index, overwrite=True)

        # 5) Store client -> provider_index in app DB so queries go via Firestore mapping
        print(f"[provider {provider}] Mapping client {client_id} -> index {index} in app DB")
        set_client_provider_index(client_id, index)

        summary.append((provider, client_id, index))

    print("\n=== Seeding complete ===")
    for provider, client_id, index in summary:
        print(f"  provider={provider}, client_id={client_id}, index={index}")

    # Optional: exercise full flow via HTTP for each seeded provider
    api_base = os.environ.get("API_BASE", "http://127.0.0.1:8000")
    api_key = os.environ.get("API_KEY", "dev-key-123")
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    print("\n=== Testing /v1/query for each client_id ===")
    for provider, client_id, index in summary:
        question = f"What services does {provider} provide?"
        payload = {"client_id": client_id, "question": question, "top_k": 5}
        try:
            resp = requests.post(f"{api_base}/v1/query", json=payload, headers=headers, timeout=30)
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            print(f"client_id={client_id}, provider={provider}, status={resp.status_code}, response={data}")
        except Exception as e:
            print(f"client_id={client_id}, provider={provider} -> ERROR calling /v1/query: {e}")

    print("\nYou can now query via /v1/query using the seeded client_ids.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", nargs="+", default=["Fatima", "Alpha", "Beta"], help="Provider names to seed")
    ap.add_argument("--start-client-id", type=int, default=200, help="Starting client id (incremented per provider)")
    ap.add_argument("--start-index", type=int, default=60, help="Starting provider index (incremented per provider)")
    args = ap.parse_args()

    seed_providers(args.providers, args.start_client_id, args.start_index)


if __name__ == "__main__":
    main()
