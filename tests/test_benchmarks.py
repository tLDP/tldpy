"""Performance benchmarks for tldpy view utilities."""

import pytest
from unittest.mock import patch

import sys
import os

# Add the tldpy app directory so Django modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tldpy"))

# Configure Django settings before importing any Django code
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tldp.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "benchmark-secret-key")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///dev.db")

import django

django.setup()

from tldp.views import (
    decode_content,
    extract_breadcrumbs,
    extract_title,
    get_category_for_key,
    render_search_results,
)

# ---------------------------------------------------------------------------
# Fixtures: realistic HTML payloads
# ---------------------------------------------------------------------------

SMALL_HTML = (
    "<html><head><title>3-Button Mouse HOWTO</title></head>"
    "<body><h1>3-Button Mouse HOWTO</h1><p>Short document.</p></body></html>"
)

LARGE_HTML = (
    "<html><head><title>Bash Beginners Guide</title></head><body>"
    "<h1>Bash Beginners Guide</h1>"
    + "".join(
        f"<h2>Chapter {i}</h2><p>{'Lorem ipsum dolor sit amet. ' * 40}</p>"
        for i in range(50)
    )
    + "</body></html>"
)

HTML_NO_TITLE = (
    "<html><head></head><body><h1>Untitled Document</h1>"
    "<p>Content without a title tag.</p></body></html>"
)

LDPLIST_DATA = {
    "HOWTO": [f"howto-{i}" for i in range(464)],
    "Guides": [f"guide-{i}" for i in range(22)],
    "FAQs": [f"faq-{i}" for i in range(4)],
}

SEARCH_RESULTS = [
    {
        "key": f"doc-{i}",
        "title": f"Document Title {i}",
        "url": f"/en/doc-{i}/",
        "category": "HOWTO" if i % 3 == 0 else ("Guides" if i % 3 == 1 else "FAQs"),
    }
    for i in range(50)
]


# ---------------------------------------------------------------------------
# decode_content
# ---------------------------------------------------------------------------


def test_bench_decode_content_bytes(benchmark):
    """Benchmark decoding byte content to string."""
    payload = LARGE_HTML.encode("latin-1")
    benchmark(decode_content, payload)


def test_bench_decode_content_str(benchmark):
    """Benchmark passthrough when content is already a string."""
    benchmark(decode_content, LARGE_HTML)


# ---------------------------------------------------------------------------
# extract_title
# ---------------------------------------------------------------------------


def test_bench_extract_title_small(benchmark):
    """Benchmark title extraction from a small HTML document."""
    result = benchmark(extract_title, SMALL_HTML)
    assert result == "3-Button Mouse HOWTO"


def test_bench_extract_title_large(benchmark):
    """Benchmark title extraction from a large HTML document."""
    result = benchmark(extract_title, LARGE_HTML)
    assert result == "Bash Beginners Guide"


def test_bench_extract_title_missing(benchmark):
    """Benchmark title extraction when no <title> tag is present."""
    result = benchmark(extract_title, HTML_NO_TITLE)
    assert result is None


# ---------------------------------------------------------------------------
# extract_breadcrumbs
# ---------------------------------------------------------------------------


def test_bench_extract_breadcrumbs_small(benchmark):
    """Benchmark breadcrumb extraction from a small HTML document."""
    result = benchmark(extract_breadcrumbs, SMALL_HTML)
    assert len(result) == 1
    assert result[0]["name"] == "3-Button Mouse HOWTO"


def test_bench_extract_breadcrumbs_large(benchmark):
    """Benchmark breadcrumb extraction from a large HTML document."""
    result = benchmark(extract_breadcrumbs, LARGE_HTML)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# get_category_for_key
# ---------------------------------------------------------------------------


@patch("tldp.views.get_ldplist", return_value=LDPLIST_DATA)
def test_bench_get_category_first_match(mock_ldp, benchmark):
    """Benchmark category lookup - key found early in the first category."""
    result = benchmark(get_category_for_key, "en", "howto-0")
    assert result == "HOWTO"


@patch("tldp.views.get_ldplist", return_value=LDPLIST_DATA)
def test_bench_get_category_last_match(mock_ldp, benchmark):
    """Benchmark category lookup - key found in the last category."""
    result = benchmark(get_category_for_key, "en", "faq-3")
    assert result == "FAQs"


@patch("tldp.views.get_ldplist", return_value=LDPLIST_DATA)
def test_bench_get_category_miss(mock_ldp, benchmark):
    """Benchmark category lookup - key not found in any category."""
    result = benchmark(get_category_for_key, "en", "nonexistent-key")
    assert result is None


# ---------------------------------------------------------------------------
# render_search_results
# ---------------------------------------------------------------------------


def test_bench_render_search_results_many(benchmark):
    """Benchmark rendering 50 search results into HTML."""
    result = benchmark(render_search_results, "bash", SEARCH_RESULTS)
    assert "bash" in result


def test_bench_render_search_results_empty(benchmark):
    """Benchmark rendering empty search results."""
    result = benchmark(render_search_results, "nothing", [])
    assert "No results found" in result
