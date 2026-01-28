"""Web utilities for fetching and processing web content."""

from __future__ import annotations

import re

import httpx


class FetchError(Exception):
    """Raised when URL fetching fails."""


def fetch_url_content(url: str, timeout: float = 30.0) -> str:
    """Fetch content from a URL.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        The raw content from the URL.

    Raises:
        FetchError: If the fetch fails.
    """
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; ResumeGen/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        raise FetchError(f"HTTP {e.response.status_code}: {url}") from e
    except httpx.RequestError as e:
        raise FetchError(f"Request failed: {e}") from e


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML content.

    Removes script/style tags, HTML tags, and decodes common HTML entities.

    Args:
        html: Raw HTML content.

    Returns:
        Cleaned plain text.
    """
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_and_extract_text(url: str, timeout: float = 30.0) -> str:
    """Fetch a URL and extract plain text from HTML content.

    Args:
        url: The URL to fetch.
        timeout: Request timeout in seconds.

    Returns:
        Extracted plain text from the URL.

    Raises:
        FetchError: If the fetch fails.
    """
    html = fetch_url_content(url, timeout=timeout)
    return extract_text_from_html(html)
