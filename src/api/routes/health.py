"""
Health check endpoints.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.config.settings import settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    environment: str
    timestamp: str
    debug: bool


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    version: str
    environment: str
    timestamp: str
    debug: bool
    services: dict


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse: Basic health status
    """
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow().isoformat(),
        debug=settings.DEBUG,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check with service status.
    
    Returns:
        DetailedHealthResponse: Detailed health status including services
    """
    services = {
        "database": "unknown",  # TODO: Check DB connection
        "redis": "unknown",     # TODO: Check Redis connection
        "celery": "unknown",    # TODO: Check Celery workers
    }
    
    return DetailedHealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow().isoformat(),
        debug=settings.DEBUG,
        services=services,
    )
