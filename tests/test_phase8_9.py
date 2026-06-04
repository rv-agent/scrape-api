"""
Phase 8+9 tests: Billing + Security hardening.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.security import (
    SecurityHeadersMiddleware,
    RequestSizeMiddleware,
    RequestLoggingMiddleware,
)


class TestSecurityHeaders:
    """Test security headers middleware."""

    def _make_app(self):
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        return app

    def test_x_content_type_options(self):
        """Should have X-Content-Type-Options: nosniff."""
        client = TestClient(self._make_app())
        resp = client.get("/test")
        assert resp.headers.get("x-content-type-options") == "nosniff"

    def test_x_frame_options(self):
        """Should have X-Frame-Options: DENY."""
        client = TestClient(self._make_app())
        resp = client.get("/test")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_referrer_policy(self):
        """Should have Referrer-Policy."""
        client = TestClient(self._make_app())
        resp = client.get("/test")
        assert "referrer-policy" in resp.headers

    def test_permissions_policy(self):
        """Should have Permissions-Policy."""
        client = TestClient(self._make_app())
        resp = client.get("/test")
        assert "permissions-policy" in resp.headers


class TestRequestSize:
    """Test request size limiting."""

    def _make_app(self, max_size=100):
        app = FastAPI()
        app.add_middleware(RequestSizeMiddleware, max_size=max_size)

        @app.post("/test")
        async def test_endpoint():
            return {"ok": True}

        return app

    def test_small_request_passes(self):
        """Small request should pass."""
        client = TestClient(self._make_app(max_size=1000))
        resp = client.post("/test", json={"data": "small"})
        assert resp.status_code == 200

    def test_oversized_request_rejected(self):
        """Request exceeding max size should be rejected."""
        client = TestClient(self._make_app(max_size=10))
        resp = client.post(
            "/test",
            content="x" * 100,
            headers={"content-length": "100"},
        )
        assert resp.status_code == 413


class TestBillingModule:
    """Test billing module imports."""

    def test_import_billing(self):
        """Billing module should import cleanly."""
        from src.api.routes.billing import router, TIER_PRICES, SubscriptionResponse, TierInfo
        assert router.prefix == "/api/v1/billing"

    def test_tier_prices_complete(self):
        """All tiers should be defined."""
        from src.api.routes.billing import TIER_PRICES
        assert "free" in TIER_PRICES
        assert "starter" in TIER_PRICES
        assert "pro" in TIER_PRICES
        assert "enterprise" in TIER_PRICES

    def test_tier_pricing(self):
        """Tier prices should be correct."""
        from src.api.routes.billing import TIER_PRICES
        assert TIER_PRICES["free"]["price"] == 0
        assert TIER_PRICES["starter"]["price"] == 19
        assert TIER_PRICES["pro"]["price"] == 49
        assert TIER_PRICES["enterprise"]["price"] == 199

    def test_tier_limits(self):
        """Tier limits should increase with price."""
        from src.api.routes.billing import TIER_PRICES
        assert TIER_PRICES["free"]["requests_per_day"] < TIER_PRICES["starter"]["requests_per_day"]
        assert TIER_PRICES["starter"]["requests_per_day"] < TIER_PRICES["pro"]["requests_per_day"]

    def test_tierinfo_schema(self):
        """TierInfo schema should work."""
        from src.api.routes.billing import TierInfo
        info = TierInfo(
            name="Free",
            price=0,
            requests_per_day=100,
            requests_per_month=3000,
            features=["Basic"],
        )
        assert info.name == "Free"


class TestFullAppRoutes:
    """Test that the full app creates with all routes."""

    def test_app_creates(self):
        """Full app should create successfully with all routes."""
        from src.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes]

        # Core routes
        assert "/health" in routes
        assert "/api/v1/scrape" in routes
        assert "/api/v1/batch" in routes
        assert "/api/v1/keys" in routes

        # Phase 5+
        assert "/api/v1/webhooks" in routes
        assert "/api/v1/export/{job_id}" in routes
        assert "/api/v1/scheduler" in routes
        assert "/api/v1/billing/tiers" in routes

    def test_route_count(self):
        """Should have 20+ routes."""
        from src.main import create_app
        app = create_app()
        routes = [r.path for r in app.routes]
        assert len(routes) >= 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
