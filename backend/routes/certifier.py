"""CERTIFIER public API — certification consulting endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.certifier_service import get_certifier_service

router = APIRouter(prefix="/api/certifier", tags=["certifier"])


# ─── Schemas ─────────────────────────────────────────────────────────────────


class CertifierQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)


class CertifierQueryResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: str
    model: str


class RegulationInfo(BaseModel):
    file: str
    title: str
    source: str


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/query", response_model=CertifierQueryResponse)
async def certifier_query(req: CertifierQueryRequest):
    """Ask a question about EAEU vehicle certification."""
    service = get_certifier_service()
    result = await service.query(req.question)
    return result


@router.get("/regulations", response_model=list[RegulationInfo])
async def certifier_regulations():
    """List technical regulations loaded in the knowledge base."""
    service = get_certifier_service()
    return service.get_regulations()
