"""Deterministic rubric checks against an answer's text.

A criterion is a small dict from cases.yaml. Supported kinds:

- must_contain        — single regex must match
- must_not_contain    — single regex must NOT match (catches anti-patterns)
- any_of              — at least one of N regexes matches
- all_of              — all N regexes match

All matching is case-insensitive and DOTALL by default.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_FLAGS = re.IGNORECASE | re.DOTALL
_EVIDENCE_LEN = 160


@dataclass
class CheckResult:
    name: str
    kind: str
    passed: bool
    evidence: str | None
    why: str


def _truncate(s: str) -> str:
    s = s.replace("\n", " ")
    return s if len(s) <= _EVIDENCE_LEN else s[:_EVIDENCE_LEN] + "…"


def _first_match(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, _FLAGS)
    return _truncate(m.group(0)) if m else None


def check_one(criterion: dict[str, Any], text: str) -> CheckResult:
    name = criterion["name"]
    kind = criterion["kind"]
    why = criterion.get("why", "")

    if kind == "must_contain":
        ev = _first_match(text, criterion["pattern"])
        return CheckResult(name, kind, ev is not None, ev, why)

    if kind == "must_not_contain":
        ev = _first_match(text, criterion["pattern"])
        return CheckResult(name, kind, ev is None, ev, why)

    if kind == "any_of":
        for p in criterion["patterns"]:
            ev = _first_match(text, p)
            if ev is not None:
                return CheckResult(name, kind, True, ev, why)
        return CheckResult(name, kind, False, None, why)

    if kind == "all_of":
        evidences: list[str] = []
        for p in criterion["patterns"]:
            ev = _first_match(text, p)
            if ev is None:
                return CheckResult(
                    name, kind, False, f"missing pattern: {p}", why
                )
            evidences.append(ev)
        return CheckResult(name, kind, True, " | ".join(evidences), why)

    raise ValueError(f"unknown rubric kind: {kind!r} on criterion {name!r}")


def grade(rubric: list[dict[str, Any]], text: str) -> list[CheckResult]:
    return [check_one(c, text) for c in rubric]


def pass_rate(results: list[CheckResult]) -> float:
    if not results:
        return 0.0
    return sum(1 for r in results if r.passed) / len(results)
