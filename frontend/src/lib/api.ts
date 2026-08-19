import {
  AnalyzeResponse,
  AnalyzeResponseSchema,
  CompareResponse,
  CompareResponseSchema,
} from "./schemas";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type JdSlot = { text: string; url: string; file: File | null; label?: string };

export type AnalyzeInput = {
  resumeFile?: File | null;
  resumeText?: string;
  jdSlots: JdSlot[];
  useStub?: boolean;
};

function appendResume(form: FormData, input: AnalyzeInput) {
  if (input.resumeFile) form.append("resume", input.resumeFile);
  if (input.resumeText?.trim()) form.append("resume_text", input.resumeText.trim());
}

function filledSlots(slots: JdSlot[]): JdSlot[] {
  return slots.filter(
    (s) => s.text.trim() || s.url.trim() || s.file,
  );
}

function isCompareMode(slots: JdSlot[]): boolean {
  return filledSlots(slots).length > 1;
}

async function parseError(res: Response): Promise<string> {
  let detail = await res.text();
  try {
    const parsed = JSON.parse(detail) as { detail?: string };
    if (parsed.detail) detail = parsed.detail;
  } catch {
    /* keep raw */
  }
  return detail || `Request failed (${res.status})`;
}

export async function analyzeResumeJd(input: AnalyzeInput): Promise<AnalyzeResponse> {
  if (input.useStub) {
    const res = await fetch(`${API_BASE}/analyze/stub`, { method: "POST" });
    if (!res.ok) throw new Error(await parseError(res));
    return AnalyzeResponseSchema.parse(await res.json());
  }

  const slots = filledSlots(input.jdSlots);
  if (slots.length === 0) {
    throw new Error("At least one job description is required.");
  }

  const form = new FormData();
  appendResume(form, input);
  const primary = slots[0];
  if (primary.text.trim()) form.append("jd_text", primary.text.trim());
  if (primary.url.trim()) form.append("jd_url", primary.url.trim());
  if (primary.file) form.append("jd_file", primary.file);

  const res = await fetch(`${API_BASE}/analyze`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return AnalyzeResponseSchema.parse(await res.json());
}

export async function compareResumeJds(input: AnalyzeInput): Promise<CompareResponse> {
  if (input.useStub) {
    const res = await fetch(`${API_BASE}/analyze/compare/stub`, { method: "POST" });
    if (!res.ok) throw new Error(await parseError(res));
    return CompareResponseSchema.parse(await res.json());
  }

  const slots = filledSlots(input.jdSlots);
  if (slots.length < 2) {
    throw new Error("Add at least two job descriptions to compare.");
  }
  if (slots.length > 3) {
    throw new Error("At most 3 job descriptions supported.");
  }

  const form = new FormData();
  appendResume(form, input);
  slots.forEach((slot, i) => {
    if (slot.text.trim()) form.append(`jd_text_${i}`, slot.text.trim());
    if (slot.url.trim()) form.append(`jd_url_${i}`, slot.url.trim());
    if (slot.file) form.append(`jd_file_${i}`, slot.file);
    if (slot.label?.trim()) form.append(`jd_label_${i}`, slot.label.trim());
  });

  const res = await fetch(`${API_BASE}/analyze/compare`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await parseError(res));
  return CompareResponseSchema.parse(await res.json());
}

export async function runAnalysis(input: AnalyzeInput): Promise<
  | { mode: "single"; result: AnalyzeResponse }
  | { mode: "compare"; compare: CompareResponse }
> {
  if (isCompareMode(input.jdSlots)) {
    const compare = await compareResumeJds(input);
    return { mode: "compare", compare };
  }
  const result = await analyzeResumeJd(input);
  return { mode: "single", result };
}

export { isCompareMode };
