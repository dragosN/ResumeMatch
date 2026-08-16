import { AnalyzeForm } from "@/components/AnalyzeForm";

export default function Home() {
  return (
    <main className="relative flex-1">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-y-0 left-0 hidden w-3 bg-[var(--signal)] sm:block"
      />

      <div className="mx-auto w-full max-w-6xl px-5 pb-20 pt-10 sm:px-10 sm:pt-14 lg:px-12">
        <header className="anim-rise mb-14 max-w-3xl">
          <p
            className="text-[clamp(2.75rem,8vw,5.5rem)] font-extrabold leading-[0.92] tracking-[-0.04em] text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display), sans-serif" }}
          >
            ResumeMatch
          </p>
          <p className="mt-5 max-w-lg text-[1.05rem] leading-relaxed text-[var(--muted)] sm:text-lg">
            Line up your resume against a job description. See the score, the
            gaps, and what to rewrite — without inventing experience you don’t
            have.
          </p>
          <a
            href="#workspace"
            className="mt-8 inline-flex items-center gap-2 border-b-2 border-[var(--signal)] pb-0.5 text-sm font-semibold tracking-wide text-[var(--ink)] transition-colors hover:text-[var(--signal)]"
          >
            Start analysis
            <span aria-hidden className="translate-y-px">
              ↓
            </span>
          </a>
        </header>

        <AnalyzeForm />
      </div>
    </main>
  );
}
