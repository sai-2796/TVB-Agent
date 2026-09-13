import logging
from typing import Optional, Tuple

logger = logging.getLogger("tvb_agent.currency_normalizer")

# Standardized conversion rates to USD (reference benchmarks)
CURRENCY_RATES = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "AUD": 0.66,
    "CAD": 0.74,
    "INR": 0.012,
    "JPY": 0.0067,
    "SGD": 0.75,
    "BRL": 0.18,
    "CHF": 1.13,
    "SEK": 0.095,
}

SYMBOL_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
}


def normalize_currency_to_usd(
    amount: float, currency_str: str = "USD"
) -> Optional[float]:
    """
    Normalizes a financial amount in a foreign currency to USD using defensible exchange rates.
    Returns None if currency is unsupported or unverified.
    """
    if amount <= 0.0:
        return 0.0

    curr = currency_str.strip().upper()
    if curr in SYMBOL_MAP:
        curr = SYMBOL_MAP[curr]

    if curr in CURRENCY_RATES:
        rate = CURRENCY_RATES[curr]
        normalized = amount * rate
        logger.info(f"Currency normalized: {amount} {curr} -> ${normalized:,.2f} USD (rate={rate})")
        return normalized

    logger.warning(f"Unsupported currency '{currency_str}'. Set normalized_usd to None.")
    return None
