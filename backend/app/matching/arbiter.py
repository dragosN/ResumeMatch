"""LLM arbiter for review-band skill pairs only."""

from __future__ import annotations

from app.llm.provider import ChatProvider

ARBITER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "is_match": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["is_match", "reason"],
}

SYSTEM = """You are a strict technical recruiter assistant.
Given a candidate resume skill and a job requirement, decide whether the candidate skill
satisfies the requirement. Be conservative: only say yes when the skill genuinely covers
the requirement. Similar names that refer to different technologies (e.g. Java vs JavaScript)
must be rejected."""


def arbitrate_match(
    resume_skill: str,
    jd_skill: str,
    *,
    similarity: float,
    chat: ChatProvider,
) -> tuple[bool, str]:
    """Ask the LLM whether resume_skill satisfies jd_skill. Returns (is_match, reason)."""
    user = (
        f'Resume skill: "{resume_skill}"\n'
        f'Job requirement: "{jd_skill}"\n'
        f"Embedding similarity (for context only): {similarity:.2f}\n\n"
        "Does the resume skill satisfy the job requirement?"
    )
    try:
        result = chat.complete_json(SYSTEM, user, ARBITER_SCHEMA)
        is_match = bool(result.get("is_match"))
        reason = str(result.get("reason", "")).strip() or "LLM arbiter decision"
        return is_match, reason
    except Exception as exc:  # noqa: BLE001
        return False, f"Arbiter unavailable — kept in review ({exc})"
