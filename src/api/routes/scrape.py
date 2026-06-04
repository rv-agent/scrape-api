"""
Scrape API endpoints.

POST /api/v1/scrape  — Single URL scrape
POST /api/v1/batch   — Batch URL scrape
GET  /api/v1/status/{job_id} — Check job status
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.api_key import validate_api_key, APIKeyValidator
from src.api.validation import (
    validate_url,
    validate_selector,
    validate_batch_size,
    sanitize_headers,
    sanitize_string,
)
from src.config.settings import settings
from src.models.api_key import APIKey
from src.models.database import get_db_session
from src.models.scrape_job import ScrapeJob
from src.models.schemas import (
    ScrapeRequest,
    ScrapeResponse,
    ScrapeData,
    ScrapeMetadata,
    ScrapeJobStatus,
    BatchScrapeRequest,
    BatchScrapeResponse,
    JobStatusResponse,
)
from src.scraper.http_scraper import HttpScraper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


def _build_scrape_data(result, request: ScrapeRequest, validated_selector: Optional[str] = None) -> ScrapeData:
    """Build ScrapeData from scraper result."""
    data = result.data or {}

    # Apply CSS selector if provided
    selector_results = None
    if validated_selector and result.content:
        try:
            soup = BeautifulSoup(result.content, "lxml")
            elements = soup.select(validated_selector)
            selector_results = [el.get_text(strip=True) for el in elements]
        except Exception as e:
            logger.warning("Selector extraction failed: %s", e)

    return ScrapeData(
        title=data.get("title"),
        text=data.get("text") if request.extract_text else None,
        links=data.get("links"),
        images=data.get("images"),
        selector_results=selector_results,
        raw_html=result.content if not request.extract_text else None,
    )


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    status_code=status.HTTP_200_OK,
    summary="Scrape a single URL",
    description="Submit a URL for scraping. Returns extracted data as JSON.",
)
async def scrape_url(
    request: ScrapeRequest,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Scrape a single URL and return extracted data.

    - **url**: Target URL (required)
    - **render_js**: Use headless browser for JS-heavy pages
    - **extract_text**: Extract clean text (default: true)
    - **selector**: CSS selector for targeted extraction
    - **format**: Response format (json/csv)
    - **timeout**: Request timeout in seconds
    """
    job_id = str(uuid.uuid4())
    logger.info("Scrape request: job=%s url=%s key=%s...", job_id, request.url, api_key.key_prefix)

    # Validate URL (SSRF protection)
    validated_url = validate_url(str(request.url))

    # Validate selector
    validated_selector = validate_selector(request.selector)

    # Sanitize headers
    clean_headers = sanitize_headers(request.headers)

    # Create job record
    job = ScrapeJob(
        id=job_id,
        api_key_id=api_key.id,
        url=validated_url,
        render_js=request.render_js,
        extract_text=request.extract_text,
        selector=validated_selector,
        response_format=request.format.value,
    )
    session.add(job)
    await session.flush()

    # Increment usage
    await APIKeyValidator.increment_usage(api_key, session)

    # Execute scrape
    job.mark_running()
    await session.flush()

    timeout = request.timeout or settings.SCRAPER_TIMEOUT

    try:
        async with HttpScraper(timeout=timeout) as scraper:
            result = await scraper.scrape(
                url=validated_url,
                headers=clean_headers,
                extract_text=request.extract_text,
            )

        if result.status.value == "completed":
            scrape_data = _build_scrape_data(result, request, validated_selector)
            metadata = ScrapeMetadata(
                elapsed_seconds=result.metadata.get("elapsed_seconds", 0),
                content_type=result.metadata.get("content_type"),
                content_length=result.metadata.get("content_length", 0),
                status_code=result.status_code,
            )

            job.mark_completed(
                data=scrape_data.model_dump(exclude_none=True),
                elapsed=metadata.elapsed_seconds,
                content_type=metadata.content_type,
                content_length=metadata.content_length,
                status_code=metadata.status_code,
            )
            await session.flush()

            return ScrapeResponse(
                job_id=job_id,
                status=ScrapeJobStatus.COMPLETED,
                url=str(request.url),
                data=scrape_data,
                metadata=metadata,
                created_at=job.created_at,
            )
        else:
            job.mark_failed(result.error or "Scrape failed")
            await session.flush()

            return ScrapeResponse(
                job_id=job_id,
                status=ScrapeJobStatus.FAILED,
                url=str(request.url),
                error=result.error,
                created_at=job.created_at,
            )

    except Exception as e:
        logger.exception("Scrape error for job %s", job_id)
        job.mark_failed(str(e))
        await session.flush()

        return ScrapeResponse(
            job_id=job_id,
            status=ScrapeJobStatus.FAILED,
            url=str(request.url),
            error=str(e),
            created_at=job.created_at,
        )


@router.post(
    "/batch",
    response_model=BatchScrapeResponse,
    status_code=status.HTTP_200_OK,
    summary="Scrape multiple URLs",
    description="Submit multiple URLs for scraping. Returns results for each URL.",
)
async def batch_scrape(
    request: BatchScrapeRequest,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Scrape multiple URLs in a single request.

    - **urls**: List of URLs (max 50)
    - Other params same as /scrape
    """
    batch_id = str(uuid.uuid4())
    logger.info("Batch scrape: batch=%s urls=%d key=%s...", batch_id, len(request.urls), api_key.key_prefix)

    # Validate batch size against tier
    validate_batch_size(request.urls, api_key.tier)

    results = []
    completed = 0
    failed = 0

    for url in request.urls:
        single_request = ScrapeRequest(
            url=url,
            render_js=request.render_js,
            extract_text=request.extract_text,
            selector=request.selector,
            headers=request.headers,
            format=request.format,
            timeout=request.timeout,
        )

        # Reuse single scrape logic
        response = await scrape_url(single_request, api_key, session)

        # Tag with batch_id
        job_result = await session.execute(
            select(ScrapeJob).where(ScrapeJob.id == response.job_id)
        )
        job = job_result.scalar_one_or_none()
        if job:
            job.batch_id = batch_id
            await session.flush()

        results.append(response)
        if response.status == ScrapeJobStatus.COMPLETED:
            completed += 1
        else:
            failed += 1

    return BatchScrapeResponse(
        batch_id=batch_id,
        total=len(request.urls),
        completed=completed,
        failed=failed,
        results=results,
    )


@router.get(
    "/status/{job_id}",
    response_model=JobStatusResponse,
    summary="Check job status",
    description="Get the status of a scrape job.",
)
async def get_job_status(
    job_id: str,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Check the status of a scrape job.

    - **job_id**: Job ID from scrape response
    """
    result = await session.execute(
        select(ScrapeJob).where(
            ScrapeJob.id == job_id,
            ScrapeJob.api_key_id == api_key.id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return JobStatusResponse(
        job_id=job.id,
        status=ScrapeJobStatus(job.status),
        url=job.url,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error=job.error,
    )
