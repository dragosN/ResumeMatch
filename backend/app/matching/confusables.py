"""Known confusable skill pairs that must not auto-match on embedding alone."""

from __future__ import annotations

from app.matching.normalize import canonical_skill

# Pairs that should never be promoted to "matched" by embedding similarity alone.
CONFUSABLE_PAIRS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"java", "javascript"}),
        frozenset({"c", "c++"}),
        frozenset({"c", "csharp"}),
        frozenset({"c++", "csharp"}),
        frozenset({"sql", "mysql"}),
        frozenset({"sql", "postgresql"}),
        frozenset({"mysql", "postgresql"}),
        frozenset({"react", "react native"}),
        frozenset({"aws", "azure"}),
        frozenset({"aws", "gcp"}),
        frozenset({"azure", "gcp"}),
        frozenset({"ml", "mlops"}),
        frozenset({"devops", "sre"}),
    }
)


def is_confusable_pair(skill_a: str, skill_b: str) -> bool:
    """Return True if these skills are known false-positive embedding neighbors."""
    a = canonical_skill(skill_a)
    b = canonical_skill(skill_b)
    if a == b:
        return False
    return frozenset({a, b}) in CONFUSABLE_PAIRS
