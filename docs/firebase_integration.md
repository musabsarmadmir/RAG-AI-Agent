Firebase Integration Guide

Overview

This guide shows how to replace the local JSON provider index used by `app/provider_index.py` with a Firestore-backed store, and explains how to enable, set up and migrate mappings. The repository includes a Firestore scaffold `app/provider_index_firestore.py` which mirrors the same functions used by the rest of the app.

Goals

- Enable Firestore-backed provider index mapping (optional toggle)
- Securely provide credentials to the app
- Migrate existing mappings from the local JSON file into Firestore
- Optionally, use Firestore security rules and IAM best practices for production

Prerequisites

- Google Cloud project with Firestore enabled (Native mode)
- Service account with `roles/datastore.user` (or `roles/datastore.owner` during migration) and Cloud Firestore API access
- The machine running this app must have `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service account JSON file, or have ADC (Application Default Credentials) configured.

Install dependencies

Add to your Python environment:

```powershell
# from repo root (PowerShell)
.\.venv\Scripts\Activate.ps1; pip install google-cloud-firestore
```

Environment variables

- `FIRESTORE_ENABLED=1` — enable Firestore-backed provider index store
- `GOOGLE_APPLICATION_CREDENTIALS` — Path to service account JSON file

Example (PowerShell):

```powershell
$env:FIRESTORE_ENABLED = '1'; $env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\path\to\service-account.json'
```

How it works in this repo

- `app/provider_index.py` will delegate calls to `app/provider_index_firestore.py` when `FIRESTORE_ENABLED` is truthy.
- The Firestore collection used is `provider_index_mappings` (document id = index, document field `provider` = provider name).

Migration steps (local -> Firestore)

1. Export existing mappings (if any):

```powershell
python - <<'PY'
from app import provider_index
import json
print(json.dumps(provider_index.load_index_map(), indent=2))
PY
```

2. Enable Firestore and set credentials as above
3. Run a migration script (example):

```powershell
python - <<'PY'
from app import provider_index
from app import provider_index_firestore as pif
m = provider_index.load_index_map()
# save to firestore
pif.save_index_map(m)
print('migrated', m)
PY
```

4. Verify mappings

```powershell
curl -H "x-api-key: <API_KEY>" http://localhost:8000/v1/provider-indices
```

Security & Production notes

- Use a service account with the least privilege necessary (limit to Firestore access only).
- Don't commit service account JSON to git. Use secret management (e.g., Azure KeyVault, GCP Secret Manager, environment variables on the host).
- Consider enabling Firestore rules and/or use a dedicated service account per environment (prod/staging/dev).

Troubleshooting

- Permission errors: verify service account has Firestore access on the GCP project and correct role.
- Missing credentials: ensure `GOOGLE_APPLICATION_CREDENTIALS` is set or your host has ADC configured.
- Local fallback: If `FIRESTORE_ENABLED` is not set or Firestore calls fail, the app will fall back to the local JSON file.

Extending for Cloud Storage

If you later migrate provider assets (docs, chunks, faiss) to Cloud Storage, you can similarly add a small adapter that translates `ensure_provider_dirs` and other file operations into GCS bucket paths. Keep in mind FAISS indexes are binary and you'll need to download them locally for fast search or use an alternative vector DB.

Contact

If you want, I can also scaffold a migration script that copies `rag-data/providers/*` assets to a GCS bucket and stores provider metadata in Firestore documents. Ask and I will scaffold it.
