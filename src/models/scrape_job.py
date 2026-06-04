"""
Scrape Job database model.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, Float, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base


class ScrapeJob(Base):
    """Scrape job tracking."""

    __tablename__ = "scrape_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    api_key_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    render_js: Mapped[bool] = mapped_column(default=False)
    extract_text: Mapped[bool] = mapped_column(default=True)
    selector: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_format: Mapped[str] = mapped_column(String(10), default="json")

    # Results
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    elapsed_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    content_length: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Batch tracking
    batch_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    def mark_running(self) -> None:
        """Mark job as running."""
        self.status = "running"
        self.started_at = datetime.utcnow()

    def mark_completed(self, data: dict, elapsed: float, **meta) -> None:
        """Mark job as completed with results."""
        self.status = "completed"
        self.data = data
        self.elapsed_seconds = elapsed
        self.content_type = meta.get("content_type")
        self.content_length = meta.get("content_length", 0)
        self.status_code = meta.get("status_code")
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error: str, elapsed: float = 0) -> None:
        """Mark job as failed."""
        self.status = "failed"
        self.error = error
        self.elapsed_seconds = elapsed
        self.completed_at = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<ScrapeJob {self.id[:8]}... status={self.status}>"
