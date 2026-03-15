"""Opportunities API — поиск конкурсов, генерация идей, анализ рынка."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.opportunity_scanner import get_scanner
from services.market_analyzer import get_analyzer

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


class ScanRequest(BaseModel):
    query: str | None = Field(None, description="Custom search query")


class AnalyzeRequest(BaseModel):
    title: str
    description: str = ""
    url: str = ""
    type: str = "grant"


class ProposalRequest(BaseModel):
    competition_name: str
    description: str


class MarketRequest(BaseModel):
    topic: str


class CompetitorRequest(BaseModel):
    niche: str


# ─── Endpoints ───────────────────────────────────────────


@router.get("/sources")
async def list_sources():
    """List all known sources of opportunities."""
    scanner = get_scanner()
    return {"summary": await scanner.scan_sources_summary()}


@router.post("/scan")
async def scan_opportunities(req: ScanRequest):
    """Scan the web for grants, hackathons, competitions."""
    scanner = get_scanner()
    results = await scanner.scan_web(req.query)
    return {
        "count": len(results),
        "results": [
            {
                "title": r.title,
                "url": r.url,
                "type": r.type,
                "description": r.description,
                "relevance": round(r.relevance_score, 2),
            }
            for r in results
        ],
    }


@router.post("/analyze")
async def analyze_opportunity(req: AnalyzeRequest):
    """Deep AI analysis of a specific opportunity."""
    from services.opportunity_scanner import Opportunity

    opp = Opportunity(
        title=req.title,
        source="manual",
        url=req.url,
        type=req.type,
        description=req.description,
    )
    scanner = get_scanner()
    analysis = await scanner.analyze_opportunity(opp)
    return {"analysis": analysis}


@router.post("/ideas")
async def generate_ideas(context: str = ""):
    """Generate money-making ideas for AI Zavod."""
    scanner = get_scanner()
    ideas = await scanner.generate_ideas(context)
    return {"ideas": ideas}


@router.post("/proposal")
async def generate_proposal(req: ProposalRequest):
    """Generate application/proposal for a competition."""
    analyzer = get_analyzer()
    proposal = await analyzer.generate_proposal(req.competition_name, req.description)
    return {"proposal": proposal}


@router.post("/market")
async def market_scan(req: MarketRequest):
    """Quick market assessment for a topic."""
    analyzer = get_analyzer()
    result = await analyzer.quick_market_scan(req.topic)
    return {"analysis": result}


@router.post("/competitors")
async def competitor_analysis(req: CompetitorRequest):
    """Detailed competitor analysis for a niche."""
    analyzer = get_analyzer()
    result = await analyzer.analyze_competitors(req.niche)
    return {"analysis": result}
