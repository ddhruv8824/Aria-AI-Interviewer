import type { Problem } from "@/components/CodingQuestion";

export const CODING_ROUND_TIME_SEC = Number(
  process.env.NEXT_PUBLIC_CODING_ROUND_TIME_SEC ?? 20 * 60,
);

export const INTERVIEW_LANGUAGES = ["python", "javascript"] as const;

export const numberClassifierProblem: Problem = {
  id: "classify_number",
  title: "Classify a Number",
  difficulty: "Easy",
  description:
    "Given an integer n, print:\n" +
    '  "Positive" if n > 0\n' +
    '  "Negative" if n < 0\n' +
    '  "Zero" if n == 0\n\n' +
    "Read n from stdin.",
  starterCode: {
    python: `n = int(input())
if n > 0:
    print("Positive")
elif n < 0:
    print("Negative")
else:
    print("Zero")
`,
    javascript: `const fs = require("fs");
const n = parseInt(fs.readFileSync(0, "utf8").trim(), 10);
if (n > 0) {
  console.log("Positive");
} else if (n < 0) {
  console.log("Negative");
} else {
  console.log("Zero");
}
`,
  },
  testCases: [
    { input: "5", expected_output: "Positive", label: "Example 1" },
    { input: "-3", expected_output: "Negative", label: "Example 2" },
    { input: "0", expected_output: "Zero", label: "Example 3" },
    { input: "100", expected_output: "Positive", label: "Hidden: large positive", hidden: true },
    { input: "-1", expected_output: "Negative", label: "Hidden: small negative", hidden: true },
  ],
};

export const reverseStringProblem: Problem = {
  id: "reverse_string",
  title: "Reverse a String",
  difficulty: "Easy",
  description:
    "Read a single line string s from stdin and print the reversed string.\n\n" +
    "Example: input `hello` → output `olleh`",
  starterCode: {
    python: `s = input().strip()
# print reversed string
`,
    javascript: `const fs = require("fs");
const s = fs.readFileSync(0, "utf8").trim();
// print reversed string
`,
  },
  testCases: [
    { input: "hello", expected_output: "olleh", label: "Example 1" },
    { input: "abc", expected_output: "cba", label: "Example 2" },
    { input: "a", expected_output: "a", label: "Example 3" },
    { input: "OpenAI", expected_output: "IAnepO", label: "Hidden: mixed case", hidden: true },
    { input: "12345", expected_output: "54321", label: "Hidden: digits", hidden: true },
  ],
};

export const CODING_PROBLEMS: Record<string, Problem> = {
  classify_number: numberClassifierProblem,
  reverse_string: reverseStringProblem,
};

export const DEFAULT_CODING_PROBLEM_ID = "classify_number";

export function getCodingProblem(id: string): Problem {
  return CODING_PROBLEMS[id] ?? numberClassifierProblem;
}

export function pickInterviewProblem(): Problem {
  const ids = Object.keys(CODING_PROBLEMS);
  const id = ids[Math.floor(Math.random() * ids.length)] ?? DEFAULT_CODING_PROBLEM_ID;
  return getCodingProblem(id);
}
