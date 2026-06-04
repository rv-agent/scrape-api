"""
Playwright-based scraper for dynamic pages.

Full browser rendering for JavaScript-heavy sites.
Integrates proxy rotation and UA rotation.
"""

import logging
import time
from typing import Optional, Dict, Any

from src.scraper.base import BaseScraper, ScrapeResult, ScrapeStatus

logger = logging.getLogger(__name__)


class PlaywrightScraper(BaseScraper):
    """
    Playwright-based scraper for dynamic pages.
    
    Uses Playwright for full browser rendering.
    Best for: SPAs, JavaScript-heavy sites, anti-bot protected sites.
    
    Features:
    - Proxy rotation (passed to browser context)
    - User-Agent rotation with fingerprint consistency
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._browser = None
        self._playwright = None
    
    async def _ensure_browser(self):
        """Ensure browser is launched."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ]
                )
                logger.info("Playwright browser launched")
            except Exception as e:
                logger.error("Failed to launch browser: %s", str(e))
                raise
    
    async def scrape(
        self,
        url: str,
        wait_for: Optional[str] = None,
        wait_until: str = "networkidle",
        screenshot: bool = False,
        extract_text: bool = True,
        javascript: Optional[str] = None,
        **kwargs,
    ) -> ScrapeResult:
        """
        Scrape a URL using Playwright browser with proxy and UA rotation.
        
        Args:
            url: Target URL
            wait_for: CSS selector to wait for
            wait_until: Navigation wait condition (load, domcontentloaded, networkidle)
            screenshot: Whether to take screenshot
            extract_text: Whether to extract clean text
            javascript: JavaScript to execute after page load
            **kwargs: Additional parameters
            
        Returns:
            ScrapeResult with content and metadata
        """
        start_time = time.monotonic()
        page = None
        
        try:
            await self._ensure_browser()
            
            # Get rotated UA + fingerprint headers
            ua = self.ua_manager.get_random() if self.ua_rotation else self.user_agent
            fingerprint = None
            for fp in self.ua_manager._pool:
                if fp.user_agent == ua:
                    fingerprint = fp
                    break
            if fingerprint is None:
                fingerprint = self.ua_manager.get_fingerprint()
            
            # Get proxy
            proxy_url = self._get_next_proxy()
            
            # Build context options
            context_options = {
                "user_agent": fingerprint.user_agent,
                "viewport": {"width": 1920, "height": 1080},
                "locale": "en-US",
            }
            
            # Add proxy to context if available
            if proxy_url:
                context_options["proxy"] = {"server": proxy_url}
                logger.debug("Playwright using proxy: %s", proxy_url[:30])
            
            context = await self._browser.new_context(**context_options)
            
            # Set extra headers for fingerprint consistency
            extra_headers = {}
            if fingerprint.accept:
                extra_headers["Accept"] = fingerprint.accept
            if fingerprint.accept_language:
                extra_headers["Accept-Language"] = fingerprint.accept_language
            
            page = await context.new_page()
            
            if extra_headers:
                await page.set_extra_http_headers(extra_headers)
            
            # Navigate
            response = await page.goto(
                url,
                wait_until=wait_until,
                timeout=self.timeout * 1000,
            )
            
            # Wait for specific element if specified
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10000)
            
            # Execute custom JavaScript if specified
            if javascript:
                await page.evaluate(javascript)
            
            # Get content
            content = await page.content()
            status_code = response.status if response else None
            
            # Extract data
            data_extracted = None
            if extract_text:
                title = await page.title()
                
                # Extract text content
                text_content = await page.evaluate("""
                    () => {
                        // Remove scripts and styles
                        const clone = document.body.cloneNode(true);
                        clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                        return clone.innerText;
                    }
                """)
                
                # Extract links
                links = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)
                """)
                
                # Extract images
                images = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('img[src]')).map(img => img.src)
                """)
                
                data_extracted = {
                    "title": title,
                    "text": text_content,
                    "links": links,
                    "images": images,
                }
            
            # Take screenshot if requested
            screenshot_bytes = None
            if screenshot:
                screenshot_bytes = await page.screenshot(type="png")
            
            elapsed = time.monotonic() - start_time
            self._record_proxy_success(elapsed)
            
            logger.info(
                "Playwright scraped %s - status=%s, size=%d, elapsed=%.2fs, proxy=%s",
                url, status_code, len(content), elapsed,
                proxy_url[:30] if proxy_url else "none",
            )
            
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.COMPLETED,
                status_code=status_code,
                content=content,
                data=data_extracted,
                metadata={
                    "elapsed_seconds": elapsed,
                    "rendered": True,
                    "screenshot": screenshot_bytes is not None,
                    "screenshot_size": len(screenshot_bytes) if screenshot_bytes else None,
                    "proxy_used": proxy_url is not None,
                    "browser_used": "chromium",
                },
            )
            
        except Exception as e:
            elapsed = time.monotonic() - start_time
            self._record_proxy_failure()
            logger.exception("Playwright error scraping %s", url)
            return ScrapeResult(
                url=url,
                status=ScrapeStatus.FAILED,
                error=f"Browser error: {str(e)}",
                metadata={"elapsed_seconds": elapsed},
            )
            
        finally:
            if page:
                await page.close()
    
    async def close(self):
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        await super().close()
