"""
Phase 6 tests: Auto-detect + Pagination + Webhook + Export.
"""

import pytest

from src.scraper.auto_detect import detect_structure, DetectedStructure
from src.scraper.pagination import (
    detect_pagination,
    build_page_url,
    get_next_page_url,
    PaginationResult,
)


# ══════════════════════════════════════════════════════════════════════
# Auto-Detect Tests
# ══════════════════════════════════════════════════════════════════════

class TestAutoDetect:
    """Test HTML structure auto-detection."""

    def test_empty_html(self):
        """Empty input returns empty type."""
        result = detect_structure("")
        assert result.data_type == "empty"
        assert result.confidence == 0.0

    def test_detect_title(self):
        """Should extract page title."""
        html = "<html><head><title>My Page</title></head><body></body></html>"
        result = detect_structure(html)
        assert result.title == "My Page"

    def test_detect_og_title(self):
        """Should fallback to og:title."""
        html = '<html><head><meta property="og:title" content="OG Title"></head><body></body></html>'
        result = detect_structure(html)
        assert result.title == "OG Title"

    def test_detect_h1_title(self):
        """Should fallback to first h1."""
        html = "<html><body><h1>H1 Title</h1></body></html>"
        result = detect_structure(html)
        assert result.title == "H1 Title"

    def test_detect_meta_tags(self):
        """Should extract meta properties."""
        html = """
        <html><head>
            <meta property="og:description" content="A description">
            <meta name="author" content="John Doe">
        </head><body></body></html>
        """
        result = detect_structure(html)
        assert result.meta.get("og_description") == "A description"
        assert result.meta.get("author") == "John Doe"

    def test_detect_headings(self):
        """Should extract all heading levels."""
        html = """
        <html><body>
            <h1>Title</h1>
            <h2>Subtitle 1</h2>
            <h2>Subtitle 2</h2>
            <h3>Section</h3>
        </body></html>
        """
        result = detect_structure(html)
        assert len(result.headings) == 4
        assert result.headings[0] == {"level": "h1", "text": "Title"}

    def test_detect_table(self):
        """Should extract HTML tables."""
        html = """
        <html><body>
            <table>
                <caption>Products</caption>
                <thead><tr><th>Name</th><th>Price</th></tr></thead>
                <tbody>
                    <tr><td>Widget</td><td>$10</td></tr>
                    <tr><td>Gadget</td><td>$20</td></tr>
                </tbody>
            </table>
        </body></html>
        """
        result = detect_structure(html)
        assert len(result.tables) == 1
        table = result.tables[0]
        assert table.caption == "Products"
        assert table.headers == ["Name", "Price"]
        assert table.row_count == 2
        assert table.col_count == 2

    def test_detect_list(self):
        """Should extract ul/ol lists."""
        html = """
        <html><body>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
                <li>Item 3</li>
            </ul>
        </body></html>
        """
        result = detect_structure(html)
        assert len(result.lists) == 1
        assert result.lists[0].items == ["Item 1", "Item 2", "Item 3"]
        assert result.lists[0].list_type == "ul"

    def test_detect_links(self):
        """Should extract links."""
        html = """
        <html><body>
            <a href="https://example.com">Example</a>
            <a href="/page">Internal</a>
            <a href="#anchor">Anchor</a>
        </body></html>
        """
        result = detect_structure(html)
        # Anchor links are filtered
        assert len(result.links) == 2

    def test_detect_images(self):
        """Should extract images."""
        html = """
        <html><body>
            <img src="/photo.jpg" alt="Photo">
            <img src="/logo.png" alt="Logo">
        </body></html>
        """
        result = detect_structure(html)
        assert len(result.images) == 2
        assert result.images[0]["src"] == "/photo.jpg"

    def test_classify_article(self):
        """Article page should be classified correctly."""
        html = """
        <html><head>
            <meta property="og:type" content="article">
            <meta name="author" content="John">
        </head><body>
            <h1>Article Title</h1>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt.</p>
            <p>Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip.</p>
        </body></html>
        """
        result = detect_structure(html)
        assert result.data_type == "article"
        assert result.confidence > 0.5

    def test_classify_table(self):
        """Table-heavy page should be classified as table."""
        html = """
        <html><body>
            <table><thead><tr><th>A</th><th>B</th></tr></thead>
            <tbody><tr><td>1</td><td>2</td></tr></tbody></table>
            <table><thead><tr><th>C</th><th>D</th></tr></thead>
            <tbody><tr><td>3</td><td>4</td></tr></tbody></table>
            <table><thead><tr><th>E</th><th>F</th></tr></thead>
            <tbody><tr><td>5</td><td>6</td></tr></tbody></table>
        </body></html>
        """
        result = detect_structure(html)
        assert result.data_type == "table"

    def test_to_dict(self):
        """to_dict should return clean API-friendly output."""
        html = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
        result = detect_structure(html)
        d = result.to_dict()
        assert "data_type" in d
        assert "confidence" in d
        assert d["title"] == "Test"


# ══════════════════════════════════════════════════════════════════════
# Pagination Tests
# ══════════════════════════════════════════════════════════════════════

class TestPagination:
    """Test pagination detection."""

    def test_no_pagination(self):
        """Page without pagination should return empty result."""
        html = "<html><body><p>No pagination here</p></body></html>"
        result = detect_pagination(html, "https://example.com")
        assert result.has_next is False
        assert result.next_url is None

    def test_rel_next_link(self):
        """Should detect rel=next link."""
        html = """
        <html><head>
            <link rel="next" href="/page/2">
        </head><body></body></html>
        """
        result = detect_pagination(html, "https://example.com")
        assert result.has_next is True
        assert result.next_url == "https://example.com/page/2"

    def test_rel_prev_link(self):
        """Should detect rel=prev link."""
        html = """
        <html><head>
            <link rel="prev" href="/page/1">
        </head><body></body></html>
        """
        result = detect_pagination(html, "https://example.com")
        assert result.prev_url == "https://example.com/page/1"

    def test_text_next_link(self):
        """Should detect 'Next' text links."""
        html = """
        <html><body>
            <a href="/page/2">Next</a>
        </body></html>
        """
        result = detect_pagination(html, "https://example.com")
        assert result.has_next is True
        assert result.next_url == "https://example.com/page/2"

    def test_arrow_next_link(self):
        """Should detect arrow symbols as next."""
        html = """
        <html><body>
            <a href="/page/2">»</a>
        </body></html>
        """
        result = detect_pagination(html, "https://example.com")
        assert result.has_next is True

    def test_numbered_pagination(self):
        """Should detect numbered page links."""
        html = """
        <html><body>
            <nav class="pagination">
                <a href="/page/1">1</a>
                <a href="/page/2">2</a>
                <a href="/page/3">3</a>
            </nav>
        </body></html>
        """
        result = detect_pagination(html, "https://example.com")
        assert result.pagination_type == "numbered"
        assert len(result.page_urls) >= 3

    def test_page_in_query_param(self):
        """Should detect page number from query params."""
        html = """
        <html><body>
            <a href="/search?page=5">5</a>
        </body></html>
        """
        result = detect_pagination(html, "https://example.com")
        found = [l for l in result.page_urls if l.page_number == 5]
        assert len(found) == 1

    def test_build_page_url(self):
        """build_page_url should construct correct URL."""
        url = build_page_url("https://example.com/search?q=test", 3)
        assert "page=3" in url
        assert "q=test" in url

    def test_get_next_page_url(self):
        """get_next_page_url helper should work."""
        html = '<html><head><link rel="next" href="/page/2"></head></html>'
        result = detect_pagination(html, "https://example.com")
        assert get_next_page_url(result) == "https://example.com/page/2"

    def test_pagination_class_based(self):
        """Should detect pagination from CSS class."""
        html = """
        <html><body>
            <div class="page-nav">
                <a href="/page/1">1</a>
                <a href="/page/2" class="active">2</a>
                <a href="/page/3">3</a>
            </div>
        </body></html>
        """
        result = detect_pagination(html, "https://example.com")
        assert len(result.page_urls) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
