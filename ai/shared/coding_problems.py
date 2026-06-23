"""Coding round configuration — problem IDs match frontend/src/lib/codingProblems.ts"""

from __future__ import annotations

import os
import random

CODING_ROUND_TIME_SEC = int(os.getenv("CODING_ROUND_TIME_SEC", str(20 * 60)))

CODING_PROBLEM_IDS = ("classify_number", "reverse_string")
DEFAULT_CODING_PROBLEM_ID = "classify_number"


def pick_coding_problem_id() -> str:
    return random.choice(CODING_PROBLEM_IDS)
