"""
Webhook callback system for ScrapeAPI.

Allows users to register webhook URLs that get called when scrape jobs complete.
Includes retry logic for failed deliveries.
"""

import hashlib
import hmac
import logging
import time
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select, Column, String, Boolean, Integer, DateTime, Text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.api_key import validate_api_key
from src.models.api_key import APIKey
from src.models.database import Base, get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks")


# ── Database Model ──────────────────────────────────────────────────

class Webhook(Base):
    """Webhook subscription model."""
    __tablename__ = "webhooks"

    id = Column(String, primary_key=True)
    api_key_id = Column(String, nullable=False, index=True)
    url = Column(String, nullable=False)
    secret = Column(String, nullable=False)  # For HMAC signature
    events = Column(String, default="scrape.completed")  # Comma-separated events
    is_active = Column(Boolean, default=True)
    retry_count = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_triggered_at = Column(DateTime, nullable=True)
    last_status_code = Column(Integer, nullable=True)
    failure_count = Column(Integer, default=0)


# ── Schemas ─────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    """Request to create a webhook."""
    url: str = Field(..., description="Webhook callback URL", examples=["https://example.com/webhook"])
    events: str = Field(default="scrape.completed", description="Events to subscribe to (comma-separated)")


class WebhookResponse(BaseModel):
    """Webhook information."""
    id: str
    url: str
    events: str
    is_active: bool
    created_at: datetime
    last_triggered_at: Optional[datetime] = None
    last_status_code: Optional[int] = None
    failure_count: int = 0


class WebhookEvent(BaseModel):
    """Webhook payload sent to callback URL."""
    event: str
    timestamp: str
    data: dict
    signature: str


# ── Webhook Delivery ────────────────────────────────────────────────

async def deliver_webhook(
    webhook: Webhook,
    event: str,
    data: dict,
    max_retries: int = 3,
) -> bool:
    """
    Deliver a webhook event to the registered URL.

    Args:
        webhook: Webhook subscription
        event: Event type (e.g., "scrape.completed")
        data: Event data payload
        max_retries: Max delivery attempts

    Returns:
        True if delivered successfully
    """
    timestamp = datetime.utcnow().isoformat()
    payload = {
        "event": event,
        "timestamp": timestamp,
        "data": data,
    }

    # Generate HMAC signature
    import json
    body = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        webhook.secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()
    payload["signature"] = signature

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Event": event,
        "X-Webhook-Signature": f"sha256={signature}",
        "User-Agent": "ScrapeAPI-Webhook/1.0",
    }

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(webhook.url, json=payload, headers=headers)

                if response.status_code < 400:
                    logger.info("Webhook delivered: %s → %d", webhook.url, response.status_code)
                    webhook.last_triggered_at = datetime.utcnow()
                    webhook.last_status_code = response.status_code
                    webhook.failure_count = 0
                    return True
                else:
                    logger.warning(
                        "Webhook delivery failed: %s → %d (attempt %d/%d)",
                        webhook.url, response.status_code, attempt + 1, max_retries,
                    )

        except Exception as e:
            logger.warning(
                "Webhook delivery error: %s — %s (attempt %d/%d)",
                webhook.url, str(e), attempt + 1, max_retries,
            )

        # Exponential backoff
        if attempt < max_retries - 1:
            backoff = (2 ** attempt) * 1.0
            time.sleep(backoff)

    # All retries failed
    webhook.failure_count += 1
    webhook.last_status_code = 0
    logger.error("Webhook delivery exhausted: %s (failures: %d)", webhook.url, webhook.failure_count)
    return False


async def trigger_webhooks(
    session: AsyncSession,
    api_key_id: str,
    event: str,
    data: dict,
) -> int:
    """
    Trigger all active webhooks for an API key.

    Args:
        session: Database session
        api_key_id: API key ID
        event: Event type
        data: Event data

    Returns:
        Number of successfully delivered webhooks
    """
    result = await session.execute(
        select(Webhook).where(
            Webhook.api_key_id == api_key_id,
            Webhook.is_active == True,
        )
    )
    webhooks = result.scalars().all()

    delivered = 0
    for webhook in webhooks:
        # Skip webhooks with too many consecutive failures
        if webhook.failure_count >= 10:
            webhook.is_active = False
            logger.warning("Deactivated webhook %s after 10 consecutive failures", webhook.id)
            continue

        success = await deliver_webhook(webhook, event, data, webhook.retry_count)
        if success:
            delivered += 1

    await session.flush()
    return delivered


# ── API Endpoints ───────────────────────────────────────────────────

@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a webhook",
    description="Subscribe to webhook events for scrape job completion.",
)
async def create_webhook(
    request: WebhookCreate,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Register a new webhook endpoint."""
    import uuid
    import secrets

    webhook_id = str(uuid.uuid4())
    webhook_secret = secrets.token_urlsafe(32)

    webhook = Webhook(
        id=webhook_id,
        api_key_id=api_key.id,
        url=str(request.url),
        secret=webhook_secret,
        events=request.events,
    )
    session.add(webhook)
    await session.flush()

    logger.info("Created webhook %s for key %s → %s", webhook_id, api_key.key_prefix, request.url)

    return WebhookResponse(
        id=webhook.id,
        url=webhook.url,
        events=webhook.events,
        is_active=webhook.is_active,
        created_at=webhook.created_at,
    )


@router.get(
    "",
    response_model=list[WebhookResponse],
    summary="List webhooks",
    description="List all registered webhooks for the API key.",
)
async def list_webhooks(
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """List all webhooks for the authenticated API key."""
    result = await session.execute(
        select(Webhook).where(Webhook.api_key_id == api_key.id)
    )
    webhooks = result.scalars().all()

    return [
        WebhookResponse(
            id=w.id,
            url=w.url,
            events=w.events,
            is_active=w.is_active,
            created_at=w.created_at,
            last_triggered_at=w.last_triggered_at,
            last_status_code=w.last_status_code,
            failure_count=w.failure_count,
        )
        for w in webhooks
    ]


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook",
    description="Remove a registered webhook.",
)
async def delete_webhook(
    webhook_id: str,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a webhook by ID."""
    result = await session.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.api_key_id == api_key.id,
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found",
        )

    await session.delete(webhook)
    await session.flush()
