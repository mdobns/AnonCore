"""Moderation middleware – pre-flight content filter with Regex + NLP."""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex-based filter (first pass – fast, synchronous)
# ---------------------------------------------------------------------------

# Extend this list as needed; patterns are case-insensitive
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(hate|kill\s+your?self|kys)\b", re.IGNORECASE),
    re.compile(r"\b(n[i1]gg[ae3]r|f[a4]gg[o0]t)\b", re.IGNORECASE),
    re.compile(r"\b(doxx(ing)?|swat(ting)?)\b", re.IGNORECASE),
    re.compile(r"\b(buy\s+(my\s+)?)?(?:crypto|nft)\s*(now|fast|quick)\b", re.IGNORECASE),
    # Phone numbers / emails often used in spam/phishing
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
]


def _regex_check(content: str) -> Optional[str]:
    """Return a violation label if the content matches a blocked pattern, else ``None``."""
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(content):
            return f"regex:{pattern.pattern}"
    return None


# ---------------------------------------------------------------------------
# NLP stub (second pass – plug in Perspective API / spaCy here)
# ---------------------------------------------------------------------------

def _nlp_check(content: str) -> Optional[str]:
    """Run NLP-based toxicity analysis.

    This is a *stub* that can be replaced with a real implementation such as
    the Google Perspective API or a local spaCy model.  It returns a violation
    label string if the content exceeds the toxicity threshold, otherwise
    ``None``.

    Replace the body of this function with your preferred NLP integration::

        # Example: Perspective API
        from googleapiclient import discovery
        client = discovery.build("commentanalyzer", "v1alpha1", ...)
        result = client.comments().analyze(body={
            "comment": {"text": content},
            "requestedAttributes": {"TOXICITY": {}}
        }).execute()
        score = result["attributeScores"]["TOXICITY"]["summaryScore"]["value"]
        if score > 0.85:
            return f"nlp:toxicity:{score:.2f}"
        return None
    """
    # Heuristic stub: flag extremely short all-caps strings as aggressive
    words = content.split()
    if len(words) >= 3 and sum(1 for w in words if w.isupper()) / len(words) > 0.8:
        return "nlp:all_caps_aggression"
    return None


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class ModerationResult:
    """Result of running the moderation pipeline on a piece of content."""

    __slots__ = ("flagged", "violation", "content")

    def __init__(self, flagged: bool, violation: Optional[str], content: str) -> None:
        self.flagged = flagged
        self.violation = violation
        self.content = content

    def __repr__(self) -> str:
        return (
            f"ModerationResult(flagged={self.flagged}, violation={self.violation!r})"
        )


def run_moderation(content: str) -> ModerationResult:
    """Run the full moderation pipeline on *content*.

    Pipeline steps
    --------------
    1. Empty-content guard.
    2. Length limit (10 000 characters).
    3. Regex-based keyword filter.
    4. NLP toxicity model (stub by default).

    Parameters
    ----------
    content:
        The raw text submitted by the user.

    Returns
    -------
    ModerationResult
        ``.flagged`` is ``True`` when content should be rejected.
    """
    if not content or not content.strip():
        return ModerationResult(flagged=True, violation="empty_content", content=content)

    if len(content) > 10_000:
        return ModerationResult(flagged=True, violation="too_long", content=content)

    violation = _regex_check(content)
    if violation:
        logger.info("Content flagged by regex: %s", violation)
        return ModerationResult(flagged=True, violation=violation, content=content)

    violation = _nlp_check(content)
    if violation:
        logger.info("Content flagged by NLP: %s", violation)
        return ModerationResult(flagged=True, violation=violation, content=content)

    return ModerationResult(flagged=False, violation=None, content=content)
