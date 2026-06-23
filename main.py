"""
Minimal code-execution backend for a LeetCode-style coding question.

Talks to a self-hosted Judge0 instance (see docker-compose.yml in this repo).
Takes source code + a language, runs it against each test case's stdin,
compares actual vs expected stdout, returns pass/fail per test case.

Install:
  pip install fastapi uvicorn httpx --break-system-packages

Run (after Judge0 is up via docker-compose):
  uvicorn main:app --reload --port 8000
"""

import os
import time
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

JUDGE0_URL = os.environ.get("JUDGE0_URL", "http://localhost:2358")

LANGUAGE_IDS = {
    "python": 71,   # Python 3.8.1
    "javascript": 63,  # Node.js 12.14.0
    "java": 62,     # OpenJDK 13.0.1
    "cpp": 54,      # GCC 9.2.0
}

app = FastAPI(title="Coding Question Execution Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict to your frontend's origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class TestCase(BaseModel):
    input: str
    expected_output: str
    label: Optional[str] = None
    hidden: bool = False


class RunRequest(BaseModel):
    source_code: str
    language: str
    test_cases: list[TestCase]


class TestResult(BaseModel):
    label: Optional[str]
    passed: bool
    hidden: bool
    input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    stderr: Optional[str] = None
    status: str


class RunResponse(BaseModel):
    all_passed: bool
    passed_count: int
    total_count: int
    results: list[TestResult]


def normalize(s: Optional[str]) -> str:
    return (s or "").strip()


async def submit_to_judge0(client: httpx.AsyncClient, source_code: str,
                             language_id: int, stdin: str) -> dict:
    resp = await client.post(
        f"{JUDGE0_URL}/submissions?base64_encoded=false&wait=false",
        json={"source_code": source_code, "language_id": language_id, "stdin": stdin},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Judge0 submission failed ({resp.status_code}): {resp.text[:300]}. "
                   f"Is Judge0 running at {JUDGE0_URL}? See docker-compose.yml.",
        )
    token = resp.json()["token"]

    for _ in range(30):  # ~15s max wait
        poll = await client.get(
            f"{JUDGE0_URL}/submissions/{token}?base64_encoded=false", timeout=30
        )
        data = poll.json()
        if data.get("status", {}).get("id", 0) > 2:  # >2 means finished
            return data
        time.sleep(0.5)

    raise HTTPException(status_code=504, detail="Judge0 execution timed out")


@app.post("/run", response_model=RunResponse)
async def run_code(req: RunRequest):
    language_id = LANGUAGE_IDS.get(req.language.lower())
    if not language_id:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{req.language}'. Supported: {list(LANGUAGE_IDS)}",
        )

    results: list[TestResult] = []
    async with httpx.AsyncClient() as client:
        for tc in req.test_cases:
            data = await submit_to_judge0(client, req.source_code, language_id, tc.input)
            status_desc = data.get("status", {}).get("description", "Unknown")
            actual = data.get("stdout")
            stderr = data.get("stderr") or data.get("compile_output")
            passed = status_desc == "Accepted" and normalize(actual) == normalize(tc.expected_output)

            results.append(TestResult(
                label=tc.label,
                passed=passed,
                hidden=tc.hidden,
                input=None if tc.hidden else tc.input,
                expected_output=None if tc.hidden else tc.expected_output,
                actual_output=None if tc.hidden else actual,
                stderr=stderr,
                status=status_desc,
            ))

    passed_count = sum(1 for r in results if r.passed)
    return RunResponse(
        all_passed=passed_count == len(results),
        passed_count=passed_count,
        total_count=len(results),
        results=results,
    )


@app.get("/health")
def health():
    return {"status": "ok", "judge0_url": JUDGE0_URL}
