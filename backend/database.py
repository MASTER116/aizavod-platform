from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "aizavod.db"


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if url:
        return url
    return f"sqlite:///{DB_PATH}"


def _is_sqlite() -> bool:
    return get_database_url().startswith("sqlite")


def _engine_kwargs() -> dict:
    if _is_sqlite():
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_recycle": 280,
        "pool_pre_ping": True,
    }


engine = create_engine(get_database_url(), **_engine_kwargs())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine, checkfirst=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
