"""
Application settings using Pydantic Settings.

Environment variables can be set in .env file or system environment.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    APP_NAME: str = "ScrapeAPI"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Debug mode")
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    LOG_FORMAT: str = Field(default="json", description="Log format: json, text")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./scrapeapi.db",
        description="Database URL (SQLite for dev, PostgreSQL for prod)"
    )
    DB_ECHO: bool = Field(default=False, description="SQLAlchemy echo mode")
    DB_POOL_SIZE: int = Field(default=10, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, description="Database max overflow connections")
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds (1 hour)")
    
    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL"
    )
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_FREE_TIER: int = Field(default=100, description="Free tier requests per day")
    RATE_LIMIT_STARTER: int = Field(default=10000, description="Starter tier requests per month")
    RATE_LIMIT_PRO: int = Field(default=50000, description="Pro tier requests per month")
    
    # Proxy Configuration
    PROXY_ENABLED: bool = Field(default=False, description="Enable proxy rotation")
    PROXY_STRATEGY: str = Field(default="round_robin", description="Proxy rotation strategy: round_robin, random, fastest")
    PROXY_DATACENTER_URL: Optional[str] = Field(default=None, description="Datacenter proxy URL")
    PROXY_RESIDENTIAL_URL: Optional[str] = Field(default=None, description="Residential proxy URL")
    PROXY_MAX_FAILS: int = Field(default=3, description="Max failures before marking proxy unhealthy")
    PROXY_HEALTH_CHECK_INTERVAL: int = Field(default=300, description="Proxy health check interval in seconds")
    PROXY_HEALTH_CHECK_URL: str = Field(default="https://httpbin.org/ip", description="URL for proxy health checks")
    
    # Scraper Configuration
    SCRAPER_TIMEOUT: int = Field(default=30, description="Scrape request timeout in seconds")
    SCRAPER_MAX_RETRIES: int = Field(default=3, description="Max retry attempts")
    SCRAPER_RETRY_BASE_DELAY: float = Field(default=1.0, description="Base delay for retry exponential backoff (seconds)")
    SCRAPER_RETRY_MAX_DELAY: float = Field(default=30.0, description="Max delay for retry backoff (seconds)")
    SCRAPER_RETRY_EXPONENTIAL_BASE: float = Field(default=2.0, description="Exponential base for retry backoff")
    SCRAPER_RETRY_JITTER: bool = Field(default=True, description="Add jitter to retry delays")
    SCRAPER_USER_AGENT: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="Default User-Agent string"
    )
    SCRAPER_UA_ROTATION: bool = Field(default=True, description="Enable User-Agent rotation per request")
    
    # Sentry (Error Tracking)
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.1, description="Sentry traces sample rate")
    
    # API Keys
    API_KEY_HEADER: str = Field(default="X-API-Key", description="API key header name")
    API_KEY_LENGTH: int = Field(default=32, description="API key length")
    
    # Seed API key for development
    SEED_API_KEY: str = Field(
        default="sk-dev-test1234567890abcdefghijklmnop",
        description="Seed API key for development testing"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings (for dependency injection)."""
    return settings
