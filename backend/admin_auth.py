"""Admin panel JWT auth: token creation, verification, and FastAPI dependency."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_admin_panel_config, get_backend_api_key

security = HTTPBearer(auto_error=False)


def create_access_token(username: str) -> str:
    cfg = get_admin_panel_config()
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=cfg.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, cfg.jwt_secret, algorithm="HS256")


def verify_token(token: str) -> str:
    cfg = get_admin_panel_config()
    try:
        payload = jwt.decode(token, cfg.jwt_secret, algorithms=["HS256"])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return sub
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def verify_admin_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    # Allow internal access via X-API-Key (for telegram bot)
    api_key = request.headers.get("X-API-Key", "")
    backend_key = get_backend_api_key()
    if api_key and backend_key and api_key == backend_key:
        return "bot"

    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return verify_token(credentials.credentials)
