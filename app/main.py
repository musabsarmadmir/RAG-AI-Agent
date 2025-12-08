from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from pathlib import Path
from .config import PROVIDERS_DIR, CORS_ORIGINS
from .utils import ensure_provider_dirs, write_file
from .pipeline import build_index_for_provider
from .app_db import get_client_provider
from .embeddings import default_embedding_provider, get_default_embedding_model
from .llm import call_llm_strict
from .core.security import api_key_auth
from .api.models import QueryRequest, QueryResponse, UploadStatus, HealthResponse, HealthProvider
from sqlitedict import SqliteDict
import faiss
import numpy as np
import os
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Agent - Provider Query Service")

# CORS for browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/v1/health', response_model=HealthResponse)
async def health():
    """Basic health check plus simple index stats."""
    providers = []
    try:
        base = PROVIDERS_DIR
        if base.exists():
            for p in sorted(base.iterdir()):
                if not p.is_dir():
                    continue
                idx = (p / 'index' / 'faiss.bin')
                providers.append({
                    'name': p.name,
                    'has_index': idx.exists(),
                })
    except Exception:
        providers = []
    return HealthResponse(status='ok', providers=[HealthProvider(**p) for p in providers])


@app.post('/v1/upload/provider/{provider}/metadata', response_model=UploadStatus)
async def upload_metadata(provider: str, file: UploadFile = File(...), _auth=Depends(api_key_auth)):
    dirs = ensure_provider_dirs(PROVIDERS_DIR, provider)
    dest = dirs['excel'] / 'metadata.xlsx'
    content = await file.read()
    write_file(dest, content)
    return UploadStatus(status='saved', path=str(dest))


@app.post('/v1/upload/provider/{provider}/document', response_model=UploadStatus)
async def upload_document(provider: str, file: UploadFile = File(...), _auth=Depends(api_key_auth)):
    dirs = ensure_provider_dirs(PROVIDERS_DIR, provider)
    if not file.filename:
        raise HTTPException(status_code=400, detail='uploaded file must have a filename')
    safe_name = Path(file.filename).name
    dest = dirs['docs'] / safe_name
    content = await file.read()
    write_file(dest, content)
    return UploadStatus(status='saved', path=str(dest))


@app.post('/v1/admin/rebuild-index/{provider}')
async def rebuild_index(provider: str, _auth=Depends(api_key_auth)):
    dirs = ensure_provider_dirs(PROVIDERS_DIR, provider)
    # Run pipeline synchronously for simplicity
    build_index_for_provider(provider, PROVIDERS_DIR)
    return JSONResponse({'status': 'rebuild_finished', 'provider': provider})


@app.post('/testing/fake-metadata/{provider}')
async def testing_create_fake_metadata(provider: str):
    """Create a simple `metadata.xlsx` file in the provider's `excel/` folder for testing."""
    dirs = ensure_provider_dirs(PROVIDERS_DIR, provider)
    df = pd.DataFrame([
        {
            'name': f'{provider} Test Provider',
            'email': f'contact@{provider}.example',
            'phone': '555-0100',
            'services_summary': 'Test services: alpha, beta, gamma',
            'charges': 'Variable'
        }
    ])
    dest = dirs['excel'] / 'metadata.xlsx'
    df.to_excel(dest, index=False)
    return JSONResponse({'status': 'fake_metadata_created', 'path': str(dest)})


@app.post('/testing/fake-doc/{provider}')
async def testing_create_fake_doc(provider: str):
    """Create a simple test .txt document in provider/docs for pipeline testing."""
    dirs = ensure_provider_dirs(PROVIDERS_DIR, provider)
    dest = dirs['docs'] / f'{provider}_sample.txt'
    sample_text = (
        "This is a sample document for provider: " + provider + ".\n"
        "It contains example details about services and contact info.\n"
        "Use this file to test parsing, chunking and indexing." 
    )
    dest.write_text(sample_text, encoding='utf-8')
    return JSONResponse({'status': 'fake_doc_created', 'path': str(dest)})


@app.post('/v1/query', response_model=QueryResponse)
async def query(payload: QueryRequest, _auth=Depends(api_key_auth)):
    client_id = payload.client_id
    question = payload.question
    provider = get_client_provider(client_id)
    if not provider:
        raise HTTPException(status_code=404, detail='assigned provider not found for client')

    dirs = ensure_provider_dirs(PROVIDERS_DIR, provider)
    idx_path = dirs['index'] / 'faiss.bin'
    db_path = dirs['db'] / 'metadata.sqlite'
    if not idx_path.exists() or not db_path.exists():
        missing = []
        if not idx_path.exists():
            missing.append(f"index file missing: {idx_path}")
        if not db_path.exists():
            missing.append(f"db file missing: {db_path}")
        raise HTTPException(status_code=400, detail=f"Provider data incomplete; {', '.join(missing)}. Please rebuild the provider index.")

    # load provider-local sqlite
    with SqliteDict(str(db_path)) as pdb:
        vector_keys = pdb.get('vector_keys', [])
        # load faiss index
        index = faiss.read_index(str(idx_path))
        # Validate index integrity
        if index.ntotal == 0:
            raise HTTPException(status_code=400, detail='Provider index is empty. Please rebuild the provider index.')
        if vector_keys and len(vector_keys) != index.ntotal:
            raise HTTPException(status_code=400, detail=f'Provider index and DB are out of sync (index count={index.ntotal}, db vectors={len(vector_keys)}). Please rebuild the provider index.')
        # determine embedding model recorded at index time (or use default)
        model_key = pdb.get('embedding_model') or get_default_embedding_model()
        try:
            qemb = default_embedding_provider.embed_text_with_model(model_key, question)
        except Exception as e:
            # If preferred provider is not available, surface error rather than silently using a different model
            raise HTTPException(status_code=500, detail=f'Embedding provider error for model {model_key}: {e}')
        qvec = np.array(qemb, dtype='float32').reshape(1, -1)
        top_k = max(1, min(payload.top_k or 5, index.ntotal))
        D, I = index.search(qvec, top_k)
        hits = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            key = vector_keys[idx]
            chunk = pdb.get(key)
            if chunk:
                hits.append({'key': key, 'text': chunk['text'], 'score': float(dist)})

        if not hits:
            return QueryResponse(answer='Not available.', sources=[])

        # Build context from hits (provider-local only)
        context = '\n\n'.join([h['text'] for h in hits])
        answer = call_llm_strict(question, context)

        # Hallucination filtering: split sentences and check token overlap
        import re

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

        if not kept:
            final = 'Not available.'
        else:
            final = ' '.join(kept)

        sources = [h['key'] for h in hits]
        return QueryResponse(answer=final, sources=sources)


@app.get('/v1/providers')
async def list_providers():
    base = PROVIDERS_DIR
    items = []
    if base.exists():
        for p in sorted(base.iterdir()):
            if p.is_dir():
                items.append(p.name)
    return JSONResponse({'providers': items})

