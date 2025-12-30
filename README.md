# RAG AI Agent

A multi‑provider Retrieval‑Augmented Generation (RAG) service built on FastAPI, FAISS, SQLite, OpenAI, and Google Firestore.

Each **provider** (e.g. Fatima, Ali, Talal) has its own documents and metadata, a local FAISS + SQLite index, and an optional Firestore mirror for metadata and index mappings. Clients are mapped to providers (or numeric provider indices), and queries run against the assigned provider only.

---

## High‑Level Architecture

- **API layer** – FastAPI app in [app/main.py](app/main.py):
  - File upload endpoints for provider metadata and documents.
  - Admin endpoints to rebuild indices and manage provider‑index mappings.
  - Query endpoint `/v1/query` that performs RAG for a given `client_id`.
- **Indexing pipeline** – [app/pipeline.py](app/pipeline.py):
  - Reads provider metadata (`metadata.xlsx`) and docs (`.pdf`, `.docx`, `.txt`).
  - Normalizes and chunks text.
  - Embeds chunks (OpenAI or SBERT) and builds a FAISS index.
  - Stores chunks, vectors, and metadata in a provider‑local SQLite DB (SqliteDict).
- **Client ↔ provider mapping** – [app/app_db.py](app/app_db.py):
  - Stores `client_id -> provider` or `client_id -> provider_index` in `rag-data/app_db.sqlite`.
- **Provider index mapping (Firestore‑backed)** – [app/provider_index.py](app/provider_index.py) and [app/provider_index_firestore.py](app/provider_index_firestore.py):
  - Maps `provider_index` (e.g. `48`) ↔ provider name (e.g. `"Fatima"`).
  - When `FIRESTORE_ENABLED=1`, mappings are stored in Firestore.
- **Retrieval path at query time**:
  1. `client_id` → local app DB → (optional numeric index).
  2. Numeric index → Firestore mapping → provider name.
  3. Provider name → local FAISS index + SQLite DB under `rag-data/providers/<provider>`.
  4. FAISS top‑k vectors → chunk texts → OpenAI LLM with strict grounding.

Supporting docs:

- Firestore details: [docs/firebase_integration.md](docs/firebase_integration.md)
- Docker & deployment: [docs/docker_guide.md](docs/docker_guide.md)

---

## Repository Layout

- [app/](app) – FastAPI app, config, embeddings, pipeline, provider index logic, security, API models.
- [scripts/](scripts) – Helper scripts for local dev, testing, and Firestore seeding.
- [rag-data/](rag-data) – Local provider data (docs, chunks, indices, DBs).
- [docs/](docs) – Additional guides (Firebase, Docker).
- [requirements.txt](requirements.txt) – Python dependencies.
- [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml) – Containerization and local stack.

Key scripts:

- [scripts/test_all.py](scripts/test_all.py) – One‑shot end‑to‑end test of a single provider (Fatima) and `/v1/query`.
- [scripts/run_build_debug.py](scripts/run_build_debug.py) – Rebuild index for a provider.
- [scripts/run_local_query.py](scripts/run_local_query.py) – Local RAG test without HTTP.
- [scripts/seed_providers_firestore.py](scripts/seed_providers_firestore.py) – Seed multiple providers, build indices, migrate to Firestore, assign client/index mappings, and hit `/v1/query`.
- [scripts/inspect_firestore_providers.py](scripts/inspect_firestore_providers.py) – Inspect providers and mappings in Firestore.

---

## Prerequisites

- Python 3.11 (recommended) and `pip`.
- A Google Cloud project with Firestore (Native mode) if you want Firestore integration.
- An OpenAI API key for LLM/embedding calls.
- (Optional) Docker + Docker Compose for containerized deployment.

---

## Local Development Setup (without Docker)

### 1. Clone and create virtualenv

```powershell
cd "C:\path\to\RAG AI Agent"
python -m venv .venv
& ".venv/Scripts/Activate.ps1"
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure local.env

Create a `local.env` file in the project root (if not already present):

```env
OPENAI_API_KEY=sk-...your-openai-key...
API_KEY=dev-key-123
CORS_ORIGINS=http://localhost:3000
FIRESTORE_ENABLED=1
GOOGLE_APPLICATION_CREDENTIALS=C:/full/path/to/rag-agent-firestore.json
```

Notes:

- Do **not** commit real keys or service account JSON.
- If you do not want Firestore, set `FIRESTORE_ENABLED=0` and omit `GOOGLE_APPLICATION_CREDENTIALS`.

### 3. Start the API server

```powershell
cd "C:\path\to\RAG AI Agent"
& ".venv/Scripts/Activate.ps1"
uvicorn app.main:app --reload
```

The API is now available at `http://127.0.0.1:8000`.

---

## End‑to‑End Local Test

There are two main ways to exercise the full flow.

### Option A – One‑shot test for a single provider (Fatima)

Terminal 1 – run the API:

```powershell
cd "C:\path\to\RAG AI Agent"
& ".venv/Scripts/Activate.ps1"
uvicorn app.main:app --reload
```

Terminal 2 – run the test script:

```powershell
cd "C:\path\to\RAG AI Agent"
& ".venv/Scripts/Activate.ps1"
python scripts/test_all.py
```

This will:

- Load `local.env` into `os.environ`.
- Create/refresh a Fatima provider and assign `client_id=100`.
- Upload metadata and docs via HTTP (`/v1/upload/...`).
- Rebuild FAISS + SQLite index for Fatima.
- Validate FAISS/DB consistency.
- Call `POST /v1/query` with `client_id=100` and print the LLM answer.

### Option B – Seed multiple providers and test via `/v1/query`

With the API running (as above), in another terminal:

```powershell
cd "C:\path\to\RAG AI Agent"
& ".venv/Scripts/Activate.ps1"

python scripts/seed_providers_firestore.py `
    --providers Ali Talal Hamza Bilal Ayan `
    --start-client-id 300 `
    --start-index 80
```

For each provider, this will:

1. Create local test data in `rag-data/providers/<provider>`.
2. Build a FAISS + SQLite index locally.
3. Migrate chunks into Firestore.
4. Register a Firestore mapping `index -> provider`.
5. Store `client_id -> provider_index` in `rag-data/app_db.sqlite`.
6. Call `POST /v1/query` for that `client_id` and print the response.

Example resulting mappings:

- Ali:   `client_id=300`, `provider_index=80`
- Talal: `client_id=301`, `provider_index=81`
- Hamza: `client_id=302`, `provider_index=82`
- Bilal: `client_id=303`, `provider_index=83`
- Ayan:  `client_id=304`, `provider_index=84`

You can then manually query any of these:

```powershell
$Headers = @{
    "x-api-key"    = "dev-key-123"
    "Content-Type" = "application/json"
}

$Body = @{
    client_id = 300
    question  = "What services does Ali provide?"
    top_k     = 5
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri "http://127.0.0.1:8000/v1/query" `
    -Headers $Headers `
    -Body $Body
```

---

## Firestore Integration

Firestore integration is optional and controlled via env.

- When `FIRESTORE_ENABLED=1`:
  - [app/provider_index.py](app/provider_index.py) delegates provider‑index operations to [app/provider_index_firestore.py](app/provider_index_firestore.py).
  - Provider index mappings (`index -> provider`) are read/written to a Firestore document `metadata/providers_index`.
  - Seeding scripts can also upload provider chunks into Firestore under the `providers` collection.
- When `FIRESTORE_ENABLED=0` or unset:
  - Provider mappings fall back to a local JSON file under `rag-data/providers_index.json`.

For deeper details and troubleshooting, see [docs/firebase_integration.md](docs/firebase_integration.md).

---

## API Overview

All endpoints live under `http://<host>:8000`.

### Health & discovery

- `GET /v1/health` – Basic health check and per‑provider index presence.
- `GET /v1/providers` – List provider directory names under `rag-data/providers`.

### Upload & index management

All write/admin endpoints require `x-api-key` header and use the `API_KEY` env var.

- `POST /v1/upload/provider/{provider}/metadata`
  - Body: `multipart/form-data` with `file` (Excel `.xlsx`).
  - Saves to `rag-data/providers/{provider}/excel/metadata.xlsx`.
- `POST /v1/upload/provider/{provider}/document`
  - Body: `multipart/form-data` with `file` (PDF, DOCX, TXT).
  - Saves to `rag-data/providers/{provider}/docs/`.
- `POST /v1/admin/rebuild-index/{provider}`
  - Rebuilds FAISS + SQLite index for a provider (by name or numeric index).

### Provider index mappings

- `GET /v1/provider-indices` – Return all `index -> provider` mappings.
- `GET /v1/provider-indices/{index}` – Return provider for a given `index`.
- `POST /v1/provider-indices/{index}`
  - JSON body: `{ "provider": "Fatima", "overwrite": true }`.
  - Set mapping `index -> provider` (respects `overwrite`).
- `DELETE /v1/provider-indices/{index}` – Delete a mapping.

### Client ↔ provider mappings

- `POST /v1/client/{client_id}/assign-index`
  - JSON body: `{ "provider_index": 48 }`.
  - Store `client_id -> provider_index` (string) in app DB.
- `GET /v1/client/{client_id}/provider`
  - Returns both resolved provider name and stored index (if any).

### Query

- `POST /v1/query`
  - JSON body:
    - `client_id: int`
    - `question: str`
    - `top_k: int` (optional, default 5)
  - Resolves provider for the client, loads provider‑specific FAISS + SQLite index, performs vector search, and calls the LLM with strict grounding.
  - Response model [app/api/models.py](app/api/models.py): `QueryResponse` with `answer` and `sources`.

---

## Docker & Deployment

The repo includes first‑class Docker support.

- [Dockerfile](Dockerfile) – Multi‑stage build, installs dependencies, runs FastAPI with Uvicorn.
- [docker-compose.yml](docker-compose.yml) – Local stack with:
  - `rag-api` service exposing port 8000.
  - Volumes for `rag-data/` and `secrets/rag-agent-firestore.json`.
  - Env vars for `API_KEY`, `CORS_ORIGINS`, `FIRESTORE_ENABLED`, `GOOGLE_APPLICATION_CREDENTIALS`, `OPENAI_API_KEY`.

Quick start (Windows example):

```powershell
cd "C:\path\to\RAG AI Agent"
mkdir secrets
# Place your service account at: .\secrets\rag-agent-firestore.json

# Build and run
docker compose build
$env:OPENAI_API_KEY = "YOUR_REAL_OPENAI_KEY_HERE"
docker compose up -d
```

Then follow [docs/docker_guide.md](docs/docker_guide.md) for:

- Seeding providers from the host.
- Querying the containerized API.
- Example production deployment on a single VM.

---

## Security & Production Considerations

- **Secrets**: Never commit `local.env` or service account JSON. Use env vars or a secret manager.
- **API keys**: Replace `API_KEY=dev-key-123` with a strong, rotated key for any shared/deployed environment.
- **Auth**: Before exposing publicly, consider JWT/OAuth2 (or an API gateway) for auth instead of a single static key.
- **Performance**:
  - FAISS indices are loaded from disk per query in the current design; consider caching indices in memory or using a managed vector DB if load grows.
- **Observability**: Add structured logging and, optionally, tracing/metrics if running in production (e.g. with OpenTelemetry).

---

## Model & SDK Notes

- This project uses the OpenAI Python SDK (v2‑style) where available.
- The main chat model is `gpt-4o-mini` by default (configurable in [app/llm.py](app/llm.py)).
- Embeddings default to `openai:text-embedding-3-small` when `OPENAI_API_KEY` is set, otherwise fall back to SBERT (`all-MiniLM-L6-v2`).

If you are running this on a different OpenAI‑compatible endpoint, you may need to adjust the client initialization in [app/llm.py](app/llm.py) and [app/embeddings.py](app/embeddings.py).
