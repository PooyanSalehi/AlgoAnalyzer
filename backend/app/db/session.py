"""SQLAlchemy declarative base and engine/session management.

The backend is database agnostic: it talks to PostgreSQL in production
(``DATABASE_URL=postgresql+psycopg://...``) and transparently falls back to
a local SQLite file for zero-configuration development.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _build_engine():
    settings = get_settings()
    url = settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (dev convenience; use Alembic migrations in prod)."""
    # Import models so they are registered on the Base metadata.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
