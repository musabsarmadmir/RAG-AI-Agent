r"""
Interactive terminal chat against local RAG without HTTP.

Usage (PowerShell):
    python .\scripts\chat_terminal.py --provider Fatima
    # OR use client mapping
    python .\scripts\chat_terminal.py --client-id 100

Commands inside chat:
  /exit        Quit
  /rebuild     Rebuild index for the active provider
  /switch NAME Switch to another provider
  /topk N      Set retrieval top_k (1-20)
"""
import argparse
import sys
import traceback
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.app_db import get_client_provider
from app.config import PROVIDERS_DIR
from app.pipeline import build_index_for_provider
from app.embeddings import default_embedding_provider, get_default_embedding_model
from app.llm import call_llm_strict, call_llm_chat
from sqlitedict import SqliteDict
import faiss
import numpy as np
import re


def resolve_provider(client_id: int | None, provider: str | None) -> str | None:
    if provider:
        return provider
    if client_id is not None:
        return get_client_provider(int(client_id))
    return None


HELP_MSG = """Commands: /exit, /rebuild, /switch NAME, /topk N"""

def ensure_index(provider: str) -> bool:
    dirs = (PROVIDERS_DIR / provider)
    idx_path = dirs / 'index' / 'faiss.bin'
    db_path = dirs / 'db' / 'metadata.sqlite'
    if idx_path.exists() and db_path.exists():
        return True
    print(f"Index or DB missing for provider '{provider}'. Rebuilding...")
    build_index_for_provider(provider, PROVIDERS_DIR)
    ok = idx_path.exists() and db_path.exists()
    print("Rebuild:", "OK" if ok else "FAILED")
    return ok


def retrieve_and_answer(provider: str, question: str, top_k: int = 5, mode: str = "auto") -> tuple[str, list[str]]:
    dirs = (PROVIDERS_DIR / provider)
    idx_path = dirs / 'index' / 'faiss.bin'
    db_path = dirs / 'db' / 'metadata.sqlite'
    with SqliteDict(str(db_path)) as pdb:
        vector_keys = pdb.get('vector_keys', [])
        model_key = pdb.get('embedding_model') or get_default_embedding_model()
        index = faiss.read_index(str(idx_path))
        qemb = default_embedding_provider.embed_text_with_model(model_key, question)
        qvec = np.array(qemb, dtype='float32').reshape(1, -1)
        k = max(1, min(top_k, index.ntotal))
        D, I = index.search(qvec, k)
        hits = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            key = vector_keys[idx]
            chunk = pdb.get(key)
            if chunk:
                hits.append({'key': key, 'text': chunk['text'], 'score': float(dist)})
        # Build context and decide response mode
        context = "\n\n".join([h['text'] for h in hits]) if hits else None
        use_chat = False
        if mode == "chat":
            use_chat = True
        elif mode == "strict":
            use_chat = False
        else:  # auto
            # Simple heuristic: short greetings or generic small-talk → chat
            ql = question.lower().strip()
            greetings = ("hi", "hello", "hey", "yo", "sup")
            use_chat = (len(ql) <= 20 and any(ql.startswith(g) for g in greetings)) or (context is None)

        if use_chat:
            answer = call_llm_chat(question, context)
        else:
            if not hits or context is None:
                return 'Not available.', []
            answer = call_llm_strict(question, context)
        # Simple hallucination filtering
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        kept = []
        chunk_texts = [h['text'] for h in hits]
        for s in sentences:
            s_tokens = set(re.findall(r"\w+", s.lower()))
            overlap = 0
            for ct in chunk_texts:
                ct_tokens = set(re.findall(r"\w+", ct.lower()))
                if s_tokens & ct_tokens:
                    overlap += 1
            if overlap > 0:
                kept.append(s)
        final = ' '.join(kept) if kept else 'Not available.'
        sources = [h['key'] for h in hits]
        return final, sources


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--provider', type=str, default=None, help='Provider name (e.g., Fatima)')
    ap.add_argument('--client-id', type=int, default=None, help='Client id mapped to a provider')
    ap.add_argument('--top-k', type=int, default=5, help='Retrieval top_k (1-20)')
    ap.add_argument('--mode', type=str, default='auto', choices=['auto','chat','strict'], help='Response mode')
    args = ap.parse_args()

    provider = resolve_provider(args.client_id, args.provider) or 'Fatima'
    top_k = max(1, min(args.top_k, 20))
    mode = args.mode

    print(f"Active provider: {provider}  |  top_k={top_k}  |  mode={mode}")
    print(HELP_MSG)

    if not ensure_index(provider):
        print("Failed to ensure index. Exiting.")
        sys.exit(1)

    while True:
        try:
            q = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()  # newline
            break
        if not q:
            continue
        if q.lower() in ("/exit", "exit", "quit", ":q"):
            break
        if q.startswith('/rebuild'):
            ensure_index(provider)
            continue
        if q.startswith('/switch'):
            parts = q.split()
            if len(parts) >= 2:
                npv = parts[1]
                provider = npv
                print(f"Switched provider to: {provider}")
                ensure_index(provider)
            else:
                print("Usage: /switch <provider>")
            continue
        if q.startswith('/topk'):
            parts = q.split()
            if len(parts) >= 2 and parts[1].isdigit():
                top_k = max(1, min(int(parts[1]), 20))
                print(f"Set top_k={top_k}")
            else:
                print("Usage: /topk <N>")
            continue
        if q.startswith('/mode'):
            parts = q.split()
            if len(parts) >= 2 and parts[1] in ('auto','chat','strict'):
                mode = parts[1]
                print(f"Set mode={mode}")
            else:
                print("Usage: /mode <auto|chat|strict>")
            continue

        try:
            answer, sources = retrieve_and_answer(provider, q, top_k=top_k, mode=mode)
            print("Assistant>", answer)
            if sources:
                print("Sources:", ", ".join(sources))
        except Exception:
            traceback.print_exc()


if __name__ == '__main__':
    main()
