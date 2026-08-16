"""Pydantic schemas — source of truth. Hand-mirrored in frontend/src/lib/schemas.ts."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SeniorityLevel(str, Enum):
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    unknown = "unknown"


class ExtractedProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    years_experience: Optional[float] = None
    seniority_level: Optional[SeniorityLevel] = None
    roles: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    summary: str = ""
    # Completeness signals — set by extractor, not the LLM
    extraction_warnings: list[str] = Field(default_factory=list)


class ExtractedRequirements(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    min_years_experience: Optional[float] = None
    seniority_level: Optional[SeniorityLevel] = None
    responsibilities: list[str] = Field(default_factory=list)
    # Exact phrases for ATS keyword check (Day 3); populated during JD extraction
    ats_phrases: list[str] = Field(default_factory=list)
    extraction_warnings: list[str] = Field(default_factory=list)


class MatchConfidence(str, Enum):
    matched = "matched"
    review = "review"
    missing = "missing"


class SkillMatch(BaseModel):
    resume_skill: Optional[str] = None
    jd_skill: str
    confidence: MatchConfidence
    similarity: Optional[float] = None
    reason: Optional[str] = None


class CategoryScores(BaseModel):
    technical: float = 0.0
    experience: float = 0.0
    domain: float = 0.0
    soft: float = 0.0


class AtsFlag(BaseModel):
    phrase: str
    found_in_resume: bool


class RewriteSuggestion(BaseModel):
    original: str
    suggested: str
    targets_skill: str
    rationale: str


class AnalyzeResponse(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    category_scores: CategoryScores = Field(default_factory=CategoryScores)
    matched_skills: list[SkillMatch] = Field(default_factory=list)
    missing_required: list[SkillMatch] = Field(default_factory=list)
    missing_nice_to_have: list[SkillMatch] = Field(default_factory=list)
    overqualified: list[str] = Field(default_factory=list)
    review_band: list[SkillMatch] = Field(default_factory=list)
    summary: str = ""
    profile: Optional[ExtractedProfile] = None
    requirements: Optional[ExtractedRequirements] = None
    ats_flags: list[AtsFlag] = Field(default_factory=list)
    rewrite_suggestions: list[RewriteSuggestion] = Field(default_factory=list)
    # Day 1: when match/score is stubbed
    matching_stubbed: bool = False
