"use client";

import { useEffect, useState } from "react";
import { CategoryChart } from "@/components/CategoryChart";
import type {
  AnalyzeResponse,
  CompareResponse,
  JdComparisonItem,
  RewriteSuggestion,
  SkillMatch,
} from "@/lib/schemas";

function skillLabel(m: SkillMatch): string {
  if (m.resume_skill && m.resume_skill !== m.jd_skill) {
    return `${m.resume_skill} → ${m.jd_skill}`;
  }
  return m.jd_skill;
}

function useCountUp(target: number, durationMs = 700) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(Math.round(target * eased));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs]);
  return value;
}

const toneColor: Record<"matched" | "missing" | "review" | "nice" | "over" | "ats-ok" | "ats-miss", string> = {
  matched: "var(--match)",
  missing: "var(--gap)",
  review: "var(--review)",
  nice: "var(--nice)",
  over: "#5b4a8a",
  "ats-ok": "var(--match)",
  "ats-miss": "var(--gap)",
};

type Props = {
  result: AnalyzeResponse;
  compare?: CompareResponse | null;
  selectedCompareIndex?: number;
  onSelectCompare?: (index: number) => void;
};

export function ResultsView({
  result,
  compare,
  selectedCompareIndex = 0,
  onSelectCompare,
}: Props) {
  const score = useCountUp(Math.round(result.overall_score));
  const cats = result.category_scores;
  const atsFound = result.ats_flags.filter((f) => f.found_in_resume);
  const atsMissing = result.ats_flags.filter((f) => !f.found_in_resume);

  return (
    <section
      id="results"
      className="anim-rise space-y-12 border-t-2 border-[var(--ink)] pt-10"
    >
      {result.matching_stubbed && (
        <p
          className="text-xs text-[var(--muted)]"
          style={{ fontFamily: "var(--font-mono), monospace" }}
        >
          Demo mode — stub data with sample ATS flags and rewrite suggestions.
        </p>
      )}

      {compare && compare.ranked.length > 1 && (
        <CompareRanked
          ranked={compare.ranked}
          selectedIndex={selectedCompareIndex}
          onSelect={onSelectCompare}
        />
      )}

      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] lg:items-end">
        <div className="anim-score">
          <p
            className="text-[11px] font-medium uppercase tracking-[0.16em] text-[var(--muted)]"
            style={{ fontFamily: "var(--font-mono), monospace" }}
          >
            Overall match
          </p>
          <p
            className="mt-1 text-[clamp(4.5rem,14vw,7.5rem)] font-extrabold leading-none tracking-[-0.05em] text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display), sans-serif" }}
          >
            {score}
            <span className="ml-1 text-3xl font-semibold text-[var(--muted)]">/100</span>
          </p>
        </div>

        <div>
          <p className="mb-3 text-[12px] font-medium text-[var(--muted)]">Category breakdown</p>
          <CategoryChart scores={cats} />
        </div>
      </div>

      <div>
        <h2
          className="text-xl font-bold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display), sans-serif" }}
        >
          Reading
        </h2>
        <p className="mt-3 max-w-3xl text-[1.05rem] leading-[1.65] text-[var(--ink)]">
          {result.summary}
        </p>
      </div>

      {result.ats_flags.length > 0 && (
        <div className="grid gap-10 md:grid-cols-2">
          <SkillGroup
            title="ATS keywords found"
            tone="ats-ok"
            items={atsFound.map((f) => f.phrase)}
            delay={0}
            hint="Exact phrases present in resume text"
          />
          <SkillGroup
            title="ATS keywords missing"
            tone="ats-miss"
            items={atsMissing.map((f) => f.phrase)}
            delay={40}
            hint="Literal JD phrases not found — add if truthful"
          />
        </div>
      )}

      <div className="grid gap-10 md:grid-cols-2">
        <SkillGroup
          title="Matched"
          tone="matched"
          items={result.matched_skills.map(skillLabel)}
          delay={0}
        />
        <SkillGroup
          title="Missing required"
          tone="missing"
          items={result.missing_required.map(skillLabel)}
          delay={40}
        />
        <SkillGroup
          title="Missing nice-to-have"
          tone="nice"
          items={result.missing_nice_to_have.map(skillLabel)}
          delay={80}
        />
        <SkillGroup
          title="Review band"
          tone="review"
          items={result.review_band.map(skillLabel)}
          delay={120}
        />
        {result.overqualified.length > 0 && (
          <SkillGroup
            title="Overqualified"
            tone="over"
            items={result.overqualified}
            delay={160}
          />
        )}
      </div>

      {result.rewrite_suggestions.length > 0 && (
        <RewriteSection suggestions={result.rewrite_suggestions} />
      )}

      {(result.profile || result.requirements) && (
        <div className="grid gap-6 border-t border-[var(--line)] pt-8 md:grid-cols-2">
          {result.profile && (
            <details className="group">
              <summary className="cursor-pointer list-none text-sm font-semibold text-[var(--ink)] marker:content-none [&::-webkit-details-marker]:hidden">
                <span className="border-b border-dashed border-[var(--line)] pb-0.5 group-open:border-[var(--ink)]">
                  Extracted profile · {result.profile.skills.length} skills
                </span>
              </summary>
              <pre
                className="mt-4 max-h-64 overflow-auto bg-[var(--panel)] p-4 text-[11px] leading-relaxed text-[var(--muted)]"
                style={{ fontFamily: "var(--font-mono), monospace" }}
              >
                {JSON.stringify(result.profile, null, 2)}
              </pre>
            </details>
          )}
          {result.requirements && (
            <details className="group">
              <summary className="cursor-pointer list-none text-sm font-semibold text-[var(--ink)] marker:content-none [&::-webkit-details-marker]:hidden">
                <span className="border-b border-dashed border-[var(--line)] pb-0.5 group-open:border-[var(--ink)]">
                  Requirements · {result.requirements.ats_phrases?.length ?? 0} ATS phrases
                </span>
              </summary>
              <pre
                className="mt-4 max-h-64 overflow-auto bg-[var(--panel)] p-4 text-[11px] leading-relaxed text-[var(--muted)]"
                style={{ fontFamily: "var(--font-mono), monospace" }}
              >
                {JSON.stringify(result.requirements, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </section>
  );
}

function CompareRanked({
  ranked,
  selectedIndex,
  onSelect,
}: {
  ranked: JdComparisonItem[];
  selectedIndex: number;
  onSelect?: (index: number) => void;
}) {
  return (
    <div>
      <h2
        className="text-lg font-bold tracking-tight text-[var(--ink)]"
        style={{ fontFamily: "var(--font-display), sans-serif" }}
      >
        JD comparison
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Ranked by match score — select a role to inspect details.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {ranked.map((item, idx) => {
          const active = idx === selectedIndex;
          return (
            <button
              key={`${item.label}-${idx}`}
              type="button"
              onClick={() => onSelect?.(idx)}
              className={`border p-4 text-left transition-colors ${
                active
                  ? "border-[var(--ink)] bg-[var(--panel)]"
                  : "border-[var(--line)] bg-transparent hover:border-[var(--muted)]"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold leading-snug text-[var(--ink)]">
                  {idx === 0 && (
                    <span className="mr-2 text-[10px] font-bold uppercase tracking-wider text-[var(--signal)]">
                      Best
                    </span>
                  )}
                  {item.label}
                </p>
                <span
                  className="shrink-0 text-xl font-bold tabular-nums text-[var(--ink)]"
                  style={{ fontFamily: "var(--font-display), sans-serif" }}
                >
                  {Math.round(item.overall_score)}
                </span>
              </div>
              {item.top_gaps.length > 0 && (
                <p className="mt-2 text-xs text-[var(--muted)]">
                  Gaps: {item.top_gaps.slice(0, 3).join(", ")}
                </p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function RewriteSection({ suggestions }: { suggestions: RewriteSuggestion[] }) {
  return (
    <div>
      <h2
        className="text-xl font-bold tracking-tight text-[var(--ink)]"
        style={{ fontFamily: "var(--font-display), sans-serif" }}
      >
        Rewrite suggestions
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Tailor existing bullets with JD phrasing — only apply changes that reflect real experience.
      </p>
      <ul className="mt-4 space-y-4">
        {suggestions.map((s, i) => (
          <li key={`${s.targets_skill}-${i}`} className="border border-[var(--line)] p-4">
            <p
              className="text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]"
              style={{ fontFamily: "var(--font-mono), monospace" }}
            >
              Targets: {s.targets_skill}
            </p>
            <p className="mt-2 text-sm text-[var(--muted)] line-through decoration-[var(--line)]">
              {s.original}
            </p>
            <p className="mt-2 text-sm font-medium leading-relaxed text-[var(--ink)]">
              {s.suggested}
            </p>
            <p className="mt-2 text-xs text-[var(--muted)]">{s.rationale}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SkillGroup({
  title,
  tone,
  items,
  delay,
  hint,
}: {
  title: string;
  tone: "matched" | "missing" | "review" | "nice" | "over" | "ats-ok" | "ats-miss";
  items: string[];
  delay: number;
  hint?: string;
}) {
  return (
    <div className="anim-rise" style={{ animationDelay: `${delay}ms` }}>
      <div className="mb-3 flex items-center gap-2">
        <span
          className="inline-block size-2.5 shrink-0"
          style={{ background: toneColor[tone] }}
          aria-hidden
        />
        <h3
          className="text-sm font-semibold tracking-wide text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display), sans-serif" }}
        >
          {title}
        </h3>
      </div>
      {hint && <p className="mb-2 text-xs text-[var(--muted)]">{hint}</p>}
      {items.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">None</p>
      ) : (
        <ul className="space-y-1.5">
          {items.map((item) => (
            <li
              key={`${title}-${item}`}
              className="border-l-2 pl-3 text-sm leading-snug text-[var(--ink)]"
              style={{ borderColor: toneColor[tone] }}
            >
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
