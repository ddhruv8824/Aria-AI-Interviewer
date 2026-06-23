"use client";

import { useEffect, useRef, useState } from "react";
import { Clock } from "lucide-react";
import { motion } from "motion/react";
import CodingQuestion, { type Problem, type RunResponse } from "@/components/CodingQuestion";
import { INTERVIEWER_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";

function formatCountdown(totalSec: number): string {
  const mm = String(Math.floor(totalSec / 60)).padStart(2, "0");
  const ss = String(totalSec % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

interface CodingRoundScreenProps {
  problem: Problem;
  timeLimitSec: number;
  startedAt: number;
  isSubmitting: boolean;
  onSubmit: (payload: {
    source_code: string;
    language: string;
    result: RunResponse | null;
    time_taken_sec: number;
    timed_out: boolean;
  }) => void | Promise<void>;
}

export function CodingRoundScreen({
  problem,
  timeLimitSec,
  startedAt,
  isSubmitting,
  onSubmit,
}: CodingRoundScreenProps) {
  const [remainingSec, setRemainingSec] = useState(timeLimitSec);
  const submittedRef = useRef(false);
  const latestCodeRef = useRef({ code: problem.starterCode.python ?? "", language: "python" });

  useEffect(() => {
    submittedRef.current = false;
  }, [problem]);

  useEffect(() => {
    const tick = () => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      const left = Math.max(0, timeLimitSec - elapsed);
      setRemainingSec(left);
      if (left === 0 && !submittedRef.current) {
        submittedRef.current = true;
        void onSubmit({
          source_code: latestCodeRef.current.code,
          language: latestCodeRef.current.language,
          result: null,
          time_taken_sec: timeLimitSec,
          timed_out: true,
        });
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [onSubmit, startedAt, timeLimitSec]);

  const urgent = remainingSec <= 60;

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="space-y-6"
    >
      <div className="rounded-3xl border border-auralis bg-panel-auralis p-6 md:p-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <span className="mb-3 inline-flex rounded-full bg-surface-variant px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-primary">
              Coding round · Live
            </span>
            <h2 className="text-3xl font-semibold tracking-tighter text-primary md:text-4xl">
              Timed coding challenge
            </h2>
            <p className="mt-2 max-w-2xl text-base leading-relaxed text-secondary-auralis">
              {INTERVIEWER_NAME} has moved you to the coding section. Solve the problem below in Python or
              JavaScript. Use <strong className="font-medium text-primary">Run Tests</strong> to check your
              work, then <strong className="font-medium text-primary">Submit Answer</strong> when ready.
            </p>
          </div>
          <div
            className={cn(
              "flex items-center gap-3 rounded-2xl border px-5 py-4",
              urgent
                ? "border-red-500/30 bg-red-500/10 text-red-900"
                : "border-auralis bg-surface text-primary",
            )}
          >
            <Clock className="h-5 w-5" strokeWidth={1.75} />
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.25em] opacity-70">
                Time remaining
              </div>
              <div className="font-mono text-2xl font-semibold tracking-tight">
                {formatCountdown(remainingSec)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-3xl border border-auralis bg-card-auralis">
        <CodingQuestion
          problem={problem}
          mode="interview"
          readOnly={isSubmitting || submittedRef.current}
          submitLabel={isSubmitting ? "Submitting…" : "Submit Answer"}
          onCodeChange={(code, language) => {
            latestCodeRef.current = { code, language };
          }}
          onSubmit={async ({ source_code, language, result }) => {
            if (submittedRef.current) return;
            submittedRef.current = true;
            latestCodeRef.current = { code: source_code, language };
            const elapsed = Math.min(
              timeLimitSec,
              Math.floor((Date.now() - startedAt) / 1000),
            );
            await onSubmit({
              source_code,
              language,
              result,
              time_taken_sec: elapsed,
              timed_out: false,
            });
          }}
        />
      </div>
    </motion.section>
  );
}
