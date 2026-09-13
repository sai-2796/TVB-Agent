import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from models.company import CompanyResearch
from models.executive import ExecutiveProfile, ExecutiveRole
from models.email import ExecutiveEmail, EmailVerificationStatus, TechnicalStatus, FinalEmailStatus
from models.evidence import Evidence, VerificationMethod, SourceTier
from tools.interfaces import EmailVerificationProvider, SearchProvider, WebResearchProvider
from tools.email_verification import get_email_verification_provider, is_valid_email_syntax
from tools.generic_email import is_generic_email
from tools.domain_utils import normalize_domain
from tools.evidence_extractor import EvidenceExtractor

logger = logging.getLogger("tvb_agent.contact_agent")


def generate_candidate_email_patterns(first_name: str, last_name: str, domain: str) -> List[str]:
    """Generates candidate email pattern hypotheses for search/verification."""
    if not first_name or not domain:
        return []

    fn = re.sub(r"[^a-z0-9]", "", first_name.lower())
    ln = re.sub(r"[^a-z0-9]", "", last_name.lower()) if last_name else ""
    dom = normalize_domain(domain)

    patterns: List[str] = []
    if fn and ln:
        patterns.append(f"{fn}.{ln}@{dom}")
        patterns.append(f"{fn}@{dom}")
        patterns.append(f"{fn[0]}{ln}@{dom}")
    elif fn:
        patterns.append(f"{fn}@{dom}")

    return patterns


class ContactAgent:
    """
    Executive Contact & Email Verification Agent enforcing TVB's 3-Stage Protocol:
    Stage A (Identity) -> Stage B (Person-Email Association) -> Stage C (Technical Deliverability Validation).
    """

    def __init__(
        self,
        email_verifier: Optional[EmailVerificationProvider] = None,
        search_provider: Optional[SearchProvider] = None,
        web_provider: Optional[WebResearchProvider] = None,
    ):
        self.email_verifier = email_verifier or get_email_verification_provider()
        self.search_provider = search_provider
        self.web_provider = web_provider
        self.verification_cache: Dict[str, Dict[str, Any]] = {}

    def process_contact_verification(
        self, company_research: CompanyResearch
    ) -> ExecutiveEmail:
        """
        Executes the 3-stage executive contact verification protocol for a candidate company.
        """
        exec_profile = company_research.executive
        domain = company_research.domain
        company_name = company_research.company_name or domain

        logger.info(f"ContactAgent processing contact verification for '{company_name}' ({domain})")

        # Stage A: Executive Identity Verification
        if not exec_profile or not exec_profile.full_name or not exec_profile.identity_verified or not exec_profile.is_current_leadership:
            logger.warning(f"ContactAgent Stage A FAIL: Active executive identity unverified for '{domain}'.")
            return ExecutiveEmail(
                verification_status=EmailVerificationStatus.UNVERIFIED,
                technical_status=TechnicalStatus.UNKNOWN,
                final_status=FinalEmailStatus.NOT_VERIFIED,
            )

        exec_name = exec_profile.full_name
        name_parts = exec_name.split()
        first_name = name_parts[0]
        last_name = name_parts[-1] if len(name_parts) > 1 else ""

        # Gather Candidate Emails from Research Evidence + Pattern Hypotheses
        candidate_emails: List[ExecutiveEmail] = []
        seen_addresses = set()

        # 1. Direct discovery from existing research evidence text and raw claims
        for ev in company_research.all_evidence:
            text_to_search = f"{ev.evidence_text or ''} {ev.raw_claim or ''}"
            if not text_to_search.strip():
                continue
            email_matches = re.findall(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", text_to_search)
            for raw_addr in email_matches:
                norm_addr = raw_addr.strip().lower()
                if norm_addr in seen_addresses:
                    continue
                seen_addresses.add(norm_addr)

                is_gen = is_generic_email(norm_addr)
                # Association check: Check if executive name is present in evidence snippet or claim
                assoc_verified = False
                if not is_gen and (first_name.lower() in text_to_search.lower() or (last_name and last_name.lower() in text_to_search.lower())):
                    assoc_verified = True

                candidate_emails.append(
                    ExecutiveEmail(
                        email=norm_addr,
                        normalized_email=norm_addr,
                        executive_name=exec_name,
                        is_generic=is_gen,
                        is_pattern_candidate=False,
                        association_verified=assoc_verified,
                        association_evidence=[ev] if assoc_verified else [],
                        source_url=ev.source_url,
                    )
                )

        # 2. Add Candidate Email Pattern Hypotheses (explicitly marked as pattern candidates without initial association)
        pattern_addrs = generate_candidate_email_patterns(first_name, last_name, domain)
        for pattern_addr in pattern_addrs:
            norm_pattern = pattern_addr.strip().lower()
            if norm_pattern in seen_addresses:
                continue
            seen_addresses.add(norm_pattern)

            candidate_emails.append(
                ExecutiveEmail(
                    email=norm_pattern,
                    normalized_email=norm_pattern,
                    executive_name=exec_name,
                    is_generic=False,
                    is_pattern_candidate=True,
                    association_verified=False,  # Pattern hypothesis CANNOT be marked associated without public evidence!
                    association_evidence=[],
                )
            )

        if not candidate_emails:
            logger.info(f"No email candidates found for executive '{exec_name}' at '{domain}'.")
            return ExecutiveEmail(
                executive_name=exec_name,
                verification_status=EmailVerificationStatus.UNVERIFIED,
                technical_status=TechnicalStatus.UNKNOWN,
                final_status=FinalEmailStatus.NOT_VERIFIED,
            )

        # Process Each Candidate Email through Stage B & Stage C
        evaluated_candidates: List[ExecutiveEmail] = []

        for cand in candidate_emails:
            email_str = cand.email
            if not email_str:
                continue

            # Stage B Check: Generic Rejection
            if cand.is_generic or is_generic_email(email_str):
                cand.final_status = FinalEmailStatus.REJECTED
                cand.technical_status = TechnicalStatus.INVALID
                cand.verification_status = EmailVerificationStatus.INVALID
                evaluated_candidates.append(cand)
                continue

            # Stage C Check: Technical Email Deliverability Verification (with cache)
            if email_str in self.verification_cache:
                tech_res = self.verification_cache[email_str]
            else:
                tech_res = self.email_verifier.verify(email_str, domain)
                self.verification_cache[email_str] = tech_res

            cand.syntax_valid = tech_res.get("syntax_valid", True)
            cand.domain_valid = tech_res.get("domain_valid", True)
            cand.mx_valid = tech_res.get("mx_valid", False)
            cand.provider_status = tech_res.get("reason", "")
            cand.verification_provider = tech_res.get("provider", "EmailVerifier")
            cand.verification_timestamp = tech_res.get("timestamp")

            raw_tech = tech_res.get("technical_status", TechnicalStatus.UNKNOWN.value)
            try:
                cand.technical_status = TechnicalStatus(raw_tech)
            except ValueError:
                cand.technical_status = TechnicalStatus.UNKNOWN

            is_deliverable = tech_res.get("is_deliverable", False)

            # Stage B & C Synthesis: Final Status Determination
            if cand.association_verified and is_deliverable and cand.technical_status in (TechnicalStatus.DELIVERABLE, TechnicalStatus.VERIFIED):
                cand.final_status = FinalEmailStatus.VERIFIED
                cand.verification_status = EmailVerificationStatus.VERIFIED
                cand.verification_method = VerificationMethod.API_CHECK
            elif cand.is_pattern_candidate or not cand.association_verified:
                # Pattern candidate without public association proof CANNOT become VERIFIED!
                cand.final_status = FinalEmailStatus.NOT_VERIFIED
                cand.verification_status = EmailVerificationStatus.UNVERIFIED
                cand.verification_method = VerificationMethod.UNVERIFIED
            elif cand.technical_status == TechnicalStatus.MX_VALIDATED:
                # MX validation alone does NOT equal VERIFIED!
                cand.final_status = FinalEmailStatus.NOT_VERIFIED
                cand.verification_status = EmailVerificationStatus.UNVERIFIED
                cand.verification_method = VerificationMethod.MX_CHECK
            else:
                cand.final_status = FinalEmailStatus.NOT_VERIFIED
                cand.verification_status = EmailVerificationStatus.UNVERIFIED

            evaluated_candidates.append(cand)

        # Select top candidate satisfying Stage A + B + C (final_status == VERIFIED)
        verified_candidates = [c for c in evaluated_candidates if c.final_status == FinalEmailStatus.VERIFIED]

        if verified_candidates:
            winner = verified_candidates[0]
            logger.info(f"ContactAgent SUCCESS: Direct executive email verified: '{winner.email}' for '{exec_name}'")
            return winner

        # If no candidate satisfied full verification, return top evaluated candidate with NOT_VERIFIED status
        top_fallback = evaluated_candidates[0]
        logger.info(f"ContactAgent: No email candidate satisfied full verification protocol. Selected '{top_fallback.email}' (status={top_fallback.final_status.value})")
        return top_fallback
