"""
Celery async task queue for ScrapeAPI.

Offloads long-running scrape jobs to background workers.
Supports task chaining, retries, and result storage.
"""

import logging
from typing import Optional

from celery import Celery

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "scrapeapi",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=60,
    task_time_limit=120,
    task_default_retry_delay=30,
    task_max_retries=3,
    result_expires=3600,  # Results expire after 1 hour
)


@celery_app.task(bind=True, name="scrape.execute")
def execute_scrape_task(
    self,
    job_id: str,
    url: str,
    selector: Optional[str] = None,
    render_js: bool = False,
    timeout: int = 30,
) -> dict:
    """
    Execute a scrape job as a Celery task.

    Args:
        job_id: Job ID for tracking
        url: Target URL
        selector: CSS selector
        render_js: Use headless browser
        timeout: Request timeout

    Returns:
        Scrape result dict
    """
    import asyncio
    from src.scraper.http_scraper import HttpScraper

    logger.info("Celery task started: job=%s url=%s", job_id, url)

    try:
        # Run async scraper in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                _async_scrape(url, selector, render_js, timeout)
            )
        finally:
            loop.close()

        logger.info("Celery task completed: job=%s", job_id)
        return {
            "job_id": job_id,
            "status": "completed",
            "data": result,
        }

    except Exception as exc:
        logger.exception("Celery task failed: job=%s", job_id)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


async def _async_scrape(url, selector, render_js, timeout):
    """Async scrape helper for Celery tasks."""
    from src.scraper.http_scraper import HttpScraper

    async with HttpScraper(timeout=timeout) as scraper:
        result = await scraper.scrape(url=url, extract_text=True)

    if result.status.value == "completed":
        data = result.data or {}
        if selector:
            from bs4 import BeautifulSoup
            if result.content:
                soup = BeautifulSoup(result.content, "lxml")
                elements = soup.select(selector)
                data["selector_results"] = [el.get_text(strip=True) for el in elements]
        return data
    else:
        raise Exception(result.error or "Scrape failed")


@celery_app.task(name="scrape.batch")
def execute_batch_task(
    batch_id: str,
    urls: list,
    selector: Optional[str] = None,
    render_js: bool = False,
    timeout: int = 30,
) -> dict:
    """Execute a batch scrape as a Celery task."""
    results = []
    for url in urls:
        try:
            result = execute_scrape_task(None, url, selector, render_js, timeout)
            results.append(result)
        except Exception as e:
            results.append({"url": url, "status": "failed", "error": str(e)})

    return {
        "batch_id": batch_id,
        "total": len(urls),
        "results": results,
    }
