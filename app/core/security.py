from fastapi import Header, HTTPException
from ..config import API_KEYS

async def api_key_auth(x_api_key: str | None = Header(default=None)):
    """Simple API key header check. Uses `x-api-key` header.

    Configure keys via `API_KEY` or `API_KEYS` env variables (comma-separated).
    """
    # If no keys configured, allow all (useful for local dev)
    if not API_KEYS:
        return True
    if not x_api_key or x_api_key not in API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return True
