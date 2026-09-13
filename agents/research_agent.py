import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
from models.discovery import DiscoveredCandidate
from models.company import CompanyResearch
from models.evidence import Evidence, VerificationMethod
from models.financial import FinancialsData, FinancialType
from models.us_presence import USPresenceData, USPresenceStatus
from models.executive import ExecutiveProfile, ExecutiveRole
from tools.interfaces import SearchProvider, WebResearchProvider
from tools.search import SearchService, get_search_provider
from tools.web_research import get_web_research_provider
from tools.evidence_extractor import EvidenceExtractor
from tools.currency_normalizer import normalize_currency_to_usd
from tools.domain_utils import normalize_domain
from agents.research_planner import ResearchPlanner
from agents.conflict_resolver import ConflictResolver

logger = logging.getLogger("tvb_agent.research_agent")


def parse_financial_claim(text: str) -> tuple[FinancialType, float, str, bool]:
    """
    Parses textual evidence to extract financial claim details:
    (financial_type, raw_amount, currency, is_total_amount)
    """
    if not text:
        return FinancialType.UNKNOWN, 0.0, "USD", False

    text_lower = text.lower()

    # Detect currency symbol
    currency = "USD"
    if "€" in text or "eur" in text_lower or "euro" in text_lower:
        currency = "EUR"
    elif "£" in text or "gbp" in text_lower or "pound" in text_lower:
        currency = "GBP"

    # Match numerical amounts with mandatory currency symbol or M/B/K/million/billion suffix
    amount_match = re.search(
        r"(\$|€|£)\s*(\d+(?:\.\d+)?)\s*(m|million|b|billion|k|thousand)?|\b(\d+(?:\.\d+)?)\s*(m|million|b|billion|k|thousand)\b",
        text_lower,
    )
    raw_amount = 0.0
    if amount_match:
        if amount_match.group(2):
            val = float(amount_match.group(2))
            unit = amount_match.group(3)
        else:
            val = float(amount_match.group(4))
            unit = amount_match.group(5)

        if unit in ("b", "billion"):
            raw_amount = val * 1_000_000_000.0
        elif unit in ("m", "million"):
            raw_amount = val * 1_000_000.0
        elif unit in ("k", "thousand"):
            raw_amount = val * 1_000.0
        else:
            raw_amount = val

    # Determine financial type
    ftype = FinancialType.UNKNOWN
    is_total = False

    if "valuation" in text_lower or "valued at" in text_lower or "market size" in text_lower:
        ftype = FinancialType.VALUATION
    elif "revenue" in text_lower or "arr" in text_lower or "annual revenue" in text_lower:
        ftype = FinancialType.REVENUE
        is_total = True
    elif "total funding" in text_lower or "cumulative funding" in text_lower or "total raised" in text_lower:
        ftype = FinancialType.FUNDING
        is_total = True
    elif "seed" in text_lower or "series a" in text_lower or "round" in text_lower or "raised" in text_lower or "funding" in text_lower:
        ftype = FinancialType.FUNDING_ROUND
        is_total = False

    return ftype, raw_amount, currency, is_total


def parse_us_presence_text(text: str, domain: str) -> tuple[USPresenceStatus, Optional[str], List[str]]:
    """Parses text evidence to evaluate US operational footprint."""
    if not text:
        return USPresenceStatus.UNKNOWN, None, []

    text_lower = text.lower()
    offices: List[str] = []
    hq_country: Optional[str] = None

    # Check for explicit negative US presence statements (e.g., "zero US office", "no US office")
    has_no_us_office = any(
        neg in text_lower
        for neg in [
            "zero us office",
            "no us office",
            "no us offices",
            "no us headquarters",
            "without us office",
            "zero us presence",
            "no us presence",
        ]
    )

    # Detect physical US HQ / office signals
    has_us_office = (not has_no_us_office) and any(
        k in text_lower
        for k in [
            "us headquarters",
            "headquartered in san francisco",
            "headquartered in new york",
            "us office",
            "san francisco, ca",
            "new york, ny",
            "austin, tx",
            "boston, ma",
            "silicon valley",
        ]
    )

    if has_us_office or ((not has_no_us_office) and "united states" in text_lower and "headquarters" in text_lower):
        return USPresenceStatus.SIGNIFICANT_US_PRESENCE, "United States", ["US Office"]

    # Detect European / Non-US HQ signals
    non_us_countries = [
        ("estonia", "Estonia"),
        ("germany", "Germany"),
        ("france", "France"),
        ("uk", "United Kingdom"),
        ("united kingdom", "United Kingdom"),
        ("london", "United Kingdom"),
        ("berlin", "Germany"),
        ("tallinn", "Estonia"),
        ("singapore", "Singapore"),
        ("brazil", "Brazil"),
        ("india", "India"),
    ]

    for country_kw, country_name in non_us_countries:
        if country_kw in text_lower:
            hq_country = country_name
            break

    if hq_country and hq_country != "United States":
        return USPresenceStatus.VERIFIED_NO_US_PRESENCE, hq_country, []

    return USPresenceStatus.UNKNOWN, None, []


def parse_executive_text(text: str) -> tuple[Optional[str], Optional[ExecutiveRole], bool]:
    """Parses text evidence to identify active CEO or Co-founder."""
    if not text:
        return None, None, False

    # Check for former executive indicators (which must NOT pass)
    if "former ceo" in text.lower() or "ex-ceo" in text.lower() or "stepped down" in text.lower():
        return None, None, False

    # Match CEO / Founder patterns (both 'CEO John Doe' and 'John Doe, CEO' or 'John Doe is CEO')
    pattern1 = re.search(r"(?:CEO|Co-founder|Chief Executive Officer)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", text)
    pattern2 = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:is|as)?\s*(?:the\s+)?(CEO|Co-founder|Chief Executive Officer)", text)

    if pattern1:
        name = pattern1.group(1).strip()
        return name, ExecutiveRole.CEO, True
    elif pattern2:
        name = pattern2.group(1).strip()
        role_str = pattern2.group(2)
        role = ExecutiveRole.CO_FOUNDER if "co-founder" in role_str.lower() else ExecutiveRole.CEO
        return name, role, True

    return None, None, False


class ResearchAgent:
    """
    Autonomous Research Agent that collects, parses, and resolves empirical evidence
    for discovered candidate companies across the 4 major research domains.
    """

    def __init__(
        self,
        search_provider: Optional[SearchProvider] = None,
        web_provider: Optional[WebResearchProvider] = None,
    ):
        self.search_service = SearchService(provider=search_provider or get_search_provider())
        self.web_provider = web_provider or get_web_research_provider()

    def research_candidate(
        self, candidate: DiscoveredCandidate, depth: str = "standard", max_pages: int = 8
    ) -> CompanyResearch:
        """
        Executes complete multi-angle web research for a candidate company.
        """
        domain = candidate.company_domain or normalize_domain(candidate.discovery_source_url) or "unknown.com"
        company_name = candidate.company_name or domain.split(".")[0].capitalize()

        start_time = datetime.now(timezone.utc).isoformat()
        logger.info(f"ResearchAgent starting research for '{company_name}' ({domain}) - depth={depth}")

        # Plan targeted queries
        query_plan = ResearchPlanner.generate_research_plan(candidate, depth=depth, max_queries=max_pages)

        sources_consulted: List[str] = []
        source_failures: List[dict] = []
        warnings: List[str] = []

        all_evidence: List[Evidence] = []
        financial_evidence_list: List[Evidence] = []
        platform_evidence_list: List[Evidence] = []
        us_evidence_list: List[Evidence] = []
        exec_evidence_list: List[Evidence] = []
        fetched_source_urls: set[str] = set()

        pages_fetched = 0

        # Execute queries and fetch pages
        for area, queries in query_plan.items():
            if pages_fetched >= max_pages:
                warnings.append(f"Reached max_pages budget limit ({max_pages}).")
                break

            for q in queries:
                if pages_fetched >= max_pages:
                    break

                try:
                    search_results = self.search_service.search_single(q, limit=2)
                except Exception as exc:
                    warnings.append(f"Search failed for query '{q}': {exc}")
                    continue
                for s_res in search_results:
                    if pages_fetched >= max_pages:
                        break

                    if s_res.url in fetched_source_urls:
                        continue
                    fetched_source_urls.add(s_res.url)

                    sources_consulted.append(s_res.url)
                    try:
                        page_data = self.web_provider.fetch(s_res.url)
                    except Exception as exc:
                        failure = {
                            "url": s_res.url,
                            "stage": "fetch",
                            "error": str(exc),
                        }
                        source_failures.append(failure)
                        warnings.append(f"Source fetch failed for '{s_res.url}': {exc}")
                        continue
                    pages_fetched += 1

                    if not page_data.get("is_accessible", True):
                        source_failures.append(
                            {
                                "url": s_res.url,
                                "stage": "fetch",
                                "status_code": page_data.get("status_code", 0),
                                "error": page_data.get("error_reason", "Source inaccessible"),
                            }
                        )
                        continue

                    snippet = page_data.get("main_text") or s_res.snippet or ""
                    if not snippet:
                        source_failures.append(
                            {
                                "url": s_res.url,
                                "stage": "extraction",
                                "status_code": page_data.get("status_code", 0),
                                "error": "No usable extracted content",
                            }
                        )
                        continue

                    # Process Financial Evidence
                    ftype, raw_amt, curr, is_total = parse_financial_claim(snippet)
                    if ftype != FinancialType.UNKNOWN and raw_amt > 0:
                        norm_usd = normalize_currency_to_usd(raw_amt, curr)
                        ev = EvidenceExtractor.create_evidence(
                            field="financials",
                            page_data=page_data,
                            raw_claim=snippet,
                            evidence_text=snippet,
                            value=norm_usd or raw_amt,
                            confidence=0.85,
                        )
                        if ev:
                            financial_evidence_list.append(ev)
                            all_evidence.append(ev)

                    # Process Platform Evidence
                    text_lower = snippet.lower()
                    if any(k in text_lower for k in ["platform", "saas", "software", "api", "cloud", "dashboard", "b2b"]):
                        ev = EvidenceExtractor.create_evidence(
                            field="is_tech_platform",
                            page_data=page_data,
                            raw_claim=snippet,
                            evidence_text=snippet,
                            value="Tech Platform",
                            confidence=0.9,
                        )
                        if ev:
                            platform_evidence_list.append(ev)
                            all_evidence.append(ev)

                    # Process US Presence Evidence
                    status, hq_country, offices = parse_us_presence_text(snippet, domain)
                    if status != USPresenceStatus.UNKNOWN or hq_country:
                        ev = EvidenceExtractor.create_evidence(
                            field="us_presence",
                            page_data=page_data,
                            raw_claim=snippet,
                            evidence_text=snippet,
                            value=hq_country or status.value,
                            confidence=0.85,
                        )
                        if ev:
                            us_evidence_list.append(ev)
                            all_evidence.append(ev)

                    # Process Executive Evidence
                    exec_name, exec_role, is_active = parse_executive_text(snippet)
                    if exec_name and exec_role and is_active:
                        ev = EvidenceExtractor.create_evidence(
                            field="executive",
                            page_data=page_data,
                            raw_claim=snippet,
                            evidence_text=snippet,
                            value=exec_name,
                            confidence=0.9,
                        )
                        if ev:
                            exec_evidence_list.append(ev)
                            all_evidence.append(ev)

        # Conflict Detection & Resolution
        conflicts = []

        # Resolve Financials
        win_fin_ev, fin_conf = ConflictResolver.resolve_financial_evidence(financial_evidence_list)
        if fin_conf:
            conflicts.append(fin_conf)

        fin_data = FinancialsData()
        if win_fin_ev and win_fin_ev.value is not None:
            ev_text = win_fin_ev.evidence_text or win_fin_ev.raw_claim or ""
            ftype, raw_amt, curr, is_total = parse_financial_claim(ev_text)
            norm_usd = normalize_currency_to_usd(raw_amt, curr) if raw_amt > 0 else float(win_fin_ev.value)
            is_in_range = False
            if norm_usd and 1_000_000.0 <= norm_usd <= 5_000_000.0:
                is_in_range = True

            fin_data = FinancialsData(
                financial_type=ftype,
                amount_raw=raw_amt,
                currency=curr,
                original_amount=raw_amt,
                original_currency=curr,
                normalized_usd=norm_usd,
                is_total_amount=is_total,
                is_in_range=is_in_range,
                evidence=[win_fin_ev],
            )

        # Resolve Platform
        is_tech = len(platform_evidence_list) > 0
        plat_summary = platform_evidence_list[0].raw_claim if platform_evidence_list else None

        # Resolve US Presence
        us_data = USPresenceData()
        if us_evidence_list:
            win_us = us_evidence_list[0]
            ev_text = win_us.evidence_text or win_us.raw_claim or ""
            status, hq_c, offices = parse_us_presence_text(ev_text, domain)
            us_data = USPresenceData(
                status=status,
                headquarters_country=hq_c,
                office_locations=offices,
                evidence=us_evidence_list,
            )

        # Resolve Executive
        win_exec_ev, exec_conf = ConflictResolver.resolve_executive_evidence(exec_evidence_list)
        if exec_conf:
            conflicts.append(exec_conf)

        exec_profile = ExecutiveProfile()
        if win_exec_ev and win_exec_ev.value:
            ev_text = win_exec_ev.evidence_text or win_exec_ev.raw_claim or ""
            name, role, is_act = parse_executive_text(ev_text)
            if name and role:
                exec_profile = ExecutiveProfile(
                    full_name=name,
                    role=role,
                    identity_verified=True,
                    is_current_leadership=is_act,
                    evidence=[win_exec_ev],
                )

        completeness = "complete" if len(all_evidence) >= 3 else ("partial" if len(all_evidence) >= 1 else "failed")

        return CompanyResearch(
            domain=domain,
            company_name=company_name,
            website_url=candidate.discovery_source_url,
            description=candidate.discovery_snippet,
            industry_sector=candidate.sector_hint,
            headquarters_country=us_data.headquarters_country,
            is_tech_platform=is_tech,
            platform_summary=plat_summary,
            platform_evidence=platform_evidence_list,
            financials=fin_data,
            us_presence=us_data,
            executive=exec_profile,
            all_evidence=all_evidence,
            conflicts=conflicts,
            research_completeness=completeness,
            research_depth=depth,
            sources_consulted=sources_consulted,
            source_failures=source_failures,
            warnings=warnings,
            research_timestamp=start_time,
        )
