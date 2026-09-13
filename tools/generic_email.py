GENERIC_LOCAL_PARTS = {
    "info",
    "contact",
    "hello",
    "support",
    "admin",
    "sales",
    "jobs",
    "billing",
    "press",
    "media",
    "enquiries",
    "inquiries",
    "help",
    "office",
    "team",
    "general",
    "careers",
    "marketing",
    "service",
    "privacy",
    "legal",
}


def is_generic_email(email: str | None) -> bool:
    """
    Determines whether an email address uses a generic company mailbox prefix.
    Returns True if generic, False if individual/personal.
    """
    if not email or not isinstance(email, str):
        return True

    cleaned = email.strip().lower()
    if "@" not in cleaned:
        return True

    local_part = cleaned.split("@")[0].strip()

    # Direct match against denylist
    if local_part in GENERIC_LOCAL_PARTS:
        return True

    # Handle sub-addressed or hyphenated generic prefixes (e.g. info-us@, contact.us@)
    for generic in GENERIC_LOCAL_PARTS:
        if local_part.startswith(f"{generic}.") or local_part.startswith(f"{generic}-"):
            return True

    return False
