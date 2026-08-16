"use client";

import { useEffect, useState } from "react";
import type { AnalyzeResponse, SkillMatch } from "@/lib/schemas";

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

const toneColor: Record<"matched" | "missing" | "review" | "nice" | "over", string> = {
  matched: "var(--match)",
  missing: "var(--gap)",
  review: "var(--review)",
  nice: "var(--nice)",
  over: "#5b4a8a",
};

export function ResultsView({ result }: { result: AnalyzeResponse }) {
  const score = useCountUp(Math.round(result.overall_score));
  const cats = result.category_scores;

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
          Note — matching is stubbed (exact-name overlap). Semantic pipeline lands Day 2.
        </p>
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

        <div className="grid grid-cols-2 gap-x-8 gap-y-5 sm:grid-cols-4">
          {(
            [
              ["Technical", cats.technical],
              ["Experience", cats.experience],
              ["Domain", cats.domain],
              ["Soft", cats.soft],
            ] as const
          ).map(([label, value], i) => (
            <div key={label} style={{ animationDelay: `${120 + i * 60}ms` }} className="anim-rise">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-[12px] font-medium text-[var(--muted)]">{label}</span>
                <span
                  className="text-sm font-semibold tabular-nums text-[var(--ink)]"
                  style={{ fontFamily: "var(--font-mono), monospace" }}
                >
                  {Math.round(value)}
                </span>
              </div>
              <div className="mt-2 h-[3px] overflow-hidden bg-[var(--line)]">
                <div
                  className="anim-bar h-full bg-[var(--ink)]"
                  style={{
                    width: `${Math.min(100, Math.max(0, value))}%`,
                    animationDelay: `${200 + i * 80}ms`,
                  }}
                />
              </div>
            </div>
          ))}
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
                  Requirements · {result.requirements.ats_phrases?.length ?? 0} ATS
                  phrases
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

function SkillGroup({
  title,
  tone,
  items,
  delay,
}: {
  title: string;
  tone: "matched" | "missing" | "review" | "nice" | "over";
  items: string[];
  delay: number;
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
