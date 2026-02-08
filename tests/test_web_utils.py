"""Tests for web utilities module."""

from unittest.mock import MagicMock, patch

import pytest

from resume_generator.utils.web import (
    FetchError,
    extract_text_from_html,
    fetch_and_extract_text,
    fetch_url_content,
)


class TestExtractTextFromHtml:
    """Tests for extract_text_from_html function."""

    def test_removes_script_tags(self) -> None:
        html = "<html><script>alert('test');</script><p>Content</p></html>"
        result = extract_text_from_html(html)
        assert "alert" not in result
        assert "Content" in result

    def test_removes_style_tags(self) -> None:
        html = "<html><style>body { color: red; }</style><p>Content</p></html>"
        result = extract_text_from_html(html)
        assert "color" not in result
        assert "Content" in result

    def test_removes_html_tags(self) -> None:
        html = "<div><p>Hello</p><span>World</span></div>"
        result = extract_text_from_html(html)
        assert "<" not in result
        assert ">" not in result
        assert "Hello" in result
        assert "World" in result

    def test_decodes_html_entities(self) -> None:
        html = "<p>A &amp; B &lt; C &gt; D &quot;E&quot;</p>"
        result = extract_text_from_html(html)
        assert "A & B < C > D" in result

    def test_handles_nbsp(self) -> None:
        html = "<p>Hello&nbsp;World</p>"
        result = extract_text_from_html(html)
        assert "Hello World" in result

    def test_normalizes_whitespace(self) -> None:
        html = "<p>Hello   \n\n   World</p>"
        result = extract_text_from_html(html)
        assert "Hello World" in result
        assert "  " not in result

    def test_strips_result(self) -> None:
        html = "   <p>Content</p>   "
        result = extract_text_from_html(html)
        assert result == "Content"

    def test_empty_html(self) -> None:
        result = extract_text_from_html("")
        assert result == ""

    def test_multiline_script(self) -> None:
        html = """<html>
        <script>
            function test() {
                return true;
            }
        </script>
        <p>Content</p>
        </html>"""
        result = extract_text_from_html(html)
        assert "function" not in result
        assert "Content" in result


class TestFetchUrlContent:
    """Tests for fetch_url_content function."""

    def test_successful_fetch(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test content</body></html>"

        with patch("resume_generator.utils.web.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = fetch_url_content("https://example.com")
            assert result == "<html><body>Test content</body></html>"

    def test_http_error(self) -> None:
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("resume_generator.utils.web.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_response
            )

            with pytest.raises(FetchError) as exc_info:
                fetch_url_content("https://example.com/404")

            assert "404" in str(exc_info.value)

    def test_request_error(self) -> None:
        import httpx

        with patch("resume_generator.utils.web.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError(
                "Connection failed"
            )

            with pytest.raises(FetchError) as exc_info:
                fetch_url_content("https://example.com")

            assert "Request failed" in str(exc_info.value)


class TestFetchAndExtractText:
    """Tests for fetch_and_extract_text function."""

    def test_fetches_and_extracts(self) -> None:
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Job Description</p></body></html>"

        with patch("resume_generator.utils.web.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = fetch_and_extract_text("https://example.com/job")
            assert "Job Description" in result
            assert "<" not in result

    def test_propagates_fetch_error(self) -> None:
        import httpx

        with patch("resume_generator.utils.web.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError(
                "Network error"
            )

            with pytest.raises(FetchError):
                fetch_and_extract_text("https://example.com")


class TestFetchError:
    """Tests for FetchError exception."""

    def test_is_exception(self) -> None:
        assert issubclass(FetchError, Exception)

    def test_stores_message(self) -> None:
        error = FetchError("Test error message")
        assert str(error) == "Test error message"
