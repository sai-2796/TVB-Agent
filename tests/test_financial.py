import pytest
from models.evidence import Evidence
from models.financial import FinancialsData, FinancialType
from validators.financial import FinancialValidator, ValidationStatus


def make_evidence() -> Evidence:
    return Evidence(
        field="financials",
        value="$2.5M USD",
        raw_claim="Company raised $2.5M funding",
        source_url="https://example.com/press",
        source_title="Press Release",
        source_type="press_release",
        accessed_at="2026-09-12T23:50:00Z",
        confidence=0.9,
    )


def test_financial_boundaries():
    # 999,999 USD -> FAIL
    f_low = FinancialsData(
        financial_type=FinancialType.FUNDING,
        amount_raw=999999.0,
        normalized_usd=999999.0,
        is_total_amount=True,
        evidence=[make_evidence()],
    )
    res_low = FinancialValidator.validate(f_low)
    assert res_low.status == ValidationStatus.FAIL
    assert "below minimum" in res_low.reason

    # 1,000,000 USD -> PASS
    f_min = FinancialsData(
        financial_type=FinancialType.FUNDING,
        amount_raw=1000000.0,
        normalized_usd=1000000.0,
        is_total_amount=True,
        evidence=[make_evidence()],
    )
    res_min = FinancialValidator.validate(f_min)
    assert res_min.status == ValidationStatus.PASS

    # 1,000,001 USD -> PASS
    f_min_plus = FinancialsData(
        financial_type=FinancialType.REVENUE,
        amount_raw=1000001.0,
        normalized_usd=1000001.0,
        is_total_amount=True,
        evidence=[make_evidence()],
    )
    res_min_plus = FinancialValidator.validate(f_min_plus)
    assert res_min_plus.status == ValidationStatus.PASS

    # 4,999,999 USD -> PASS
    f_max_minus = FinancialsData(
        financial_type=FinancialType.FUNDING,
        amount_raw=4999999.0,
        normalized_usd=4999999.0,
        is_total_amount=True,
        evidence=[make_evidence()],
    )
    res_max_minus = FinancialValidator.validate(f_max_minus)
    assert res_max_minus.status == ValidationStatus.PASS

    # 5,000,000 USD -> PASS
    f_max = FinancialsData(
        financial_type=FinancialType.REVENUE,
        amount_raw=5000000.0,
        normalized_usd=5000000.0,
        is_total_amount=True,
        evidence=[make_evidence()],
    )
    res_max = FinancialValidator.validate(f_max)
    assert res_max.status == ValidationStatus.PASS

    # 5,000,001 USD -> FAIL
    f_high = FinancialsData(
        financial_type=FinancialType.FUNDING,
        amount_raw=5000001.0,
        normalized_usd=5000001.0,
        is_total_amount=True,
        evidence=[make_evidence()],
    )
    res_high = FinancialValidator.validate(f_high)
    assert res_high.status == ValidationStatus.FAIL
    assert "above maximum" in res_high.reason


def test_financial_valuation_rejection():
    f_val = FinancialsData(
        financial_type=FinancialType.VALUATION,
        amount_raw=3000000.0,
        normalized_usd=3000000.0,
        is_total_amount=True,
        evidence=[make_evidence()],
    )
    res = FinancialValidator.validate(f_val)
    assert res.status == ValidationStatus.FAIL
    assert "valuation cannot be used" in res.reason


def test_financial_single_round_unverified_total():
    f_round = FinancialsData(
        financial_type=FinancialType.FUNDING_ROUND,
        amount_raw=2000000.0,
        normalized_usd=2000000.0,
        is_total_amount=False,
        evidence=[make_evidence()],
    )
    res = FinancialValidator.validate(f_round)
    assert res.status == ValidationStatus.UNKNOWN
    assert "Single funding round amount" in res.reason
