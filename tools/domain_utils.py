from urllib.parse import urlparse


def normalize_domain(url_or_domain: str | None) -> str:
    """
    Normalizes a URL or domain string into a clean root canonical domain.
    Strips protocol, paths, query params, port numbers, and leading 'www.'.
    """
    if not url_or_domain or not isinstance(url_or_domain, str):
        return ""

    cleaned = url_or_domain.strip().lower()

    # Prepend scheme if missing so urlparse parses hostname properly
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned

    try:
        parsed = urlparse(cleaned)
        hostname = parsed.hostname or ""
    except Exception:
        hostname = cleaned

    # Strip port if present
    if ":" in hostname:
        hostname = hostname.split(":")[0]

    # Strip leading 'www.'
    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname
