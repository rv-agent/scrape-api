"""
API Key authentication with database validation.
"""

import hashlib
import logging
import secrets
from typing import Optional

from fastapi import Security, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.models.database import get_db_session
from src.models.api_key import APIKey

logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(
    name=settings.API_KEY_HEADER,
    auto_error=False,
)


def generate_api_key() -> str:
    """
    Generate a secure API key.

    Returns:
        str: Generated API key in format "sk-..."
    """
    return f"sk-{secrets.token_urlsafe(settings.API_KEY_LENGTH)}"


def hash_api_key(key: str) -> str:
    """
    Hash API key for secure storage.

    Args:
        key: Raw API key

    Returns:
        str: SHA-256 hash of the key
    """
    return hashlib.sha256(key.encode()).hexdigest()


async def get_api_key_from_db(
    key: str,
    session: AsyncSession,
) -> Optional[APIKey]:
    """
    Look up API key in database.

    Args:
        key: Raw API key
        session: Database session

    Returns:
        APIKey or None if not found
    """
    key_hash = hash_api_key(key)
    result = await session.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def validate_api_key(
    api_key: Optional[str] = Security(api_key_header),
    session: AsyncSession = Depends(get_db_session),
) -> APIKey:
    """
    Validate API key from request header.

    Args:
        api_key: API key from X-API-Key header
        session: Database session

    Returns:
        APIKey: Validated API key object

    Raises:
        HTTPException: If API key is missing, invalid, or rate limited
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide it in X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Development mode: accept seed key without DB lookup
    if settings.DEBUG and api_key == settings.SEED_API_KEY:
        logger.debug("Accepted seed API key in dev mode")
        # Return a mock APIKey for dev
        mock_key = APIKey()
        mock_key.id = "dev-key-001"
        mock_key.name = "Development Key"
        mock_key.key_prefix = api_key[:8]
        mock_key.tier = "pro"
        mock_key.is_active = True
        mock_key.requests_today = 0
        mock_key.requests_this_month = 0
        mock_key.total_requests = 0
        return mock_key

    # Database lookup
    db_key = await get_api_key_from_db(api_key, session)

    if not db_key:
        logger.warning("Invalid API key attempted: %s...", api_key[:8])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check rate limit
    if not db_key.is_within_limit:
        logger.warning("Rate limit exceeded for key %s...", db_key.key_prefix)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {db_key.requests_limit} requests.",
            headers={"Retry-After": "3600"},
        )

    return db_key


class APIKeyValidator:
    """API key validation and management."""

    @staticmethod
    async def validate(key: str, session: AsyncSession) -> bool:
        """
        Validate an API key.

        Args:
            key: API key to validate
            session: Database session

        Returns:
            bool: True if valid
        """
        if settings.DEBUG and key == settings.SEED_API_KEY:
            return True
        db_key = await get_api_key_from_db(key, session)
        return db_key is not None

    @staticmethod
    async def create_key(
        name: str,
        tier: str,
        session: AsyncSession,
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.

        Args:
            name: Friendly name for the key
            tier: Subscription tier
            session: Database session

        Returns:
            tuple: (APIKey object, raw key string)
        """
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)

        db_key = APIKey(
            name=name,
            key_hash=key_hash,
            key_prefix=raw_key[:8],
            tier=tier,
        )
        session.add(db_key)
        await session.flush()

        logger.info("Created API key '%s' tier=%s", name, tier)
        return db_key, raw_key

    @staticmethod
    async def increment_usage(key: APIKey, session: AsyncSession) -> None:
        """
        Increment usage counter for an API key.

        Args:
            key: APIKey object
            session: Database session
        """
        key.increment_usage()
        await session.flush()
