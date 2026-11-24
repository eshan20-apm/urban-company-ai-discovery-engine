import re
from typing import Tuple, List

# Indian phone number patterns (10 digits starting with 6-9, with optional +91 or 0 prefix)
PHONE_REGEX = re.compile(r'(?:\+?91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b')

# Standard email regex
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

# Indian PIN code (6 digits)
PIN_REGEX = re.compile(r'\b[1-9]\d{2}[\s]?\d{3}\b')

# Common Person name prefixes in Indian feedback
NAME_PREFIX_REGEX = re.compile(
    r'\b(?:technician|partner|beautician|cleaner|electrician|plumber|mr\.|ms\.|mrs\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    re.IGNORECASE
)

class PIIRedactor:
    """Sanitizes sensitive Personally Identifiable Information (PII) from public reviews."""

    def redact(self, text: str) -> Tuple[str, List[str]]:
        """
        Redacts phone numbers, email addresses, pin codes, and technician/customer names.
        Returns the sanitized text and a list of redacted entity types.
        """
        redactions = []
        sanitized = text

        # 1. Redact Emails
        if EMAIL_REGEX.search(sanitized):
            sanitized = EMAIL_REGEX.sub("[REDACTED_EMAIL]", sanitized)
            redactions.append("EMAIL")

        # 2. Redact Phone Numbers
        if PHONE_REGEX.search(sanitized):
            sanitized = PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized)
            redactions.append("PHONE")

        # 3. Redact Names following partner/technician mentions
        def replace_name(match):
            prefix = match.group(0).split()[0]
            return f"{prefix} [REDACTED_NAME]"

        if NAME_PREFIX_REGEX.search(sanitized):
            sanitized = NAME_PREFIX_REGEX.sub(replace_name, sanitized)
            redactions.append("NAME")

        # 4. Redact Indian PIN codes preceded by location clues
        if re.search(r'\b(?:pin|pincode|zip|area)\s*[:-]?\s*[1-9]\d{5}\b', sanitized, re.IGNORECASE):
            sanitized = re.sub(r'\b(?:pin|pincode|zip|area)\s*[:-]?\s*([1-9]\d{5})\b', r'pin: [REDACTED_PIN]', sanitized, flags=re.IGNORECASE)
            redactions.append("PIN")

        return sanitized, redactions

pii_redactor = PIIRedactor()

