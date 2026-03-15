"""FastAPI dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException

from .config import get_backend_api_key
from .database import get_db
from .admin_auth import verify_admin_token


def verify_api_key(x_api_key: str = Header("")) -> str:
    """Verify X-API-Key header for webhook/bot authentication."""
    expected = get_backend_api_key()
    if not expected:
        return "no-key-configured"
    if x_api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


__all__ = ["get_db", "verify_admin_token", "verify_api_key"]
