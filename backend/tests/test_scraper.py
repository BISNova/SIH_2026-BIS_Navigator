import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.kb_updater.scraper import (
    compute_content_hash,
    extract_main_text,
    has_content_changed,
    fetch_page,
    FetchedPage,
)

SAMPLE_HTML = """
<html>
<head><script>var x = 1;</script><style>.a{color:red}</style></head>
<body>
<nav>Home | About | Contact</nav>
<header>Site Header</header>
<main>
  <h1>Products Under Compulsory Certification</h1>
  <p>This page lists products requiring mandatory BIS certification.</p>
</main>
<footer>Copyright 2026</footer>
</body>
</html>
"""


def test_extract_main_text_strips_nav_and_scripts():
    text = extract_main_text(SAMPLE_HTML)
    assert "Products Under Compulsory Certification" in text
    assert "mandatory BIS certification" in text
    assert "Home | About | Contact" not in text
    assert "color:red" not in text
    assert "Copyright 2026" not in text


def test_content_hash_is_deterministic():
    text = "Domestic Pressure Cooker scope summary."
    assert compute_content_hash(text) == compute_content_hash(text)


def test_content_hash_ignores_whitespace_differences():
    """Real pages often have trivial whitespace/formatting churn between
    fetches that isn't a real content change - the hash should be
    stable across that, or every scrape would falsely flag a change."""
    text1 = "Domestic   Pressure Cooker\n\nscope summary."
    text2 = "Domestic Pressure Cooker scope summary."
    assert compute_content_hash(text1) == compute_content_hash(text2)


def test_content_hash_changes_with_real_content_change():
    hash1 = compute_content_hash("scope covers pressure cookers up to 5 litres")
    hash2 = compute_content_hash("scope covers pressure cookers up to 10 litres")
    assert hash1 != hash2


def test_has_content_changed_true_when_never_seen_before():
    fetched = FetchedPage(url="https://example.com", text_content="x", content_hash="abc123")
    assert has_content_changed(fetched, stored_content_hash=None) is True


def test_has_content_changed_false_when_hash_matches():
    fetched = FetchedPage(url="https://example.com", text_content="x", content_hash="abc123")
    assert has_content_changed(fetched, stored_content_hash="abc123") is False


def test_has_content_changed_true_when_hash_differs():
    fetched = FetchedPage(url="https://example.com", text_content="x", content_hash="new-hash")
    assert has_content_changed(fetched, stored_content_hash="old-hash") is True


def test_fetch_page_parses_response_correctly():
    """Network call itself is mocked - see scraper.py's module docstring
    for why this exact call can't be exercised live from this sandbox."""
    mock_response = mock.Mock()
    mock_response.text = SAMPLE_HTML
    mock_response.raise_for_status = mock.Mock()

    with mock.patch("backend.kb_updater.scraper.requests.get", return_value=mock_response) as mock_get:
        result = fetch_page("https://www.bis.gov.in/product-certification/products-under-compulsory-certification/")

        assert "Products Under Compulsory Certification" in result.text_content
        assert result.content_hash == compute_content_hash(result.text_content)
        mock_get.assert_called_once()
        # confirms a real User-Agent is sent, not a default that some
        # servers block
        assert "headers" in mock_get.call_args.kwargs


def test_fetch_page_raises_on_http_error():
    mock_response = mock.Mock()
    mock_response.raise_for_status.side_effect = Exception("404 Not Found")

    with mock.patch("backend.kb_updater.scraper.requests.get", return_value=mock_response):
        try:
            fetch_page("https://example.com/missing")
            assert False, "should have raised"
        except Exception as e:
            assert "404" in str(e)
