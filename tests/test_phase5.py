"""
Phase 5 tests: Input Validation + Error Handling + CORS.

Tests:
- URL validation (valid, invalid, SSRF protection)
- Selector validation (valid, invalid, dangerous)
- Batch size limits per tier
- Parameter sanitization
- Error handler responses (structured JSON)
- CORS headers
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.validation import (
    validate_url,
    validate_selector,
    validate_batch_size,
    sanitize_string,
    sanitize_headers,
    ValidationError,
    TIER_BATCH_LIMITS,
)
from src.api.error_handler import register_error_handlers, ErrorResponse


# ══════════════════════════════════════════════════════════════════════
# URL Validation Tests
# ══════════════════════════════════════════════════════════════════════

class TestURLValidation:
    """Test URL validation with SSRF protection."""

    def test_valid_http_url(self):
        """HTTP URLs should pass."""
        result = validate_url("http://example.com")
        assert result == "http://example.com"

    def test_valid_https_url(self):
        """HTTPS URLs should pass."""
        result = validate_url("https://example.com/path?q=1")
        assert result == "https://example.com/path?q=1"

    def test_url_strips_whitespace(self):
        """Leading/trailing whitespace should be stripped."""
        result = validate_url("  https://example.com  ")
        assert result == "https://example.com"

    def test_empty_url_raises(self):
        """Empty URL should raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validate_url("")
        assert exc.value.code == "EMPTY_URL"

    def test_no_scheme_raises(self):
        """URL without scheme should raise."""
        with pytest.raises(ValidationError) as exc:
            validate_url("example.com")
        assert exc.value.code == "INVALID_SCHEME"

    def test_ftp_scheme_raises(self):
        """FTP scheme should be rejected."""
        with pytest.raises(ValidationError) as exc:
            validate_url("ftp://example.com")
        assert exc.value.code == "INVALID_SCHEME"

    def test_javascript_scheme_raises(self):
        """JavaScript scheme should be rejected."""
        with pytest.raises(ValidationError) as exc:
            validate_url("javascript:alert(1)")
        assert exc.value.code == "INVALID_SCHEME"

    def test_missing_hostname_raises(self):
        """URL without hostname should raise."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://")
        assert exc.value.code == "MISSING_HOST"

    def test_localhost_blocked(self):
        """127.0.0.1 should be blocked (SSRF)."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://127.0.0.1:8080/admin")
        assert exc.value.code == "PRIVATE_IP"

    def test_private_ip_10_blocked(self):
        """10.x.x.x should be blocked (SSRF)."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://10.0.0.1/internal")
        assert exc.value.code == "PRIVATE_IP"

    def test_private_ip_192_168_blocked(self):
        """192.168.x.x should be blocked (SSRF)."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://192.168.1.1/admin")
        assert exc.value.code == "PRIVATE_IP"

    def test_private_ip_172_16_blocked(self):
        """172.16.x.x should be blocked (SSRF)."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://172.16.0.1/internal")
        assert exc.value.code == "PRIVATE_IP"

    def test_link_local_blocked(self):
        """169.254.x.x should be blocked (SSRF)."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://169.254.169.254/metadata")
        assert exc.value.code in ("PRIVATE_IP", "BLOCKED_DOMAIN")

    def test_metadata_service_blocked(self):
        """metadata.google.internal should be blocked."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://metadata.google.internal/computeMetadata/v1/")
        assert exc.value.code == "BLOCKED_DOMAIN"

    def test_allow_private_flag(self):
        """allow_private=True should permit private IPs."""
        result = validate_url("http://10.0.0.1/internal", allow_private=True)
        assert result == "http://10.0.0.1/internal"

    def test_path_traversal_blocked(self):
        """URLs with ../ should be blocked."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://example.com/../../../etc/passwd")
        assert exc.value.code == "SUSPICIOUS_URL"

    def test_null_byte_blocked(self):
        """URLs with null bytes should be blocked."""
        with pytest.raises(ValidationError) as exc:
            validate_url("http://example.com/path%00.html")
        assert exc.value.code == "SUSPICIOUS_URL"


# ══════════════════════════════════════════════════════════════════════
# Selector Validation Tests
# ══════════════════════════════════════════════════════════════════════

class TestSelectorValidation:
    """Test CSS selector validation."""

    def test_valid_class_selector(self):
        """Standard CSS class selector should pass."""
        result = validate_selector(".my-class")
        assert result == ".my-class"

    def test_valid_id_selector(self):
        """ID selector should pass."""
        result = validate_selector("#main-content")
        assert result == "#main-content"

    def test_valid_complex_selector(self):
        """Complex selector should pass."""
        result = validate_selector("div.container > ul li a")
        assert result == "div.container > ul li a"

    def test_valid_attribute_selector(self):
        """Attribute selector should pass."""
        result = validate_selector('[data-role="content"]')
        assert result == '[data-role="content"]'

    def test_none_returns_none(self):
        """None input should return None."""
        result = validate_selector(None)
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        result = validate_selector("")
        assert result is None

    def test_too_long_raises(self):
        """Selector over 1000 chars should raise."""
        long_selector = "a" * 1001
        with pytest.raises(ValidationError) as exc:
            validate_selector(long_selector)
        assert exc.value.code == "SELECTOR_TOO_LONG"

    def test_script_tag_blocked(self):
        """Selector with <script should be blocked."""
        with pytest.raises(ValidationError) as exc:
            validate_selector('<script>alert(1)</script>')
        assert exc.value.code in ("INVALID_SELECTOR", "DANGEROUS_SELECTOR")

    def test_javascript_blocked(self):
        """Selector with javascript: should be blocked."""
        with pytest.raises(ValidationError) as exc:
            validate_selector('javascript:alert(1)')
        assert exc.value.code in ("INVALID_SELECTOR", "DANGEROUS_SELECTOR")


# ══════════════════════════════════════════════════════════════════════
# Batch Size Tests
# ══════════════════════════════════════════════════════════════════════

class TestBatchSizeValidation:
    """Test batch size limits per tier."""

    def test_free_tier_within_limit(self):
        """Free tier: 5 URLs should pass."""
        urls = [f"https://example.com/{i}" for i in range(5)]
        result = validate_batch_size(urls, "free")
        assert result == 5

    def test_free_tier_exceeds_limit(self):
        """Free tier: 6 URLs should raise."""
        urls = [f"https://example.com/{i}" for i in range(6)]
        with pytest.raises(ValidationError) as exc:
            validate_batch_size(urls, "free")
        assert exc.value.code == "BATCH_LIMIT_EXCEEDED"
        assert exc.value.details["limit"] == 5

    def test_starter_tier_limit(self):
        """Starter tier: 20 URLs should pass, 21 should fail."""
        urls_20 = [f"https://example.com/{i}" for i in range(20)]
        assert validate_batch_size(urls_20, "starter") == 20

        urls_21 = [f"https://example.com/{i}" for i in range(21)]
        with pytest.raises(ValidationError):
            validate_batch_size(urls_21, "starter")

    def test_pro_tier_limit(self):
        """Pro tier: 50 URLs should pass."""
        urls = [f"https://example.com/{i}" for i in range(50)]
        assert validate_batch_size(urls, "pro") == 50

    def test_enterprise_tier_limit(self):
        """Enterprise tier: 100 URLs should pass."""
        urls = [f"https://example.com/{i}" for i in range(100)]
        assert validate_batch_size(urls, "enterprise") == 100

    def test_unknown_tier_defaults_to_free(self):
        """Unknown tier should default to free limit."""
        urls = [f"https://example.com/{i}" for i in range(6)]
        with pytest.raises(ValidationError):
            validate_batch_size(urls, "unknown_tier")


# ══════════════════════════════════════════════════════════════════════
# Sanitization Tests
# ══════════════════════════════════════════════════════════════════════

class TestSanitization:
    """Test input sanitization."""

    def test_control_chars_removed(self):
        """Control characters should be stripped."""
        result = sanitize_string("hello\x00world\x08!")
        assert result == "helloworld!"

    def test_max_length_truncation(self):
        """Strings exceeding max_length should be truncated."""
        result = sanitize_string("a" * 20000, max_length=10000)
        assert len(result) == 10000

    def test_normal_string_unchanged(self):
        """Normal strings should pass through unchanged."""
        result = sanitize_string("Hello, World!")
        assert result == "Hello, World!"

    def test_sanitize_headers_removes_blocked(self):
        """Blocked headers (host, content-length) should be removed."""
        headers = {
            "Authorization": "Bearer token123",
            "host": "evil.com",
            "content-length": "0",
            "X-Custom": "value",
        }
        result = sanitize_headers(headers)
        assert "authorization" in result
        assert "x-custom" in result
        assert "host" not in result
        assert "content-length" not in result

    def test_sanitize_headers_none_input(self):
        """None input should return None."""
        assert sanitize_headers(None) is None

    def test_sanitize_headers_empty_dict(self):
        """Empty dict should return None."""
        assert sanitize_headers({}) is None


# ══════════════════════════════════════════════════════════════════════
# Error Handler Tests
# ══════════════════════════════════════════════════════════════════════

class TestErrorHandlers:
    """Test structured error responses."""

    def _make_app(self):
        """Create a test FastAPI app with error handlers."""
        app = FastAPI()
        register_error_handlers(app)

        @app.get("/test-validation-error")
        async def trigger_validation():
            raise ValidationError("TEST_CODE", "Test message", {"key": "value"})

        @app.get("/test-http-error")
        async def trigger_http():
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")

        @app.get("/test-unhandled")
        async def trigger_unhandled():
            raise RuntimeError("Something broke")

        return app

    def test_validation_error_response(self):
        """ValidationError should return structured 422."""
        client = TestClient(self._make_app(), raise_server_exceptions=False)
        resp = client.get("/test-validation-error")
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "TEST_CODE"
        assert body["error"]["message"] == "Test message"

    def test_http_error_response(self):
        """HTTPException should return structured response."""
        client = TestClient(self._make_app(), raise_server_exceptions=False)
        resp = client.get("/test-http-error")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert body["error"]["message"] == "Not found"

    def test_unhandled_error_hides_trace_in_prod(self):
        """Unhandled errors should not expose stack traces."""
        import src.api.error_handler as eh
        original_debug = eh.settings.DEBUG
        eh.settings.DEBUG = False
        try:
            client = TestClient(self._make_app(), raise_server_exceptions=False)
            resp = client.get("/test-unhandled")
            assert resp.status_code == 500
            body = resp.json()
            assert body["error"]["code"] == "INTERNAL_ERROR"
            assert "traceback" not in str(body)
        finally:
            eh.settings.DEBUG = original_debug


# ══════════════════════════════════════════════════════════════════════
# CORS Tests
# ══════════════════════════════════════════════════════════════════════

class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self):
        """CORS headers should be present on preflight."""
        from src.main import create_app
        app = create_app()
        client = TestClient(app)
        resp = client.options(
            "/api/v1/scrape",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Should have CORS headers
        assert "access-control-allow-origin" in resp.headers
        assert resp.headers.get("access-control-allow-credentials") == "true"

    def test_cors_preflight_cache(self):
        """Preflight should include max-age=600."""
        from src.main import create_app
        app = create_app()
        client = TestClient(app)
        resp = client.options(
            "/api/v1/scrape",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        max_age = resp.headers.get("access-control-max-age")
        assert max_age == "600"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
