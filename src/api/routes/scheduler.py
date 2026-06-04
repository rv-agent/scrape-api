"""
Scheduler for auto-scrape (cron-like recurring jobs).

Uses APScheduler for job scheduling with database persistence.
Allows users to schedule recurring scrape jobs.
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.auth.api_key import validate_api_key
from src.models.api_key import APIKey
from src.models.database import Base, get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scheduler")

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


# ── Database Model ──────────────────────────────────────────────────

class ScheduledJob(Base):
    """Scheduled scrape job model."""
    __tablename__ = "scheduled_jobs"

    id = Column(String, primary_key=True)
    api_key_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    selector = Column(String, nullable=True)
    render_js = Column(Boolean, default=False)
    cron_expression = Column(String, nullable=True)  # e.g., "0 */6 * * *"
    interval_seconds = Column(Integer, nullable=True)  # e.g., 3600
    webhook_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Schemas ─────────────────────────────────────────────────────────

class ScheduledJobCreate(BaseModel):
    """Request to create a scheduled job."""
    name: str = Field(..., min_length=1, max_length=100, description="Job name")
    url: str = Field(..., description="Target URL")
    selector: Optional[str] = Field(default=None, description="CSS selector")
    render_js: bool = Field(default=False, description="Use headless browser")
    cron_expression: Optional[str] = Field(default=None, description="Cron expression (e.g., '0 */6 * * *')")
    interval_seconds: Optional[int] = Field(default=None, ge=60, description="Interval in seconds (min 60)")
    webhook_url: Optional[str] = Field(default=None, description="Webhook callback URL")


class ScheduledJobResponse(BaseModel):
    """Scheduled job information."""
    id: str
    name: str
    url: str
    selector: Optional[str] = None
    render_js: bool = False
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    run_count: int = 0
    created_at: datetime


# ── Scheduler Management ────────────────────────────────────────────

def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def start_scheduler():
    """Start the scheduler."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


async def stop_scheduler():
    """Stop the scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


async def execute_scheduled_scrape(job_id: str, url: str, selector: str, render_js: bool):
    """Execute a scheduled scrape job."""
    from src.scraper.http_scraper import HttpScraper

    logger.info("Executing scheduled job %s → %s", job_id, url)

    try:
        async with HttpScraper(timeout=30) as scraper:
            result = await scraper.scrape(url=url, extract_text=True)

        logger.info("Scheduled job %s completed: status=%s", job_id, result.status.value)
    except Exception as e:
        logger.exception("Scheduled job %s failed: %s", job_id, str(e))


# ── API Endpoints ───────────────────────────────────────────────────

@router.post(
    "",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scheduled job",
    description="Schedule a recurring scrape job with cron or interval.",
)
async def create_scheduled_job(
    request: ScheduledJobCreate,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Create a new scheduled scrape job."""
    # Validate: must have either cron or interval
    if not request.cron_expression and not request.interval_seconds:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Must provide either cron_expression or interval_seconds",
        )

    job_id = str(uuid.uuid4())

    job = ScheduledJob(
        id=job_id,
        api_key_id=api_key.id,
        name=request.name,
        url=request.url,
        selector=request.selector,
        render_js=request.render_js,
        cron_expression=request.cron_expression,
        interval_seconds=request.interval_seconds,
        webhook_url=request.webhook_url,
    )
    session.add(job)
    await session.flush()

    # Add to APScheduler
    scheduler = get_scheduler()
    if request.cron_expression:
        trigger = CronTrigger.from_crontab(request.cron_expression)
    else:
        trigger = IntervalTrigger(seconds=request.interval_seconds)

    scheduler.add_job(
        execute_scheduled_scrape,
        trigger=trigger,
        id=job_id,
        args=[job_id, request.url, request.selector, request.render_js],
        replace_existing=True,
    )

    logger.info("Created scheduled job %s: %s", job_id, request.name)

    return ScheduledJobResponse(
        id=job.id,
        name=job.name,
        url=job.url,
        selector=job.selector,
        render_js=job.render_js,
        cron_expression=job.cron_expression,
        interval_seconds=job.interval_seconds,
        is_active=job.is_active,
        created_at=job.created_at,
    )


@router.get(
    "",
    response_model=list[ScheduledJobResponse],
    summary="List scheduled jobs",
    description="List all scheduled scrape jobs for the API key.",
)
async def list_scheduled_jobs(
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """List all scheduled jobs."""
    result = await session.execute(
        select(ScheduledJob).where(ScheduledJob.api_key_id == api_key.id)
    )
    jobs = result.scalars().all()

    return [
        ScheduledJobResponse(
            id=j.id,
            name=j.name,
            url=j.url,
            selector=j.selector,
            render_js=j.render_js,
            cron_expression=j.cron_expression,
            interval_seconds=j.interval_seconds,
            is_active=j.is_active,
            last_run_at=j.last_run_at,
            run_count=j.run_count,
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a scheduled job",
    description="Remove a scheduled scrape job.",
)
async def delete_scheduled_job(
    job_id: str,
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Delete a scheduled job."""
    result = await session.execute(
        select(ScheduledJob).where(
            ScheduledJob.id == job_id,
            ScheduledJob.api_key_id == api_key.id,
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheduled job {job_id} not found",
        )

    # Remove from scheduler
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass  # Job may not be in scheduler

    await session.delete(job)
    await session.flush()
