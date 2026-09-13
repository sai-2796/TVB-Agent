import pytest
import requests
from unittest.mock import MagicMock, patch
from tools.web_research import (
    HTTPWebResearchProvider,
    MAX_HTML_CHARS,
    MockWebResearchProvider,
    clean_html_text,
    get_web_research_provider,
)


def test_clean_html_text():
    html_raw = """
    <html>
        <head>
            <title>Test Page</title>
            <script>var x = 10;</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <header><nav><a href="#">Home</a></nav></header>
            <main>
                <h1>TechPlatform Overview</h1>
                <p>TechPlatform operates a B2B SaaS supply chain dashboard.</p>
            </main>
            <footer><p>Copyright 2026</p></footer>
        </body>
    </html>
    """
    cleaned = clean_html_text(html_raw)
    assert "var x = 10" not in cleaned
    assert "body { color: red; }" not in cleaned
    assert "Home" not in cleaned  # Nav stripped
    assert "Copyright 2026" not in cleaned  # Footer stripped
    assert "TechPlatform Overview" in cleaned
    assert "TechPlatform operates a B2B SaaS supply chain dashboard." in cleaned


def test_clean_html_text_bounds_oversized_documents():
    html_raw = "<p>kept</p>" + ("x" * MAX_HTML_CHARS) + "<p>discarded</p>"

    cleaned = clean_html_text(html_raw)

    assert "kept" in cleaned
    assert "discarded" not in cleaned


def test_http_web_research_provider_success():
    provider = HTTPWebResearchProvider(timeout=5)
    html_content = """
    <html>
        <head>
            <title>Company About Page</title>
            <meta name="date" content="2024-05-10" />
        </head>
        <body>
            <p>Our company raised $2.5M funding in 2024.</p>
        </body>
    </html>
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_res.text = html_content
    mock_res.encoding = "utf-8"
    mock_res.iter_content.return_value = [html_content.encode("utf-8")]

    with patch("requests.get", return_value=mock_res):
        res = provider.fetch("https://techplatform.io/about")
        assert res["is_accessible"] is True
        assert res["status_code"] == 200
        assert res["page_title"] == "Company About Page"
        assert res["source_domain"] == "techplatform.io"
        assert "raised $2.5M funding" in res["main_text"]
        assert res["published_date"] == "2024-05-10"


def test_http_web_research_provider_bounds_all_html_parsing():
    provider = HTTPWebResearchProvider(timeout=5)
    html_content = "<html><body>kept</body></html>" + ("x" * MAX_HTML_CHARS) + "<title>discarded</title>"
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_res.text = html_content
    mock_res.encoding = "utf-8"
    mock_res.iter_content.return_value = [html_content.encode("utf-8")]

    with patch("requests.get", return_value=mock_res):
        res = provider.fetch("https://techplatform.io/oversized")

    assert res["is_accessible"] is True
    assert "kept" in res["main_text"]
    assert "discarded" not in res["page_title"]


def test_http_web_research_provider_failures():
    provider = HTTPWebResearchProvider(timeout=5)

    # 403 Forbidden / Bot Protection -> Returns accessible=False with reason
    mock_403 = MagicMock()
    mock_403.status_code = 403
    with patch("requests.get", return_value=mock_403):
        res = provider.fetch("https://protected.com")
        assert res["is_accessible"] is False
        assert res["status_code"] == 403
        assert "Access denied" in res["error_reason"]

    # Invalid scheme -> Returns accessible=False
    res_inv = provider.fetch("not_a_valid_url")
    assert res_inv["is_accessible"] is False
    assert "Invalid or missing HTTP scheme" in res_inv["error_reason"]


@pytest.mark.parametrize("failure", ["http", "timeout"])
def test_http_web_research_provider_handles_source_failure(failure):
    provider = HTTPWebResearchProvider(timeout=1)
    if failure == "http":
        response = MagicMock(status_code=400)
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("400")
        side_effect = response
    else:
        side_effect = requests.exceptions.Timeout("timed out")

    if failure == "http":
        with patch("requests.get", return_value=side_effect):
            result = provider.fetch("https://broken.example/source")
    else:
        with patch("requests.get", side_effect=side_effect):
            result = provider.fetch("https://broken.example/source")

    assert result["is_accessible"] is False
    assert result["status_code"] in (0, 400)


def test_mock_web_research_provider():
    mock_provider = MockWebResearchProvider()
    res = mock_provider.fetch("https://example.com/test")
    assert res["is_accessible"] is True
    assert res["source_domain"] == "example.com"
