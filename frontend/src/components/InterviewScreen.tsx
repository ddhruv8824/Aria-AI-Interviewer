"use client";

import { useEffect, useRef } from "react";
import { Headphones, MessageCircle } from "lucide-react";
import { motion } from "motion/react";
import { INTERVIEWER_NAME } from "@/lib/constants";
import type { StatusColor, TranscriptEntry } from "@/lib/types";
import { cn } from "@/lib/utils";

interface InterviewScreenProps {
  statusText: string;
  statusColor: StatusColor;
  timer: string;
  transcript: TranscriptEntry[];
  isEnding: boolean;
  onStartCoding: () => void;
  onSkipCoding: () => void;
}

const STATUS_STYLES: Record<StatusColor, string> = {
  "": "bg-surface-variant border-auralis text-secondary-auralis",
  green: "bg-emerald-500/15 border-emerald-500/25 text-emerald-800",
  blue: "bg-sky-500/15 border-sky-500/25 text-sky-800",
  yellow: "bg-amber-500/15 border-amber-500/25 text-amber-800",
  red: "bg-red-500/15 border-red-500/25 text-red-800",
};

const DOT_STYLES: Record<StatusColor, string> = {
  "": "bg-secondary-auralis",
  green: "bg-emerald-500",
  blue: "bg-sky-500 animate-pulse",
  yellow: "bg-amber-500",
  red: "bg-red-500",
};

export function InterviewScreen({
  statusText,
  statusColor,
  timer,
  transcript,
  isEnding,
  onStartCoding,
  onSkipCoding,
}: InterviewScreenProps) {
  const transcriptRef = useRef<HTMLDivElement>(null);
  const visibleTranscript = transcript.filter((e) => e.text.trim().length > 0);
  const isSpeaking = statusColor === "blue";
  const canSendAudio = statusColor === "green";

  useEffect(() => {
    const el = transcriptRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [transcript, statusText]);

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="overflow-hidden rounded-3xl border border-auralis bg-panel-auralis p-8"
    >
      <div className="mb-6 flex items-center gap-4">
        <span className="rounded-full bg-surface-variant px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-primary">
          Live session
        </span>
        <div className="h-px flex-1 bg-auralis" />
      </div>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={cn(
              "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium",
              STATUS_STYLES[statusColor],
            )}
          >
            <span className={cn("h-2 w-2 rounded-full", DOT_STYLES[statusColor])} />
            {statusText}
          </span>
          <span className="rounded-full border border-auralis bg-surface px-3 py-1.5 font-mono text-sm text-primary">
            {timer}
          </span>
        </div>
      </div>

      <div
        ref={transcriptRef}
        aria-live="polite"
        className="min-h-[420px] max-h-[520px] overflow-y-auto rounded-2xl border border-auralis bg-surface/80 p-5 backdrop-blur-md no-scrollbar"
      >
        {visibleTranscript.length === 0 ? (
          <div className="flex h-full min-h-[360px] flex-col items-center justify-center gap-4 text-center">
            <div className="flex h-20 w-20 items-center justify-center rounded-full border border-auralis bg-surface shadow-lg">
              {isSpeaking ? (
                <MessageCircle className="h-8 w-8 text-primary" strokeWidth={1.75} />
              ) : (
                <Headphones className="h-8 w-8 text-primary" strokeWidth={1.75} />
              )}
            </div>
            <div>
              <p className="text-base font-medium text-primary">
                {isSpeaking
                  ? `${INTERVIEWER_NAME} is speaking…`
                  : canSendAudio
                    ? `Speak naturally — ${INTERVIEWER_NAME} is listening.`
                    : `${INTERVIEWER_NAME} is starting the interview…`}
              </p>
              <p className="mt-2 text-sm text-secondary-auralis">
                {isSpeaking
                  ? `Captions appear as ${INTERVIEWER_NAME} speaks.`
                  : canSendAudio
                    ? "Your answers will appear here."
                    : `Please wait for ${INTERVIEWER_NAME} to finish the introduction.`}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {visibleTranscript.map((entry) => (
              <div
                key={entry.id}
                className={cn(
                  "max-w-[85%] rounded-2xl border px-4 py-3",
                  entry.role === "user"
                    ? "ml-auto border-auralis bg-card-auralis"
                    : "mr-auto border-auralis bg-white/60",
                )}
              >
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-widest text-secondary-auralis">
                  {entry.role === "user" ? "You" : INTERVIEWER_NAME} · {entry.time}
                </div>
                <div className="text-sm leading-relaxed text-primary">
                  {entry.text}
                  {entry.isStreaming && (
                    <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-primary align-middle" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={onStartCoding}
          disabled={isEnding}
          className="rounded-full bg-primary px-6 py-3 text-sm font-medium text-on-primary transition-all hover:bg-black/80 disabled:opacity-60"
        >
          {isEnding ? "Starting coding round…" : "Start Coding Round →"}
        </button>
        <button
          type="button"
          onClick={onSkipCoding}
          disabled={isEnding}
          className="rounded-full border border-outline bg-transparent px-5 py-3 text-sm font-medium text-primary transition-all hover:bg-surface-variant disabled:opacity-60"
        >
          Skip coding & finish
        </button>
      </div>
    </motion.section>
  );
}
