"""
Data export endpoints for ScrapeAPI.

Supports JSON and CSV export of scrape results.
"""

import csv
import io
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.api_key import validate_api_key
from src.models.api_key import APIKey
from src.models.database import get_db_session
from src.models.scrape_job import ScrapeJob
from src.models.schemas import ScrapeJobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/export")


@router.get(
    "/{job_id}",
    summary="Export scrape results",
    description="Export scrape job results in JSON or CSV format.",
)
async def export_job(
    job_id: str,
    format: str = Query(default="json", description="Export format: json or csv"),
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Export scrape results in the requested format.

    - **job_id**: Job ID from scrape response
    - **format**: Output format (json or csv)
    """
    # Fetch job
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

    if job.status != ScrapeJobStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Job {job_id} is not completed (status: {job.status})",
        )

    if format.lower() == "csv":
        return _export_csv(job)
    else:
        return _export_json(job)


@router.get(
    "/batch/{batch_id}",
    summary="Export batch results",
    description="Export all results from a batch scrape job.",
)
async def export_batch(
    batch_id: str,
    format: str = Query(default="json", description="Export format: json or csv"),
    api_key: APIKey = Depends(validate_api_key),
    session: AsyncSession = Depends(get_db_session),
):
    """Export all results from a batch scrape."""
    result = await session.execute(
        select(ScrapeJob).where(
            ScrapeJob.batch_id == batch_id,
            ScrapeJob.api_key_id == api_key.id,
        ).order_by(ScrapeJob.created_at)
    )
    jobs = result.scalars().all()

    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found",
        )

    if format.lower() == "csv":
        return _export_batch_csv(batch_id, jobs)
    else:
        return _export_batch_json(batch_id, jobs)


def _export_json(job: ScrapeJob) -> StreamingResponse:
    """Export single job as JSON."""
    data = {
        "job_id": job.id,
        "url": job.url,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "elapsed_seconds": job.elapsed_seconds,
        "content_type": job.content_type,
        "status_code": job.status_code,
        "data": json.loads(job.data) if job.data else None,
    }

    content = json.dumps(data, indent=2, ensure_ascii=False)
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{job.id}.json"',
        },
    )


def _export_csv(job: ScrapeJob) -> StreamingResponse:
    """Export single job as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "job_id", "url", "status", "created_at", "completed_at",
        "elapsed_seconds", "status_code", "title", "text", "links", "images",
    ])

    # Parse job data
    data = json.loads(job.data) if job.data else {}

    writer.writerow([
        job.id,
        job.url,
        job.status,
        job.created_at.isoformat() if job.created_at else "",
        job.completed_at.isoformat() if job.completed_at else "",
        job.elapsed_seconds or "",
        job.status_code or "",
        data.get("title", ""),
        data.get("text", "")[:500],  # Truncate long text
        "; ".join(data.get("links", [])[:10]),
        "; ".join(data.get("images", [])[:10]),
    ])

    content = output.getvalue()
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{job.id}.csv"',
        },
    )


def _export_batch_json(batch_id: str, jobs: list) -> StreamingResponse:
    """Export batch results as JSON."""
    results = []
    for job in jobs:
        results.append({
            "job_id": job.id,
            "url": job.url,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "elapsed_seconds": job.elapsed_seconds,
            "status_code": job.status_code,
            "data": json.loads(job.data) if job.data else None,
        })

    content = json.dumps({
        "batch_id": batch_id,
        "total": len(results),
        "results": results,
    }, indent=2, ensure_ascii=False)

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="batch-{batch_id}.json"',
        },
    )


def _export_batch_csv(batch_id: str, jobs: list) -> StreamingResponse:
    """Export batch results as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "job_id", "url", "status", "created_at", "completed_at",
        "elapsed_seconds", "status_code", "title", "text", "links", "images",
    ])

    for job in jobs:
        data = json.loads(job.data) if job.data else {}
        writer.writerow([
            job.id,
            job.url,
            job.status,
            job.created_at.isoformat() if job.created_at else "",
            job.completed_at.isoformat() if job.completed_at else "",
            job.elapsed_seconds or "",
            job.status_code or "",
            data.get("title", ""),
            data.get("text", "")[:500],
            "; ".join(data.get("links", [])[:10]),
            "; ".join(data.get("images", [])[:10]),
        ])

    content = output.getvalue()
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="batch-{batch_id}.csv"',
        },
    )
