from models.evidence import SourceTier, FreshnessStatus, VerificationMethod
from tools.evidence_extractor import EvidenceExtractor
from tools.source_classifier import SourceType, classify_source_type, get_source_tier


def test_classify_source_type_and_tier():
    # Government
    st_gov = classify_source_type("https://companieshouse.gov.uk/company/12345")
    assert st_gov == SourceType.GOVERNMENT
    assert get_source_tier(st_gov) == SourceTier.TIER_1

    # Funding DB
    st_cb = classify_source_type("https://www.crunchbase.com/organization/techplatform")
    assert st_cb == SourceType.FUNDING_DATABASE
    assert get_source_tier(st_cb) == SourceTier.TIER_2

    # News Article
    st_tc = classify_source_type("https://techcrunch.com/2024/05/10/techplatform-funding/")
    assert st_tc == SourceType.NEWS_ARTICLE
    assert get_source_tier(st_tc) == SourceTier.TIER_2

    # Company About page
    st_about = classify_source_type("https://techplatform.io/about", title="About Us - TechPlatform")
    assert st_about == SourceType.COMPANY_ABOUT
    assert get_source_tier(st_about) == SourceTier.TIER_1


def test_evidence_extractor_success():
    page_data = {
        "url": "https://techplatform.io/press/seed-round",
        "page_title": "TechPlatform Raises $2.5M Seed Round",
        "main_text": "TechPlatform Ltd today announced a $2.5M Seed funding round led by TVB Ventures.",
        "published_date": "2024-05-10",
        "accessed_at": "2026-09-13T00:00:00Z",
        "is_accessible": True,
    }

    evidence = EvidenceExtractor.create_evidence(
        field="financials",
        page_data=page_data,
        raw_claim="Raised $2.5M Seed funding round",
        evidence_text="TechPlatform Ltd today announced a $2.5M Seed funding round led by TVB Ventures.",
        value=2500000.0,
        confidence=0.95,
        verification_method=VerificationMethod.DIRECT_EXTRACTION,
    )

    assert evidence is not None
    assert evidence.field == "financials"
    assert evidence.value == 2500000.0
    assert evidence.source_url == "https://techplatform.io/press/seed-round"
    assert evidence.source_title == "TechPlatform Raises $2.5M Seed Round"
    assert evidence.source_tier == SourceTier.TIER_1  # company_news page on company site
    assert evidence.confidence == 0.95
    assert evidence.freshness_status == FreshnessStatus.CURRENT
    assert evidence.source_published_date == "2024-05-10"


def test_evidence_extractor_suppression_on_missing_or_failed_data():
    # Inaccessible page -> returns None (NO fake evidence hallucinated!)
    inaccessible_page = {
        "url": "https://techplatform.io/private",
        "page_title": "403 Forbidden",
        "main_text": "",
        "is_accessible": False,
    }

    ev_inaccessible = EvidenceExtractor.create_evidence(
        field="financials",
        page_data=inaccessible_page,
        raw_claim="Claim",
        evidence_text="Snippet",
        confidence=0.9,
    )
    assert ev_inaccessible is None

    # Empty evidence snippet -> returns None (NO empty evidence created!)
    page_data = {
        "url": "https://techplatform.io/about",
        "page_title": "About Us",
        "main_text": "Page content",
        "is_accessible": True,
    }

    ev_empty_text = EvidenceExtractor.create_evidence(
        field="executive",
        page_data=page_data,
        raw_claim="CEO is Alex Smith",
        evidence_text="",  # Empty snippet
        confidence=0.9,
    )
    assert ev_empty_text is None
