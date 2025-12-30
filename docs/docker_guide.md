# RAG AI Agent – Docker & Deployment Guide

This guide explains how to run the project in Docker, with Firestore and OpenAI enabled, and how to test the complete retrieval flow end‑to‑end.

## 1. Prerequisites

- Docker and Docker Compose installed
- Google Cloud project with Firestore enabled (Native mode)
- Service account JSON with Firestore access (e.g. `roles/datastore.user`)
- OpenAI API key
- This repository cloned on your machine

Repository layout (relevant parts):

- `app/` – FastAPI app and core logic
- `scripts/` – helper scripts (index build, Firestore seeding, tests)
- `rag-data/` – local provider data (docs, chunks, FAISS index, SQLite DB)
- `Dockerfile` – container image definition
- `docker-compose.yml` – local docker‑compose setup

## 2. One‑time setup

### 2.1. Create secrets folder and copy Firestore credentials

On your host machine (same folder as this repo):

```powershell
cd "C:\Users\Musab Sarmad\Desktop\RAG AI Agent"
mkdir secrets
# Copy or move your service account file into ./secrets with this name:
#   rag-agent-firestore.json
```

After this, you should have:

- `secrets/rag-agent-firestore.json` (not committed to git)

The `docker-compose.yml` mounts this file into the container at `/secrets/rag-agent-firestore.json` and sets `GOOGLE_APPLICATION_CREDENTIALS` accordingly.

### 2.2. Ensure rag-data/ exists

If you have already run the project locally, `rag-data/` will exist. If not, just create it:

```powershell
mkdir rag-data
```

The volume mapping in `docker-compose.yml` will persist provider indices and DBs between container runs.

## 3. Build and run with Docker Compose

From the repository root (replace the path with wherever you cloned this repo):

```powershell
cd "C:\path\to\RAG AI Agent"

# Build the Docker image
docker compose build

# Run the API container in the background
$env:OPENAI_API_KEY = "YOUR_REAL_OPENAI_KEY_HERE"
docker compose up -d
```

What this does:

- Builds the image using `Dockerfile`.
- Starts the `rag-api` service defined in `docker-compose.yml`.
- Exposes FastAPI at `http://localhost:8000`.
- Mounts:
  - `./rag-data` → `/app/rag-data` (persistent provider data)
  - `./secrets/rag-agent-firestore.json` → `/secrets/rag-agent-firestore.json` (Firestore credentials)
- Sets environment variables for:
  - `API_KEY` (for `x-api-key` auth)
  - `CORS_ORIGINS` (for browser clients)
  - `FIRESTORE_ENABLED=1`
  - `GOOGLE_APPLICATION_CREDENTIALS=/secrets/rag-agent-firestore.json`
  - `OPENAI_API_KEY` (you override this before `docker compose up`)

To see logs:

```powershell
docker compose logs -f
```

To stop the container:

```powershell
docker compose down
```

## 4. Seeding providers and Firestore from the host

You will typically run seeding scripts **on the host**, with your virtualenv, while the API runs in Docker. This allows you to reuse the same `rag-data/` directory (it is mounted into the container).

### 4.1. Activate your venv

```powershell
cd "C:\path\to\RAG AI Agent"
& ".venv/Scripts/Activate.ps1"
```

### 4.2. Seed multiple providers into Firestore + local indices

For example, to create five providers (Ali, Talal, Hamza, Bilal, Ayan):

```powershell
python scripts/seed_providers_firestore.py `
    --providers Ali Talal Hamza Bilal Ayan `
    --start-client-id 300 `
    --start-index 80
```

This script will, for each provider:

1. Create local test data under `rag-data/providers/<provider>` (metadata + sample doc).
2. Build a FAISS + SQLite index locally.
3. Migrate chunks to Firestore.
4. Register a Firestore index mapping: `index -> provider`.
5. Store `client_id -> provider_index` in the app DB (`rag-data/app_db.sqlite`).
6. Call `POST /v1/query` against the running API for that client and print the response.

Example mapping after the above command:

- Ali:   `client_id = 300`, `provider_index = 80`
- Talal: `client_id = 301`, `provider_index = 81`
- Hamza: `client_id = 302`, `provider_index = 82`
- Bilal: `client_id = 303`, `provider_index = 83`
- Ayan:  `client_id = 304`, `provider_index = 84`

## 5. Manually querying the API (from host)

With the container running, you can test queries via PowerShell using `Invoke-RestMethod`:

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

Change `client_id` and the wording of the question to test other providers.

## 6. Verifying Firestore contents

You can inspect provider mappings and Firestore providers using the helper script:

```powershell
& ".venv/Scripts/Activate.ps1"
python scripts/inspect_firestore_providers.py
```

This prints:

- The index → provider mapping stored in Firestore.
- All provider IDs in the Firestore `providers` collection.

## 7. Production notes

- **Secrets**: Never commit `local.env` or service account JSON to git. Use environment variables or your platform's secret manager in production.
- **Scaling**: For higher load, run multiple `rag-api` containers behind a reverse proxy (NGINX, Traefik, etc.).
- **Performance**: Consider caching FAISS indices in memory, or moving to a managed vector DB if provider count or traffic grows.
- **Security**: Replace the simple static `API_KEY` with a more robust auth system (JWT/OAuth2) before exposing publicly.

With this setup, you can:

1. Build and run the API in Docker.
2. Seed multiple providers and mappings via host scripts.
3. Issue queries that traverse Firestore → FAISS → SQLite → OpenAI entirely inside the container.

## 8. Example production deployment (single VM)

Below is a simple pattern you can adapt for a real server (Linux VM or on‑prem machine). Adjust paths and commands for your environment.

### 8.1. Prepare the server

On the target machine:

1. Install Docker and Docker Compose.
2. Create a folder for the app, e.g. `/opt/rag-ai-agent`.
3. Copy the repository contents to `/opt/rag-ai-agent` (e.g. via `git clone` or `scp`).
4. Create the secrets and data folders:

```bash
mkdir -p /opt/rag-ai-agent/secrets
mkdir -p /opt/rag-ai-agent/rag-data
``` 

5. Copy your Firestore service account JSON to:

```bash
cp /path/to/rag-agent-firestore.json /opt/rag-ai-agent/secrets/rag-agent-firestore.json
``` 

### 8.2. Configure environment

On the server, set environment variables before starting the stack (for example in your shell profile or a small wrapper script):

```bash
export OPENAI_API_KEY="YOUR_REAL_OPENAI_KEY_HERE"
export API_KEY="a-strong-production-api-key"
```

You can also override values in `docker-compose.yml` or use a `.env` file next to it if you prefer Compose‑style configuration.

### 8.3. Build and start the stack

From `/opt/rag-ai-agent`:

```bash
cd /opt/rag-ai-agent
docker compose build
docker compose up -d
```

At this point the API is available inside the server at `http://localhost:8000`. You would typically:

- Put an NGINX or other reverse proxy in front, terminating TLS (HTTPS).
- Restrict access to admin endpoints (upload, rebuild, seeding) via network rules and/or stronger auth.

### 8.4. Seeding and operations in production

For production, you have two main options:

- **Option A – Seed from the server host** (recommended):
  - Install Python + venv on the server.
  - Use the same scripts (`seed_providers_firestore.py`, `inspect_firestore_providers.py`) against the shared `/opt/rag-ai-agent/rag-data` directory while the container is running.

- **Option B – Seed from a separate ops machine**:
  - Run the scripts locally and then sync `rag-data/` to the server (e.g. via `rsync` or storage replication), ensuring the Firestore environment is the same.

### 8.5. Updating the application

To deploy a new version:

```bash
cd /opt/rag-ai-agent
git pull              # or copy a new version
docker compose build  # rebuild image with new code
docker compose up -d  # restart with zero‑downtime (Compose recreates the container)
```

Because `rag-data/` and `secrets/` are mounted as volumes, indices and credentials will persist across container rebuilds.

## 9. GitHub integration – building and deploying Docker images

You can use GitHub to build and store your Docker images, then pull and run them on your server.

### 9.1. Publish images to GitHub Container Registry (GHCR)

1. In GitHub, create a **Personal Access Token (classic)** or **fine‑grained token** with `write:packages` and `read:packages`.
2. On your machine (or CI runner), authenticate Docker to GHCR:

```bash
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
```

3. From the repo root, build and tag the image for GHCR:

```bash
cd /path/to/RAG-AI-Agent
IMAGE="ghcr.io/YOUR_GITHUB_USERNAME/rag-ai-agent:latest"

docker build -t "$IMAGE" .
docker push "$IMAGE"
```

You now have a versioned image hosted in GitHub Container Registry.

### 9.2. Point your server to the GHCR image

On the target server, instead of building locally, you can pull from GHCR.

1. Log in to GHCR on the server (same `docker login ghcr.io ...` command).
2. In `docker-compose.yml` on the server, override the service to use the remote image, for example:

```yaml
services:
  rag-api:
    image: ghcr.io/YOUR_GITHUB_USERNAME/rag-ai-agent:latest
    # ... keep volumes and environment as before ...
```

3. Deploy/update:

```bash
cd /opt/rag-ai-agent
docker compose pull
docker compose up -d
```

This way, updating the app becomes: build + push from your dev/CI environment, then `docker compose pull && docker compose up -d` on the server.

### 9.3. Automating builds with GitHub Actions (optional)

You can automate the image build and push on every push to `main` using a GitHub Actions workflow like this (place in `.github/workflows/docker.yml`):

```yaml
name: Build and publish Docker image

on:
  push:
    branches: ["main"]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/rag-ai-agent:latest
```

After this is set up:

- Every push to `main` builds and pushes `ghcr.io/<owner>/rag-ai-agent:latest`.
- Your server deploy step stays the same (`docker compose pull && docker compose up -d`), but now updates are triggered by GitHub pushes rather than manual local builds.
