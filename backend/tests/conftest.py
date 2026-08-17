"""Shared test fixtures for matching pipeline."""

from __future__ import annotations

from app.llm.provider import EmbeddingProvider
from app.matching.normalize import canonical_skill


# Hand-tuned unit vectors for deterministic embedding tests.
# Similar skills share dimensions; confusables are close but below match threshold.
_SKILL_VECTORS: dict[str, list[float]] = {
    "react": [1.0, 0.0, 0.0, 0.0],
    "component-based ui development": [0.92, 0.08, 0.0, 0.0],
    "angular": [0.0, 1.0, 0.0, 0.0],
    "javascript": [0.0, 0.0, 1.0, 0.0],
    "java": [0.0, 0.0, 0.82, 0.18],
    "python": [0.0, 0.0, 0.0, 1.0],
    "ruby": [0.0, 0.0, 0.0, 0.85],
    "typescript": [0.15, 0.0, 0.55, 0.35],
    "graphql": [0.0, 0.0, 0.0, 0.95],
    "node": [0.7, 0.0, 0.3, 0.0],
    "kubernetes": [0.0, 0.0, 0.0, 0.9],
    "docker": [0.0, 0.0, 0.0, 0.88],
    "postgresql": [0.0, 0.5, 0.0, 0.5],
    "mysql": [0.0, 0.48, 0.0, 0.52],
    "aws": [0.5, 0.5, 0.0, 0.0],
    "azure": [0.48, 0.52, 0.0, 0.0],
}


class FakeEmbeddingProvider:
    """Deterministic embedder for unit tests."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_lookup_vector(t) for t in texts]


def _lookup_vector(text: str) -> list[float]:
    key = canonical_skill(text)
    if key in _SKILL_VECTORS:
        return _SKILL_VECTORS[key]
    # Unknown skills: hash to a sparse vector
    vec = [0.0, 0.0, 0.0, 0.0]
    for i, ch in enumerate(key[:8]):
        vec[i % 4] += (ord(ch) % 17) / 100.0
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec] if norm else vec
