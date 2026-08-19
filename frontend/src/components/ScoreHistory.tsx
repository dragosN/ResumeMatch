"use client";

import type { HistoryEntry } from "@/lib/history";

export function ScoreHistory({ entries }: { entries: HistoryEntry[] }) {
  if (entries.length === 0) return null;

  return (
    <section className="anim-rise border-t border-[var(--line)] pt-8">
      <h2
        className="text-lg font-bold tracking-tight text-[var(--ink)]"
        style={{ fontFamily: "var(--font-display), sans-serif" }}
      >
        Score history
      </h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Last {entries.length} run{entries.length === 1 ? "" : "s"} stored locally in this browser.
      </p>
      <ul className="mt-4 divide-y divide-[var(--line)] border border-[var(--line)]">
        {entries.map((entry) => (
          <li
            key={entry.id}
            className="flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 text-sm"
          >
            <div className="min-w-0">
              <p className="truncate font-medium text-[var(--ink)]">{entry.jdLabel}</p>
              <p
                className="text-xs text-[var(--muted)]"
                style={{ fontFamily: "var(--font-mono), monospace" }}
              >
                {new Date(entry.timestamp).toLocaleString()}
                {entry.mode === "compare" ? " · compare" : ""}
              </p>
            </div>
            <div className="text-right">
              <p
                className="text-lg font-bold tabular-nums text-[var(--ink)]"
                style={{ fontFamily: "var(--font-display), sans-serif" }}
              >
                {entry.score}
              </p>
              {entry.compareScores && entry.compareScores.length > 1 && (
                <p className="text-[11px] text-[var(--muted)]">
                  {entry.compareScores.map((c) => `${c.score}`).join(" · ")}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
