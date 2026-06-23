"use client";

import { useCallback, useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { Play, Send } from "lucide-react";
import { getCodeRunUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface TestCase {
  input: string;
  expected_output: string;
  label?: string;
  hidden?: boolean;
}

export interface Problem {
  id?: string;
  title: string;
  difficulty: "Easy" | "Medium" | "Hard";
  description: string;
  starterCode: Record<string, string>;
  testCases: TestCase[];
}

interface TestResult {
  label?: string;
  passed: boolean;
  hidden: boolean;
  input?: string;
  expected_output?: string;
  actual_output?: string;
  stderr?: string;
  status: string;
}

export interface RunResponse {
  all_passed: boolean;
  passed_count: number;
  total_count: number;
  results: TestResult[];
}

const ALL_LANGUAGES = [
  { id: "python", label: "Python", monacoId: "python" },
  { id: "javascript", label: "JavaScript", monacoId: "javascript" },
];

const DIFFICULTY_STYLES = {
  easy: "bg-emerald-500/15 border-emerald-500/25 text-emerald-800",
  medium: "bg-amber-500/15 border-amber-500/25 text-amber-800",
  hard: "bg-red-500/15 border-red-500/25 text-red-800",
};

interface CodingQuestionProps {
  problem: Problem;
  backendUrl?: string;
  mode?: "preview" | "interview";
  readOnly?: boolean;
  initialLanguage?: string;
  submitLabel?: string;
  onCodeChange?: (code: string, language: string) => void;
  onSubmit?: (payload: {
    source_code: string;
    language: string;
    result: RunResponse | null;
  }) => void | Promise<void>;
}

export default function CodingQuestion({
  problem,
  backendUrl,
  mode = "preview",
  readOnly = false,
  initialLanguage = "python",
  submitLabel = "Submit Answer",
  onCodeChange,
  onSubmit,
}: CodingQuestionProps) {
  const runUrl = backendUrl ?? getCodeRunUrl();
  const languages = ALL_LANGUAGES.filter((l) => problem.starterCode[l.id]);
  const [language, setLanguage] = useState(initialLanguage);
  const [code, setCode] = useState(problem.starterCode[initialLanguage] ?? problem.starterCode.python ?? "");
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<RunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLanguage(initialLanguage);
    setCode(problem.starterCode[initialLanguage] ?? problem.starterCode.python ?? "");
    setResult(null);
    setError(null);
  }, [problem, initialLanguage]);

  function handleLanguageChange(lang: string) {
    const next = problem.starterCode[lang] ?? "";
    setLanguage(lang);
    setCode(next);
    setResult(null);
    setError(null);
    onCodeChange?.(next, lang);
  }

  const runTests = useCallback(async (): Promise<RunResponse> => {
    const resp = await fetch(`${runUrl}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_code: code, language, test_cases: problem.testCases }),
    });
    if (!resp.ok) {
      let detail = await resp.text();
      try {
        const parsed = JSON.parse(detail) as { detail?: string };
        detail = parsed.detail ?? detail;
      } catch {
        /* use raw text */
      }
      throw new Error(detail);
    }
    return resp.json();
  }, [code, language, problem.testCases, runUrl]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await runTests());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run code");
    } finally {
      setRunning(false);
    }
  }

  async function handleSubmit() {
    if (!onSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      let runResult: RunResponse | null = null;
      try {
        runResult = await runTests();
        setResult(runResult);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to run code before submit");
      }
      await onSubmit({ source_code: code, language, result: runResult });
    } finally {
      setSubmitting(false);
    }
  }

  const diffKey = problem.difficulty.toLowerCase() as keyof typeof DIFFICULTY_STYLES;
  const isInterview = mode === "interview";

  return (
    <div className="grid min-h-[560px] grid-cols-1 lg:grid-cols-2">
      <div className="border-b border-auralis p-6 lg:border-b-0 lg:border-r">
        <div className="mb-4 flex items-start justify-between gap-4">
          <h3 className="text-[20px] font-semibold tracking-tight text-primary">{problem.title}</h3>
          <span
            className={cn(
              "shrink-0 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em]",
              DIFFICULTY_STYLES[diffKey],
            )}
          >
            {problem.difficulty}
          </span>
        </div>
        <p className="mb-6 whitespace-pre-line text-sm leading-relaxed text-secondary-auralis">
          {problem.description}
        </p>
        <div className="space-y-3">
          {problem.testCases
            .filter((t) => !t.hidden)
            .map((tc, i) => (
              <div key={i} className="rounded-xl border border-auralis bg-panel-auralis p-4">
                <div className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-secondary-auralis">
                  {tc.label ?? `Example ${i + 1}`}
                </div>
                <code className="block text-sm text-primary">Input: {tc.input}</code>
                <code className="mt-1 block text-sm text-primary">Output: {tc.expected_output}</code>
              </div>
            ))}
        </div>
      </div>

      <div className="flex min-h-[420px] flex-col">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-auralis bg-surface-container-low px-4 py-3">
          <select
            value={language}
            disabled={readOnly}
            onChange={(e) => handleLanguageChange(e.target.value)}
            className="rounded-full border border-auralis bg-surface px-4 py-2 text-sm font-medium text-primary outline-none transition-colors hover:bg-surface-variant/50 disabled:opacity-60"
          >
            {languages.map((l) => (
              <option key={l.id} value={l.id}>
                {l.label}
              </option>
            ))}
          </select>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={handleRun}
              disabled={running || submitting || readOnly}
              className="inline-flex items-center gap-2 rounded-full border border-outline bg-transparent px-5 py-2 text-sm font-medium text-primary transition-all hover:bg-surface-variant disabled:opacity-60"
            >
              <Play className="h-4 w-4 fill-current" />
              {running ? "Running…" : "Run Tests"}
            </button>
            {isInterview && onSubmit && (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={running || submitting || readOnly}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2 text-sm font-medium text-on-primary transition-all hover:bg-black/80 disabled:opacity-60"
              >
                <Send className="h-4 w-4" />
                {submitting ? "Submitting…" : submitLabel}
              </button>
            )}
          </div>
        </div>

        <div className="min-h-[280px] flex-1 border-b border-auralis">
          <Editor
            height="100%"
            language={languages.find((l) => l.id === language)?.monacoId ?? "python"}
            value={code}
            onChange={(v) => {
              if (readOnly) return;
              const next = v ?? "";
              setCode(next);
              onCodeChange?.(next, language);
            }}
            theme="light"
            options={{
              fontSize: 14,
              minimap: { enabled: false },
              automaticLayout: true,
              scrollBeyondLastLine: false,
              padding: { top: 12 },
              readOnly,
            }}
          />
        </div>

        <div className="max-h-[180px] overflow-y-auto bg-surface/80 p-4 no-scrollbar">
          {error && (
            <div className="rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          )}
          {result && (
            <div className="space-y-2">
              <div
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.1em]",
                  result.all_passed
                    ? "bg-emerald-500/15 text-emerald-800"
                    : "bg-red-500/15 text-red-800",
                )}
              >
                {result.passed_count}/{result.total_count} test cases passed
              </div>
              {result.results.map((r, i) => (
                <div
                  key={i}
                  className={cn(
                    "rounded-xl border px-3 py-2 text-sm",
                    r.passed
                      ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-900"
                      : "border-red-500/25 bg-red-500/10 text-red-900",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span>{r.passed ? "✓" : "✗"}</span>
                    <span className="font-medium">{r.label ?? `Test ${i + 1}`}</span>
                    <span className="text-xs uppercase tracking-wider opacity-70">{r.status}</span>
                  </div>
                  {!r.passed && !r.hidden && (
                    <div className="mt-1 text-xs opacity-80">
                      Expected: {r.expected_output} — Got: {r.actual_output || r.stderr || "(no output)"}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export { numberClassifierProblem } from "@/lib/codingProblems";
