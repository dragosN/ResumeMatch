"""Embedding similarity helpers."""

from __future__ import annotations

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def best_similarity(
    target_vector: list[float],
    candidate_vectors: list[list[float]],
) -> tuple[int, float]:
    """Return index and highest cosine similarity for candidate vectors."""
    best_idx = -1
    best_sim = -1.0
    for idx, vec in enumerate(candidate_vectors):
        sim = cosine_similarity(target_vector, vec)
        if sim > best_sim:
            best_sim = sim
            best_idx = idx
    return best_idx, best_sim if best_idx >= 0 else 0.0
