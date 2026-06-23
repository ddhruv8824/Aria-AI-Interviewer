"""
api/routers/code_run.py
───────────────────────
LeetCode-style code execution for the coding question UI.

Default: local in-process runner (no Docker, Postgres, or Redis).
Optional: set CODE_EXECUTOR=judge0 and JUDGE0_URL for self-hosted Judge0.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/code", tags=["Code"])

CODE_EXECUTOR = os.environ.get("CODE_EXECUTOR", "local").lower()
JUDGE0_URL = os.environ.get("JUDGE0_URL", "http://localhost:2358")
LOCAL_TIMEOUT_SEC = int(os.environ.get("CODE_RUN_TIMEOUT_SEC", "10"))

LANGUAGE_IDS = {
    "python": 71,
    "javascript": 63,
}

LOCAL_LANGUAGES = {"python", "javascript"}


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


def _normalize(s: Optional[str]) -> str:
    return (s or "").strip()


def _local_command(language: str) -> list[str]:
    lang = language.lower()
    if lang == "python":
        return [sys.executable, "-c"]
    if lang == "javascript":
        node = shutil.which("node")
        if not node:
            raise HTTPException(
                status_code=503,
                detail="Node.js is not installed. Use Python for local testing, or install Node.js.",
            )
        return [node, "-e"]
    raise HTTPException(
        status_code=400,
        detail=(
            f"Language '{language}' is not supported in local mode. "
            f"Supported locally: {sorted(LOCAL_LANGUAGES)}. "
            "Set CODE_EXECUTOR=judge0 for Java/C++."
        ),
    )


def _run_local(source_code: str, language: str, stdin: str) -> tuple[Optional[str], Optional[str], str]:
    prefix = _local_command(language)
    try:
        proc = subprocess.run(
            [*prefix, source_code],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=LOCAL_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return None, f"Execution timed out ({LOCAL_TIMEOUT_SEC}s limit)", "Time Limit Exceeded"

    stdout = proc.stdout
    stderr = (proc.stderr or "").strip() or None
    if proc.returncode != 0:
        detail = stderr or f"Process exited with code {proc.returncode}"
        return stdout or None, detail, "Runtime Error"
    return stdout, stderr, "Accepted"


async def _submit_to_judge0(
    client: httpx.AsyncClient,
    source_code: str,
    language_id: int,
    stdin: str,
) -> dict:
    resp = await client.post(
        f"{JUDGE0_URL}/submissions?base64_encoded=false&wait=false",
        json={"source_code": source_code, "language_id": language_id, "stdin": stdin},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=(
                f"Judge0 submission failed ({resp.status_code}): {resp.text[:300]}. "
                f"Is Judge0 running at {JUDGE0_URL}?"
            ),
        )
    token = resp.json()["token"]

    for _ in range(30):
        poll = await client.get(
            f"{JUDGE0_URL}/submissions/{token}?base64_encoded=false",
            timeout=30,
        )
        data = poll.json()
        if data.get("status", {}).get("id", 0) > 2:
            return data
        time.sleep(0.5)

    raise HTTPException(status_code=504, detail="Judge0 execution timed out")


def _result_from_judge0(data: dict, tc: TestCase) -> TestResult:
    status_desc = data.get("status", {}).get("description", "Unknown")
    actual = data.get("stdout")
    stderr = data.get("stderr") or data.get("compile_output")
    passed = status_desc == "Accepted" and _normalize(actual) == _normalize(tc.expected_output)
    return TestResult(
        label=tc.label,
        passed=passed,
        hidden=tc.hidden,
        input=None if tc.hidden else tc.input,
        expected_output=None if tc.hidden else tc.expected_output,
        actual_output=None if tc.hidden else actual,
        stderr=stderr,
        status=status_desc,
    )


def _result_from_local(actual: Optional[str], stderr: Optional[str], status: str, tc: TestCase) -> TestResult:
    passed = status == "Accepted" and _normalize(actual) == _normalize(tc.expected_output)
    if status == "Accepted" and not passed:
        status = "Wrong Answer"
    return TestResult(
        label=tc.label,
        passed=passed,
        hidden=tc.hidden,
        input=None if tc.hidden else tc.input,
        expected_output=None if tc.hidden else tc.expected_output,
        actual_output=None if tc.hidden else actual,
        stderr=stderr,
        status=status,
    )


@router.get("/health")
async def code_health():
    return {
        "status": "ok",
        "executor": CODE_EXECUTOR,
        "local_languages": sorted(LOCAL_LANGUAGES),
        "judge0_url": JUDGE0_URL if CODE_EXECUTOR == "judge0" else None,
    }


@router.post("/run", response_model=RunResponse)
async def run_code(req: RunRequest) -> RunResponse:
    language = req.language.lower()
    results: list[TestResult] = []

    if CODE_EXECUTOR == "judge0":
        language_id = LANGUAGE_IDS.get(language)
        if not language_id:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language '{req.language}'. Supported: {list(LANGUAGE_IDS)}",
            )
        async with httpx.AsyncClient() as client:
            for tc in req.test_cases:
                data = await _submit_to_judge0(client, req.source_code, language_id, tc.input)
                results.append(_result_from_judge0(data, tc))
    else:
        if language not in LOCAL_LANGUAGES:
            _local_command(language)
        for tc in req.test_cases:
            actual, stderr, status = _run_local(req.source_code, language, tc.input)
            results.append(_result_from_local(actual, stderr, status, tc))

    passed_count = sum(1 for r in results if r.passed)
    return RunResponse(
        all_passed=passed_count == len(results),
        passed_count=passed_count,
        total_count=len(results),
        results=results,
    )
