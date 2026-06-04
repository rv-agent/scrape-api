"""
ScrapeAPI - FastAPI Application Entry Point

Usage:
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
    
    atau:
    python -m src.main
"""

import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.api.routes.health import router as health_router
from src.api.routes.scrape import router as scrape_router
from src.api.routes.keys import router as keys_router
from src.api.routes.webhooks import router as webhooks_router
from src.api.routes.export import router as export_router
from src.api.routes.scheduler import router as scheduler_router
from src.api.routes.billing import router as billing_router
from src.api.middleware import RateLimitMiddleware
from src.api.error_handler import register_error_handlers
from src.api.security import (
    SecurityHeadersMiddleware,
    RequestSizeMiddleware,
    RequestLoggingMiddleware,
)
from src.models.database import init_db, close_db
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting ScrapeAPI v%s", settings.APP_VERSION)
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("Debug mode: %s", settings.DEBUG)
    
    # Startup: initialize database
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown: cleanup
    await close_db()
    logger.info("Shutting down ScrapeAPI")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="ScrapeAPI",
        description="Platform scraping API untuk developer. Kirim URL, dapat data JSON.",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )
    
    # Rate limiting middleware (sliding window per API key)
    app.add_middleware(RateLimitMiddleware, window_seconds=60)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request size limit (10MB)
    app.add_middleware(RequestSizeMiddleware, max_size=10 * 1024 * 1024)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600,  # Preflight cache 10 minutes
    )
    
    # Global error handlers
    register_error_handlers(app)
    
    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(scrape_router, tags=["Scrape"])
    app.include_router(keys_router, tags=["API Keys"])
    app.include_router(webhooks_router, tags=["Webhooks"])
    app.include_router(export_router, tags=["Export"])
    app.include_router(scheduler_router, tags=["Scheduler"])
    app.include_router(billing_router, tags=["Billing"])
    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
