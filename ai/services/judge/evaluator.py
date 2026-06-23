"""
services/judge/evaluator.py
────────────────────────────
LLM-as-Judge pattern: uses Gemini to evaluate a completed interview session
and produce a structured, multi-dimensional scorecard.

Architecture
────────────
After the interview session ends, the full transcript (Q&A pairs) and the
candidate's resume context are assembled into a detailed judge prompt and
sent to the Gemini text model (NOT the live audio model).

The judge prompt instructs Gemini to:
  1. Score the candidate on 5 dimensions (1-10 each)
  2. Provide a short rationale per dimension
  3. Compute a weighted overall score
  4. Give 2-3 concrete strengths
  5. Give 2-3 concrete areas for improvement
  6. Return everything as valid JSON

Public API
──────────
    run_judge(transcript, resume_context, api_key) -> JudgeReport | None
    print_report(report: JudgeReport) -> None
"""

from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from typing import Optional

from shared.ui import Colors, print_status, print_error


# ──────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────

@dataclass
class DimensionScore:
    name:      str
    score:     int          # 1-10
    rationale: str


@dataclass
class JudgeReport:
    dimensions:          list[DimensionScore] = field(default_factory=list)
    overall_score:       float = 0.0
    overall_verdict:     str   = ""
    strengths:           list[str] = field(default_factory=list)
    improvements:        list[str] = field(default_factory=list)
    hire_recommendation: str = ""   # "Strong Yes" / "Yes" / "Maybe" / "No"


# ──────────────────────────────────────────────
# Scoring configuration
# ──────────────────────────────────────────────

_DIMENSIONS = [
    ("Technical Knowledge",
     "How well did the candidate demonstrate technical depth in their domain? "
     "Did their answers align with the skills listed on their resume?"),
    ("Communication & Clarity",
     "Were answers structured, concise, and easy to follow? "
     "Did the candidate express ideas clearly in a voice setting?"),
    ("Problem-Solving Approach",
     "Did the candidate break problems down logically? "
     "Did they consider trade-offs or alternatives?"),
    ("Behavioural & Situational Responses",
     "Did behavioural answers follow STAR format (Situation, Task, Action, Result)? "
     "Were examples specific and credible?"),
    ("Resume Consistency",
     "Did the candidate's spoken answers align with what is stated on their resume? "
     "Were there contradictions or knowledge gaps in areas they claimed expertise?"),
]

_WEIGHTS = [0.30, 0.20, 0.20, 0.15, 0.15]   # must sum to 1.0

_JUDGE_SYSTEM = """\
You are an expert technical interview evaluator.
Your job is to impartially assess a candidate's interview performance
using only the transcript and resume provided — no prior knowledge.
Be fair but rigorous. Base every score on specific evidence from the transcript.
Respond ONLY with valid JSON — no markdown fences, no commentary outside the JSON.
"""

# Fallback model chain — tries newest first, backs off on quota errors
_JUDGE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


# ──────────────────────────────────────────────
# Judge prompt builder
# ──────────────────────────────────────────────

def _build_judge_prompt(
    transcript: list[tuple[str, str, str]],
    resume_context: str,
) -> str:
    """Assemble the full prompt sent to the Gemini judge."""

    qa_lines: list[str] = []
    for _ts, role, text in transcript:
        if not text.strip() or text.strip() in ("[interrupted]", "[inaudible]"):
            continue
        speaker = "CANDIDATE" if role == "You" else "INTERVIEWER"
        qa_lines.append(f"{speaker}: {text.strip()}")

    transcript_text = "\n".join(qa_lines) if qa_lines else "(No transcript available)"

    dim_instructions = "\n".join(
        f'  "{name}": {{"score": <1-10>, "rationale": "<2-3 sentence justification>"}}'
        for name, _ in _DIMENSIONS
    )

    dim_criteria = "\n".join(
        f"  • {name}: {criteria}"
        for name, criteria in _DIMENSIONS
    )

    return textwrap.dedent(f"""
    You are evaluating a technical job interview. Below is the candidate's resume
    context and the full interview transcript. Score the candidate on each dimension
    using ONLY evidence from the transcript.

    ═══════════════════════════════════════
    CANDIDATE RESUME CONTEXT
    ═══════════════════════════════════════
    {resume_context if resume_context else "(No resume provided)"}

    ═══════════════════════════════════════
    INTERVIEW TRANSCRIPT
    ═══════════════════════════════════════
    {transcript_text}

    ═══════════════════════════════════════
    SCORING CRITERIA (score each 1-10)
    ═══════════════════════════════════════
    {dim_criteria}

    ═══════════════════════════════════════
    REQUIRED JSON OUTPUT FORMAT
    ═══════════════════════════════════════
    Return ONLY this JSON object (no markdown, no extra text):

    {{
      "dimensions": {{
    {dim_instructions}
      }},
      "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
      "improvements": ["<area 1>", "<area 2>", "<area 3>"],
      "hire_recommendation": "<Strong Yes | Yes | Maybe | No>",
      "overall_verdict": "<2-3 sentence holistic summary of the candidate's performance>"
    }}
    """).strip()


# ──────────────────────────────────────────────
# Core judge call
# ──────────────────────────────────────────────

def run_judge(
    transcript:     list[tuple[str, str, str]],
    resume_context: str,
    api_key:        str | None = None,
    model:          str | None = None,
) -> Optional[JudgeReport]:
    """
    Send the interview to Groq for evaluation.

    Returns a JudgeReport on success, or None if it fails.
    This is a synchronous function — call it via run_in_executor if needed.
    """
    try:
        from groq import Groq  # type: ignore
    except ImportError:
        print_error("groq package not installed — cannot run judge.")
        return None

    from shared.config import GROQ_API_KEY, GROQ_JUDGE_MODEL

    key = api_key or GROQ_API_KEY
    if not key:
        print_error(
            "Groq API key is not set. Please set the GROQ_API_KEY environment variable "
            "or update it in shared/config.py."
        )
        return None

    model_name = model or GROQ_JUDGE_MODEL
    print_status(f"Running LLM-as-Judge evaluation via Groq ({model_name}) …", Colors.CYAN)

    try:
        client = Groq(api_key=key)
        prompt = _build_judge_prompt(transcript, resume_context)

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": _JUDGE_SYSTEM,
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=model_name,
            response_format={"type": "json_object"},
        )
        raw = chat_completion.choices[0].message.content.strip()

        # Strip accidental markdown fences (just in case)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)
        print_status(f"Judge evaluation complete (model: {model_name})", Colors.GREEN)
        return _parse_report(data)

    except json.JSONDecodeError as e:
        print_error(f"Judge returned invalid JSON: {e}")
        return None
    except Exception as e:
        print_error(f"Judge call failed via Groq: {e}")
        return None


def _parse_report(data: dict) -> JudgeReport:
    """Convert the raw JSON dict from Gemini into a JudgeReport."""
    report = JudgeReport()
    raw_dims: dict = data.get("dimensions", {})
    weighted_sum = 0.0

    for i, (name, _) in enumerate(_DIMENSIONS):
        entry  = raw_dims.get(name, {})
        score  = int(entry.get("score", 5))
        reason = entry.get("rationale", "")
        report.dimensions.append(DimensionScore(name=name, score=score, rationale=reason))
        weighted_sum += score * _WEIGHTS[i]

    report.overall_score       = round(weighted_sum, 1)
    report.overall_verdict     = data.get("overall_verdict", "")
    report.strengths           = data.get("strengths", [])
    report.improvements        = data.get("improvements", [])
    report.hire_recommendation = data.get("hire_recommendation", "—")

    return report


# ──────────────────────────────────────────────
# Pretty-print the report to terminal
# ──────────────────────────────────────────────

def _score_bar(score: int, total: int = 10) -> str:
    filled = round(score * 10 / total)
    return f"[{'█' * filled}{'░' * (10 - filled)}] {score}/{total}"


def _score_color(score: int) -> str:
    if score >= 8: return Colors.GREEN
    if score >= 6: return Colors.YELLOW
    return Colors.RED


def _recommend_color(rec: str) -> str:
    rec_l = rec.lower()
    if "strong yes" in rec_l: return Colors.GREEN
    if "yes"        in rec_l: return Colors.GREEN
    if "maybe"      in rec_l: return Colors.YELLOW
    return Colors.RED


def print_report(report: JudgeReport) -> None:
    """Print the full scorecard to the terminal."""
    W = 62

    print()
    print(f"{Colors.CYAN}{Colors.BOLD}" + "═" * W + Colors.RESET)
    print(f"{Colors.CYAN}{Colors.BOLD}  📊  INTERVIEW SCORECARD  (LLM-as-Judge){Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}" + "═" * W + Colors.RESET)
    print()

    for dim in report.dimensions:
        color = _score_color(dim.score)
        print(
            f"  {color}{Colors.BOLD}{dim.name:<36}{Colors.RESET}"
            f"  {color}{_score_bar(dim.score)}{Colors.RESET}"
        )
        for line in textwrap.wrap(dim.rationale, width=56):
            print(f"    {Colors.DIM}{line}{Colors.RESET}")
        print()

    overall_color = _score_color(int(round(report.overall_score)))
    print("─" * W)
    print(
        f"  {Colors.BOLD}Overall Score (weighted){Colors.RESET}"
        f"   {overall_color}{Colors.BOLD}{report.overall_score:.1f} / 10{Colors.RESET}"
    )
    print()

    rec_color = _recommend_color(report.hire_recommendation)
    print(
        f"  Hire Recommendation:  "
        f"{rec_color}{Colors.BOLD}{report.hire_recommendation}{Colors.RESET}"
    )
    print()

    if report.overall_verdict:
        print(f"{Colors.BOLD}  Verdict{Colors.RESET}")
        for line in textwrap.wrap(report.overall_verdict, width=56):
            print(f"    {line}")
        print()

    if report.strengths:
        print(f"{Colors.GREEN}{Colors.BOLD}  ✅  Strengths{Colors.RESET}")
        for s in report.strengths:
            for line in textwrap.wrap(s, width=54):
                print(f"    {Colors.GREEN}• {line}{Colors.RESET}")
        print()

    if report.improvements:
        print(f"{Colors.YELLOW}{Colors.BOLD}  ⚠️   Areas for Improvement{Colors.RESET}")
        for imp in report.improvements:
            for line in textwrap.wrap(imp, width=54):
                print(f"    {Colors.YELLOW}• {line}{Colors.RESET}")
        print()

    print(f"{Colors.CYAN}{Colors.BOLD}" + "═" * W + Colors.RESET)
    print()
