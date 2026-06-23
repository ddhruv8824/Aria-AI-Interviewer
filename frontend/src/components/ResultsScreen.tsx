"use client";

import { motion } from "motion/react";
import type { ScorecardReport } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ResultsScreenProps {
  report: ScorecardReport | null;
  onRestart: () => void;
}

function hireBadgeClass(rec: string): string {
  const lower = rec.toLowerCase();
  if (lower.includes("yes") || lower.includes("hire") || lower.includes("recommend")) return "yes";
  if (lower.includes("no") || lower.includes("reject") || lower.includes("not")) return "no";
  return "maybe";
}

const BADGE_STYLES = {
  yes: "bg-emerald-500/15 border-emerald-500/25 text-emerald-800",
  no: "bg-red-500/15 border-red-500/25 text-red-800",
  maybe: "bg-amber-500/15 border-amber-500/25 text-amber-800",
};

function ScoreRing({ score }: { score: number }) {
  const pct = Math.min(100, (score / 10) * 100);
  const r = 36;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;

  return (
    <div className="relative h-[88px] w-[88px] shrink-0">
      <svg width="88" height="88" viewBox="0 0 88 88" className="-rotate-90">
        <circle cx="44" cy="44" r={r} fill="none" stroke="#E7E7E4" strokeWidth="6" />
        <circle
          cx="44"
          cy="44"
          r={r}
          fill="none"
          stroke="#000000"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-2xl font-semibold tracking-tight text-primary">{score.toFixed(1)}</div>
          <div className="text-[11px] uppercase tracking-widest text-secondary-auralis">/ 10</div>
        </div>
      </div>
    </div>
  );
}

export function ResultsScreen({ report, onRestart }: ResultsScreenProps) {
  if (!report) return null;

  const score = report.overall_score ?? 0;
  const hire = report.hire_recommendation || "—";
  const badgeClass = hireBadgeClass(hire) as keyof typeof BADGE_STYLES;

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="rounded-3xl border border-auralis bg-card-auralis p-8 md:p-10"
    >
      <div className="mb-8 flex items-center gap-4">
        <span className="rounded-full bg-surface-variant px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-primary">
          Complete
        </span>
        <div className="h-px flex-1 bg-auralis" />
      </div>

      <h2 className="mb-8 text-4xl font-semibold tracking-tighter text-primary md:text-[48px]">
        Your Interview Scorecard
      </h2>

      <div className="mb-10 flex flex-col gap-6 rounded-2xl border border-auralis bg-panel-auralis p-6 sm:flex-row sm:items-center">
        <ScoreRing score={score} />
        <div>
          <span
            className={cn(
              "mb-3 inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em]",
              BADGE_STYLES[badgeClass],
            )}
          >
            {hire}
          </span>
          <h3 className="text-xl font-semibold tracking-tight text-primary">Overall performance</h3>
          <p className="mt-2 max-w-xl text-base leading-relaxed text-secondary-auralis">
            {report.overall_verdict || ""}
          </p>
        </div>
      </div>

      {(report.dimensions || []).length > 0 && (
        <div className="mb-8">
          <h3 className="mb-4 text-xs font-semibold uppercase tracking-[0.1em] text-secondary-auralis">
            Dimensions
          </h3>
          <div className="space-y-4">
            {report.dimensions!.map((d) => (
              <div key={d.name} className="rounded-xl border border-auralis bg-panel-auralis p-5">
                <div className="mb-3 flex items-center justify-between gap-4">
                  <span className="font-medium text-primary">{d.name}</span>
                  <span className="text-sm font-semibold text-primary">{d.score}/10</span>
                </div>
                <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-auralis">
                  <div
                    className="h-full rounded-full bg-primary transition-all duration-700"
                    style={{ width: `${(d.score / 10) * 100}%` }}
                  />
                </div>
                <p className="text-sm leading-relaxed text-secondary-auralis">{d.rationale}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {!!report.strengths?.length && (
          <div className="rounded-xl border border-auralis bg-panel-auralis p-5">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.1em] text-secondary-auralis">
              Strengths
            </h3>
            <ul className="space-y-2 text-sm leading-relaxed text-primary">
              {report.strengths.map((s) => (
                <li key={s} className="flex gap-2">
                  <span className="text-emerald-600">✓</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {!!report.improvements?.length && (
          <div className="rounded-xl border border-auralis bg-panel-auralis p-5">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.1em] text-secondary-auralis">
              Areas to improve
            </h3>
            <ul className="space-y-2 text-sm leading-relaxed text-primary">
              {report.improvements.map((s) => (
                <li key={s} className="flex gap-2">
                  <span className="text-secondary-auralis">→</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="mt-10">
        <button
          type="button"
          onClick={onRestart}
          className="rounded-full bg-primary px-6 py-3 text-sm font-medium text-on-primary transition-all hover:bg-black/80"
        >
          Start New Interview
        </button>
      </div>
    </motion.section>
  );
}
