# RAG AI Agent API

Public FastAPI service exposing provider ingestion and query endpoints for the RAG pipeline.

## Quick Start (Local)

1. Create and activate venv, install deps:

```powershell
python -m venv .venv; & ".\.venv\Scripts\Activate.ps1"; pip install -r requirements.txt
```

2. Optional: set env in `local.env` (auto-loaded):

```
OPENAI_API_KEY=your_key
API_KEY=dev-key-123
CORS_ORIGINS=http://localhost:3000
```

3. Run the server:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

4. Interactive local chat (no HTTP):

```powershell
# Create a test provider and client mapping (optional)
python .\scripts\create_test_provider.py Fatima 100
# Build index if not present
python .\scripts\run_build_debug.py
# Start chat against provider Fatima
python .\scripts\chat_terminal.py --provider Fatima
# Or, use client mapping
python .\scripts\chat_terminal.py --client-id 100
```

## Endpoints

- `GET /v1/health` — service status + provider index presence
- `GET /v1/providers` — list provider names
- `POST /v1/upload/provider/{provider}/metadata` — upload Excel `metadata.xlsx` (requires `x-api-key`)
- `POST /v1/upload/provider/{provider}/document` — upload a document (pdf/docx/txt) (requires `x-api-key`)
- `POST /v1/admin/rebuild-index/{provider}` — parse, chunk, embed, and build FAISS for a provider (requires `x-api-key`)
- `POST /v1/query` — body `{ client_id:number, question:string, top_k?:number }` (requires `x-api-key`)

Add `x-api-key: <API_KEY>` header if API keys are configured.

## Docker

Build and run:

```powershell
docker build -t rag-agent .
docker run -p 8000:8000 -e API_KEY=dev-key-123 rag-agent
```

## Azure Deployment (Overview)

- Push image to Azure Container Registry (ACR)
- Deploy to Azure App Service (Web App for Containers) or Azure Container Apps
- Configure env vars: `OPENAI_API_KEY`, `API_KEYS`, `CORS_ORIGINS`
- Mount or bake `rag-data` as needed, or store indexes in Blob Storage
- Enable Application Insights and set health probe to `/health`

## Notes

- Index and DB files under `rag-data/**/index` and `rag-data/**/db` are ignored by git and docker build to avoid large binaries.
- For multiple API keys, use `API_KEYS=key1,key2,key3`.
