import logging
import re
import time
import requests
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from bs4 import BeautifulSoup
from config.settings import Settings, get_settings
from tools.domain_utils import normalize_domain
from tools.interfaces import WebResearchProvider

logger = logging.getLogger("tvb_agent.web_research")
MAX_HTML_CHARS = 250_000


def clean_html_text(html_content: str) -> str:
    """
    Extracts clean, readable research text from raw HTML content.
    Strips scripts, styles, header/footer navigation, boilerplate elements,
    and consolidates excessive white space.
    """
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content[:MAX_HTML_CHARS], "lxml")

    # Remove non-content tags
    for tag in soup(["script", "style", "nav", "header", "footer", "form", "aside", "noscript", "svg"]):
        tag.decompose()

    # Extract clean text from remaining elements
    text = soup.get_text(separator=" ")

    # Collapse multiple spaces and line breaks
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_page_title(soup: BeautifulSoup) -> str:
    """Extracts clean page title from HTML title tag or og:title meta."""
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    return ""


def extract_published_date(soup: BeautifulSoup) -> Optional[str]:
    """Extracts publication date from meta tags or time element if available."""
    # Check meta tags
    meta_date_keys = [
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "publication_date"}),
        ("meta", {"name": "date"}),
        ("meta", {"name": "parsely-pub-date"}),
    ]
    for tag_name, attrs in meta_date_keys:
        element = soup.find(tag_name, attrs)
        if element and element.get("content"):
            return element["content"].strip()

    # Check <time> tag
    time_element = soup.find("time")
    if time_element and time_element.get("datetime"):
        return time_element["datetime"].strip()

    return None


class MockWebResearchProvider(WebResearchProvider):
    """Mock implementation of WebResearchProvider for testing."""

    def __init__(self, mock_responses: Optional[Dict[str, Dict[str, Any]]] = None):
        self.mock_responses = mock_responses or {}

    def fetch(self, url: str) -> Dict[str, Any]:
        if url in self.mock_responses:
            return self.mock_responses[url]
        return {
            "url": url,
            "page_title": "Mock Title",
            "main_text": f"Mock page content for {url}",
            "status_code": 200,
            "source_domain": normalize_domain(url),
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "published_date": None,
            "is_accessible": True,
            "error_reason": None,
        }


class HTTPWebResearchProvider(WebResearchProvider):
    """Concrete WebResearchProvider utilizing HTTP requests and HTML parsing."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36 TVBAgent/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, timeout: int = 10, headers: Optional[Dict[str, str]] = None):
        self.timeout = timeout
        self.headers = headers or self.DEFAULT_HEADERS

    def _read_bounded_response(self, response: requests.Response) -> str:
        deadline = time.monotonic() + self.timeout
        chunks = []
        total_bytes = 0

        try:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if time.monotonic() >= deadline:
                    raise requests.exceptions.Timeout(
                        f"Response body exceeded {self.timeout}s deadline"
                    )
                if not chunk:
                    continue
                remaining = MAX_HTML_CHARS - total_bytes
                if remaining <= 0:
                    break
                chunk_bytes = chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
                chunks.append(chunk_bytes[:remaining])
                total_bytes += min(len(chunk_bytes), remaining)
                if total_bytes >= MAX_HTML_CHARS:
                    break

            encoding = response.encoding or "utf-8"
            return b"".join(chunks).decode(encoding, errors="replace")
        finally:
            response.close()

    def fetch(self, url: str) -> Dict[str, Any]:
        accessed_at = datetime.now(timezone.utc).isoformat()
        domain = normalize_domain(url)

        if not url or not url.startswith(("http://", "https://")):
            logger.warning(f"HTTPWebResearchProvider: Invalid URL '{url}'")
            return {
                "url": url,
                "page_title": "",
                "main_text": "",
                "status_code": 0,
                "source_domain": domain,
                "accessed_at": accessed_at,
                "published_date": None,
                "is_accessible": False,
                "error_reason": "Invalid or missing HTTP scheme in URL",
            }

        try:
            logger.info(f"HTTPWebResearchProvider fetching URL: '{url}'")
            response = requests.get(
                url,
                headers=self.headers,
                timeout=(self.timeout, self.timeout),
                allow_redirects=True,
                stream=True,
            )

            status_code = response.status_code
            if status_code in (401, 403):
                logger.warning(f"Access denied (HTTP {status_code}) for URL: '{url}'")
                return {
                    "url": url,
                    "page_title": "",
                    "main_text": "",
                    "status_code": status_code,
                    "source_domain": domain,
                    "accessed_at": accessed_at,
                    "published_date": None,
                    "is_accessible": False,
                    "error_reason": f"Access denied (HTTP {status_code}) - authentication/bot protection required",
                }

            if status_code == 404:
                logger.warning(f"Page not found (HTTP 404) for URL: '{url}'")
                return {
                    "url": url,
                    "page_title": "",
                    "main_text": "",
                    "status_code": status_code,
                    "source_domain": domain,
                    "accessed_at": accessed_at,
                    "published_date": None,
                    "is_accessible": False,
                    "error_reason": "Page not found (HTTP 404)",
                }

            response.raise_for_status()
            response_text = self._read_bounded_response(response)
            content_type = response.headers.get("Content-Type", "")

            # Ensure we are parsing text HTML
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                logger.info(f"Non-HTML content type '{content_type}' for URL: '{url}'")
                raw_text = response_text[:2000]
                return {
                    "url": url,
                    "page_title": "",
                    "main_text": raw_text,
                    "status_code": status_code,
                    "source_domain": domain,
                    "accessed_at": accessed_at,
                    "published_date": None,
                    "is_accessible": True,
                    "error_reason": None,
                }

            bounded_html = response_text
            soup = BeautifulSoup(bounded_html, "lxml")
            page_title = extract_page_title(soup)
            published_date = extract_published_date(soup)
            main_text = clean_html_text(bounded_html)

            logger.info(f"Successfully fetched and parsed page '{url}' ({len(main_text)} chars extracted)")
            return {
                "url": url,
                "page_title": page_title,
                "main_text": main_text,
                "status_code": status_code,
                "source_domain": domain,
                "accessed_at": accessed_at,
                "published_date": published_date,
                "is_accessible": True,
                "error_reason": None,
            }

        except requests.exceptions.Timeout:
            logger.error(f"HTTPWebResearchProvider timeout fetching URL: '{url}'")
            return {
                "url": url,
                "page_title": "",
                "main_text": "",
                "status_code": 0,
                "source_domain": domain,
                "accessed_at": accessed_at,
                "published_date": None,
                "is_accessible": False,
                "error_reason": f"Connection timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as exc:
            logger.error(f"HTTPWebResearchProvider request error fetching '{url}': {exc}")
            return {
                "url": url,
                "page_title": "",
                "main_text": "",
                "status_code": 0,
                "source_domain": domain,
                "accessed_at": accessed_at,
                "published_date": None,
                "is_accessible": False,
                "error_reason": f"Network request failure: {str(exc)}",
            }
        except Exception as exc:
            logger.error(f"HTTPWebResearchProvider unexpected error fetching '{url}': {exc}")
            return {
                "url": url,
                "page_title": "",
                "main_text": "",
                "status_code": 0,
                "source_domain": domain,
                "accessed_at": accessed_at,
                "published_date": None,
                "is_accessible": False,
                "error_reason": f"Unexpected parsing error: {str(exc)}",
            }


def get_web_research_provider(
    provider_name: Optional[str] = None, settings: Optional[Settings] = None
) -> WebResearchProvider:
    """Factory function instantiating the WebResearchProvider."""
    app_settings = settings or get_settings()
    timeout = app_settings.request_timeout_seconds
    p_name = (provider_name or "http").lower()

    if p_name == "mock":
        return MockWebResearchProvider()
    return HTTPWebResearchProvider(timeout=timeout)
