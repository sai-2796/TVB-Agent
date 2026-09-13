# TVB Agentic AI Deal Sourcing System

Autonomous Agentic AI deal-sourcing system built for **The Venture Build (TVB)**. The system dynamically discovers early-stage technology companies, researches financial metrics ($1M–$5M USD), evaluates non-US operational footprints, identifies executive decision makers (CEO / Co-founder), and validates direct executive contact emails using evidence-first verification protocols.

---

## 🏛️ Project Architecture & Documentation

- [PROJECT_SPEC.md](PROJECT_SPEC.md) — Formal Project Specification (Functional requirements, hard criteria, discovery loop design, no-hallucination rules).
- [ARCHITECTURE.md](ARCHITECTURE.md) — System Architecture Blueprint (Component design, state machine, data models, validation layer, provider abstractions).
- [DECISION_LOG.md](DECISION_LOG.md) — Architecture Decision Records (ADRs).

---

## 📦 System Requirements

- **Python**: `3.11+`
- **Dependencies**: `pydantic`, `pytest`, `python-dotenv`, `streamlit`, `google-genai`

---

## 🚀 Setup & Installation

1. **Clone & Environment Setup:**
   ```bash
   git clone <repository_url>
   cd tvb-agent
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and set your credentials:
   ```bash
   cp .env.example .env
   ```

3. **Run Test Suite:**
   ```bash
   pytest -v
   ```

---

## 🧪 Testing Coverage

The foundation test suite validates deterministic qualification logic, boundary limits, generic email rejection, domain canonicalization, and SQLite storage:
- `tests/test_financial.py`: $1M–$5M USD strict boundary checks and valuation rejection.
- `tests/test_email.py`: Generic email denylist filtering and identity-association validation.
- `tests/test_deduplication.py`: URL normalization and root domain canonicalization.
- `tests/test_executive.py`: CEO/Co-founder verification and former leadership rejection.
- `tests/test_platform.py`: Tech platform vs traditional business validation.
- `tests/test_us_presence.py`: Minimal to no US presence checks.
- `tests/test_qualification.py`: Deterministic 5-criteria master qualification engine.
- `tests/test_lead_store.py`: SQLite persistence CRUD operations.
# TVB-Agent
