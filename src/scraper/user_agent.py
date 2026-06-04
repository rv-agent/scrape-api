"""
User-Agent rotation with realistic browser fingerprints.

Maintains a pool of current, realistic User-Agent strings grouped by
browser/platform. Supports random selection, per-request rotation,
and fingerprint-consistent header generation.
"""

import logging
import random
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class BrowserType(str, Enum):
    """Supported browser types."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"
    EDGE = "edge"


class PlatformType(str, Enum):
    """Supported platforms."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    ANDROID = "android"
    IOS = "ios"


@dataclass
class UserAgentFingerprint:
    """A User-Agent with associated fingerprint headers."""
    user_agent: str
    browser: BrowserType
    platform: PlatformType
    accept: str
    accept_language: str
    accept_encoding: str
    sec_ch_ua: Optional[str] = None
    sec_ch_ua_platform: Optional[str] = None
    sec_ch_ua_mobile: Optional[str] = None


# Realistic User-Agent pool (updated for 2024-2025 browsers)
_UA_POOL: List[UserAgentFingerprint] = [
    # Chrome on Windows
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        browser=BrowserType.CHROME,
        platform=PlatformType.WINDOWS,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        accept_language="en-US,en;q=0.9",
        accept_encoding="gzip, deflate, br",
        sec_ch_ua='"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        sec_ch_ua_platform='"Windows"',
        sec_ch_ua_mobile="?0",
    ),
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        browser=BrowserType.CHROME,
        platform=PlatformType.WINDOWS,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        accept_language="en-US,en;q=0.9",
        accept_encoding="gzip, deflate, br",
        sec_ch_ua='"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
        sec_ch_ua_platform='"Windows"',
        sec_ch_ua_mobile="?0",
    ),
    # Chrome on macOS
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        browser=BrowserType.CHROME,
        platform=PlatformType.MACOS,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        accept_language="en-US,en;q=0.9",
        accept_encoding="gzip, deflate, br",
        sec_ch_ua='"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        sec_ch_ua_platform='"macOS"',
        sec_ch_ua_mobile="?0",
    ),
    # Chrome on Linux
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        browser=BrowserType.CHROME,
        platform=PlatformType.LINUX,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        accept_language="en-US,en;q=0.9",
        accept_encoding="gzip, deflate, br",
        sec_ch_ua='"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        sec_ch_ua_platform='"Linux"',
        sec_ch_ua_mobile="?0",
    ),
    # Firefox on Windows
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        browser=BrowserType.FIREFOX,
        platform=PlatformType.WINDOWS,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        accept_language="en-US,en;q=0.5",
        accept_encoding="gzip, deflate, br",
    ),
    # Firefox on macOS
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
        browser=BrowserType.FIREFOX,
        platform=PlatformType.MACOS,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        accept_language="en-US,en;q=0.5",
        accept_encoding="gzip, deflate, br",
    ),
    # Firefox on Linux
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        browser=BrowserType.FIREFOX,
        platform=PlatformType.LINUX,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        accept_language="en-US,en;q=0.5",
        accept_encoding="gzip, deflate, br",
    ),
    # Safari on macOS
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        browser=BrowserType.SAFARI,
        platform=PlatformType.MACOS,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        accept_language="en-US,en;q=0.9",
        accept_encoding="gzip, deflate, br",
    ),
    # Edge on Windows
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        browser=BrowserType.EDGE,
        platform=PlatformType.WINDOWS,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        accept_language="en-US,en;q=0.9",
        accept_encoding="gzip, deflate, br",
        sec_ch_ua='"Chromium";v="124", "Microsoft Edge";v="124", "Not-A.Brand";v="99"',
        sec_ch_ua_platform='"Windows"',
        sec_ch_ua_mobile="?0",
    ),
    # Chrome on Android
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
        browser=BrowserType.CHROME,
        platform=PlatformType.ANDROID,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        accept_language="en-US,en;q=0.9",
        accept_encoding="gzip, deflate, br",
        sec_ch_ua='"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        sec_ch_ua_platform='"Android"',
        sec_ch_ua_mobile="?1",
    ),
    # Safari on iOS
    UserAgentFingerprint(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        browser=BrowserType.SAFARI,
        platform=PlatformType.IOS,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        accept_language="en-US,en;q=0.9",
        accept_encoding="gzip, deflate, br",
    ),
]


class UserAgentManager:
    """
    Manages User-Agent rotation with fingerprint consistency.
    
    Features:
    - Random UA selection per request
    - Filter by browser type or platform
    - Consistent fingerprint headers (Accept, Sec-CH-UA, etc.)
    - Custom UA pool extension
    """

    def __init__(
        self,
        pool: Optional[List[UserAgentFingerprint]] = None,
        default_ua: Optional[str] = None,
    ):
        self._pool = pool or list(_UA_POOL)
        self._default = default_ua or self._pool[0].user_agent
        self._last_index = -1

    def get_random(self) -> str:
        """Get a random User-Agent string."""
        fp = random.choice(self._pool)
        return fp.user_agent

    def get_fingerprint(self, index: Optional[int] = None) -> UserAgentFingerprint:
        """
        Get a full fingerprint (UA + headers).
        
        Args:
            index: Specific index. If None, picks random.
            
        Returns:
            UserAgentFingerprint with all headers.
        """
        if index is not None:
            return self._pool[index % len(self._pool)]
        return random.choice(self._pool)

    def get_next(self) -> str:
        """Get next User-Agent in rotation (round-robin)."""
        self._last_index = (self._last_index + 1) % len(self._pool)
        return self._pool[self._last_index].user_agent

    def get_by_browser(self, browser: BrowserType) -> str:
        """Get a random User-Agent for a specific browser."""
        matching = [fp for fp in self._pool if fp.browser == browser]
        if not matching:
            logger.warning("No UAs for browser %s, using random", browser.value)
            return self.get_random()
        return random.choice(matching).user_agent

    def get_by_platform(self, platform: PlatformType) -> str:
        """Get a random User-Agent for a specific platform."""
        matching = [fp for fp in self._pool if fp.platform == platform]
        if not matching:
            logger.warning("No UAs for platform %s, using random", platform.value)
            return self.get_random()
        return random.choice(matching).user_agent

    def get_headers(self, user_agent: Optional[str] = None) -> Dict[str, str]:
        """
        Get complete set of headers matching a User-Agent.
        
        If user_agent is provided, finds its fingerprint and returns matching headers.
        If not found, returns headers for a random fingerprint.
        
        Args:
            user_agent: Specific UA string to match.
            
        Returns:
            Dict of HTTP headers consistent with the UA fingerprint.
        """
        fingerprint = None

        if user_agent:
            for fp in self._pool:
                if fp.user_agent == user_agent:
                    fingerprint = fp
                    break

        if fingerprint is None:
            fingerprint = random.choice(self._pool)

        headers = {
            "User-Agent": fingerprint.user_agent,
            "Accept": fingerprint.accept,
            "Accept-Language": fingerprint.accept_language,
            "Accept-Encoding": fingerprint.accept_encoding,
        }

        if fingerprint.sec_ch_ua:
            headers["Sec-CH-UA"] = fingerprint.sec_ch_ua
        if fingerprint.sec_ch_ua_platform:
            headers["Sec-CH-UA-Platform"] = fingerprint.sec_ch_ua_platform
        if fingerprint.sec_ch_ua_mobile is not None:
            headers["Sec-CH-UA-Mobile"] = fingerprint.sec_ch_ua_mobile

        return headers

    def add_custom(self, fingerprint: UserAgentFingerprint) -> None:
        """Add a custom User-Agent fingerprint to the pool."""
        # Avoid duplicates
        if any(fp.user_agent == fingerprint.user_agent for fp in self._pool):
            logger.debug("UA already in pool")
            return
        self._pool.append(fingerprint)
        logger.info("Added custom UA: %s (total=%d)", fingerprint.user_agent[:60], len(self._pool))

    @property
    def pool_size(self) -> int:
        """Number of User-Agents in the pool."""
        return len(self._pool)

    def get_stats(self) -> Dict:
        """Get UA pool statistics."""
        browsers = {}
        platforms = {}
        for fp in self._pool:
            browsers[fp.browser.value] = browsers.get(fp.browser.value, 0) + 1
            platforms[fp.platform.value] = platforms.get(fp.platform.value, 0) + 1

        return {
            "total": len(self._pool),
            "browsers": browsers,
            "platforms": platforms,
        }

    def __repr__(self) -> str:
        return f"UserAgentManager(pool_size={len(self._pool)})"
