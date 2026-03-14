import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    telegram_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[str] = mapped_column(String(20), default="free")  # free, starter, pro, enterprise
    questions_today: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
