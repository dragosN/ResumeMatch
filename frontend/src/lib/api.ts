import { AnalyzeResponse, AnalyzeResponseSchema } from "./schemas";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export async function fetchStubAnalyze(): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE}/analyze/stub`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Stub analyze failed: ${res.status} ${await res.text()}`);
  }
  return AnalyzeResponseSchema.parse(await res.json());
}

export type AnalyzeInput = {
  resumeFile?: File | null;
  resumeText?: string;
  /** Primary JD (slot 0). Additional slots are UI-only until Day 3 compare. */
  jdSlots: { text: string; url: string; file: File | null }[];
  useStub?: boolean;
};

export async function analyzeResumeJd(input: AnalyzeInput): Promise<AnalyzeResponse> {
  if (input.useStub) {
    return fetchStubAnalyze();
  }

  const primary = input.jdSlots[0];
  if (!primary) {
    throw new Error("At least one job description slot is required.");
  }

  const form = new FormData();
  if (input.resumeFile) {
    form.append("resume", input.resumeFile);
  }
  if (input.resumeText?.trim()) {
    form.append("resume_text", input.resumeText.trim());
  }
  if (primary.text.trim()) {
    form.append("jd_text", primary.text.trim());
  }
  if (primary.url.trim()) {
    form.append("jd_url", primary.url.trim());
  }
  if (primary.file) {
    form.append("jd_file", primary.file);
  }

  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    let detail = await res.text();
    try {
      const parsed = JSON.parse(detail) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
    } catch {
      /* keep raw */
    }
    throw new Error(detail || `Analyze failed (${res.status})`);
  }
  return AnalyzeResponseSchema.parse(await res.json());
}
