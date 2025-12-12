"""Quick smoke test for Firestore connectivity.

Usage:
  python scripts/test_firestore_conn.py
"""
from app.provider_index_firestore import get_firestore_client


def main():
    db = get_firestore_client()
    col = db.collection("__rag_test_conn__")
    doc = col.document("ping")
    doc.set({"ok": True})
    got = doc.get()
    print("Firestore test document:", got.to_dict())


if __name__ == "__main__":
    main()
