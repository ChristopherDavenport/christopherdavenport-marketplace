"""Result writers: JSON (machine) and Markdown (human)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any


def _checks_to_dict(checks: list[Any]) -> list[dict[str, Any]]:
    return [asdict(c) for c in checks]


def serialize_results(plugin: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(cases)
    if n == 0:
        return {"plugin": plugin, "cases": [], "summary": {}}

    judge_wins = sum(1 for c in cases if c["judge"]["winner"] == "skill")
    judge_losses = sum(1 for c in cases if c["judge"]["winner"] == "baseline")
    judge_ties = n - judge_wins - judge_losses

    expectations_met = sum(1 for c in cases if c.get("expectation_met"))

    by_expectation: dict[str, dict[str, int]] = {}
    for c in cases:
        exp = c.get("expectation", "skill_wins")
        b = by_expectation.setdefault(exp, {"total": 0, "met": 0})
        b["total"] += 1
        if c.get("expectation_met"):
            b["met"] += 1

    # Average rubric only over cases that have a non-empty rubric — off-topic
    # guards typically declare no rubric and would otherwise drag the mean.
    scored = [c for c in cases if c["baseline"]["rubric"]]
    if scored:
        baseline_pass = sum(c["baseline"]["rubric_pass_rate"] for c in scored) / len(scored)
        skill_pass = sum(c["skill"]["rubric_pass_rate"] for c in scored) / len(scored)
    else:
        baseline_pass = 0.0
        skill_pass = 0.0

    total_cost = sum(
        c["baseline"]["cost_usd"] + c["skill"]["cost_usd"] for c in cases
    )

    return {
        "plugin": plugin,
        "summary": {
            "n_cases": n,
            "expectations_met": expectations_met,
            "by_expectation": by_expectation,
            "judge_wins_for_skill": judge_wins,
            "judge_wins_for_baseline": judge_losses,
            "judge_ties": judge_ties,
            "n_scored": len(scored),
            "baseline_rubric_pass_rate": round(baseline_pass, 4),
            "skill_rubric_pass_rate": round(skill_pass, 4),
            "rubric_delta": round(skill_pass - baseline_pass, 4),
            "total_cli_cost_usd": round(total_cost, 4),
        },
        "cases": cases,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def _rubric_table(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "_(no rubric)_"
    lines = ["| Criterion | Pass | Evidence |", "| --- | --- | --- |"]
    for c in checks:
        ev = (c["evidence"] or "").replace("|", "\\|")
        mark = "✓" if c["passed"] else "✗"
        lines.append(f"| {c['name']} | {mark} | `{ev}` |" if ev else f"| {c['name']} | {mark} | |")
    return "\n".join(lines)


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    plugin = payload["plugin"]
    cases = payload["cases"]

    by_exp = s.get("by_expectation", {})
    by_exp_line = ", ".join(
        f"{kind} {v['met']}/{v['total']}" for kind, v in sorted(by_exp.items())
    ) or "(none)"

    headline_parts = [
        f"# Eval report: `{plugin}`",
        "",
        f"- Cases: **{s['n_cases']}**",
        f"- Expectations met: **{s['expectations_met']}/{s['n_cases']}** "
        f"({by_exp_line})",
        f"- Judge: skill won **{s['judge_wins_for_skill']}**, baseline won "
        f"**{s['judge_wins_for_baseline']}**, ties **{s['judge_ties']}**",
        f"- Rubric pass-rate (over {s['n_scored']} scored case(s)): baseline "
        f"**{s['baseline_rubric_pass_rate']:.0%}**, "
        f"skill **{s['skill_rubric_pass_rate']:.0%}** "
        f"(Δ **{s['rubric_delta']:+.0%}**)",
        f"- CLI cost: **${s['total_cli_cost_usd']:.2f}** "
        "(judge cost not counted)",
        "",
    ]

    table = [
        "## Cases",
        "",
        "| Case | Expected | Met | Judge | Baseline rubric | Skill rubric |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in cases:
        met_mark = "✓" if c.get("expectation_met") else "✗"
        table.append(
            f"| `{c['id']}` | {c.get('expectation', 'skill_wins')} | {met_mark} "
            f"| **{c['judge']['winner']}** "
            f"| {c['baseline']['rubric_pass_rate']:.0%} "
            f"| {c['skill']['rubric_pass_rate']:.0%} |"
        )
    table.append("")

    details = ["## Per-case detail", ""]
    for c in cases:
        exp = c.get("expectation", "skill_wins")
        met = c.get("expectation_met", True)
        flag = "" if met else " — **[FAILED EXPECTATION]**"
        details += [
            f"### `{c['id']}`",
            "",
            f"**Expected:** `{exp}` · **Met:** {'✓' if met else '✗'}{flag}",
            "",
            "**Prompt**",
            "",
            "```",
            c["prompt"].strip(),
            "```",
            "",
            f"**Judge:** **{c['judge']['winner']}** — {c['judge']['reasoning']}",
            "",
            "**Per-criterion verdict (judge)**",
            "",
            "| Criterion | Better |",
            "| --- | --- |",
        ]
        for pc in c["judge"]["per_criterion"]:
            details.append(f"| {pc['name']} | {pc['better']} |")
        details += [
            "",
            "**Baseline rubric**",
            "",
            _rubric_table(c["baseline"]["rubric"]),
            "",
            "**Skill rubric**",
            "",
            _rubric_table(c["skill"]["rubric"]),
            "",
            "<details><summary>Baseline answer</summary>",
            "",
            c["baseline"]["text"].strip(),
            "",
            "</details>",
            "",
            "<details><summary>Skill-loaded answer</summary>",
            "",
            c["skill"]["text"].strip(),
            "",
            "</details>",
            "",
            "---",
            "",
        ]

    return "\n".join(headline_parts + table + details)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(render_markdown(payload))
