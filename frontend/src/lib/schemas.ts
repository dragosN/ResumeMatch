/**
 * Zod schemas hand-mirrored from backend/app/extraction/schemas.py (Pydantic SoT).
 */
import { z } from "zod";

export const SeniorityLevelSchema = z.enum([
  "junior",
  "mid",
  "senior",
  "lead",
  "unknown",
]);

export const ExtractedProfileSchema = z.object({
  skills: z.array(z.string()),
  years_experience: z.number().nullable().optional(),
  seniority_level: SeniorityLevelSchema.nullable().optional(),
  roles: z.array(z.string()),
  education: z.array(z.string()),
  summary: z.string(),
  extraction_warnings: z.array(z.string()).default([]),
});

export const ExtractedRequirementsSchema = z.object({
  required_skills: z.array(z.string()),
  nice_to_have_skills: z.array(z.string()),
  min_years_experience: z.number().nullable().optional(),
  seniority_level: SeniorityLevelSchema.nullable().optional(),
  responsibilities: z.array(z.string()),
  ats_phrases: z.array(z.string()).default([]),
  extraction_warnings: z.array(z.string()).default([]),
});

export const MatchConfidenceSchema = z.enum(["matched", "review", "missing"]);

export const SkillMatchSchema = z.object({
  resume_skill: z.string().nullable().optional(),
  jd_skill: z.string(),
  confidence: MatchConfidenceSchema,
  similarity: z.number().nullable().optional(),
  reason: z.string().nullable().optional(),
});

export const CategoryScoresSchema = z.object({
  technical: z.number(),
  experience: z.number(),
  domain: z.number(),
  soft: z.number(),
});

export const AtsFlagSchema = z.object({
  phrase: z.string(),
  found_in_resume: z.boolean(),
});

export const RewriteSuggestionSchema = z.object({
  original: z.string(),
  suggested: z.string(),
  targets_skill: z.string(),
  rationale: z.string(),
});

export const AnalyzeResponseSchema = z.object({
  overall_score: z.number().min(0).max(100),
  category_scores: CategoryScoresSchema,
  matched_skills: z.array(SkillMatchSchema),
  missing_required: z.array(SkillMatchSchema),
  missing_nice_to_have: z.array(SkillMatchSchema),
  overqualified: z.array(z.string()),
  review_band: z.array(SkillMatchSchema),
  summary: z.string(),
  profile: ExtractedProfileSchema.nullable().optional(),
  requirements: ExtractedRequirementsSchema.nullable().optional(),
  ats_flags: z.array(AtsFlagSchema).default([]),
  rewrite_suggestions: z.array(RewriteSuggestionSchema).default([]),
  matching_stubbed: z.boolean().default(false),
});

export const JdComparisonItemSchema = z.object({
  label: z.string(),
  overall_score: z.number().min(0).max(100),
  summary: z.string(),
  top_gaps: z.array(z.string()),
  result: AnalyzeResponseSchema,
});

export const CompareResponseSchema = z.object({
  ranked: z.array(JdComparisonItemSchema),
  profile: ExtractedProfileSchema.nullable().optional(),
});

export type AnalyzeResponse = z.infer<typeof AnalyzeResponseSchema>;
export type CompareResponse = z.infer<typeof CompareResponseSchema>;
export type JdComparisonItem = z.infer<typeof JdComparisonItemSchema>;
export type SkillMatch = z.infer<typeof SkillMatchSchema>;
export type CategoryScores = z.infer<typeof CategoryScoresSchema>;
export type AtsFlag = z.infer<typeof AtsFlagSchema>;
export type RewriteSuggestion = z.infer<typeof RewriteSuggestionSchema>;
