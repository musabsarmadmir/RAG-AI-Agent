r"""Run a local query against the Fatima provider without HTTP, printing detailed debug info.
Usage: .venv/Scripts/python.exe scripts/run_local_query.py
"""
import sys
import traceback
from pathlib import Path

# Ensure project root is on sys.path so `app` package imports work when script is run directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.app_db import get_client_provider
from app.config import PROVIDERS_DIR
from app.embeddings import embedder
from app.llm import call_llm_strict
from sqlitedict import SqliteDict
import faiss
import numpy as np

def main():
    client_id = 100
    question = "What services does Fatima provide?"
    try:
        prov = get_client_provider(client_id)
        print('provider for', client_id, prov)
        dirs = PROVIDERS_DIR / prov
        idx_path = dirs / 'index' / 'faiss.bin'
        db_path = dirs / 'db' / 'metadata.sqlite'
        print('index exists:', idx_path.exists(), 'db exists:', db_path.exists())

        with SqliteDict(str(db_path)) as pdb:
            vector_keys = pdb.get('vector_keys', [])
            print('vector_keys count:', len(vector_keys))
            if not idx_path.exists():
                print('FAISS index missing at', idx_path)
                return
            index = faiss.read_index(str(idx_path))
            # Compute query embedding. If embedding dim mismatches index dim, try local SentenceTransformer fallback.
            qvec_raw = embedder.embed_text(question)
            qvec = np.array(qvec_raw, dtype='float32').reshape(1, -1)
            if qvec.shape[1] != index.d:
                print(f'Embedding dim ({qvec.shape[1]}) != index dim ({index.d}). Trying local SentenceTransformer fallback.')
                try:
                    from sentence_transformers import SentenceTransformer
                    st = SentenceTransformer('all-MiniLM-L6-v2')
                    qvec_local = st.encode([question], show_progress_bar=False)
                    qvec = np.array(qvec_local, dtype='float32').reshape(1, -1)
                    print('Fallback embedding dim:', qvec.shape[1])
                except Exception as e:
                    print('SentenceTransformer fallback failed:', e)
            D, I = index.search(qvec, min(5, index.ntotal))
            print('faiss results indices:', I, 'distances:', D)
            hits = []
            for dist, idx in zip(D[0], I[0]):
                if idx < 0:
                    continue
                key = vector_keys[idx]
                chunk = pdb.get(key)
                hits.append({'key': key, 'text': chunk['text'][:200], 'score': float(dist)})
            print('Retrieved hits sample:', hits)
            context = "\n\n".join([h['text'] for h in hits])
            ans = call_llm_strict(question, context)
            print('\nLLM answer:')
            print(ans)
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    main()
