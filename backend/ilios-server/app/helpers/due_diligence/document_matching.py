"""Read-only Document Identity matching for guided upload / duplicate prevention (Task #92).

Pure, side-effect-free name matching used by the duplicate-check endpoint so that
when a user is about to create a *new* Document Identity in a site's Data Room, we
can advise them that one or more existing identities look like the same business
document (e.g. a proposed "PVsyst" against an existing "PVsyst Final" /
"PVsyst Revised").

This is strictly advisory: it NEVER blocks, mutates, or creates anything. The
caller decides whether to upload a new version to an existing identity or to
explicitly create a separate one. There is intentionally no DB access here so the
ranking logic stays trivially testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

# Sequence-ratio threshold above which two normalized names count as a near match
# even when neither contains the other. Tuned to flag obvious typos / reorderings
# without flooding the user with weak guesses.
NEAR_MATCH_RATIO = 0.82

# Default maximum number of candidates returned, best (highest score) first.
MAX_CANDIDATES = 5

# Tokens that describe a *version / revision* of a document rather than the
# document's identity. They are ignored when comparing the "significant" core of
# two names so that "PVsyst Final" and "PVsyst Revised" both reduce to "pvsyst".
_VERSION_TOKENS = frozenset(
    {
        "final",
        "draft",
        "revised",
        "revision",
        "rev",
        "version",
        "ver",
        "copy",
        "updated",
        "update",
        "new",
        "old",
        "latest",
        "current",
        "previous",
        "prior",
        "signed",
        "executed",
        "clean",
        "redline",
        "amended",
        "amendment",
    }
)

_PUNCT_RE = re.compile(r"[^a-z0-9]+")
_VERSION_NUMBER_RE = re.compile(r"^v?\d+(?:\.\d+)*$")


@dataclass
class DuplicateMatch:
    """A single existing identity that resembles a proposed document name."""

    document_id: int
    name: str
    kind: str | None
    section_id: int | None
    section_name: str | None
    files_count: int
    is_archived: bool
    match_type: str  # "exact" | "near"
    score: float


@dataclass
class IdentityCandidate:
    """A flattened view of an existing Document Identity to compare against.

    ``names`` carries every string the identity may be known by (resolved
    identity name + aliases + raw enum value) so an alias can trigger a match.
    """

    document_id: int
    display_name: str
    names: list[str]
    kind: str | None
    section_id: int | None
    section_name: str | None
    files_count: int
    is_archived: bool


def normalize_name(value: str | None) -> str:
    """Lowercase, strip punctuation, and collapse whitespace for comparison."""
    if not value:
        return ""
    lowered = value.strip().lower()
    cleaned = _PUNCT_RE.sub(" ", lowered)
    return " ".join(cleaned.split())


def _significant_tokens(normalized: str) -> set[str]:
    """Identity-bearing tokens: drops version words and bare version numbers."""
    tokens = normalized.split()
    return {
        token
        for token in tokens
        if token not in _VERSION_TOKENS and not _VERSION_NUMBER_RE.match(token)
    }


def _score_pair(proposed_norm: str, candidate_norm: str) -> tuple[str | None, float]:
    """Classify a proposed vs. candidate normalized name.

    Returns ``(match_type, score)`` where match_type is ``"exact"``, ``"near"``,
    or ``None`` when the names are not considered related.
    """
    if not proposed_norm or not candidate_norm:
        return None, 0.0

    if proposed_norm == candidate_norm:
        return "exact", 1.0

    proposed_sig = _significant_tokens(proposed_norm)
    candidate_sig = _significant_tokens(candidate_norm)

    # Same identity core after dropping version words (e.g. "pvsyst" vs
    # "pvsyst final") -> treat as an exact identity match.
    if proposed_sig and proposed_sig == candidate_sig:
        return "exact", 0.99

    ratio = SequenceMatcher(None, proposed_norm, candidate_norm).ratio()

    # One identity's significant core fully contains the other's -> near match
    # ("pvsyst" within "pvsyst post permit"). Score blends containment with the
    # raw ratio so closer lengths rank higher.
    if proposed_sig and candidate_sig:
        if proposed_sig <= candidate_sig or candidate_sig <= proposed_sig:
            shared = len(proposed_sig & candidate_sig)
            largest = max(len(proposed_sig), len(candidate_sig))
            containment = shared / largest if largest else 0.0
            return "near", max(ratio, 0.6 + 0.4 * containment)

    if ratio >= NEAR_MATCH_RATIO:
        return "near", ratio

    return None, 0.0


def find_duplicate_candidates(
    proposed_name: str,
    candidates: list[IdentityCandidate],
    limit: int = MAX_CANDIDATES,
) -> list[DuplicateMatch]:
    """Return existing identities that resemble ``proposed_name``, best first.

    Exact matches always outrank near matches; within a tier the higher score
    wins, then identities that already have uploaded files (more likely the real
    home for a new version) are preferred.
    """
    proposed_norm = normalize_name(proposed_name)
    if not proposed_norm:
        return []

    matches: list[DuplicateMatch] = []
    for candidate in candidates:
        best_type: str | None = None
        best_score = 0.0
        for name in candidate.names:
            match_type, score = _score_pair(proposed_norm, normalize_name(name))
            if match_type is None:
                continue
            # Prefer an exact hit; otherwise keep the strongest score seen.
            if best_type is None or (match_type == "exact" and best_type != "exact") or score > best_score:
                best_type = match_type
                best_score = score
        if best_type is None:
            continue
        matches.append(
            DuplicateMatch(
                document_id=candidate.document_id,
                name=candidate.display_name,
                kind=candidate.kind,
                section_id=candidate.section_id,
                section_name=candidate.section_name,
                files_count=candidate.files_count,
                is_archived=candidate.is_archived,
                match_type=best_type,
                score=round(best_score, 4),
            )
        )

    matches.sort(
        key=lambda m: (m.match_type == "exact", m.score, m.files_count),
        reverse=True,
    )
    return matches[:limit]
