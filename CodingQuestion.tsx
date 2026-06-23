/**
 * CodingQuestion.tsx
 * -----------------------------------------------------------------------
 * A minimal LeetCode-style coding question screen: problem statement on
 * the left, Monaco editor + run button + test results on the right.
 *
 * Install:
 *   npm install @monaco-editor/react
 *
 * Usage:
 *   <CodingQuestion problem={numberClassifierProblem} />
 * -----------------------------------------------------------------------
 */

"use client";

import { useState } from "react";
import Editor from "@monaco-editor/react";

export interface TestCase {
  input: string;
  expected_output: string;
  label?: string;
  hidden?: boolean;
}

export interface Problem {
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

interface RunResponse {
  all_passed: boolean;
  passed_count: number;
  total_count: number;
  results: TestResult[];
}

const LANGUAGES = [
  { id: "python", label: "Python", monacoId: "python" },
  { id: "javascript", label: "JavaScript", monacoId: "javascript" },
  { id: "java", label: "Java", monacoId: "java" },
  { id: "cpp", label: "C++", monacoId: "cpp" },
];

export default function CodingQuestion({
  problem,
  backendUrl = "http://localhost:8000",
}: {
  problem: Problem;
  backendUrl?: string;
}) {
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(problem.starterCode["python"] ?? "");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function handleLanguageChange(lang: string) {
    setLanguage(lang);
    setCode(problem.starterCode[lang] ?? "");
    setResult(null);
    setError(null);
  }

  async function handleRun() {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch(`${backendUrl}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_code: code, language, test_cases: problem.testCases }),
      });
      if (!resp.ok) throw new Error(await resp.text());
      setResult(await resp.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run code");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="cq-root">
      <div className="cq-panel cq-problem">
        <div className="cq-header">
          <h2>{problem.title}</h2>
          <span className={`cq-diff cq-diff-${problem.difficulty.toLowerCase()}`}>
            {problem.difficulty}
          </span>
        </div>
        <p className="cq-desc">{problem.description}</p>
        <div className="cq-examples">
          {problem.testCases.filter((t) => !t.hidden).map((tc, i) => (
            <div key={i} className="cq-example">
              <div className="cq-example-label">{tc.label ?? `Example ${i + 1}`}</div>
              <code>Input: {tc.input}</code>
              <code>Output: {tc.expected_output}</code>
            </div>
          ))}
        </div>
      </div>

      <div className="cq-panel cq-editor-panel">
        <div className="cq-toolbar">
          <select value={language} onChange={(e) => handleLanguageChange(e.target.value)}>
            {LANGUAGES.map((l) => (
              <option key={l.id} value={l.id}>{l.label}</option>
            ))}
          </select>
          <button onClick={handleRun} disabled={running}>
            {running ? "Running..." : "Run"}
          </button>
        </div>

        <div className="cq-editor-wrap">
          <Editor
            height="100%"
            language={LANGUAGES.find((l) => l.id === language)?.monacoId}
            value={code}
            onChange={(v) => setCode(v ?? "")}
            theme="vs-dark"
            options={{ fontSize: 14, minimap: { enabled: false }, automaticLayout: true }}
          />
        </div>

        <div className="cq-results">
          {error && <div className="cq-error">{error}</div>}
          {result && (
            <>
              <div className={`cq-summary ${result.all_passed ? "cq-pass" : "cq-fail"}`}>
                {result.passed_count}/{result.total_count} test cases passed
              </div>
              {result.results.map((r, i) => (
                <div key={i} className={`cq-row ${r.passed ? "cq-pass" : "cq-fail"}`}>
                  <span>{r.passed ? "✓" : "✗"}</span>
                  <span>{r.label ?? `Test ${i + 1}`}</span>
                  <span className="cq-status">{r.status}</span>
                  {!r.passed && !r.hidden && (
                    <div className="cq-detail">
                      Expected: {r.expected_output} — Got: {r.actual_output || r.stderr || "(no output)"}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      <style jsx>{`
        .cq-root { display: grid; grid-template-columns: 360px 1fr; height: 100%; background: #1e1e1e; color: #d4d4d4; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
        .cq-panel { padding: 20px; overflow-y: auto; }
        .cq-problem { border-right: 1px solid #333; }
        .cq-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .cq-header h2 { font-size: 18px; margin: 0; }
        .cq-diff { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
        .cq-diff-easy { background: #1e3a2b; color: #4ade80; }
        .cq-diff-medium { background: #3a2e1e; color: #fbbf24; }
        .cq-diff-hard { background: #3a1e1e; color: #f87171; }
        .cq-desc { font-size: 14px; line-height: 1.6; white-space: pre-wrap; color: #ccc; }
        .cq-examples { margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
        .cq-example { background: #252526; border-radius: 6px; padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
        .cq-example-label { font-size: 12px; color: #888; }
        .cq-example code { font-size: 13px; color: #9cdcfe; }
        .cq-editor-panel { display: flex; flex-direction: column; padding: 0; }
        .cq-toolbar { display: flex; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid #333; }
        .cq-toolbar select { background: #2d2d2d; color: #d4d4d4; border: 1px solid #444; border-radius: 4px; padding: 6px 10px; }
        .cq-toolbar button { background: #0e639c; color: white; border: none; border-radius: 4px; padding: 7px 16px; font-weight: 600; cursor: pointer; }
        .cq-toolbar button:disabled { opacity: 0.6; cursor: not-allowed; }
        .cq-editor-wrap { flex: 1; min-height: 280px; }
        .cq-results { max-height: 220px; overflow-y: auto; border-top: 1px solid #333; padding: 12px 16px; }
        .cq-error { color: #f87171; font-size: 13px; }
        .cq-summary { font-weight: 600; margin-bottom: 10px; }
        .cq-summary.cq-pass { color: #4ade80; }
        .cq-summary.cq-fail { color: #f87171; }
        .cq-row { font-size: 13px; padding: 6px 0; border-bottom: 1px solid #2a2a2a; }
        .cq-row.cq-pass span:first-child { color: #4ade80; }
        .cq-row.cq-fail span:first-child { color: #f87171; }
        .cq-status { margin-left: 8px; color: #888; font-size: 12px; }
        .cq-detail { margin-top: 4px; font-size: 12px; color: #aaa; font-family: monospace; }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sample if/else problem — LeetCode style
// ---------------------------------------------------------------------------

export const numberClassifierProblem: Problem = {
  title: "Classify a Number",
  difficulty: "Easy",
  description:
    "Given an integer n, print:\n" +
    '  "Positive" if n > 0\n' +
    '  "Negative" if n < 0\n' +
    '  "Zero" if n == 0\n\n' +
    "Read n from input.",
  starterCode: {
    python: "n = int(input())\n# your code here\n",
    javascript:
      "const n = parseInt(require('fs').readFileSync(0, 'utf8').trim());\n// your code here\n",
    java:
      "import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        // your code here\n    }\n}\n",
    cpp: "#include <iostream>\nusing namespace std;\n\nint main() {\n    int n;\n    cin >> n;\n    // your code here\n    return 0;\n}\n",
  },
  testCases: [
    { input: "5", expected_output: "Positive", label: "Example 1" },
    { input: "-3", expected_output: "Negative", label: "Example 2" },
    { input: "0", expected_output: "Zero", label: "Example 3" },
    { input: "100", expected_output: "Positive", label: "Hidden: large positive", hidden: true },
    { input: "-1", expected_output: "Negative", label: "Hidden: small negative", hidden: true },
  ],
};
