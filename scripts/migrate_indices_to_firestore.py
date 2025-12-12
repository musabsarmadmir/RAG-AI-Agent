"""Migrate local provider chunks into Firestore.

Usage:
  python scripts/migrate_indices_to_firestore.py --dry-run
  python scripts/migrate_indices_to_firestore.py

This script walks `rag-data/providers/*/chunks/*.json` and uploads them.
It respects a `--dry-run` flag to only count files.
"""
import argparse
from pathlib import Path
from app.provider_index_firestore import migrate_provider_from_local
from app.config import RAG_DATA


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(RAG_DATA / "providers"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--provider", default=None, help="Only migrate this provider (folder name)")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print("Source path does not exist:", source)
        return

    providers = [p for p in source.iterdir() if p.is_dir()]
    if args.provider:
        providers = [p for p in providers if p.name == args.provider]

    results = []
    for p in providers:
        res = migrate_provider_from_local(p, dry_run=args.dry_run)
        results.append(res)
        print(res)

    print("Migration complete. Providers processed:", len(results))


if __name__ == "__main__":
    main()
