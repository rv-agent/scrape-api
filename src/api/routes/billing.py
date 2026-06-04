"""
Stripe billing integration for ScrapeAPI.

Handles subscription management, checkout sessions, and webhook events.
Supports Free, Starter, Pro, and Enterprise tiers.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.auth.api_key import validate_api_key
from src.config.settings import settings
from src.models.api_key import APIKey
from src.models.database import Base, get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing")

# Stripe configuration
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = getattr(settings, 'STRIPE_WEBHOOK_SECRET', 'whsec_placeholder')


# ── Tier Pricing ────────────────────────────────────────────────────

TIER_PRICES = {
    "free": {
        "name": "Free",
        "price": 0,
        "requests_per_day": 100,
        "requests_per_month": 3000,
        "features": ["Basic scraping", "JSON export", "Email support"],
    },
    "starter": {
        "name": "Starter",
        "price": 19,
        "stripe_price_id": "price_starter_monthly",
        "requests_per_day": 500,
        "requests_per_month": 10000,
        "features": ["Everything in Free", "CSV export", "Webhooks", "Priority support"],
    },
    "pro": {
        "name": "Pro",
        "price": 49,
        "stripe_price_id": "price_pro_monthly",
        "requests_per_day": 2000,
        "requests_per_month": 50000,
        "features": ["Everything in Starter", "Proxy rotation", "Scheduler", "API priority"],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 199,
        "stripe_price_id": "price_enterprise_monthly",
        "requests_per_day": -1,  # Unlimited
        "requests_per_month": -1,
        "features": ["Everything in Pro", "Dedicated proxy", "SLA", "Custom integration"],
    },
}


# ── Database Model ──────────────────────────────────────────────────

class Subscription(Base):
    """Subscription/billing model."""
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True)
    api_key_id = Column(String, nullable=False, unique=True, index=True)
    tier = Column(String, default="free")
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    stripe_price_id = Column(String, nullable=True)
    status = Column(String, default="active")  # active, canceled, past_due
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Schemas ─────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    tier: str = Field(..., description="Subscription tier: starter, pro, enterprise")
    success_url: str = Field(default="https://scrapeapi.com/billing/success", description="Redirect URL after success")
    cancel_url: str = Field(default="https://scrapeapi.com/billing/cancel", description="Redirect URL after cancel")


class CheckoutResponse(BaseModel):
    """Checkout session response."""
    checkout_url: str
    session_id: str


class SubscriptionResponse(BaseModel):
    """Subscription information."""
    tier: str
    status: str
    price: int
    requests_per_day: int
    requests_per_month: int
    features: list
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False


class TierInfo(BaseModel):
    """Tier pricing information."""
    name: str
    price: int
    requests_per_day: int
    requests_per_month: int
    features: list


# ── API Endpoints ───────────────────────────────────────────────────

@router.get(
    "/tiers",
    response_model=list[TierInfo],
    summary="List pricing tiers",
    description="Get available subscription tiers and pricing.",
)
async def list_tiers():
    """List all available pricing tiers."""
    return [
        TierInfo(
            name=tier["name"],
            price=tier["price"],
            requests_per_day=tier["requests_per_day"],
            requests_per_month=tier["requests_per_month"],
            features=tier["features"],
        )
        for tier in TIER_PRICES.values()
    ]


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Get current subscription",
    description="Get the current subscription for the API key.",
)
async def get_subscription(
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Get current subscription details."""
    result = await session.execute(
        select(Subscription).where(Subscription.api_key_id == api_key.id)
    )
    sub = result.scalar_one_or_none()

    if not sub:
        # Return free tier defaults
        tier_info = TIER_PRICES["free"]
        return SubscriptionResponse(
            tier="free",
            status="active",
            price=0,
            requests_per_day=tier_info["requests_per_day"],
            requests_per_month=tier_info["requests_per_month"],
            features=tier_info["features"],
        )

    tier_info = TIER_PRICES.get(sub.tier, TIER_PRICES["free"])
    return SubscriptionResponse(
        tier=sub.tier,
        status=sub.status,
        price=tier_info["price"],
        requests_per_day=tier_info["requests_per_day"],
        requests_per_month=tier_info["requests_per_month"],
        features=tier_info["features"],
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    summary="Create checkout session",
    description="Create a Stripe checkout session for subscription upgrade.",
)
async def create_checkout(
    request: CheckoutRequest,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a Stripe checkout session."""
    if request.tier not in TIER_PRICES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid tier: {request.tier}",
        )

    tier_info = TIER_PRICES[request.tier]
    if request.tier == "free":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot checkout for free tier",
        )

    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price": tier_info["stripe_price_id"],
                "quantity": 1,
            }],
            success_url=request.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.cancel_url,
            metadata={
                "api_key_id": api_key.id,
                "tier": request.tier,
            },
        )

        return CheckoutResponse(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id,
        )

    except stripe.error.StripeError as e:
        logger.error("Stripe error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment provider error: {str(e)}",
        )


@router.post(
    "/cancel",
    response_model=SubscriptionResponse,
    summary="Cancel subscription",
    description="Cancel subscription at end of current billing period.",
)
async def cancel_subscription(
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Cancel subscription at period end."""
    result = await session.execute(
        select(Subscription).where(Subscription.api_key_id == api_key.id)
    )
    sub = result.scalar_one_or_none()

    if not sub or sub.tier == "free":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No active subscription to cancel",
        )

    if sub.stripe_subscription_id:
        try:
            stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=True,
            )
        except stripe.error.StripeError as e:
            logger.error("Stripe cancel error: %s", str(e))

    sub.cancel_at_period_end = True
    await session.flush()

    tier_info = TIER_PRICES.get(sub.tier, TIER_PRICES["free"])
    return SubscriptionResponse(
        tier=sub.tier,
        status=sub.status,
        price=tier_info["price"],
        requests_per_day=tier_info["requests_per_day"],
        requests_per_month=tier_info["requests_per_month"],
        features=tier_info["features"],
        current_period_end=sub.current_period_end,
        cancel_at_period_end=True,
    )


@router.post(
    "/webhook",
    summary="Stripe webhook handler",
    description="Handle Stripe webhook events for subscription updates.",
)
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle events
    if event["type"] == "checkout.session.completed":
        await _handle_checkout_completed(event["data"]["object"], session)
    elif event["type"] == "customer.subscription.updated":
        await _handle_subscription_updated(event["data"]["object"], session)
    elif event["type"] == "customer.subscription.deleted":
        await _handle_subscription_deleted(event["data"]["object"], session)
    elif event["type"] == "invoice.payment_failed":
        await _handle_payment_failed(event["data"]["object"], session)

    return {"status": "ok"}


async def _handle_checkout_completed(session_data: dict, session: AsyncSession):
    """Handle completed checkout."""
    metadata = session_data.get("metadata", {})
    api_key_id = metadata.get("api_key_id")
    tier = metadata.get("tier", "free")

    if not api_key_id:
        return

    sub = Subscription(
        id=str(uuid.uuid4()),
        api_key_id=api_key_id,
        tier=tier,
        stripe_customer_id=session_data.get("customer"),
        stripe_subscription_id=session_data.get("subscription"),
        stripe_price_id=TIER_PRICES.get(tier, {}).get("stripe_price_id"),
        status="active",
    )
    session.add(sub)
    await session.flush()
    logger.info("Subscription created: key=%s tier=%s", api_key_id, tier)


async def _handle_subscription_updated(sub_data: dict, session: AsyncSession):
    """Handle subscription update."""
    result = await session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_data["id"])
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = sub_data.get("status", sub.status)
        await session.flush()


async def _handle_subscription_deleted(sub_data: dict, session: AsyncSession):
    """Handle subscription cancellation."""
    result = await session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_data["id"])
    )
    sub = result.scalar_one_or_none()
    if sub:
        sub.status = "canceled"
        sub.tier = "free"
        await session.flush()


async def _handle_payment_failed(invoice_data: dict, session: AsyncSession):
    """Handle failed payment."""
    sub_id = invoice_data.get("subscription")
    if sub_id:
        result = await session.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = "past_due"
            await session.flush()
