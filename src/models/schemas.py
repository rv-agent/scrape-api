"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────

class ScrapeJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResponseFormat(str, Enum):
    JSON = "json"
    CSV = "csv"


class TierLevel(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ── Scrape Request/Response ────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    """Single URL scrape request."""
    url: str = Field(..., description="Target URL to scrape (must include http:// or https://)", examples=["https://example.com"])
    render_js: bool = Field(default=False, description="Use headless browser for JS rendering")
    extract_text: bool = Field(default=True, description="Extract clean text from HTML")
    selector: Optional[str] = Field(default=None, description="CSS selector to extract specific elements")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom HTTP headers")
    format: ResponseFormat = Field(default=ResponseFormat.JSON, description="Response format")
    timeout: Optional[int] = Field(default=None, ge=5, le=120, description="Request timeout in seconds")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL has proper scheme."""
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class BatchScrapeRequest(BaseModel):
    """Multiple URL scrape request."""
    urls: List[str] = Field(..., min_length=1, max_length=50, description="List of URLs to scrape")
    render_js: bool = Field(default=False, description="Use headless browser for JS rendering")
    extract_text: bool = Field(default=True, description="Extract clean text from HTML")
    selector: Optional[str] = Field(default=None, description="CSS selector to extract specific elements")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom HTTP headers")
    format: ResponseFormat = Field(default=ResponseFormat.JSON, description="Response format")
    timeout: Optional[int] = Field(default=None, ge=5, le=120, description="Request timeout in seconds")

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        """Validate all URLs have proper scheme."""
        cleaned = []
        for url in v:
            url = url.strip()
            if not url:
                raise ValueError("URL cannot be empty")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(f"URL must start with http:// or https://: {url}")
            cleaned.append(url)
        return cleaned


class ScrapeData(BaseModel):
    """Extracted data from a scrape."""
    title: Optional[str] = None
    text: Optional[str] = None
    links: Optional[List[str]] = None
    images: Optional[List[str]] = None
    selector_results: Optional[List[str]] = None
    raw_html: Optional[str] = None


class ScrapeMetadata(BaseModel):
    """Metadata about the scrape operation."""
    elapsed_seconds: float
    content_type: Optional[str] = None
    content_length: int = 0
    status_code: Optional[int] = None


class ScrapeResponse(BaseModel):
    """Single URL scrape response."""
    job_id: str = Field(..., description="Unique job identifier")
    status: ScrapeJobStatus
    url: str
    data: Optional[ScrapeData] = None
    metadata: Optional[ScrapeMetadata] = None
    error: Optional[str] = None
    created_at: datetime


class BatchScrapeResponse(BaseModel):
    """Batch scrape response."""
    batch_id: str = Field(..., description="Unique batch identifier")
    total: int
    completed: int
    failed: int
    results: List[ScrapeResponse]


class JobStatusResponse(BaseModel):
    """Job status check response."""
    job_id: str
    status: ScrapeJobStatus
    url: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


# ── API Key ────────────────────────────────────────────────────────────────

class APIKeyCreate(BaseModel):
    """Request to create a new API key."""
    name: str = Field(..., min_length=1, max_length=100, description="Friendly name for the key")
    tier: TierLevel = Field(default=TierLevel.FREE, description="Subscription tier")


class APIKeyResponse(BaseModel):
    """API key information."""
    id: str
    name: str
    key_prefix: str = Field(description="First 8 chars of key for identification")
    tier: TierLevel
    is_active: bool
    requests_today: int = 0
    requests_limit: int = 0
    created_at: datetime
    last_used_at: Optional[datetime] = None


class APIKeyCreatedResponse(APIKeyResponse):
    """Response when creating a new key — includes full key (only shown once)."""
    key: str = Field(description="Full API key — save this, it won't be shown again")


# ── Usage / Stats ──────────────────────────────────────────────────────────

class UsageStats(BaseModel):
    """Usage statistics for an API key."""
    key_id: str
    key_name: str
    tier: TierLevel
    requests_today: int
    requests_this_month: int
    requests_limit: int
    total_requests: int
    avg_response_time_ms: float


# ── Error Responses ────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    status_code: int
