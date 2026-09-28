
"""Conservative checks for ambiguous operational action requests."""

import re


ADVICE_PATTERNS = (
    r"\bshould\s+i\b",
    r"\bshould\s+we\b",
    r"\bdo\s+i\s+need\s+to\b",
    r"\bdo\s+we\s+need\s+to\b",
    r"\bwould\s+it\s+be\s+(?:safe|wise|appropriate)\b",
    r"\bis\s+it\s+(?:safe|wise|appropriate)\s+to\b",
    r"\bwhat\s+(?:if|happens\s+if)\b",
    r"\bbefore\s+i\s+decide\b",
    r"\bbefore\s+we\s+decide\b",
)


def is_advice_request(query: str) -> bool:
    """
    Detect questions about whether an operational action
    should be taken, rather than an instruction to take it.

    This is a conservative safeguard, not a complete
    natural-language authorization system.
    """
    normalized = " ".join(query.casefold().split())

    return any(
        re.search(pattern, normalized)
        for pattern in ADVICE_PATTERNS
    )