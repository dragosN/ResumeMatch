"""Evaluate skill-pair matching precision/recall on labeled set."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.extraction.schemas import MatchConfidence
from app.matching.confusables import is_confusable_pair
from app.matching.embeddings import cosine_similarity
from app.matching.normalize import is_weaker_than_requirement, skill_satisfies
from app.matching.skill_matcher import classify_pair
from app.llm.provider import EmbeddingProvider

EVAL_PATH = Path(__file__).resolve().parent / "skill_pairs.jsonl"


@dataclass
class EvalMetrics:
    precision: float
    recall: float
    f1: float
    total: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int


def load_skill_pairs(path: Path | None = None) -> list[dict]:
    pairs: list[dict] = []
    with open(path or EVAL_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pairs.append(json.loads(line))
    return pairs


def predict_match(
    resume_skill: str,
    jd_skill: str,
    similarity: float,
    *,
    match_threshold: float = 0.85,
    review_threshold: float = 0.65,
) -> bool:
    """Positive prediction = matched (review band counts as negative for strict eval)."""
    if skill_satisfies(resume_skill, jd_skill):
        return True
    if is_weaker_than_requirement(resume_skill, jd_skill):
        return False
    if is_confusable_pair(resume_skill, jd_skill):
        return False
    confidence, _ = classify_pair(
        resume_skill,
        jd_skill,
        similarity,
        match_threshold=match_threshold,
        review_threshold=review_threshold,
    )
    return confidence == MatchConfidence.matched


def run_eval(
    embedder: EmbeddingProvider,
    *,
    match_threshold: float = 0.85,
    review_threshold: float = 0.65,
    path: Path | None = None,
) -> EvalMetrics:
    pairs = load_skill_pairs(path)
    unique_skills = list(
        dict.fromkeys(
            [p["resume_skill"] for p in pairs] + [p["jd_skill"] for p in pairs]
        )
    )
    vectors = embedder.embed(unique_skills)
    skill_vec = dict(zip(unique_skills, vectors))

    tp = fp = fn = tn = 0
    for pair in pairs:
        rs, js = pair["resume_skill"], pair["jd_skill"]
        expected = pair["label"] == "match"
        sim = cosine_similarity(skill_vec[rs], skill_vec[js])
        predicted = predict_match(
            rs,
            js,
            sim,
            match_threshold=match_threshold,
            review_threshold=review_threshold,
        )
        if predicted and expected:
            tp += 1
        elif predicted and not expected:
            fp += 1
        elif not predicted and expected:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return EvalMetrics(
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(f1, 3),
        total=len(pairs),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
    )


if __name__ == "__main__":
    from app.llm.provider import get_embedding_provider

    metrics = run_eval(get_embedding_provider())
    print(f"Eval on {metrics.total} labeled pairs:")
    print(f"  Precision: {metrics.precision:.1%}")
    print(f"  Recall:    {metrics.recall:.1%}")
    print(f"  F1:        {metrics.f1:.3f}")
    print(f"  TP={metrics.true_positives} FP={metrics.false_positives} "
          f"FN={metrics.false_negatives} TN={metrics.true_negatives}")
