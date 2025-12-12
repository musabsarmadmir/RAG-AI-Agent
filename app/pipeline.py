from pathlib import Path
import re
import json
from .utils import ensure_provider_dirs, write_json
from .embeddings import default_embedding_provider, get_default_embedding_model
from sqlitedict import SqliteDict
import faiss
import numpy as np
import pandas as pd
import PyPDF2
import docx


def _read_docs_text(docs_dir: Path) -> str:
    texts = []
    for p in sorted(docs_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() == '.pdf':
            try:
                with open(p, 'rb') as fh:
                    reader = PyPDF2.PdfReader(fh)
                    pages = [pg.extract_text() or '' for pg in reader.pages]
                    texts.append('\n'.join(pages))
            except Exception:
                continue
        elif p.suffix.lower() in ('.docx', '.doc'):
            try:
                doc = docx.Document(p)
                texts.append('\n'.join([para.text for para in doc.paragraphs]))
            except Exception:
                continue
        elif p.suffix.lower() in ('.txt',):
            texts.append(p.read_text(encoding='utf-8', errors='ignore'))
    return '\n'.join(texts)


def _normalize_whitespace(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()


def build_index_for_provider(provider: str, base_dir: Path):
    dirs = ensure_provider_dirs(base_dir, provider)
    db_path = dirs['db'] / 'metadata.sqlite'
    with SqliteDict(str(db_path), autocommit=True) as db:
        # Step 1: Excel parsing
        meta_path = dirs['excel'] / 'metadata.xlsx'
        provider_meta = {}
        if meta_path.exists():
            try:
                df = pd.read_excel(meta_path)
                # try to extract columns by common names
                cols = {c.lower(): c for c in df.columns}
                # take first row
                first = df.iloc[0].to_dict()
                provider_meta = {
                    'name': first.get(cols.get('name', ''), '' ) if cols.get('name') else first.get('name',''),
                    'email': first.get(cols.get('email', ''), '' ) if cols.get('email') else first.get('email',''),
                    'phone': first.get(cols.get('phone', ''), '' ) if cols.get('phone') else first.get('phone',''),
                    'services_summary': first.get(cols.get('services summary', ''), '' ) if cols.get('services summary') else first.get('services_summary',''),
                    'charges': first.get(cols.get('charges', ''), '' ) if cols.get('charges') else first.get('charges',''),
                }
            except Exception:
                provider_meta = {}
        db['provider_metadata'] = provider_meta

        # Step 2: Document parsing
        docs_text = _read_docs_text(dirs['docs'])
        combined = json.dumps(provider_meta, ensure_ascii=False) + '\n' + docs_text
        combined = _normalize_whitespace(combined)
        parsed_path = dirs['parsed'] / 'raw_text.txt'
        parsed_path.parent.mkdir(parents=True, exist_ok=True)
        parsed_path.write_text(combined, encoding='utf-8')
        db['raw_text'] = combined

        # Step 3: Chunking
        chunk_size = 800
        overlap = 200
        chunks = []
        i = 0
        start = 0
        text_len = len(combined)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk_text = combined[start:end]
            chunk_obj = {'id': i, 'text': chunk_text}
            chunk_path = dirs['chunks'] / f'chunk_{i}.json'
            write_json(chunk_path, chunk_obj)
            db[f'chunk_{i}'] = chunk_obj
            chunks.append(chunk_text)
            i += 1
            if end == text_len:
                break
            start = end - overlap

        # Step 4: Embedding
        vectors = []
        if chunks:
            # decide which embedding model to use and record it so queries reuse
            model_key = get_default_embedding_model()
            db['embedding_model'] = model_key
            vectors = default_embedding_provider.embed_texts_with_model(model_key, chunks)
            for idx, vec in enumerate(vectors):
                db[f'vector_{idx}'] = vec

        # Step 5: FAISS index
        if vectors:
            arr = np.array(vectors).astype('float32')
            dim = arr.shape[1]
            index = faiss.IndexFlatL2(dim)
            index.add(arr)
            idx_path = dirs['index'] / 'faiss.bin'
            faiss.write_index(index, str(idx_path))
            # store mapping vector idx -> chunk key
            mapping = [f'chunk_{i}' for i in range(len(vectors))]
            db['vector_keys'] = mapping

    return True


def build_index_for_provider_index(provider_index: int, base_dir: Path):
    """Resolve numeric provider index to provider name and build its index."""
    try:
        from . import provider_index as _pi
    except Exception:
        raise RuntimeError('provider_index module not available')
    provider = _pi.get_provider_by_index(int(provider_index))
    if not provider:
        raise RuntimeError(f'No provider found for index {provider_index}')
    return build_index_for_provider(provider, base_dir)
