from enum import Enum
from models.evidence import SourceTier
from tools.domain_utils import normalize_domain


class SourceType(str, Enum):
    COMPANY_WEBSITE = "company_website"
    COMPANY_ABOUT = "company_about"
    COMPANY_PRODUCT = "company_product"
    COMPANY_TEAM = "company_team"
    COMPANY_NEWS = "company_news"
    FUNDING_DATABASE = "funding_database"
    BUSINESS_DATABASE = "business_database"
    NEWS_ARTICLE = "news_article"
    LINKEDIN = "linkedin"
    GOVERNMENT = "government"
    OTHER = "other"


def classify_source_type(url: str, title: str = "", snippet: str = "") -> SourceType:
    """
    Classifies a web source into a structured SourceType based on URL and text signals.
    """
    if not url:
        return SourceType.OTHER

    url_lower = url.lower()
    domain = normalize_domain(url)
    title_lower = title.lower() if title else ""
    snippet_lower = snippet.lower() if snippet else ""

    # Government / Regulatory
    if domain.endswith((".gov", ".gov.uk", ".europa.eu", ".gov.in")) or "companieshouse.gov.uk" in domain:
        return SourceType.GOVERNMENT

    # Professional profiles / LinkedIn
    if "linkedin.com" in domain:
        return SourceType.LINKEDIN

    # Recognized Funding & Startup Databases
    funding_domains = {
        "crunchbase.com",
        "pitchbook.com",
        "tracxn.com",
        "dealroom.co",
        "cbinsights.com",
        "golden.com",
        "f6s.com",
        "ycombinator.com",
    }
    if domain in funding_domains:
        return SourceType.FUNDING_DATABASE

    # Recognized Business Directories & Databases
    business_db_domains = {
        "bloomberg.com",
        "reuters.com",
        "zoominfo.com",
        "apollo.io",
        "apollo.com",
        "dnb.com",
        "owler.com",
        "kompass.com",
    }
    if domain in business_db_domains:
        return SourceType.BUSINESS_DATABASE

    # Tech News Publications
    news_domains = {
        "techcrunch.com",
        "eu-startups.com",
        "techinasia.com",
        "venturebeat.com",
        "sifted.eu",
        "forbes.com",
        "wsj.com",
        "ft.com",
        "businessinsider.com",
        "e27.co",
    }
    if domain in news_domains or "news" in domain:
        return SourceType.NEWS_ARTICLE

    # Official Company Site Paths & Titles
    path = url_lower.replace(f"https://{domain}", "").replace(f"http://{domain}", "")
    if any(k in path for k in ["/about", "/company", "/story", "/who-we-are"]) or "about us" in title_lower:
        return SourceType.COMPANY_ABOUT

    if any(k in path for k in ["/product", "/platform", "/solution", "/features", "/pricing", "/api"]) or "product" in title_lower:
        return SourceType.COMPANY_PRODUCT

    if any(k in path for k in ["/team", "/leadership", "/management", "/founders", "/people"]) or "leadership" in title_lower or "team" in title_lower:
        return SourceType.COMPANY_TEAM

    if any(k in path for k in ["/press", "/news", "/blog", "/media", "/releases"]) or "press release" in title_lower or "news" in title_lower:
        return SourceType.COMPANY_NEWS

    # Default company website or generic
    if domain and ("about" in snippet_lower or "platform" in snippet_lower or "contact" in snippet_lower):
        return SourceType.COMPANY_WEBSITE

    return SourceType.OTHER


def get_source_tier(source_type: SourceType) -> SourceTier:
    """
    Maps a SourceType to its corresponding SourceTier ranking.
    """
    tier_1_types = {
        SourceType.COMPANY_WEBSITE,
        SourceType.COMPANY_ABOUT,
        SourceType.COMPANY_PRODUCT,
        SourceType.COMPANY_TEAM,
        SourceType.COMPANY_NEWS,
        SourceType.GOVERNMENT,
    }
    tier_2_types = {
        SourceType.FUNDING_DATABASE,
        SourceType.BUSINESS_DATABASE,
        SourceType.NEWS_ARTICLE,
    }
    tier_3_types = {
        SourceType.LINKEDIN,
    }

    if source_type in tier_1_types:
        return SourceTier.TIER_1
    elif source_type in tier_2_types:
        return SourceTier.TIER_2
    elif source_type in tier_3_types:
        return SourceTier.TIER_3
    else:
        return SourceTier.TIER_4
