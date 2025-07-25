"""
Utility helpers for the URL shortener service.
"""

from __future__ import annotations

import re
import secrets
import string
from urllib.parse import urlparse


# -------------------------------
# Constants
# -------------------------------

ALPHANUMERIC: str = string.ascii_letters + string.digits
SHORT_CODE_LENGTH: int = 6

# Strict URL regex based on RFC 3986 components (simple but effective).
# We still rely on urlparse for final validation.
_URL_REGEX = re.compile(
    r"^(?:http|https)://"           # scheme
    r"(?:\S+(?::\S*)?@)?"           # user:pass authentication
    r"(?:[A-Za-z0-9\-._~%]+)"       # host
    r"(?::\d{2,5})?"                # optional port
    r"(?:[/?#][^\s]*)?$",           # path / query / fragment
    re.IGNORECASE,
)


# -------------------------------
# Public Functions
# -------------------------------

def generate_short_code() -> str:
    """
    Generate a cryptographically secure, 6-character alphanumeric short code.

    Returns
    -------
    str
        The generated short code.
    """
    return "".join(secrets.choice(ALPHANUMERIC) for _ in range(SHORT_CODE_LENGTH))


def is_valid_url(url: str) -> bool:
    """
    Validate a URL string using a regex and urllib.parse components.

    Parameters
    ----------
    url : str
        The URL to validate.

    Returns
    -------
    bool
        True if valid, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False

    if not _URL_REGEX.match(url):
        return False

    parsed = urlparse(url)
    return all([parsed.scheme, parsed.netloc])
