"""
Base scraper class and common scraping utilities.

Integrates proxy rotation, User-Agent rotation, and retry logic.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import httpx

from src.scraper.proxy_manager import ProxyManager
from src.scraper.user_agent import UserAgentManager
from src.scraper.retry import RetryHandler, RetryConfig

logger = logging.getLogger(__name__)


class ScrapeStatus(str, Enum):
    """Scrape job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScrapeResult:
    """Result of a scraping operation."""
    url: str
    status: ScrapeStatus
    status_code: Optional[int] = None
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseScraper(ABC):
    """
    Abstract base class for scrapers.
    
    Integrates:
    - Proxy rotation (ProxyManager)
    - User-Agent rotation (UserAgentManager)
    - Retry with exponential backoff (RetryHandler)
    
    Subclasses must implement the `scrape` method.
    """
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
        proxy: Optional[str] = None,
        # Proxy manager
        proxy_manager: Optional[ProxyManager] = None,
        proxies: Optional[List[str]] = None,
        proxy_strategy: str = "round_robin",
        # User-Agent manager
        ua_manager: Optional[UserAgentManager] = None,
        ua_rotation: bool = True,
        # Retry config
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 30.0,
        retry_exponential_base: float = 2.0,
        retry_jitter: bool = True,
    ):
        self.timeout = timeout
        self.ua_rotation = ua_rotation
        
        # Initialize ProxyManager
        if proxy_manager:
            self.proxy_manager = proxy_manager
        elif proxies:
            self.proxy_manager = ProxyManager(proxies=proxies, strategy=proxy_strategy)
        else:
            self.proxy_manager = ProxyManager(
                proxies=[proxy] if proxy else [],
                strategy=proxy_strategy,
            )
        
        # Initialize UserAgentManager
        self.ua_manager = ua_manager or UserAgentManager()
        self.user_agent = user_agent or self.ua_manager.get_random()
        
        # Initialize RetryHandler
        self.retry_handler = RetryHandler(
            max_retries=max_retries,
            base_delay=retry_base_delay,
            max_delay=retry_max_delay,
            exponential_base=retry_exponential_base,
            jitter=retry_jitter,
        )
        
        self._client: Optional[httpx.AsyncClient] = None
        self._current_proxy: Optional[str] = None
    
    def _get_next_proxy(self) -> Optional[str]:
        """Get next proxy from the pool."""
        if self.proxy_manager.proxy_count == 0:
            return None
        return self.proxy_manager.get_proxy()
    
    def _get_request_headers(self) -> Dict[str, str]:
        """Get headers with rotated User-Agent and consistent fingerprint."""
        if self.ua_rotation:
            return self.ua_manager.get_headers()
        return {"User-Agent": self.user_agent}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with current proxy and UA."""
        # Always create a fresh client to pick up new proxy/UA per request
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        
        proxy = self._get_next_proxy()
        self._current_proxy = proxy
        headers = self._get_request_headers()
        
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers=headers,
            proxy=proxy,
        )
        
        if proxy:
            logger.debug("HTTP client created with proxy: %s", proxy[:30])
        
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _record_proxy_success(self, response_time: float) -> None:
        """Record proxy success for health tracking."""
        if self._current_proxy:
            self.proxy_manager.record_success(self._current_proxy, response_time)
    
    def _record_proxy_failure(self) -> None:
        """Record proxy failure for health tracking."""
        if self._current_proxy:
            self.proxy_manager.record_failure(self._current_proxy)
    
    @abstractmethod
    async def scrape(self, url: str, **kwargs) -> ScrapeResult:
        """
        Scrape a URL and return the result.
        
        Args:
            url: Target URL to scrape
            **kwargs: Additional parameters
            
        Returns:
            ScrapeResult with status, content, and metadata
        """
        pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
