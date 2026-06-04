"""
API Key database model.

Tier limits are sourced from application settings (configurable via env vars).
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base

logger = logging.getLogger(__name__)


class APIKey(Base):
    """API key for authentication and rate limiting."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    requests_today: Mapped[int] = mapped_column(Integer, default=0)
    requests_this_month: Mapped[int] = mapped_column(Integer, default=0)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @staticmethod
    def _get_tier_limits() -> dict:
        """Get tier limits from settings (lazy import to avoid circular)."""
        from src.config.settings import settings
        return {
            "free": settings.RATE_LIMIT_FREE_TIER,
            "starter": settings.RATE_LIMIT_STARTER,
            "pro": settings.RATE_LIMIT_PRO,
            "enterprise": -1,  # unlimited
        }

    @property
    def requests_limit(self) -> int:
        """Get request limit based on tier from settings."""
        limits = self._get_tier_limits()
        return limits.get(self.tier, 100)

    @property
    def is_within_limit(self) -> bool:
        """Check if within rate limit."""
        if self.requests_limit == -1:  # unlimited
            return True
        if self.tier == "free":
            return self.requests_today < self.requests_limit
        return self.requests_this_month < self.requests_limit

    def increment_usage(self) -> None:
        """Increment usage counters."""
        self.requests_today += 1
        self.requests_this_month += 1
        self.total_requests += 1
        self.last_used_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<APIKey {self.key_prefix}... tier={self.tier}>"
