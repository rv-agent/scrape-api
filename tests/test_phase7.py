"""
Phase 7 tests: Scheduler + Redis cache + Celery tasks.
"""

import pytest
from src.utils.cache import _cache_key


class TestCacheKey:
    """Test cache key generation."""

    def test_basic_key(self):
        """Should generate consistent key for same inputs."""
        key1 = _cache_key("https://example.com")
        key2 = _cache_key("https://example.com")
        assert key1 == key2

    def test_different_urls_different_keys(self):
        """Different URLs should produce different keys."""
        key1 = _cache_key("https://example.com")
        key2 = _cache_key("https://other.com")
        assert key1 != key2

    def test_selector_changes_key(self):
        """Adding selector should change key."""
        key1 = _cache_key("https://example.com")
        key2 = _cache_key("https://example.com", selector=".content")
        assert key1 != key2

    def test_render_js_changes_key(self):
        """render_js flag should change key."""
        key1 = _cache_key("https://example.com", render_js=False)
        key2 = _cache_key("https://example.com", render_js=True)
        assert key1 != key2

    def test_key_format(self):
        """Key should have correct prefix."""
        key = _cache_key("https://example.com")
        assert key.startswith("scrape:result:")


class TestSchedulerModule:
    """Test scheduler module imports."""

    def test_import_scheduler(self):
        """Scheduler module should import cleanly."""
        from src.api.routes.scheduler import router, get_scheduler
        assert router.prefix == "/api/v1/scheduler"

    def test_get_scheduler_returns_instance(self):
        """get_scheduler should return an AsyncIOScheduler."""
        from src.api.routes.scheduler import get_scheduler
        scheduler = get_scheduler()
        assert scheduler is not None

    def test_schemas_import(self):
        """Schemas should import correctly."""
        from src.api.routes.scheduler import ScheduledJobCreate, ScheduledJobResponse
        # Test creating a schema
        job = ScheduledJobCreate(
            name="Test Job",
            url="https://example.com",
            interval_seconds=3600,
        )
        assert job.name == "Test Job"
        assert job.interval_seconds == 3600


class TestCeleryModule:
    """Test Celery module imports."""

    def test_import_celery(self):
        """Celery module should import cleanly."""
        from src.tasks.celery_app import celery_app, execute_scrape_task
        assert celery_app.main == "scrapeapi"

    def test_celery_config(self):
        """Celery should have correct config."""
        from src.tasks.celery_app import celery_app
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.task_time_limit == 120


class TestCacheModule:
    """Test cache module imports."""

    def test_import_cache(self):
        """Cache module should import cleanly."""
        from src.utils.cache import get_cached, set_cached, invalidate_cached, get_cache_stats
        assert callable(get_cached)
        assert callable(set_cached)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
