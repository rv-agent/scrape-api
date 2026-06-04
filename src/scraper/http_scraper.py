"""
HTTP-based scraper for static pages.

Fast, lightweight scraping without browser rendering.
Integrates proxy rotation, UA rotation, and retry logic.
"""

import logging
import time
from typing import Optional, Dict, Any

import httpx
from bs4 import BeautifulSoup

from src.scraper.base import BaseScraper, ScrapeResult, ScrapeStatus
from src.scraper.retry import retry_async, RetryConfig, is_retryable_status

logger = logging.getLogger(__name__)


class HttpScraper(BaseScraper):
    """
    HTTP-based scraper for static pages.
    
    Uses httpx for HTTP requests and BeautifulSoup for parsing.
    Best for: static HTML pages, APIs, simple scraping tasks.
    
    Features:
    - Automatic proxy rotation
    - User-Agent rotation with fingerprint consistency
    - Retry with exponential backoff on transient failures
    """
    
    async def scrape(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
        extract_text: bool = True,
        **kwargs,
    ) -> ScrapeResult:
        """
        Scrape a URL using HTTP request with retry support.
        
        Args:
            url: Target URL
            method: HTTP method (GET, POST)
            headers: Additional headers
            params: Query parameters
            data: Form data for POST
            extract_text: Whether to extract clean text
            **kwargs: Additional parameters
            
        Returns:
            ScrapeResult with content and metadata
        """
        start_time = time.monotonic()
        
        # Build retry config from handler
        retry_config = RetryConfig(
            max_retries=self.retry_handler.config.max_retries,
            base_delay=self.retry_handler.config.base_delay,
            max_delay=self.retry_handler.config.max_delay,
            exponential_base=self.retry_handler.config.exponential_base,
            jitter=self.retry_handler.config.jitter,
        )

        async def _do_request() -> httpx.Response:
            """Execute the HTTP request (called by retry handler)."""
            client = await self._get_client()
            
            # Merge custom headers on top of fingerprint headers
            request_headers = dict(client.headers)
            if headers:
                request_headers.update(headers)
            
            response = await client.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                data=data,
            )
            
            # Check for retryable status codes
            if is_retryable_status(response.status_code, retry_config):
                self._record_proxy_failure()
                raise httpx.HTTPStatusError(
                    message=f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
            
            return response

        try:
            response = await retry_async(
                _do_request,
                config=retry_config,
                on_retry=lambda attempt, exc, delay: self._record_proxy_failure(),
            )
            
            elapsed = time.monotonic() - start_time
            self._record_proxy_success(elapsed)
            
            # Parse content
            content = response.text
            data_extracted = None
            
            if extract_text and "text/html" in response.headers.get("content-type", ""):
                soup = BeautifulSoup(content, "lxml")
                # Remove script and style elements
                for element in soup(["script", "style", "noscript"]):
                    element.decompose()
                data_extracted = {
                    "title": soup.title.string if soup.title else None,
                    "text": soup.get_text(separator="\n", strip=True),
                    "links": [a.get("href") for a in soup.find_all("a", href=True)],
                    "images": [img.get("src") for img in soup.find_all("img", src=True)],
                }
            
            logger.info(
                "Scraped %s - status=%d, size=%d, elapsed=%.2fs, proxy=%s",
                url, response.status_code, len(content), elapsed,
                self._current_proxy[:30] if self._current_proxy else "none",
            )
            
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.COMPLETED,
                status_code=response.status_code,
                content=content,
                data=data_extracted,
                headers=dict(response.headers),
                metadata={
                    "elapsed_seconds": elapsed,
                    "content_type": response.headers.get("content-type"),
                    "content_length": len(content),
                    "proxy_used": self._current_proxy is not None,
                    "retries": self.retry_handler.config.max_retries,  # actual retries tracked by retry_async
                },
            )
            
        except httpx.TimeoutException as e:
            elapsed = time.monotonic() - start_time
            self._record_proxy_failure()
            logger.error("Timeout scraping %s after retries: %s", url, str(e))
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.FAILED,
                error=f"Request timeout after {self.timeout}s (with retries)",
                metadata={"elapsed_seconds": elapsed},
            )
            
        except httpx.HTTPStatusError as e:
            elapsed = time.monotonic() - start_time
            self._record_proxy_failure()
            logger.error("HTTP error scraping %s: %s", url, str(e))
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.FAILED,
                status_code=e.response.status_code,
                error=f"HTTP {e.response.status_code}: {str(e)}",
                metadata={"elapsed_seconds": elapsed},
            )
            
        except httpx.RequestError as e:
            elapsed = time.monotonic() - start_time
            self._record_proxy_failure()
            logger.error("Request error scraping %s after retries: %s", url, str(e))
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.FAILED,
                error=f"Request error after retries: {str(e)}",
                metadata={"elapsed_seconds": elapsed},
            )
            
        except Exception as e:
            elapsed = time.monotonic() - start_time
            self._record_proxy_failure()
            logger.exception("Unexpected error scraping %s", url)
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.FAILED,
                error=f"Unexpected error: {str(e)}",
                metadata={"elapsed_seconds": elapsed},
            )
