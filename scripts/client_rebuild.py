import requests
import os

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_KEY = os.environ.get("API_KEY", "dev-key-123")
PROVIDER = os.environ.get("PROVIDER", "Fatima")

headers = {"x-api-key": API_KEY}
r = requests.post(f"{API_BASE}/v1/admin/rebuild-index/{PROVIDER}", headers=headers)
print(r.status_code, r.text)
