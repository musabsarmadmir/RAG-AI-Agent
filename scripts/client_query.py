import requests
import os

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_KEY = os.environ.get("API_KEY", "dev-key-123")

payload = {
    "client_id": int(os.environ.get("CLIENT_ID", "1")),
    "question": os.environ.get("QUESTION", "What services are offered?"),
    "top_k": int(os.environ.get("TOP_K", "5"))
}

headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}
r = requests.post(f"{API_BASE}/v1/query", json=payload, headers=headers)
print(r.status_code, r.text)
