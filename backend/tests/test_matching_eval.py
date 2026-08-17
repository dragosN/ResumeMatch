"""Precision/recall on labeled skill pairs (synonym + threshold rules; no Ollama required)."""

from __future__ import annotations

from app.extraction.schemas import MatchConfidence
from app.matching.confusables import is_confusable_pair
from app.matching.embeddings import cosine_similarity
from app.matching.normalize import is_weaker_than_requirement, skill_satisfies, skills_equivalent
from app.matching.skill_matcher import classify_pair
from eval.run_eval import EVAL_PATH, load_skill_pairs, predict_match
from tests.conftest import FakeEmbeddingProvider


def _eval_with_embedder(embedder) -> dict:
    pairs = load_skill_pairs(EVAL_PATH)
    unique = list(
        dict.fromkeys([p["resume_skill"] for p in pairs] + [p["jd_skill"] for p in pairs])
    )
    vectors = embedder.embed(unique)
    skill_vec = dict(zip(unique, vectors))

    tp = fp = fn = tn = 0
    for pair in pairs:
        rs, js = pair["resume_skill"], pair["jd_skill"]
        expected = pair["label"] == "match"
        sim = cosine_similarity(skill_vec[rs], skill_vec[js])

        # Layer 1: synonyms / implications always match
        if skill_satisfies(rs, js):
            predicted = True
        elif is_weaker_than_requirement(rs, js):
            predicted = False
        elif is_confusable_pair(rs, js):
            predicted = False
        else:
            conf, _ = classify_pair(rs, js, sim)
            predicted = conf == MatchConfidence.matched

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
    return {"precision": precision, "recall": recall, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def test_synonym_pairs_always_match():
    """Pairs labeled match that share a canonical form must resolve via normalize layer."""
    pairs = load_skill_pairs(EVAL_PATH)
    from app.matching.normalize import canonical_skill

    synonym_pairs = [
        p
        for p in pairs
        if p["label"] == "match"
        and canonical_skill(p["resume_skill"]) == canonical_skill(p["jd_skill"])
    ]
    for pair in synonym_pairs:
        assert skills_equivalent(pair["resume_skill"], pair["jd_skill"]), pair


def test_confusable_pairs_never_auto_match():
    pairs = load_skill_pairs(EVAL_PATH)
    confusables = [p for p in pairs if p["label"] == "no_match" and is_confusable_pair(p["resume_skill"], p["jd_skill"])]
    for pair in confusables:
        sim = 0.99  # even with high embedding similarity
        assert not predict_match(pair["resume_skill"], pair["jd_skill"], sim)


def test_eval_synonym_layer_precision():
    """Synonym + confusable rules alone should achieve high precision on labeled set."""
    metrics = _eval_with_embedder(FakeEmbeddingProvider())
    # Fake embedder won't cover all semantic pairs; synonym+confusable rules still testable
    assert metrics["precision"] >= 0.75, metrics
    assert metrics["tp"] + metrics["fn"] > 0
