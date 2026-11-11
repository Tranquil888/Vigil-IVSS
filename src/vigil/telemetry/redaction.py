"""Remove anything secret before a line reaches the developer log."""

from __future__ import annotations

import re

REDACTED = "[redacted]"
EMBEDDING_OMITTED = "[embedding omitted]"

_CREDENTIALS_IN_URL = re.compile(
    r"(?i)\b(rtsp|rtsps|http|https)://[^\s/@]+@"
)
_BEARER = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)\S+")
_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key)\b\s*[=:]\s*[^\s&,;]+"
)
_VECTOR = re.compile(
    r"\[\s*(?:-?\d+(?:\.\d+)?\s*,\s*){16,}-?\d+(?:\.\d+)?\s*\]"
)


def redact_text(text: str) -> str:
    text = _VECTOR.sub(EMBEDDING_OMITTED, text)
    text = _CREDENTIALS_IN_URL.sub(lambda match: match.group(1) + "://", text)
    text = _BEARER.sub(lambda match: match.group(1) + REDACTED, text)
    text = _ASSIGNMENT.sub(lambda match: match.group(1) + "=" + REDACTED, text)
    return text
