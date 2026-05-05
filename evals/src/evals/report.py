"""Result writers: JSON (machine) and Markdown (human).

Multi-model shape: each case carries a `models` map keyed by alias
(haiku/sonnet/opus). The summary aggregates per-model and totals across all.
N=1 (single-model run) renders cleanly — same templates, just one column.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _aggregate_one_model(cases: list[dict[str, Any]], alias: str) -> dict[str, Any]:
    """Aggregate stats for a single model across all cases."""
    n = len(cases)
    if n == 0:
        return {}

    per = [c["models"][alias] for c in cases if alias in c["models"]]
    if not per:
        return {}

    judge_wins = sum(1 for m in per if m["judge"]["winner"] == "skill")
    judge_losses = sum(1 for m in per if m["judge"]["winner"] == "baseline")
    judge_ties = len(per) - judge_wins - judge_losses
    expectations_met = sum(1 for m in per if m.get("expectation_met"))

    scored = [m for m in per if m["baseline"]["rubric"]]
    if scored:
        baseline_pass = sum(m["baseline"]["rubric_pass_rate"] for m in scored) / len(scored)
        skill_pass = sum(m["skill"]["rubric_pass_rate"] for m in scored) / len(scored)
    else:
        baseline_pass = skill_pass = 0.0

    cost = sum(m["baseline"]["cost_usd"] + m["skill"]["cost_usd"] for m in per)

    return {
        "n_cases": len(per),
        "expectations_met": expectations_met,
        "judge_wins_for_skill": judge_wins,
        "judge_wins_for_baseline": judge_losses,
        "judge_ties": judge_ties,
        "n_scored": len(scored),
        "baseline_rubric_pass_rate": round(baseline_pass, 4),
        "skill_rubric_pass_rate": round(skill_pass, 4),
        "rubric_delta": round(skill_pass - baseline_pass, 4),
        "cost_usd": round(cost, 4),
    }


def serialize_results(
    plugin: str, cases: list[dict[str, Any]], models: list[str]
) -> dict[str, Any]:
    n = len(cases)
    if n == 0:
        return {"plugin": plugin, "cases": [], "summary": {}}

    per_model = {alias: _aggregate_one_model(cases, alias) for alias in models}

    by_expectation: dict[str, dict[str, int]] = {}
    for c in cases:
        exp = c.get("expectation", "skill_wins")
        b = by_expectation.setdefault(exp, {"total": 0, "met": {a: 0 for a in models}})
        b["total"] += 1
        for alias in models:
            if c["models"].get(alias, {}).get("expectation_met"):
                b["met"][alias] += 1

    total_cost = sum(m.get("cost_usd", 0.0) for m in per_model.values())

    return {
        "plugin": plugin,
        "summary": {
            "n_cases": n,
            "models": models,
            "per_model": per_model,
            "by_expectation": by_expectation,
            "total_cost_usd": round(total_cost, 4),
        },
        "cases": cases,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


# ----- markdown rendering --------------------------------------------------


def _rubric_table(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "_(no rubric)_"
    lines = ["| Criterion | Pass | Evidence |", "| --- | --- | --- |"]
    for c in checks:
        ev = (c["evidence"] or "").replace("|", "\\|")
        mark = "✓" if c["passed"] else "✗"
        lines.append(
            f"| {c['name']} | {mark} | `{ev}` |" if ev else f"| {c['name']} | {mark} | |"
        )
    return "\n".join(lines)


def _judge_short(winner: str) -> str:
    return {"skill": "✓ skill", "baseline": "✗ baseline", "tie": "= tie"}.get(winner, winner)


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    plugin = payload["plugin"]
    cases = payload["cases"]
    if not s:
        # All cases failed (or none ran). Emit a stub so the file still exists.
        return f"# Eval report: `{plugin}`\n\n_No cases produced results._\n"
    models: list[str] = s["models"]
    backend = payload.get("backend", "sdk")
    backend_label = (
        "CLI subprocess (claude --bare --plugin-dir)" if backend == "cli"
        else "SDK direct (sonnet/haiku at temperature=0; opus uncontrolled)"
    )

    lines: list[str] = [
        f"# Eval report: `{plugin}`",
        "",
        f"- Backend: **{backend_label}**",
        f"- Cases: **{s['n_cases']}**",
        f"- Models: **{', '.join(models)}**",
        f"- Total cost: **${s['total_cost_usd']:.2f}** (judge cost not counted)",
        "",
        "## Per-model summary",
        "",
        "| Model | Expectations met | Judge (skill / baseline / tie) | Rubric: baseline → skill (Δ) |",
        "| --- | --- | --- | --- |",
    ]
    for alias in models:
        m = s["per_model"][alias]
        if not m:
            lines.append(f"| {alias} | _no data_ | | |")
            continue
        opus_note = " ¹" if alias == "opus" else ""
        lines.append(
            f"| `{alias}`{opus_note} | {m['expectations_met']}/{m['n_cases']} "
            f"| {m['judge_wins_for_skill']} / {m['judge_wins_for_baseline']} / {m['judge_ties']} "
            f"| {m['baseline_rubric_pass_rate']:.0%} → {m['skill_rubric_pass_rate']:.0%} "
            f"({m['rubric_delta']:+.0%}) |"
        )
    if "opus" in models:
        lines += ["", "¹ Opus 4.7 does not accept the `temperature` parameter; its numbers are indicators, not measurements (re-runs may flip individual verdicts)."]
    lines.append("")

    # Per-expectation breakdown
    by_exp = s.get("by_expectation", {})
    if by_exp:
        lines += ["## Expectations by kind", ""]
        header = "| Expectation kind | Total |" + "".join(f" {a} met |" for a in models)
        sep = "| --- | --- |" + "".join(" --- |" for _ in models)
        lines += [header, sep]
        for kind, v in sorted(by_exp.items()):
            row = f"| `{kind}` | {v['total']} |"
            for a in models:
                row += f" {v['met'][a]}/{v['total']} |"
            lines.append(row)
        lines.append("")

    # Cases summary table
    lines += ["## Cases", ""]
    header = "| Case | Expected |" + "".join(f" {a} |" for a in models)
    sep = "| --- | --- |" + "".join(" --- |" for _ in models)
    lines += [header, sep]
    for c in cases:
        row = f"| `{c['id']}` | {c.get('expectation', 'skill_wins')} |"
        for a in models:
            m = c["models"].get(a)
            if not m:
                row += " _n/a_ |"
                continue
            mark = "✓" if m.get("expectation_met") else "✗"
            row += f" {mark} {_judge_short(m['judge']['winner'])} |"
        lines.append(row)
    lines.append("")

    # Per-case detail
    lines += ["## Per-case detail", ""]
    for c in cases:
        lines += [
            f"### `{c['id']}`",
            "",
            "**Prompt**",
            "",
            "```",
            c["prompt"].strip(),
            "```",
            "",
        ]
        if c.get("judge_focus"):
            lines += [f"**Judge focus:** {c['judge_focus'].strip()}", ""]

        for alias in models:
            m = c["models"].get(alias)
            if not m:
                lines.append(f"#### `{alias}` — _no data_")
                continue
            exp_met = m.get("expectation_met")
            flag = "" if exp_met else " — **[FAILED EXPECTATION]**"
            lines += [
                f"#### `{alias}`",
                "",
                f"**Met:** {'✓' if exp_met else '✗'}{flag}  ·  "
                f"**Judge:** **{m['judge']['winner']}** — {m['judge']['reasoning']}",
                "",
                "**Per-criterion verdict (judge)**",
                "",
                "| Criterion | Better |",
                "| --- | --- |",
            ]
            for pc in m["judge"]["per_criterion"]:
                lines.append(f"| {pc['name']} | {pc['better']} |")
            lines += [
                "",
                "**Baseline rubric**",
                "",
                _rubric_table(m["baseline"]["rubric"]),
                "",
                "**Skill rubric**",
                "",
                _rubric_table(m["skill"]["rubric"]),
                "",
                f"<details><summary>{alias}: baseline answer</summary>",
                "",
                m["baseline"]["text"].strip(),
                "",
                "</details>",
                "",
                f"<details><summary>{alias}: skill-loaded answer</summary>",
                "",
                m["skill"]["text"].strip(),
                "",
                "</details>",
                "",
            ]

        lines += ["---", ""]

    return "\n".join(lines)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(render_markdown(payload))
