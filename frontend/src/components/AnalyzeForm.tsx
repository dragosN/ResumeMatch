"use client";

import { FormEvent, useEffect, useState } from "react";
import { ResultsView } from "@/components/ResultsView";
import { ScoreHistory } from "@/components/ScoreHistory";
import { isCompareMode, runAnalysis, type JdSlot } from "@/lib/api";
import {
  fingerprintResume,
  historyFromCompare,
  historyFromSingle,
  loadHistory,
  saveHistoryEntry,
  type HistoryEntry,
} from "@/lib/history";
import type { AnalyzeResponse, CompareResponse } from "@/lib/schemas";

const emptySlot = (): JdSlot => ({ text: "", url: "", file: null });

function jdLabelFromSlot(slot: JdSlot, index: number): string {
  const line = slot.text.trim().split("\n")[0]?.slice(0, 50);
  if (line) return line;
  if (slot.file?.name) return slot.file.name;
  if (slot.url.trim()) return slot.url.trim();
  return `JD ${index + 1}`;
}

export function AnalyzeForm() {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [jdSlots, setJdSlots] = useState<JdSlot[]>([emptySlot()]);
  const [useStub, setUseStub] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [compare, setCompare] = useState<CompareResponse | null>(null);
  const [selectedCompareIndex, setSelectedCompareIndex] = useState(0);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  function updateSlot(index: number, patch: Partial<JdSlot>) {
    setJdSlots((prev) => prev.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  }

  function addJdSlot() {
    setJdSlots((prev) => (prev.length >= 3 ? prev : [...prev, emptySlot()]));
  }

  function removeJdSlot(index: number) {
    setJdSlots((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setResult(null);
    setCompare(null);

    try {
      const output = await runAnalysis({
        resumeFile,
        resumeText,
        jdSlots,
        useStub,
      });

      const fp = fingerprintResume(resumeText, resumeFile?.name);

      if (output.mode === "compare") {
        setCompare(output.compare);
        setSelectedCompareIndex(0);
        const best = output.compare.ranked[0]?.result ?? null;
        setResult(best);
        const entry = historyFromCompare(output.compare, fp);
        setHistory(saveHistoryEntry(entry));
      } else {
        setResult(output.result);
        const label = jdLabelFromSlot(jdSlots[0], 0);
        const entry = historyFromSingle(output.result, label, fp);
        setHistory(saveHistoryEntry(entry));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const compareMode = isCompareMode(jdSlots);
  const activeResult =
    compare && compare.ranked[selectedCompareIndex]
      ? compare.ranked[selectedCompareIndex].result
      : result;

  return (
    <div className="space-y-14">
      <form id="workspace" onSubmit={onSubmit} className="scroll-mt-8 space-y-10">
        <div className="grid gap-10 lg:grid-cols-2 lg:gap-12">
          <section className="anim-rise" style={{ animationDelay: "80ms" }}>
            <div className="mb-4 flex items-baseline justify-between gap-3 border-b border-[var(--line)] pb-3">
              <h2
                className="text-2xl font-bold tracking-tight text-[var(--ink)]"
                style={{ fontFamily: "var(--font-display), sans-serif" }}
              >
                Resume
              </h2>
              <span
                className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]"
                style={{ fontFamily: "var(--font-mono), monospace" }}
              >
                Source A
              </span>
            </div>

            <label className="block text-sm">
              <span className="mb-2 block text-[13px] font-medium text-[var(--muted)]">
                PDF or DOCX
              </span>
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md,application/pdf"
                className="file-btn block w-full text-sm text-[var(--muted)]"
                onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
              />
              {resumeFile && (
                <p
                  className="mt-2 text-xs text-[var(--ink)]"
                  style={{ fontFamily: "var(--font-mono), monospace" }}
                >
                  {resumeFile.name}
                </p>
              )}
            </label>

            <label className="mt-6 block text-sm">
              <span className="mb-2 block text-[13px] font-medium text-[var(--muted)]">
                Or paste text
              </span>
              <textarea
                className="field-area"
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Paste resume content…"
              />
            </label>
          </section>

          <section className="anim-rise space-y-6" style={{ animationDelay: "140ms" }}>
            <div className="mb-4 flex items-baseline justify-between gap-3 border-b border-[var(--line)] pb-3">
              <h2
                className="text-2xl font-bold tracking-tight text-[var(--ink)]"
                style={{ fontFamily: "var(--font-display), sans-serif" }}
              >
                Job description
                {jdSlots.length > 1 ? "s" : ""}
              </h2>
              <button
                type="button"
                onClick={addJdSlot}
                disabled={jdSlots.length >= 3}
                className="text-[13px] font-semibold text-[var(--ink)] underline decoration-[var(--line)] underline-offset-4 enabled:hover:decoration-[var(--signal)] disabled:opacity-35"
              >
                + Add JD
              </button>
            </div>

            {jdSlots.map((slot, index) => (
              <div key={index} className="space-y-3">
                <div className="flex items-center justify-between">
                  <p
                    className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--muted)]"
                    style={{ fontFamily: "var(--font-mono), monospace" }}
                  >
                    JD {index + 1}
                    {compareMode ? " · compare" : index === 0 ? " · primary" : ""}
                  </p>
                  {jdSlots.length > 1 && (
                    <button
                      type="button"
                      className="text-xs font-medium text-[var(--gap)] hover:underline"
                      onClick={() => removeJdSlot(index)}
                    >
                      Remove
                    </button>
                  )}
                </div>
                <textarea
                  className="field-area"
                  value={slot.text}
                  onChange={(e) => updateSlot(index, { text: e.target.value })}
                  placeholder="Paste the job description…"
                />
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block text-sm">
                    <span className="mb-1 block text-[13px] font-medium text-[var(--muted)]">
                      URL
                    </span>
                    <input
                      type="url"
                      className="field"
                      value={slot.url}
                      onChange={(e) => updateSlot(index, { url: e.target.value })}
                      placeholder="https://"
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="mb-1 block text-[13px] font-medium text-[var(--muted)]">
                      File
                    </span>
                    <input
                      type="file"
                      accept=".pdf,.docx,.txt,.md,application/pdf"
                      className="file-btn mt-1 block w-full text-sm text-[var(--muted)]"
                      onChange={(e) =>
                        updateSlot(index, { file: e.target.files?.[0] ?? null })
                      }
                    />
                  </label>
                </div>
              </div>
            ))}

            {compareMode && (
              <p className="text-xs text-[var(--muted)]">
                Two or more JDs filled — analysis will rank all roles and let you switch between them.
              </p>
            )}
          </section>
        </div>

        <div className="flex flex-col gap-4 border-t border-[var(--line)] pt-6 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex cursor-pointer items-center gap-2.5 text-sm text-[var(--muted)]">
            <input
              type="checkbox"
              checked={useStub}
              onChange={(e) => setUseStub(e.target.checked)}
              className="size-4 accent-[var(--signal)]"
            />
            Demo mode (stub, no Ollama)
          </label>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center bg-[var(--signal)] px-7 py-3 text-sm font-bold tracking-wide text-[var(--signal-ink)] transition-[transform,opacity] hover:opacity-95 active:translate-y-px disabled:opacity-55"
            style={{ fontFamily: "var(--font-display), sans-serif" }}
          >
            {loading
              ? "Working…"
              : compareMode
                ? "Compare roles"
                : "Analyze match"}
          </button>
        </div>
      </form>

      {error && (
        <p
          role="alert"
          className="border-l-4 border-[var(--gap)] bg-[#fff5f3] px-4 py-3 text-sm text-[var(--ink)]"
        >
          {error}
        </p>
      )}

      {activeResult && (
        <ResultsView
          result={activeResult}
          compare={compare}
          selectedCompareIndex={selectedCompareIndex}
          onSelectCompare={(idx) => {
            setSelectedCompareIndex(idx);
            if (compare?.ranked[idx]) {
              setResult(compare.ranked[idx].result);
            }
          }}
        />
      )}

      <ScoreHistory entries={history} />
    </div>
  );
}
