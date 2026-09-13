# TVB AGENT — FORMAL PROJECT SPECIFICATION (PHASE 0 & 1.1 HARDENED)

## 1. Problem Statement
The Venture Build (TVB) requires a continuous, data-driven lead generation pipeline to identify target companies fitting specific investment and partnership profiles. Manual deal sourcing across global markets is time-consuming, prone to human bias, and limited by standard search methodologies. TVB needs an autonomous, Agentic AI deal-sourcing system capable of dynamically discovering non-US technology platforms, evaluating financial metrics ($1M–$5M USD revenue/funding), identifying decision-makers (CEO/Co-founder), and validating direct professional contact emails without relying on static, hardcoded lists or generating unverified ("hallucinated") data.

---

## 2. Objective
To design and build an Agentic AI pipeline that autonomously:
1. **Discovers** new candidate companies dynamically across diverse global web sources via an iterative agentic search loop.
2. **Researches** company profiles, operating models, revenue/funding metrics, and geographical footprints.
3. **Validates** each candidate strictly against TVB's 5 Hard Qualification Criteria using programmatic deterministic checkers.
4. **Identifies** the primary executive decision-maker (CEO or Co-founder) with empirical identity verification.
5. **Finds and Verifies** direct professional email addresses for the identified executive via identity/email association and technical validation (rejecting generic emails like `info@`, `contact@`, etc.).
6. **Rejects or leaves unverified** any field or candidate lacking sufficient empirical evidence or containing unresolved conflicts (Strict No-Hallucination Policy).
7. **Delivers** a clean list of at least 15 fully qualified leads via a zero-setup, publicly accessible web application UI with evidence auditability and export capabilities.

---

## 3. Functional Requirements

### 3.1 Pipeline Execution & Control
- **User-Triggered Run:** The user can initiate autonomous discovery and research jobs with configurable batch sizes (e.g., target minimum 15 qualified leads, or customizable $N$).
- **Progress Tracking & Status:** Real-time feedback on pipeline steps: Iterative Discovery -> Deep Research -> Conflict Resolution -> Hard Validation -> Executive Sourcing -> Email Verification -> Lead Audit.
- **Export & Storage:** Capability to export qualified lead results into CSV and JSON formats with complete audit trails.

### 3.2 Dynamic Iterative Discovery Engine
- **Agentic Search Loop:** Dynamic hypothesis-driven search loop:
  `Generate Search Hypothesis -> Search -> Analyze Results -> Extract Candidates -> Identify Discovery Gaps -> Generate New Search Hypothesis -> Search Again`.
- **No Static Lists:** The discovery engine generates search strategies algorithmically based on observed candidate yield and sector gaps, using query templates only as initial guidance.
- **Deduplication:** Strict deduplication by normalized root domain name and standardized legal entity name across runs.

### 3.3 Autonomous Research & Evidence Extraction
- **Multi-Angle Web Scraper/Researcher:** Extract content from company landing pages, "About Us", press releases, Crunchbase/PitchBook public mirrors, LinkedIn public company pages, regulatory filings, and tech news.
- **Structured Evidence Harvesting:** Record source URLs, titles, extracted text claims, publication dates, freshness metadata, source tiers, confidence scores, and research timestamps for every data point.

### 3.4 Contact Identification & Verification Engine
- **Three-Stage Executive Contact Protocol:**
  1. *Executive Identity Verification:* Prove that the identified person is currently the active CEO or Co-founder.
  2. *Executive-Email Association:* Find reliable public evidence directly associating the specific email address string with that executive.
  3. *Technical Email Validation:* Determine technical deliverability using a pluggable Email Verification API / provider (with MX/SMTP fallback).
- **Generic Email Rejection:** Explicitly reject generic mailboxes (`info@`, `contact@`, `sales@`, `hello@`, `support@`, `admin@`).
- **Pattern Handling:** Pattern-generated emails (e.g., `first.last@domain.com`) are treated solely as candidate hypotheses and CANNOT be marked `VERIFIED` without explicit identity-association evidence or positive verification API response.

---

## 4. Hard Qualification Criteria

A company is marked **QUALIFIED** if and only if **ALL FIVE** criteria are fully satisfied with verifiable evidence:

| Criterion | Metric / Scope | Qualification Rule | Disqualification Trigger |
| :--- | :--- | :--- | :--- |
| **A. Financial Criterion** | Verified Revenue OR Verified Total Funding | Range: **$1,000,000 to $5,000,000 USD** (inclusive). Valuation, employee count, estimated revenue, or single round amount MUST NOT be treated as total funding/revenue unless explicitly supported by evidence. | < $1M USD, > $5M USD, missing evidence, unverified estimations, or unresolved conflicts. |
| **B. Tech Platform** | Operating Model | Must operate a genuine **technology-related platform/product/business** (SaaS, B2B, B2B2C, AI, HealthTech, EdTech, Cyber, Fintech, Travel, Digital Twin, etc.). | Traditional business merely using third-party tech internally (e.g., local retail, traditional consulting). |
| **C. Minimal US Presence** | Geographical Footprint | Must have **minimal to no presence in the United States**. Evaluated on HQ, physical offices, subsidiaries, operating locations, core US team. (*Note: Serving US customers does NOT equate to US presence*). | Main HQ in US, primary executive team based in US, or major physical office footprint in US. |
| **D. Executive Identification** | Key Decision Maker | Active **CEO or Co-founder** must be identified with full legal name, exact role title, source URL, evidence snippet, freshness status, and confidence score. | Unable to verify active CEO/Co-founder or stale leadership information. |
| **E. Verified Executive Email** | Direct Contact | Individual professional email belonging to the identified CEO/Co-founder **must pass technical validation AND identity-association verification**. | Generic emails (`info@`, `contact@`), failed verification API check, guessed email without verification. |

---

## 5. Dynamic Discovery Loop Requirements

1. **Iterative Search Hypothesis Architecture:**
   ```
   Generate Search Hypothesis
   ↓
   Search Web / Directories
   ↓
   Analyze Results & Yield
   ↓
   Extract Candidates
   ↓
   Identify Discovery Gaps (Geography / Sector / Yield)
   ↓
   Generate New Search Hypothesis
   ↓
   Search Again
   ```

2. **Query Diversity & Adaptation:**
   - The agent dynamically adjusts sector terms (B2B SaaS, HealthTech, AI platform), geography filters (Europe, LATAM, SEA, MENA, Africa), and funding indicators based on current yield.
   - Initial seed templates serve as starting points; subsequent queries are generated autonomously by the discovery agent.

3. **Anti-Duplication & Rate Handling:**
   - Global exclusion set based on root domain canonicalization (e.g., `example.com`).
   - Rate limiting, polite crawling delays, and failure retry backoffs.

---

## 6. Evidence Model & Source Quality

### 6.1 Evidence Schema
Every decision within the pipeline must be backed by an explicit **Evidence Object**:

```json
{
  "field": "funding_amount",
  "value": 2500000,
  "currency": "USD",
  "raw_claim": "Company X raised $2.5M in Series Seed led by VC Y in Q2 2024",
  "source_url": "https://example-tech-news.com/article-123",
  "source_title": "Company X raises $2.5M Seed",
  "source_type": "press_release",
  "source_published_date": "2024-05-10",
  "accessed_at": "2026-09-12T23:41:00Z",
  "freshness_status": "CURRENT",
  "source_tier": "Tier_2",
  "confidence": 0.95,
  "verification_method": "EXTRACTION_AND_CROSS_CHECK",
  "evidence_conflict_id": null
}
```

### 6.2 Source Freshness & Conflict Resolution
1. **Source Freshness:** Metadata tags (`published_date`, `accessed_at`, `freshness_status`) are evaluated to prefer current evidence and detect stale leadership/contact information.
2. **Conflict Resolution Protocol:**
   - **Detection:** If credible sources disagree on financial metrics, HQ location, or CEO identity, a conflict is flagged (`evidence_conflict_id`).
   - **Targeted Sourcing:** The research agent executes secondary queries to resolve the discrepancy.
   - **Hierarchy & Recency:** Higher source tiers (Tier 1 > Tier 2 > Tier 3) and more recent publication dates take precedence.
   - **Conservative Fallback:** If conflict cannot be resolved with high confidence, set field to `UNKNOWN` and mark candidate as `UNQUALIFIED`.

---

## 7. Strict No-Hallucination Policy

1. **Zero Guessing:** If financial range, HQ location, tech platform status, CEO name, or email cannot be verified by empirical web evidence, mark the field as `"Unverified"` or `null`.
2. **Pattern Guess Rejection:** Generated email patterns are candidates only. An address is never marked `VERIFIED` without technical deliverability validation AND identity-association evidence.
3. **Hard Stop Rejection:** A company missing even ONE required criterion or containing an unresolved conflict MUST be assigned `qualification_status: "UNQUALIFIED"`.
4. **No Synthetic Lead Fallbacks:** Never seed test data, placeholder leads, or dummy company records into final output runs.

---

## 8. Lead Schema

### 8.1 Primary Output Schema (Clean Lead List)
```json
{
  "company_name": "TechPlatform Ltd",
  "description": "B2B SaaS platform for automated supply chain tracking.",
  "industry_sector": "B2B SaaS / Supply Chain",
  "verified_executive_email": "alex.smith@techplatform.io"
}
```

### 8.2 Internal Comprehensive Audit Schema
```json
{
  "id": "lead_uuid_12345",
  "company_name": "TechPlatform Ltd",
  "domain": "techplatform.io",
  "website_url": "https://techplatform.io",
  "description": "B2B SaaS platform for automated supply chain tracking.",
  "industry_sector": "B2B SaaS",
  "financials": {
    "amount_usd": 2500000,
    "type": "funding",
    "raw_value": "$2.5M USD",
    "is_in_range": true,
    "evidence": [...]
  },
  "tech_platform_assessment": {
    "is_tech_platform": true,
    "platform_summary": "Proprietary cloud SaaS dashboard and API.",
    "evidence": [...]
  },
  "us_presence_assessment": {
    "status": "VERIFIED_NO_US_PRESENCE",
    "headquarters_country": "Estonia",
    "office_locations": ["Tallinn", "Berlin"],
    "evidence": [...]
  },
  "executive": {
    "full_name": "Alex Smith",
    "role": "Co-founder & CEO",
    "identity_verified": true,
    "evidence": [...]
  },
  "executive_email": {
    "email": "alex.smith@techplatform.io",
    "verification_status": "VERIFIED",
    "verification_method": "API_AND_ASSOCIATION_CHECK",
    "is_generic": false,
    "evidence": [...]
  },
  "qualification_status": "QUALIFIED",
  "overall_confidence": 0.92,
  "created_at": "2026-09-12T23:41:00Z"
}
```

---

## 9. Programmatic Qualification Logic

```
FUNCTION EvaluateLead(company):
    IF company.financials.amount_usd < 1,000,000 OR company.financials.amount_usd > 5,000,000:
        RETURN UNQUALIFIED ("Financial criteria out of range or unverified")
        
    IF NOT company.is_tech_platform:
        RETURN UNQUALIFIED ("Not a technology-related platform/product")
        
    IF company.us_presence.status NOT IN ["VERIFIED_NO_US_PRESENCE", "MINIMAL_US_PRESENCE"]:
        RETURN UNQUALIFIED ("Substantial US presence detected or unverified")
        
    IF NOT company.executive.identity_verified OR company.executive.role NOT IN ["CEO", "Co-founder", "CEO & Co-founder"]:
        RETURN UNQUALIFIED ("Active CEO or Co-founder identity not verified")
        
    IF company.executive_email.verification_status != "VERIFIED" OR company.executive_email.is_generic == TRUE:
        RETURN UNQUALIFIED ("Individual professional executive email not verified")
        
    RETURN QUALIFIED
```

---

## 10. Non-Functional Requirements

1. **Conservative Qualification Quality:** Conservative, evidence-based qualification designed to minimize false positives.
2. **Reliability & Resilience:** Graceful handling of network timeouts, blocked scraping requests, rate limits, and missing data points.
3. **Performance:** Pipeline execution for 15 qualified leads should complete within an acceptable runtime window without timing out.
4. **Auditability:** Complete chain of evidence logged for every evaluation step.

---

## 11. Deployment Requirements

1. **Public Web URL:** Deployed on a public hosting service (e.g., Streamlit Community Cloud, Render, Cloudflare Pages, Hugging Face Spaces).
2. **Zero Evaluator Setup:** The evaluator opens the URL in any standard browser and operates the application immediately. No terminal commands, API keys insertion by evaluator, or local cloning required.
3. **UI Capabilities:**
   - Trigger new discovery pipeline runs.
   - Display real-time execution log & progress indicator.
   - View formatted table of Qualified Leads (Clean Output).
   - Expand/Inspect evidence for any lead.
   - Export results as CSV/JSON.

---

## 12. Testing & Verification Requirements

1. **Unit Testing:**
   - Financial range checker validation ($1M–$5M boundary tests, currency conversions).
   - Email format & generic email filter (`info@`, `contact@`, `support@` rejection).
   - US presence parser validation.
2. **Integration Testing:**
   - Mocked search & scrape pipeline tests.
   - Email verification API/provider integration tests.
3. **End-to-End Evaluation:**
   - Autonomous dry-run targeting discovery of 15 qualified leads with complete evidence verification.

---

## 13. Known Risks & Mitigation Strategies

| Risk Factor | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Strict email verification yielding low pass rates** | High | Combine verification API checks with public executive-email association evidence. Expand candidate discovery pool volume. |
| **Web scraping anti-bot restrictions** | Medium | Use lightweight API-based search (SerpAPI, Tavily, Exa) and standard headful/headless user-agent fallback strategies. |
| **Financial data opacity in private startups** | Medium | Prioritize regions/databases with public funding records (EU registers, Crunchbase mirrors, press release archives). Disqualify gracefully if evidence is absent. |
| **Port 25 blocked on Cloud Deployment** | High | Use legitimate Email Verification API / provider as primary or fallback mechanism instead of relying solely on raw SMTP sockets. |

---

## 14. Open Technical Decisions (To be finalized before Phase 2)

1. **LLM Orchestration Framework:** Selection between custom async Python state machine vs LangGraph.
2. **Search API Provider:** Selection of primary discovery API (Tavily API vs SerpAPI vs Exa API).
3. **Email Verification Provider:** Selection of production email verification API (Hunter API, ZeroBounce API, or Bounceban API) with MX fallback.
4. **Deployment Hosting Platform:** Streamlit Community Cloud vs Render.
