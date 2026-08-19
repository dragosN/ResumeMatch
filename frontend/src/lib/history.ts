import type { CompareResponse } from "./schemas";

const STORAGE_KEY = "resumematch:history";
const MAX_ENTRIES = 20;

export type HistoryEntry = {
  id: string;
  timestamp: number;
  score: number;
  jdLabel: string;
  resumeFingerprint: string;
  mode: "single" | "compare";
  compareScores?: { label: string; score: number }[];
};

export function fingerprintResume(resumeText: string, fileName?: string | null): string {
  const base = fileName?.trim() || resumeText.trim().slice(0, 500);
  let hash = 0;
  for (let i = 0; i < base.length; i++) {
    hash = (hash << 5) - hash + base.charCodeAt(i);
    hash |= 0;
  }
  return `r${Math.abs(hash)}`;
}

export function loadHistory(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as HistoryEntry[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveHistoryEntry(entry: HistoryEntry): HistoryEntry[] {
  const prev = loadHistory();
  const next = [entry, ...prev.filter((e) => e.id !== entry.id)].slice(0, MAX_ENTRIES);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

export function clearHistory(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function historyFromSingle(
  result: { overall_score: number; requirements?: { required_skills?: string[] } | null },
  jdLabel: string,
  resumeFingerprint: string,
): HistoryEntry {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: Date.now(),
    score: Math.round(result.overall_score),
    jdLabel,
    resumeFingerprint,
    mode: "single",
  };
}

export function historyFromCompare(
  compare: CompareResponse,
  resumeFingerprint: string,
): HistoryEntry {
  const best = compare.ranked[0];
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: Date.now(),
    score: Math.round(best?.overall_score ?? 0),
    jdLabel: best?.label ?? "Multi-JD compare",
    resumeFingerprint,
    mode: "compare",
    compareScores: compare.ranked.map((r) => ({
      label: r.label,
      score: Math.round(r.overall_score),
    })),
  };
}
