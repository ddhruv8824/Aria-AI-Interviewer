# Coding Question Module — LeetCode-style editor + executor

A minimal, focused build: Monaco code editor + self-hosted Judge0 execution +
one sample if/else problem with visible and hidden test cases.

## Why self-hosted Judge0 (not a public API)

As of Feb 2026, neither Judge0's public instance nor Piston's public API are
reliable, no-signup options anymore (Piston's public API now requires manual
approval from the maintainer; Judge0's public instance has low rate limits
and no uptime guarantee). Self-hosting Judge0 via Docker is the only genuinely
free, no-gatekeeping path — and it's also the more production-tested option
for assessment/recruitment platforms specifically.

## 1. Start Judge0 (the execution engine)

```bash
cp judge0.conf.example judge0.conf
# edit judge0.conf, set real passwords (openssl rand -hex 24)

docker-compose up -d db redis
sleep 10
docker-compose up -d

# verify it's up:
curl http://localhost:2358/system_info
```

## 2. Start the backend

```bash
cd backend
pip install fastapi uvicorn httpx
uvicorn main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health`

## 3. Start the frontend

```bash
npm install @monaco-editor/react
```

Drop `CodingQuestion.tsx` into your React/Next.js app:

```tsx
import CodingQuestion, { numberClassifierProblem } from "./CodingQuestion";

export default function Page() {
  return <CodingQuestion problem={numberClassifierProblem} backendUrl="http://localhost:8000" />;
}
```

## The sample problem

**Classify a Number** (Easy) — read an integer, print `Positive`, `Negative`,
or `Zero`. Exactly the kind of simple if/else problem you'd give as a warm-up
question. 3 visible test cases (shown to the candidate) + 2 hidden ones (used
for scoring only, prevents hardcoding answers to just the visible cases).

## Adding more problems

Each problem is just an object:

```ts
{
  title: "...",
  difficulty: "Easy" | "Medium" | "Hard",
  description: "...",
  starterCode: { python: "...", javascript: "...", java: "...", cpp: "..." },
  testCases: [
    { input: "...", expected_output: "...", label: "Example 1" },
    { input: "...", expected_output: "...", label: "Hidden case", hidden: true },
  ],
}
```

Problems are stdin/stdout-based (candidate reads input, prints output) —
the simplest format to grade reliably, same approach LeetCode uses under
the hood for many of its "easy" problems before wrapping them in a function
signature.
