from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.agents.certifier.agent import process_query

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@router.get("/agents")
async def list_agents():
    return {
        "agents": [
            {
                "id": "certifier",
                "name": "CERTIFIER",
                "description": "Консалтинг по сертификации ТС ЕАЭС",
                "status": "demo",
                "tier": "free",
            },
            {
                "id": "lawyer",
                "name": "LAWYER",
                "description": "Юридические вопросы для бизнеса РФ",
                "status": "coming_soon",
                "tier": "starter",
            },
            {
                "id": "accountant",
                "name": "ACCOUNTANT",
                "description": "Бухгалтерия, налоги ИП/ООО",
                "status": "coming_soon",
                "tier": "starter",
            },
        ],
        "tiers": {
            "free": {"price": 0, "questions_per_day": settings.FREE_QUESTIONS_PER_DAY},
            "starter": {"price": settings.STARTER_PRICE_RUB, "questions_per_day": -1},
            "pro": {"price": settings.PRO_PRICE_RUB, "questions_per_day": -1},
            "enterprise": {"price": settings.ENTERPRISE_PRICE_RUB, "questions_per_day": -1},
        },
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if request.agent == "certifier":
        result = process_query(request.message)
        return ChatResponse(**result)

    return ChatResponse(
        agent=request.agent,
        response=f"Агент '{request.agent}' пока в разработке. Доступен только CERTIFIER.",
        confidence=1.0,
        source="system",
    )
