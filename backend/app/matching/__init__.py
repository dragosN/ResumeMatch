"""Skill matching pipeline: normalize → embed → arbiter → score."""

from app.matching.skill_matcher import MatchResult, match_skills
from app.matching.scorer import compute_scores

__all__ = ["MatchResult", "match_skills", "compute_scores"]
