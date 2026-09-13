import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from models.discovery import DiscoveredCandidate
from tools.domain_utils import normalize_domain
from tools.interfaces import SearchResult

THIRD_PARTY_DIRECTORY_DOMAINS = {
    "crunchbase.com",
    "pitchbook.com",
    "linkedin.com",
    "techcrunch.com",
    "ycombinator.com",
    "producthunt.com",
    "f6s.com",
    "tracxn.com",
    "dealroom.co",
    "bloomberg.com",
    "reuters.com",
    "forbes.com",
    "medium.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "youtube.com",
    "github.com",
    "wikipedia.org",
    "google.com",
    "bing.com",
    "yahoo.com",
    "news.ycombinator.com",
    "eu-startups.com",
    "techinasia.com",
    "e27.co",
}


def sanitize_company_name(raw_name: str) -> str:
    """Cleans up search title snippets to extract clean company entity names."""
    if not raw_name:
        return ""

    cleaned = raw_name.strip()

    # Remove standard site suffixes
    suffix_patterns = [
        r"\s*\|\s*Crunchbase.*$",
        r"\s*\|\s*LinkedIn.*$",
        r"\s*-\s*Product Hunt.*$",
        r"\s*-\s*TechCrunch.*$",
        r"\s*\|\s*EU-Startups.*$",
        r"\s*-\s*Wikipedia.*$",
        r"\s*:\s*Overview.*$",
        r"\s*raises?\s+\$?\d+.*$",
        r"\s*secures?\s+\$?\d+.*$",
    ]
    for pattern in suffix_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # If format is "Company Name - Short Description", take the first part
    if " - " in cleaned:
        parts = cleaned.split(" - ")
        if len(parts[0].strip()) > 1 and len(parts[0].strip()) < 50:
            cleaned = parts[0].strip()

    if ":" in cleaned:
        parts = cleaned.split(":")
        if len(parts[0].strip()) > 1 and len(parts[0].strip()) < 50:
            cleaned = parts[0].strip()

    return cleaned.strip()


def extract_domain_from_text(text: str) -> Optional[str]:
    """Attempts to find a domain string (e.g. example.io) mentioned explicitly in text."""
    if not text:
        return None

    domain_match = re.search(r"\b([a-zA-Z0-9-]+\.(?:com|io|ai|co|org|net|de|uk|eu|fr|es|br|mx))\b", text.lower())
    if domain_match:
        found_domain = domain_match.group(1)
        if found_domain not in THIRD_PARTY_DIRECTORY_DOMAINS:
            return normalize_domain(found_domain)

    return None


class CandidateExtractor:
    """Extracts candidate companies and computes lightweight discovery priority scores."""

    @classmethod
    def extract_candidate(
        cls, result: SearchResult, hypothesis: str, sector_hint: Optional[str] = None, geo_hint: Optional[str] = None
    ) -> Optional[DiscoveredCandidate]:
        if not result or not result.url:
            return None

        raw_domain = normalize_domain(result.url)

        # Canonical domain determination
        company_domain: Optional[str] = None
        if raw_domain and raw_domain not in THIRD_PARTY_DIRECTORY_DOMAINS:
            company_domain = raw_domain
        else:
            # Try to extract explicit domain from title/snippet
            text_to_search = f"{result.title} {result.snippet}"
            company_domain = extract_domain_from_text(text_to_search)

        # Company Name Extraction
        company_name = sanitize_company_name(result.title)
        if not company_name or len(company_name) < 2:
            if company_domain:
                company_name = company_domain.split(".")[0].capitalize()
            else:
                return None

        # Compute lightweight discovery priority score (NOT qualification score)
        score = 0.5
        text_lower = f"{result.title} {result.snippet}".lower()

        if company_domain:
            score += 0.2
        if any(k in text_lower for k in ["funding", "raised", "seed", "series a", "revenue", "$1m", "$2m", "$3m", "$4m", "$5m"]):
            score += 0.2
        if any(k in text_lower for k in ["platform", "saas", "software", "b2b", "api", "cloud"]):
            score += 0.1

        score = min(1.0, score)

        return DiscoveredCandidate(
            candidate_id=f"cand_{uuid.uuid4().hex[:10]}",
            company_name=company_name,
            company_domain=company_domain,
            discovery_source_url=result.url,
            discovery_source_title=result.title,
            discovery_snippet=result.snippet,
            discovery_timestamp=datetime.now(timezone.utc).isoformat(),
            discovery_hypothesis=hypothesis,
            discovery_score=score,
            sector_hint=sector_hint,
            geo_hint=geo_hint,
        )
