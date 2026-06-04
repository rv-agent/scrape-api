"""
API Key management endpoints.

POST /api/v1/keys        — Create new API key
GET  /api/v1/keys        — List API keys
GET  /api/v1/keys/usage  — Get usage stats
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.api_key import validate_api_key, APIKeyValidator
from src.models.api_key import APIKey
from src.models.database import get_db_session
from src.models.schemas import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreatedResponse,
    UsageStats,
    TierLevel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/keys")


@router.post(
    "",
    response_model=APIKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="Generate a new API key. Full key is only shown once.",
)
async def create_api_key(
    request: APIKeyCreate,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new API key.

    - **name**: Friendly name for the key
    - **tier**: Subscription tier (free/starter/pro/enterprise)

    Returns the full API key — **save it, it won't be shown again**.
    """
    db_key, raw_key = await APIKeyValidator.create_key(
        name=request.name,
        tier=request.tier.value,
        session=session,
    )

    return APIKeyCreatedResponse(
        id=db_key.id,
        name=db_key.name,
        key_prefix=db_key.key_prefix,
        tier=TierLevel(db_key.tier),
        is_active=db_key.is_active,
        requests_today=db_key.requests_today,
        requests_limit=db_key.requests_limit,
        created_at=db_key.created_at,
        last_used_at=db_key.last_used_at,
        key=raw_key,
    )


@router.get(
    "",
    response_model=list[APIKeyResponse],
    summary="List API keys",
    description="List all API keys for the authenticated account.",
)
async def list_api_keys(
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """List all API keys (does not expose full keys)."""
    result = await session.execute(
        select(APIKey).where(APIKey.is_active == True)
    )
    keys = result.scalars().all()

    return [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            tier=TierLevel(k.tier),
            is_active=k.is_active,
            requests_today=k.requests_today,
            requests_limit=k.requests_limit,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
        )
        for k in keys
    ]


@router.get(
    "/usage",
    response_model=UsageStats,
    summary="Get usage statistics",
    description="Get usage statistics for the current API key.",
)
async def get_usage_stats(
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Get usage stats for the authenticated API key."""
    return UsageStats(
        key_id=api_key.id,
        key_name=api_key.name,
        tier=TierLevel(api_key.tier),
        requests_today=api_key.requests_today,
        requests_this_month=api_key.requests_this_month,
        requests_limit=api_key.requests_limit,
        total_requests=api_key.total_requests,
        avg_response_time_ms=0.0,  # TODO: compute from jobs
    )
