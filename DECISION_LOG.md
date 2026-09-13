# DECISION LOG — TVB AGENT

## Decision 1: Evidence-Based Qualification Standard
- **Context:** The specification demands high-precision deal sourcing without hallucinating financial metrics or contact details.
- **Decision:** Qualification is strict and binary (All 5 hard criteria MUST pass). If any single field is unverified, missing, or outside thresholds, the candidate is classified as `UNQUALIFIED`. No partial or probability-weighted qualification is permitted.
- **Impact:** Eliminates false positives, ensures zero fake leads.

## Decision 2: Generic Email Rejection Rule
- **Context:** Standard lead scrapers often fall back to `info@domain.com` or `contact@domain.com`. TVB requires direct executive contact.
- **Decision:** Generic email addresses (`info@`, `contact@`, `hello@`, `support@`, `admin@`, `sales@`, `jobs@`) are strictly filtered out. Only direct CEO or Co-founder verified emails are accepted.
- **Impact:** Higher conversion rate for executive outreach; requires multi-tier verification (SMTP handshake / MX lookup / email verification APIs).

## Decision 3: Minimal US Presence Operational Rule
- **Context:** "Minimal to no US presence" must be evaluated objectively without penalizing global platforms that happen to sell to US clients.
- **Decision:** Focus evaluation on headquarters location, primary physical offices, subsidiary filings, and core management team base location. Serving US customers or having US cloud hosting (e.g. AWS US-East) does NOT disqualify a company.
- **Impact:** Prevents false disqualification of international SaaS companies selling globally.

## Decision 4: Financial Boundary Enforcement
- **Context:** Target revenue or total funding raised must be strictly between $1,000,000 and $5,000,000 USD.
- **Decision:** Numerical values are standardized to USD using historical/real-time exchange rate normalization where non-USD currencies are detected in empirical evidence. Unverified claims, estimations, valuation figures, employee count proxies, or ranges outside [$1M, $5M] trigger immediate disqualification.
- **Impact:** Strictly adheres to TVB target sizing requirements.

## Decision 5: Dynamic Iterative Discovery Loop (Phase 1.1 Hardened)
- **Context:** Static query templates are insufficient for open-ended, continuous discovery.
- **Decision:** Discovery operates as an iterative agentic feedback loop: `Generate Search Hypothesis -> Search -> Analyze Results -> Extract Candidates -> Identify Discovery Gaps -> Generate New Search Hypothesis -> Search Again`.
- **Impact:** Autonomous discovery capable of expanding into under-explored sectors and geographic regions dynamically.

## Decision 6: Three-Stage Executive Email Verification Protocol (Phase 1.1 Hardened)
- **Context:** Email patterns generated from executive names (`first.last@domain.com`) are unverified guesses and must not be blindly trusted. Technical checks alone (MX/SMTP) do not prove ownership.
- **Decision:** Email verification requires three distinct stages: (A) Executive Identity Verification (proving active CEO/Co-founder status), (B) Executive-Email Association (public proof connecting email string to executive), and (C) Technical Validation (via Email Verification API or MX check).
- **Impact:** Prevents false positive emails and guarantees direct executive contact deliverability.

## Decision 7: Email Verification API as Primary / Production Fallback (Phase 1.1 Hardened)
- **Context:** Cloud hosting environments (Streamlit Cloud, Render, Vercel) block outgoing Port 25, breaking raw SMTP socket handshakes.
- **Decision:** Raw SMTP socket checks are treated as optional signals. Production email verification relies on Email Verification APIs (Hunter, ZeroBounce, Bounceban) and MX record lookups. Unverified checks conservatively yield status `UNVERIFIED` and lead disqualification.
- **Impact:** Ensures reliable web application deployment without network socket blocking.

## Decision 8: Programmatic Conflict Resolution & Freshness Auditing (Phase 1.1 Hardened)
- **Context:** Public web sources frequently present conflicting or stale data regarding startup leadership and funding.
- **Decision:** Evidence objects include source freshness metadata (`source_published_date`, `accessed_at`, `freshness_status`). A Conflict Resolution Protocol ranks evidence by source tier (Tier 1 > Tier 2 > Tier 3) and recency. Unresolved conflicts result in field status `UNKNOWN` and candidate disqualification.
- **Impact:** Minimizes false positives and guarantees data freshness.

## Decision 9: Precision Language & Accuracy Realism (Phase 1.1 Hardened)
- **Context:** Claims of "100% precision" or "guaranteed 100% real-world accuracy" are unrealistic in open-web data extraction.
- **Decision:** All system documentation and UI descriptions use conservative terminology: "Conservative, evidence-based qualification designed to minimize false positives."
- **Impact:** Aligns technical documentation with realistic engineering standards.
