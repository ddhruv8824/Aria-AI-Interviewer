"use client";

import { Briefcase, Building2, FileUp, Mail, Mic, Sparkles } from "lucide-react";
import { motion } from "motion/react";
import { INTERVIEWER_NAME } from "@/lib/constants";
import type { PracticeSession } from "@/lib/types";
import { cn } from "@/lib/utils";

export type UploadStatus = { text: string; kind: "" | "ok" | "err" };

interface SetupScreenProps {
  practice: PracticeSession;
  resumeStatus: UploadStatus;
  jdStatus: UploadStatus;
  isStarting: boolean;
  onResumeSelect: (file: File) => void;
  onJobDescriptionSelect: (file: File) => void;
  onStart: () => void;
}

const STEPS = [
  { num: "01", label: "Upload resume (optional)", icon: FileUp },
  { num: "02", label: "Upload job description (optional)", icon: Briefcase },
  { num: "03", label: "Start & allow mic", icon: Mic },
  { num: "04", label: "Get your scorecard", icon: Sparkles },
];

function UploadZone({
  title,
  hint,
  accept,
  icon: Icon,
  status,
  onSelect,
}: {
  title: string;
  hint: string;
  accept: string;
  icon: typeof FileUp;
  status: UploadStatus;
  onSelect: (file: File) => void;
}) {
  return (
    <div>
      <label className="group flex cursor-pointer flex-col items-center rounded-2xl border border-dashed border-auralis bg-panel-auralis px-6 py-8 text-center transition-all hover:border-outline hover:bg-surface-variant/40">
        <input
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onSelect(file);
          }}
        />
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full border border-auralis bg-surface shadow-sm transition-transform group-hover:scale-105">
          <Icon className="h-5 w-5 text-primary" strokeWidth={1.75} />
        </div>
        <div className="text-sm font-medium text-primary">{title}</div>
        <div className="mt-1 text-xs text-secondary-auralis">{hint}</div>
      </label>
      {status.text && (
        <p
          className={cn(
            "mt-2 text-xs font-medium",
            status.kind === "ok" && "text-emerald-700",
            status.kind === "err" && "text-red-600",
            status.kind === "" && "text-secondary-auralis",
          )}
        >
          {status.text}
        </p>
      )}
    </div>
  );
}

export function SetupScreen({
  practice,
  resumeStatus,
  jdStatus,
  isStarting,
  onResumeSelect,
  onJobDescriptionSelect,
  onStart,
}: SetupScreenProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="rounded-3xl border border-auralis bg-card-auralis p-8 md:p-10"
    >
      <div className="mb-8 flex flex-wrap items-center gap-4">
        <span className="rounded-full bg-surface-variant px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em] text-primary">
          Step 1 · Prepare
        </span>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-auralis bg-panel-auralis px-3 py-1 text-xs font-medium text-primary">
            <Building2 className="h-3.5 w-3.5" strokeWidth={1.75} />
            {practice.companyName}
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-auralis bg-panel-auralis px-3 py-1 text-xs font-medium text-secondary-auralis">
            <Mail className="h-3.5 w-3.5" strokeWidth={1.75} />
            {practice.email}
          </span>
        </div>
        <div className="h-px min-w-[2rem] flex-1 bg-auralis" />
      </div>

      <div className="mb-10 grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-start">
        <div className="lg:col-span-7">
          <h2 className="text-4xl font-semibold tracking-tighter text-primary md:text-[56px] md:leading-[1.05]">
            Ready for your interview?
          </h2>
        </div>
        <div className="lg:col-span-5">
          <p className="text-lg leading-relaxed text-secondary-auralis">
            You are practising for <strong className="font-medium text-primary">{practice.companyName}</strong>.
            Upload your resume and/or a job description so {INTERVIEWER_NAME} can ask tailored
            questions about your background, the role, and real community-reported topics for this
            company. Allow microphone access when prompted.
          </p>
        </div>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step) => (
          <div
            key={step.num}
            className="rounded-xl border border-auralis bg-panel-auralis p-5 transition-colors hover:bg-surface-variant/50"
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-[0.25em] text-secondary-auralis">
                {step.num}
              </span>
              <step.icon className="h-4 w-4 text-secondary-auralis" strokeWidth={1.75} />
            </div>
            <div className="text-sm font-medium tracking-tight text-primary">{step.label}</div>
          </div>
        ))}
      </div>

      <div className="mb-8 grid gap-4 md:grid-cols-2">
        <UploadZone
          title="Drop resume here or click to browse"
          hint="PDF or DOCX · optional"
          accept=".pdf,.docx"
          icon={FileUp}
          status={resumeStatus}
          onSelect={onResumeSelect}
        />
        <UploadZone
          title="Drop job description here or click to browse"
          hint="PDF, DOCX, or TXT · optional"
          accept=".pdf,.docx,.txt"
          icon={Briefcase}
          status={jdStatus}
          onSelect={onJobDescriptionSelect}
        />
      </div>

      <button
        type="button"
        onClick={onStart}
        disabled={isStarting}
        className="rounded-full bg-primary px-6 py-3 text-sm font-medium text-on-primary transition-all hover:bg-black/80 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isStarting ? "Connecting…" : "Start Interview →"}
      </button>
    </motion.section>
  );
}
