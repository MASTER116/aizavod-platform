from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    agent: str = "certifier"
    user_id: str | None = None


class ChatResponse(BaseModel):
    agent: str
    response: str
    confidence: float
    source: str
