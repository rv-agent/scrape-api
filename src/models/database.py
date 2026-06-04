"""
Database connection and session management.

Supports both PostgreSQL (production) and SQLite (development).
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_engine():
    """Create async engine based on environment."""
    db_url = settings.DATABASE_URL

    # SQLite for development
    if db_url.startswith("sqlite"):
        return create_async_engine(
            db_url,
            echo=settings.DB_ECHO,
            connect_args={"check_same_thread": False},
        )

    # PostgreSQL for production
    return create_async_engine(
        db_url,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
    )


# Create engine
engine = get_engine()

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session for dependency injection.

    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    # Import all models to ensure they're registered
    from src.models.api_key import APIKey  # noqa: F401
    from src.models.scrape_job import ScrapeJob  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


async def close_db():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")
