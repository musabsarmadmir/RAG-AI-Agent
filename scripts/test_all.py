#!/usr/bin/env python3
"""scripts/test_all.py

Python end-to-end test runner for the RAG AI Agent repository.

This script performs the following actions (in sequence):
- loads `local.env` into os.environ
- creates a test provider using `scripts/create_test_provider.py`
- calls testing endpoints to ensure files exist
- uploads metadata and document via HTTP API
- triggers index rebuild via the repository script
- verifies FAISS index and sqlite DB are present and in sync
- issues a sample `POST /v1/query` and prints the response

Run this from the repository root inside the project venv:
    python scripts/test_all.py

"""
import os
import sys
import time
import json
import subprocess
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

def load_local_env(path: Path = Path('local.env')):
    if not path.exists():
        print('local.env not found, skipping load')
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            v = v.strip().strip('"').strip("'")
            os.environ[k.strip()] = v
    print('Loaded env vars: API_KEY={}, OPENAI_API_KEY={}'.format(os.environ.get('API_KEY'), '(hidden)' if os.environ.get('OPENAI_API_KEY') else ''))

def run_create_test_provider(provider='Fatima', client_id=100):
    print(f'Creating test provider {provider} -> client {client_id}')
    subprocess.check_call([sys.executable, str(ROOT/'scripts'/'create_test_provider.py'), provider, str(client_id)])

def call_endpoint(method, path, headers=None, json_body=None, files=None, timeout=30):
    url = f'http://127.0.0.1:8000{path}'
    s = requests.Session()
    retries = requests.adapters.Retry(total=3, backoff_factor=1, status_forcelist=[500,502,503,504])
    s.mount('http://', requests.adapters.HTTPAdapter(max_retries=retries))
    resp = s.request(method, url, headers=headers, json=json_body, files=files, timeout=timeout)
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data

def run_tests():
    # Load env
    load_local_env()

    api_key = os.environ.get('API_KEY')
    if not api_key:
        print('WARNING: API_KEY not set in environment; upload/rebuild/query will likely fail')

    # Create provider and files
    run_create_test_provider('Fatima', 100)

    # Call testing endpoints to create fake metadata/doc
    for ep in [f'/testing/fake-metadata/Fatima', f'/testing/fake-doc/Fatima']:
        code, data = call_endpoint('POST', ep, timeout=15)
        print(f'POST {ep} -> {code} {data}')
        if code >= 400:
            raise SystemExit(f'Endpoint {ep} failed with {code}: {data}')

    # Upload metadata and doc via API
    headers = {'x-api-key': api_key} if api_key else {}

    meta_path = ROOT/'rag-data'/'providers'/'Fatima'/'excel'/'metadata.xlsx'
    doc_path = ROOT/'rag-data'/'providers'/'Fatima'/'docs'/'Fatima_sample.txt'
    if not meta_path.exists() or not doc_path.exists():
        raise SystemExit('Expected test files not present; ensure earlier steps succeeded')

    with meta_path.open('rb') as mf:
        files = {'file': ('metadata.xlsx', mf, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        code, data = call_endpoint('POST', '/v1/upload/provider/Fatima/metadata', headers=headers, files=files, timeout=60)
        print('Upload metadata ->', code, data)
        if code != 200:
            raise SystemExit('Metadata upload failed: {}'.format(data))

    with doc_path.open('rb') as df:
        files = {'file': ('Fatima_sample.txt', df, 'text/plain')}
        code, data = call_endpoint('POST', '/v1/upload/provider/Fatima/document', headers=headers, files=files, timeout=60)
        print('Upload document ->', code, data)
        if code != 200:
            raise SystemExit('Document upload failed: {}'.format(data))

    # Rebuild index using repository script (safer for debugging)
    print('Running build script: scripts/run_build_debug.py')
    try:
        subprocess.check_call([sys.executable, str(ROOT/'scripts'/'run_build_debug.py'), '--provider', 'Fatima'])
    except subprocess.CalledProcessError as e:
        print('Build script failed:', e)
        raise

    # Verify faiss index and sqlite DB
    from sqlitedict import SqliteDict
    import faiss

    base = ROOT/'rag-data'/'providers'/'Fatima'
    idx_path = base/'index'/'faiss.bin'
    db_path = base/'db'/'metadata.sqlite'
    if not idx_path.exists():
        raise SystemExit(f'faiss index missing: {idx_path}')
    if not db_path.exists():
        raise SystemExit(f'sqlite DB missing: {db_path}')

    index = faiss.read_index(str(idx_path))
    print('FAISS ntotal:', index.ntotal)
    if index.ntotal == 0:
        raise SystemExit('FAISS index empty (ntotal == 0)')

    with SqliteDict(str(db_path)) as pdb:
        vkeys = pdb.get('vector_keys', [])
        print('DB vector_keys len:', len(vkeys))
        if len(vkeys) != index.ntotal:
            raise SystemExit(f'index/db mismatch: faiss {index.ntotal} vs db {len(vkeys)}')

    # Run a sample query
    payload = {'client_id': 100, 'question': 'What services does Fatima provide?', 'top_k': 3}
    code, data = call_endpoint('POST', '/v1/query', headers=headers|{'Content-Type':'application/json'} if headers else {'Content-Type':'application/json'}, json_body=payload, timeout=30)
    print('POST /v1/query ->', code, data)
    if code != 200:
        raise SystemExit('Query failed: {}'.format(data))

    print('\nAll checks passed successfully')

if __name__ == '__main__':
    try:
        run_tests()
    except Exception as e:
        print('ERROR:', e)
        sys.exit(3)
    sys.exit(0)
