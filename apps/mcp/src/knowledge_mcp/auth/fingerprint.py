"""
Abstract: Stable HMAC fingerprinting for MCP Personal Access Tokens.
Out of scope: Bearer parsing, token exchange, and token persistence.
"""

from __future__ import annotations

import hashlib
import hmac


def fingerprint_pat(pat: str, *, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), pat.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"pat_{digest}"
