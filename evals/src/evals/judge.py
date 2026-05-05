"""LLM-as-judge head-to-head between baseline and skill-loaded answers.

Anonymizes the two answers as A and B, randomized per case to avoid position
bias. Asks claude-sonnet-4-6 (temperature 0) for a JSON verdict, validates it
locally, retries once on parse failure, then de-anonymizes back to baseline /
skill labels.
"""

from __future__ import annotations

import json
import os
import random
import re
from dataclasses import dataclass
from typing import Any

JUDGE_MAX_TOKENS = 2048

# Picked per-provider in _client() because Vertex requires the @suffix form.
_JUDGE_MODEL_BASE = "claude-sonnet-4-6"


def _client() -> tuple[object, str]:
    """Return (client, model_id) appropriate for the current environment.

    Selection mirrors how the user already runs `claude`:
      - CLAUDE_CODE_USE_VERTEX=1   → AnthropicVertex (model gets @default suffix)
      - CLAUDE_CODE_USE_BEDROCK=1  → AnthropicBedrock
      - else                        → Anthropic (needs ANTHROPIC_API_KEY)
    """
    if os.environ.get("CLAUDE_CODE_USE_VERTEX") == "1":
        from anthropic import AnthropicVertex

        return AnthropicVertex(), f"{_JUDGE_MODEL_BASE}@default"
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1":
        from anthropic import AnthropicBedrock

        return AnthropicBedrock(), f"anthropic.{_JUDGE_MODEL_BASE}-v1:0"
    from anthropic import Anthropic

    if "ANTHROPIC_API_KEY" not in os.environ:
        raise RuntimeError(
            "judge needs auth: set CLAUDE_CODE_USE_VERTEX=1 (with "
            "ANTHROPIC_VERTEX_PROJECT_ID), CLAUDE_CODE_USE_BEDROCK=1, or "
            "ANTHROPIC_API_KEY."
        )
    return Anthropic(), _JUDGE_MODEL_BASE

_SYSTEM = """You are an impartial judge comparing two answers to the same \
programming question. You must decide which answer is more idiomatic, correct, \
and useful, using the question, the focus area, and the rubric criteria as \
your guide. Reply with a single JSON object and nothing else."""

_USER_TEMPLATE = """# Question

{question}

# Focus area for judging

{focus}

# Rubric criteria (just the names — for your reference)

{criteria}

# Answer A

{answer_a}

# Answer B

{answer_b}

# Your task

Compare the two answers. Return a single JSON object with exactly this shape:

{{
  "winner": "A" | "B" | "tie",
  "reasoning": "two or three sentences",
  "per_criterion": [
    {{"name": "<criterion name verbatim>", "better": "A" | "B" | "tie"}}
  ]
}}

Output the JSON object only — no prose, no code fence, no preamble."""


@dataclass
class CriterionVerdict:
    name: str
    better: str  # "baseline" | "skill" | "tie"


@dataclass
class JudgeVerdict:
    winner: str  # "baseline" | "skill" | "tie"
    reasoning: str
    per_criterion: list[CriterionVerdict]
    raw: dict[str, Any]


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any]:
    m = _JSON_RE.search(text)
    if not m:
        raise ValueError(f"no JSON object in judge output: {text[:300]}")
    return json.loads(m.group(0))


def _validate(parsed: dict[str, Any], criterion_names: list[str]) -> None:
    if parsed.get("winner") not in {"A", "B", "tie"}:
        raise ValueError(f"bad winner: {parsed.get('winner')!r}")
    if not isinstance(parsed.get("reasoning"), str):
        raise ValueError("reasoning missing or not a string")
    pc = parsed.get("per_criterion")
    if not isinstance(pc, list):
        raise ValueError("per_criterion missing or not a list")
    seen = {item.get("name") for item in pc if isinstance(item, dict)}
    missing = set(criterion_names) - seen
    if missing:
        raise ValueError(f"per_criterion missing entries: {sorted(missing)}")
    for item in pc:
        if item.get("better") not in {"A", "B", "tie"}:
            raise ValueError(f"bad per_criterion.better: {item}")


def judge(
    question: str,
    baseline_answer: str,
    skill_answer: str,
    judge_focus: str,
    criterion_names: list[str],
    rng_seed: int | None = None,
) -> JudgeVerdict:
    rng = random.Random(rng_seed)
    a_is_baseline = rng.random() < 0.5
    answer_a = baseline_answer if a_is_baseline else skill_answer
    answer_b = skill_answer if a_is_baseline else baseline_answer

    user = _USER_TEMPLATE.format(
        question=question.strip(),
        focus=judge_focus.strip(),
        criteria="\n".join(f"- {n}" for n in criterion_names),
        answer_a=answer_a.strip(),
        answer_b=answer_b.strip(),
    )

    client, model = _client()

    last_error: Exception | None = None
    parsed: dict[str, Any] | None = None
    for attempt in range(2):
        msg = client.messages.create(
            model=model,
            max_tokens=JUDGE_MAX_TOKENS,
            temperature=0.0,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        try:
            parsed = _extract_json(text)
            _validate(parsed, criterion_names)
            break
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            parsed = None
    if parsed is None:
        raise RuntimeError(f"judge failed twice: {last_error}")

    def deanon(label: str) -> str:
        if label == "tie":
            return "tie"
        if (label == "A") == a_is_baseline:
            return "baseline"
        return "skill"

    per_criterion = [
        CriterionVerdict(name=item["name"], better=deanon(item["better"]))
        for item in parsed["per_criterion"]
    ]
    return JudgeVerdict(
        winner=deanon(parsed["winner"]),
        reasoning=parsed["reasoning"],
        per_criterion=per_criterion,
        raw=parsed,
    )
