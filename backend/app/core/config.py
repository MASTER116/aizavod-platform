from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI ZAVOD"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "Мультиагентная SaaS-платформа для автоматизации бизнес-процессов"

    DATABASE_URL: str = "postgresql+asyncpg://aizavod:aizavod_secret@db:5432/aizavod"
    REDIS_URL: str = "redis://redis:6379/0"
    ENVIRONMENT: str = "development"

    # Тарифы
    FREE_QUESTIONS_PER_DAY: int = 3
    STARTER_PRICE_RUB: int = 4990
    PRO_PRICE_RUB: int = 14990
    ENTERPRISE_PRICE_RUB: int = 49990

    class Config:
        env_file = ".env"


settings = Settings()
