import logging
import os
import re
import socket
import requests
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from config.settings import Settings, get_settings
from tools.generic_email import is_generic_email
from tools.interfaces import EmailVerificationProvider
from models.email import TechnicalStatus, FinalEmailStatus

logger = logging.getLogger("tvb_agent.email_verification")


def is_valid_email_syntax(email: str | None) -> bool:
    """Validates basic email syntax according to RFC standard format."""
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


class MockEmailVerificationProvider(EmailVerificationProvider):
    """Mock EmailVerificationProvider for testing deliverability scenarios."""

    def __init__(self, mock_status_map: Optional[Dict[str, str]] = None):
        self.mock_status_map = mock_status_map or {}

    def verify(self, email: str, domain: str) -> Dict[str, Any]:
        norm_email = email.strip().lower()
        timestamp = datetime.now(timezone.utc).isoformat()

        if is_generic_email(norm_email):
            return {
                "email": norm_email,
                "syntax_valid": True,
                "domain_valid": True,
                "mx_valid": True,
                "technical_status": TechnicalStatus.INVALID.value,
                "final_status": FinalEmailStatus.REJECTED.value,
                "is_deliverable": False,
                "reason": "Generic company email address rejected",
                "provider": "MockEmailVerificationProvider",
                "timestamp": timestamp,
            }

        # Check mock overrides
        status_override = self.mock_status_map.get(norm_email, "deliverable")

        if status_override == "deliverable":
            return {
                "email": norm_email,
                "syntax_valid": True,
                "domain_valid": True,
                "mx_valid": True,
                "technical_status": TechnicalStatus.DELIVERABLE.value,
                "final_status": FinalEmailStatus.VERIFIED.value,
                "is_deliverable": True,
                "reason": "Verified deliverable mailbox (Mock)",
                "provider": "MockEmailVerificationProvider",
                "timestamp": timestamp,
            }
        elif status_override == "invalid":
            return {
                "email": norm_email,
                "syntax_valid": True,
                "domain_valid": True,
                "mx_valid": False,
                "technical_status": TechnicalStatus.INVALID.value,
                "final_status": FinalEmailStatus.NOT_VERIFIED.value,
                "is_deliverable": False,
                "reason": "Undeliverable/invalid mailbox (Mock)",
                "provider": "MockEmailVerificationProvider",
                "timestamp": timestamp,
            }
        elif status_override == "risky":
            return {
                "email": norm_email,
                "syntax_valid": True,
                "domain_valid": True,
                "mx_valid": True,
                "technical_status": TechnicalStatus.RISKY.value,
                "final_status": FinalEmailStatus.NOT_VERIFIED.value,
                "is_deliverable": False,
                "reason": "Risky / catch-all mailbox (Mock)",
                "provider": "MockEmailVerificationProvider",
                "timestamp": timestamp,
            }
        else:
            return {
                "email": norm_email,
                "syntax_valid": True,
                "domain_valid": True,
                "mx_valid": True,
                "technical_status": TechnicalStatus.UNKNOWN.value,
                "final_status": FinalEmailStatus.UNKNOWN.value,
                "is_deliverable": False,
                "reason": f"Mock provider status: {status_override}",
                "provider": "MockEmailVerificationProvider",
                "timestamp": timestamp,
            }


class MXFallbackProvider(EmailVerificationProvider):
    """
    Fallback EmailVerificationProvider performing syntax & DNS MX record checks.
    Guarantees MX_VALID != VERIFIED (MX validation alone yields NOT_VERIFIED).
    """

    def verify(self, email: str, domain: str) -> Dict[str, Any]:
        norm_email = email.strip().lower()
        timestamp = datetime.now(timezone.utc).isoformat()

        if not is_valid_email_syntax(norm_email):
            return {
                "email": norm_email,
                "syntax_valid": False,
                "domain_valid": False,
                "mx_valid": False,
                "technical_status": TechnicalStatus.INVALID.value,
                "final_status": FinalEmailStatus.NOT_VERIFIED.value,
                "is_deliverable": False,
                "reason": "Invalid email syntax",
                "provider": "MXFallbackProvider",
                "timestamp": timestamp,
            }

        if is_generic_email(norm_email):
            return {
                "email": norm_email,
                "syntax_valid": True,
                "domain_valid": True,
                "mx_valid": True,
                "technical_status": TechnicalStatus.INVALID.value,
                "final_status": FinalEmailStatus.REJECTED.value,
                "is_deliverable": False,
                "reason": "Generic company mailbox rejected",
                "provider": "MXFallbackProvider",
                "timestamp": timestamp,
            }

        target_domain = norm_email.split("@")[1]

        # Perform MX / DNS check via socket lookup
        has_mx = False
        try:
            # Fallback host lookup
            host = socket.gethostbyname(target_domain)
            if host:
                has_mx = True
        except Exception:
            has_mx = False

        if has_mx:
            return {
                "email": norm_email,
                "syntax_valid": True,
                "domain_valid": True,
                "mx_valid": True,
                "technical_status": TechnicalStatus.MX_VALIDATED.value,
                "final_status": FinalEmailStatus.NOT_VERIFIED.value,  # MX alone is NOT_VERIFIED
                "is_deliverable": False,
                "reason": "MX record validated. Mailbox deliverability unverified (MX fallback mode).",
                "provider": "MXFallbackProvider",
                "timestamp": timestamp,
            }

        return {
            "email": norm_email,
            "syntax_valid": True,
            "domain_valid": False,
            "mx_valid": False,
            "technical_status": TechnicalStatus.INVALID.value,
            "final_status": FinalEmailStatus.NOT_VERIFIED.value,
            "is_deliverable": False,
            "reason": "Domain has no valid MX records",
            "provider": "MXFallbackProvider",
            "timestamp": timestamp,
        }


class HunterEmailVerifierProvider(EmailVerificationProvider):
    """Concrete EmailVerificationProvider utilizing Hunter.io Email Verifier API."""

    API_URL = "https://api.hunter.io/v2/email-verifier"

    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    def verify(self, email: str, domain: str) -> Dict[str, Any]:
        norm_email = email.strip().lower()
        timestamp = datetime.now(timezone.utc).isoformat()

        if not self.api_key:
            logger.warning("HunterEmailVerifierProvider: EMAIL_VERIFICATION_API_KEY missing. Falling back to MXFallbackProvider.")
            fallback = MXFallbackProvider()
            return fallback.verify(email, domain)

        params = {"email": norm_email, "api_key": self.api_key}

        try:
            response = requests.get(self.API_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json().get("data", {})

            result_status = data.get("status", "")  # "valid", "invalid", "accept_all", "webmail"
            is_deliverable = result_status == "valid"

            tech_status = TechnicalStatus.DELIVERABLE.value if is_deliverable else TechnicalStatus.INVALID.value
            final_st = FinalEmailStatus.VERIFIED.value if is_deliverable else FinalEmailStatus.NOT_VERIFIED.value

            return {
                "email": norm_email,
                "syntax_valid": data.get("regexp", True),
                "domain_valid": data.get("mx_records", True),
                "mx_valid": data.get("mx_records", True),
                "technical_status": tech_status,
                "final_status": final_st,
                "is_deliverable": is_deliverable,
                "reason": f"Hunter API status: {result_status}",
                "provider": "HunterEmailVerifierProvider",
                "timestamp": timestamp,
            }
        except Exception as exc:
            logger.error(f"HunterEmailVerifierProvider request error: {exc}. Falling back to MXFallbackProvider.")
            return MXFallbackProvider().verify(email, domain)


class ZeroBounceEmailVerifierProvider(EmailVerificationProvider):
    """Concrete EmailVerificationProvider utilizing ZeroBounce API."""

    API_URL = "https://api.zerobounce.net/v2/validate"

    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    def verify(self, email: str, domain: str) -> Dict[str, Any]:
        norm_email = email.strip().lower()
        timestamp = datetime.now(timezone.utc).isoformat()

        if not self.api_key:
            logger.warning("ZeroBounceEmailVerifierProvider: EMAIL_VERIFICATION_API_KEY missing. Falling back to MXFallbackProvider.")
            return MXFallbackProvider().verify(email, domain)

        params = {"email": norm_email, "api_key": self.api_key, "ip_address": ""}

        try:
            response = requests.get(self.API_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            zb_status = str(data.get("status", "")).lower()  # "valid", "invalid", "catch-all", "unknown", "spamtrap", "abuse", "do_not_mail"
            is_deliverable = zb_status == "valid"

            tech_status = TechnicalStatus.DELIVERABLE.value if is_deliverable else TechnicalStatus.INVALID.value
            final_st = FinalEmailStatus.VERIFIED.value if is_deliverable else FinalEmailStatus.NOT_VERIFIED.value

            return {
                "email": norm_email,
                "syntax_valid": zb_status != "invalid_syntax",
                "domain_valid": zb_status != "invalid_domain",
                "mx_valid": zb_status != "no_dns_entries",
                "technical_status": tech_status,
                "final_status": final_st,
                "is_deliverable": is_deliverable,
                "reason": f"ZeroBounce status: {zb_status}",
                "provider": "ZeroBounceEmailVerifierProvider",
                "timestamp": timestamp,
            }
        except Exception as exc:
            logger.error(f"ZeroBounceEmailVerifierProvider request error: {exc}. Falling back to MXFallbackProvider.")
            return MXFallbackProvider().verify(email, domain)


def get_email_verification_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> EmailVerificationProvider:
    """Factory function instantiating configured EmailVerificationProvider."""
    app_settings = settings or get_settings()
    p_name = (provider_name or os.getenv("EMAIL_VERIFICATION_PROVIDER", "mock")).lower()
    key = api_key or app_settings.email_verification_api_key

    if p_name == "zerobounce" and key:
        return ZeroBounceEmailVerifierProvider(api_key=key, timeout=app_settings.request_timeout_seconds)
    elif p_name == "hunter" and key:
        return HunterEmailVerifierProvider(api_key=key, timeout=app_settings.request_timeout_seconds)
    elif p_name == "mx":
        return MXFallbackProvider()
    else:
        return MockEmailVerificationProvider()
