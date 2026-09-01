"""
app/database/session.py
────────────────────────
SQLAlchemy async engine, session factory, and base declarative model.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.app_env == "development",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


engine: AsyncEngine = create_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def create_sync_db_engine():
    return create_sync_engine(
        settings.sync_database_url,
        echo=settings.app_env == "development",
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


sync_engine = create_sync_db_engine()

SyncSessionLocal: sessionmaker[Session] = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_sync_session() -> Session:
    """Synchronous session for Celery tasks or background scripts."""
    return SyncSessionLocal()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for injecting a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all tables (use only for tests; prefer Alembic for production)."""
    async with engine.begin() as conn:
        from app.database import models  # noqa: F401 — ensure models are imported
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All database tables created")


async def drop_all_tables() -> None:
    """Drop all tables — DANGER, only for test teardown."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("All database tables dropped")

