from tools.domain_utils import normalize_domain


def test_domain_normalization():
    urls = [
        "https://www.example.com/",
        "https://example.com/about",
        "http://www.example.com/page",
        "www.example.com",
        "http://example.com:8080/test",
        "example.com",
    ]

    expected = "example.com"
    for url in urls:
        normalized = normalize_domain(url)
        assert normalized == expected, f"Failed for {url}: got {normalized}"


def test_subdomain_preservation():
    assert normalize_domain("https://app.subdomain.example.com/login") == "app.subdomain.example.com"
    assert normalize_domain("www.app.example.co.uk/test") == "app.example.co.uk"
