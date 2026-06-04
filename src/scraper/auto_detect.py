"""
Auto-detect data structure from HTML content.

Detects tables, lists, headings, metadata, and common data patterns.
Returns structured JSON with detected patterns for API consumers.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@dataclass
class DetectedTable:
    """A detected HTML table with headers and rows."""
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    row_count: int = 0
    col_count: int = 0

    def __post_init__(self):
        self.row_count = len(self.rows)
        self.col_count = len(self.headers) if self.headers else (len(self.rows[0]) if self.rows else 0)


@dataclass
class DetectedList:
    """A detected HTML list (ul/ol)."""
    items: List[str]
    list_type: str = "ul"  # ul or ol
    item_count: int = 0

    def __post_init__(self):
        self.item_count = len(self.items)


@dataclass
class DetectedStructure:
    """Complete auto-detection result."""
    title: Optional[str] = None
    meta: Dict[str, str] = field(default_factory=dict)
    headings: List[Dict[str, str]] = field(default_factory=list)  # [{level: "h1", text: "..."}]
    tables: List[DetectedTable] = field(default_factory=list)
    lists: List[DetectedList] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)  # [{text: "...", href: "..."}]
    images: List[Dict[str, str]] = field(default_factory=list)  # [{alt: "...", src: "..."}]
    forms: List[Dict[str, Any]] = field(default_factory=list)
    data_type: str = "unknown"  # article, product, listing, table, form, generic
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API-friendly dict."""
        result = {
            "data_type": self.data_type,
            "confidence": round(self.confidence, 2),
        }

        if self.title:
            result["title"] = self.title

        if self.meta:
            result["meta"] = self.meta

        if self.headings:
            result["headings"] = self.headings

        if self.tables:
            result["tables"] = [
                {
                    "caption": t.caption,
                    "headers": t.headers,
                    "rows": t.rows,
                    "row_count": t.row_count,
                    "col_count": t.col_count,
                }
                for t in self.tables
            ]

        if self.lists:
            result["lists"] = [
                {
                    "type": l.list_type,
                    "items": l.items,
                    "item_count": l.item_count,
                }
                for l in self.lists
            ]

        if self.paragraphs:
            result["paragraphs"] = self.paragraphs[:20]  # Limit to first 20

        if self.links:
            result["links"] = self.links[:100]  # Limit

        if self.images:
            result["images"] = self.images[:50]

        if self.forms:
            result["forms"] = self.forms

        return result


def detect_structure(html: str) -> DetectedStructure:
    """
    Auto-detect data structure from HTML content.

    Args:
        html: Raw HTML string

    Returns:
        DetectedStructure with all detected patterns
    """
    if not html:
        return DetectedStructure(data_type="empty", confidence=0.0)

    soup = BeautifulSoup(html, "lxml")
    result = DetectedStructure()

    # Extract title
    result.title = _extract_title(soup)

    # Extract meta tags
    result.meta = _extract_meta(soup)

    # Extract headings
    result.headings = _extract_headings(soup)

    # Extract tables
    result.tables = _extract_tables(soup)

    # Extract lists
    result.lists = _extract_lists(soup)

    # Extract paragraphs
    result.paragraphs = _extract_paragraphs(soup)

    # Extract links
    result.links = _extract_links(soup)

    # Extract images
    result.images = _extract_images(soup)

    # Extract forms
    result.forms = _extract_forms(soup)

    # Classify data type
    result.data_type, result.confidence = _classify(soup, result)

    logger.info(
        "Auto-detect: type=%s confidence=%.2f tables=%d lists=%d headings=%d",
        result.data_type, result.confidence,
        len(result.tables), len(result.lists), len(result.headings),
    )

    return result


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    """Extract page title."""
    # Try <title> tag
    title_tag = soup.find("title")
    if title_tag:
        return title_tag.get_text(strip=True)

    # Try og:title
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"]

    # Try first h1
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return None


def _extract_meta(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract useful meta tags."""
    meta = {}
    useful_props = [
        "og:title", "og:description", "og:image", "og:url", "og:type",
        "description", "author", "keywords",
        "twitter:card", "twitter:title", "twitter:description",
    ]

    for prop in useful_props:
        # Check property attribute
        tag = soup.find("meta", property=prop)
        if not tag:
            # Check name attribute
            tag = soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            # Strip "og:" prefix for cleaner output
            key = prop.replace("og:", "og_").replace("twitter:", "twitter_")
            meta[key] = tag["content"]

    return meta


def _extract_headings(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract all headings (h1-h6)."""
    headings = []
    for level in range(1, 7):
        for tag in soup.find_all(f"h{level}"):
            text = tag.get_text(strip=True)
            if text:
                headings.append({"level": f"h{level}", "text": text})
    return headings


def _extract_tables(soup: BeautifulSoup) -> List[DetectedTable]:
    """Extract HTML tables."""
    tables = []

    for table in soup.find_all("table"):
        # Extract caption
        caption = None
        caption_tag = table.find("caption")
        if caption_tag:
            caption = caption_tag.get_text(strip=True)

        # Extract headers
        headers = []
        thead = table.find("thead")
        if thead:
            for th in thead.find_all(["th", "td"]):
                headers.append(th.get_text(strip=True))
        else:
            # Try first row as header
            first_row = table.find("tr")
            if first_row:
                ths = first_row.find_all("th")
                if ths:
                    headers = [th.get_text(strip=True) for th in ths]

        # Extract rows
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td"])
            if cells:
                rows.append([cell.get_text(strip=True) for cell in cells])

        if headers or rows:
            tables.append(DetectedTable(headers=headers, rows=rows, caption=caption))

    return tables


def _extract_lists(soup: BeautifulSoup) -> List[DetectedList]:
    """Extract ordered and unordered lists."""
    lists = []

    for tag_name in ["ul", "ol"]:
        for list_tag in soup.find_all(tag_name):
            items = [li.get_text(strip=True) for li in list_tag.find_all("li", recursive=False)]
            if items:
                lists.append(DetectedList(items=items, list_type=tag_name))

    return lists


def _extract_paragraphs(soup: BeautifulSoup) -> List[str]:
    """Extract text paragraphs."""
    paragraphs = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) > 20:  # Skip very short paragraphs
            paragraphs.append(text)
    return paragraphs


def _extract_links(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract links with text."""
    links = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if text and href and not href.startswith(("#", "javascript:")):
            links.append({"text": text, "href": href})
    return links


def _extract_images(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract images."""
    images = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src:
            images.append({"src": src, "alt": alt})
    return images


def _extract_forms(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract form structures."""
    forms = []
    for form in soup.find_all("form"):
        fields = []
        for inp in form.find_all(["input", "select", "textarea"]):
            field = {
                "type": inp.get("type", inp.name),
                "name": inp.get("name", ""),
            }
            if inp.get("placeholder"):
                field["placeholder"] = inp["placeholder"]
            if inp.get("required"):
                field["required"] = True
            fields.append(field)

        if fields:
            forms.append({
                "action": form.get("action", ""),
                "method": form.get("method", "get").upper(),
                "fields": fields,
            })

    return forms


def _classify(soup: BeautifulSoup, result: DetectedStructure) -> tuple:
    """
    Classify the page type based on detected structures.

    Returns:
        (data_type, confidence) tuple
    """
    scores = {
        "article": 0.0,
        "product": 0.0,
        "listing": 0.0,
        "table": 0.0,
        "form": 0.0,
    }

    # Article signals
    if result.paragraphs:
        scores["article"] += 0.3
    if any(h["level"] == "h1" for h in result.headings):
        scores["article"] += 0.2
    if result.meta.get("og_type") == "article":
        scores["article"] += 0.3
    if result.meta.get("author"):
        scores["article"] += 0.2

    # Product signals
    if result.meta.get("og_type") == "product":
        scores["product"] += 0.4
    price_pattern = re.compile(r'[\$€£¥]\s*\d+[\d,.]*')
    if price_pattern.search(str(soup)):
        scores["product"] += 0.3
    if soup.find(class_=re.compile(r'price|cost|amount', re.I)):
        scores["product"] += 0.3

    # Listing signals
    if len(result.lists) >= 2:
        scores["listing"] += 0.3
    if len(result.links) > 20:
        scores["listing"] += 0.3
    if soup.find(class_=re.compile(r'list|grid|catalog|results', re.I)):
        scores["listing"] += 0.2

    # Table signals
    if len(result.tables) >= 1:
        scores["table"] += 0.4
    if len(result.tables) >= 3:
        scores["table"] += 0.3

    # Form signals
    if result.forms:
        scores["form"] += 0.4
    if len(result.forms) >= 2:
        scores["form"] += 0.3

    # Find winner
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 0.2:
        return "generic", 0.3

    return best_type, min(best_score, 1.0)
