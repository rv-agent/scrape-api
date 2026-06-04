"""
Pagination handler for ScrapeAPI.

Detects pagination links in HTML and provides auto-follow capability
to scrape multiple pages of results.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class PaginationLink:
    """A detected pagination link."""
    url: str
    text: str
    page_number: Optional[int] = None
    is_next: bool = False
    is_prev: bool = False


@dataclass
class PaginationResult:
    """Result of pagination detection."""
    current_page: int = 1
    total_pages: Optional[int] = None
    next_url: Optional[str] = None
    prev_url: Optional[str] = None
    page_urls: List[PaginationLink] = field(default_factory=list)
    pagination_type: str = "unknown"  # numbered, next-prev, load-more, infinite
    has_next: bool = False


def detect_pagination(html: str, base_url: str) -> PaginationResult:
    """
    Detect pagination links in HTML content.

    Args:
        html: Raw HTML string
        base_url: Base URL for resolving relative links

    Returns:
        PaginationResult with detected pagination info
    """
    if not html:
        return PaginationResult()

    soup = BeautifulSoup(html, "lxml")
    result = PaginationResult()

    # Strategy 1: Look for common pagination containers
    pagination_containers = soup.find_all(
        class_=re.compile(r'paginat|pager|page-nav|pagination', re.I)
    )
    pagination_containers += soup.find_all("nav", attrs={"aria-label": re.compile(r'paginat|page', re.I)})

    if pagination_containers:
        result = _parse_pagination_container(pagination_containers, base_url)
        if result.page_urls:
            return result

    # Strategy 2: Look for rel="next" / rel="prev" links
    result = _parse_rel_links(soup, base_url)
    if result.next_url or result.prev_url:
        return result

    # Strategy 3: Look for "Next" / "Previous" text links
    result = _parse_text_links(soup, base_url)
    if result.next_url or result.prev_url:
        return result

    # Strategy 4: Look for numbered page links
    result = _parse_numbered_links(soup, base_url)
    if result.page_urls:
        return result

    return result


def get_next_page_url(result: PaginationResult) -> Optional[str]:
    """Get the URL for the next page, if available."""
    return result.next_url


def build_page_url(base_url: str, page: int, param_name: str = "page") -> str:
    """
    Build a URL for a specific page number.

    Args:
        base_url: Base URL
        page: Page number
        param_name: Query parameter name for page

    Returns:
        URL with page parameter
    """
    parsed = urlparse(base_url)
    params = parse_qs(parsed.query)
    params[param_name] = [str(page)]
    new_query = urlencode(params, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _parse_pagination_container(containers, base_url: str) -> PaginationResult:
    """Parse pagination from container elements."""
    result = PaginationResult()
    page_links = []

    for container in containers:
        for a in container.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            text = a.get_text(strip=True)

            link = PaginationLink(url=href, text=text)

            # Detect "next" links
            if _is_next_link(a, text):
                link.is_next = True
                result.next_url = href
                result.has_next = True

            # Detect "prev" links
            elif _is_prev_link(a, text):
                link.is_prev = True
                result.prev_url = href

            # Detect numbered links
            else:
                page_num = _extract_page_number(text, href)
                if page_num:
                    link.page_number = page_num
                    if page_num > (result.total_pages or 0):
                        result.total_pages = page_num

            page_links.append(link)

    result.page_urls = page_links
    result.pagination_type = "numbered" if any(l.page_number for l in page_links) else "next-prev"

    # Detect current page from active class
    for container in containers:
        active = container.find(class_=re.compile(r'active|current|selected', re.I))
        if active:
            num = _extract_page_number(active.get_text(strip=True), "")
            if num:
                result.current_page = num

    return result


def _parse_rel_links(soup: BeautifulSoup, base_url: str) -> PaginationResult:
    """Parse pagination from rel=next/prev links."""
    result = PaginationResult()

    next_link = soup.find("link", attrs={"rel": "next"})
    if next_link and next_link.get("href"):
        result.next_url = urljoin(base_url, next_link["href"])
        result.has_next = True

    prev_link = soup.find("link", attrs={"rel": "prev"})
    if prev_link and prev_link.get("href"):
        result.prev_url = urljoin(base_url, prev_link["href"])

    if result.next_url or result.prev_url:
        result.pagination_type = "next-prev"

    return result


def _parse_text_links(soup: BeautifulSoup, base_url: str) -> PaginationResult:
    """Parse pagination from text-based next/prev links."""
    result = PaginationResult()

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        href = urljoin(base_url, a["href"])

        if _is_next_link(a, text):
            result.next_url = href
            result.has_next = True
        elif _is_prev_link(a, text):
            result.prev_url = href

    if result.next_url or result.prev_url:
        result.pagination_type = "next-prev"

    return result


def _parse_numbered_links(soup: BeautifulSoup, base_url: str) -> PaginationResult:
    """Parse numbered pagination links."""
    result = PaginationResult()
    page_links = []

    # Look for links with page numbers in text or URL
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = urljoin(base_url, a["href"])

        page_num = _extract_page_number(text, href)
        if page_num:
            link = PaginationLink(url=href, text=text, page_number=page_num)
            page_links.append(link)
            if page_num > (result.total_pages or 0):
                result.total_pages = page_num

    if page_links:
        result.page_urls = page_links
        result.pagination_type = "numbered"

        # Find next page link
        sorted_links = sorted(page_links, key=lambda l: l.page_number or 0)
        for link in sorted_links:
            if link.page_number and link.page_number > result.current_page:
                result.next_url = link.url
                result.has_next = True
                break

    return result


def _is_next_link(tag, text: str) -> bool:
    """Check if a tag is a 'next page' link."""
    text = text.lower()

    # Check text content
    next_texts = ["next", "next page", "›", "»", "→", "suivant", "siguiente", "selanjutnya"]
    if any(t in text for t in next_texts):
        return True

    # Check class/aria attributes
    classes = " ".join(tag.get("class", []))
    if re.search(r'next|forward', classes, re.I):
        return True

    aria = tag.get("aria-label", "")
    if re.search(r'next', aria, re.I):
        return True

    return False


def _is_prev_link(tag, text: str) -> bool:
    """Check if a tag is a 'previous page' link."""
    text = text.lower()

    prev_texts = ["previous", "prev", "prev page", "‹", "«", "←", "précédent", "anterior", "sebelumnya"]
    if any(t in text for t in prev_texts):
        return True

    classes = " ".join(tag.get("class", []))
    if re.search(r'prev|back', classes, re.I):
        return True

    aria = tag.get("aria-label", "")
    if re.search(r'prev', aria, re.I):
        return True

    return False


def _extract_page_number(text: str, url: str) -> Optional[int]:
    """Extract page number from text or URL."""
    # From text
    text = text.strip()
    if text.isdigit():
        num = int(text)
        if 1 <= num <= 10000:
            return num

    # From URL query params
    if url:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        for key in ["page", "p", "pg", "pagina"]:
            if key in params:
                try:
                    return int(params[key][0])
                except (ValueError, IndexError):
                    pass

        # From URL path (/page/2/, /p/3)
        match = re.search(r'/(?:page|p|pg)/(\d+)', parsed.path)
        if match:
            return int(match.group(1))

    return None
