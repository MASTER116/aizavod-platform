"""Admin authentication routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..admin_auth import create_access_token
from ..config import get_admin_panel_config
from ..schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/auth/login", response_model=TokenResponse)
def admin_login(body: LoginRequest):
    cfg = get_admin_panel_config()
    if not cfg.password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin password not configured",
        )
    if body.username != cfg.username or body.password != cfg.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(body.username)
    return TokenResponse(access_token=token)
