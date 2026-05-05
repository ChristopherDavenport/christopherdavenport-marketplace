"""Orchestrator: load a plugin's cases, run baseline + skill, score, report."""

from __future__ import annotations

import datetime as _dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from . import cli_runner, judge, report, rubric

EVALS_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = EVALS_DIR / "results"

VALID_EXPECTATIONS = {"skill_wins", "tie", "skill_wins_strict"}


def _expectation_met(
    expectation: str,
    judge_winner: str,
    skill_checks: list[rubric.CheckResult],
) -> bool:
    if expectation == "skill_wins":
        return judge_winner == "skill"
    if expectation == "tie":
        return judge_winner == "tie"
    if expectation == "skill_wins_strict":
        all_must_not_pass = all(
            c.passed for c in skill_checks if c.kind == "must_not_contain"
        )
        return judge_winner == "skill" and all_must_not_pass
    raise ValueError(f"unknown expectation: {expectation!r}")


def _load_plugin(plugin: str) -> tuple[Path, list[dict[str, Any]]]:
    plugin_root = EVALS_DIR / plugin
    if not plugin_root.is_dir():
        raise SystemExit(f"unknown plugin: {plugin} (no evals/{plugin}/)")

    plugin_dir_file = plugin_root / "plugin_dir.txt"
    if not plugin_dir_file.exists():
        raise SystemExit(f"missing {plugin_dir_file}")
    plugin_dir = (plugin_root / plugin_dir_file.read_text().strip()).resolve()
    if not plugin_dir.is_dir():
        raise SystemExit(f"plugin_dir resolves to non-existent: {plugin_dir}")

    cases_file = plugin_root / "cases.yaml"
    if not cases_file.exists():
        raise SystemExit(f"missing {cases_file}")
    cases = yaml.safe_load(cases_file.read_text())
    if not isinstance(cases, list) or not cases:
        raise SystemExit(f"{cases_file} must be a non-empty YAML list")

    for c in cases:
        exp = c.setdefault("expectation", "skill_wins")
        if exp not in VALID_EXPECTATIONS:
            raise SystemExit(
                f"case {c.get('id')!r}: bad expectation {exp!r} "
                f"(must be one of {sorted(VALID_EXPECTATIONS)})"
            )

    return plugin_dir, cases


def _filter_cases(
    cases: list[dict[str, Any]], wanted: list[str] | None
) -> list[dict[str, Any]]:
    if not wanted:
        return cases
    by_id = {c["id"]: c for c in cases}
    missing = [w for w in wanted if w not in by_id]
    if missing:
        raise SystemExit(
            f"unknown case ids: {missing} (available: {list(by_id)})"
        )
    return [by_id[w] for w in wanted]


def _run_one(
    case: dict[str, Any],
    plugin_dir: Path,
    rng_seed: int,
) -> dict[str, Any]:
    prompt = case["prompt"]
    rubric_spec = case.get("rubric", [])
    expectation = case["expectation"]
    criterion_names = [c["name"] for c in rubric_spec]

    baseline = cli_runner.run(prompt, plugin_dir=None)
    skill = cli_runner.run(prompt, plugin_dir=str(plugin_dir))

    baseline_checks = rubric.grade(rubric_spec, baseline.text)
    skill_checks = rubric.grade(rubric_spec, skill.text)

    verdict = judge.judge(
        question=prompt,
        baseline_answer=baseline.text,
        skill_answer=skill.text,
        judge_focus=case.get("judge_focus", ""),
        criterion_names=criterion_names,
        rng_seed=rng_seed,
    )

    met = _expectation_met(expectation, verdict.winner, skill_checks)

    return {
        "id": case["id"],
        "prompt": prompt,
        "expectation": expectation,
        "expectation_met": met,
        "baseline": {
            "text": baseline.text,
            "cost_usd": baseline.cost_usd,
            "rubric": [asdict(c) for c in baseline_checks],
            "rubric_pass_rate": rubric.pass_rate(baseline_checks),
        },
        "skill": {
            "text": skill.text,
            "cost_usd": skill.cost_usd,
            "rubric": [asdict(c) for c in skill_checks],
            "rubric_pass_rate": rubric.pass_rate(skill_checks),
        },
        "judge": {
            "winner": verdict.winner,
            "reasoning": verdict.reasoning,
            "per_criterion": [asdict(pc) for pc in verdict.per_criterion],
        },
    }


def run_plugin(
    plugin: str,
    case_ids: list[str] | None,
    workers: int,
    console: Console,
) -> Path:
    plugin_dir, all_cases = _load_plugin(plugin)
    cases = _filter_cases(all_cases, case_ids)

    console.print(
        f"[bold]Running {len(cases)} case(s) for plugin "
        f"[green]{plugin}[/green][/bold]"
    )
    console.print(f"  plugin dir: [dim]{plugin_dir}[/dim]")
    console.print(f"  workers:    [dim]{workers}[/dim]")

    results: list[dict[str, Any] | None] = [None] * len(cases)
    failures: list[tuple[str, Exception]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task("cases", total=len(cases))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_run_one, case, plugin_dir, idx): (idx, case["id"])
                for idx, case in enumerate(cases)
            }
            for fut in as_completed(futures):
                idx, cid = futures[fut]
                try:
                    results[idx] = fut.result()
                    console.print(f"  [green]✓[/green] {cid}")
                except Exception as e:
                    failures.append((cid, e))
                    console.print(f"  [red]✗[/red] {cid}: {e}")
                finally:
                    progress.advance(task_id)

    completed = [r for r in results if r is not None]
    payload = report.serialize_results(plugin, completed)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = RESULTS_DIR / f"{plugin}-{stamp}.json"
    md_path = RESULTS_DIR / f"{plugin}-{stamp}.md"

    report.write_json(json_path, payload)
    report.write_markdown(md_path, payload)

    # Canonical, committed-friendly copy alongside cases.yaml. Overwritten on
    # every full run; reviewers can diff to see how a skill change moved the
    # numbers. The timestamped scratch above is gitignored.
    if not case_ids:
        canonical_md = EVALS_DIR / plugin / "result.md"
        canonical_json = EVALS_DIR / plugin / "result.json"
        report.write_json(canonical_json, payload)
        report.write_markdown(canonical_md, payload)
        console.print(f"  canonical md:   [cyan]{canonical_md}[/cyan]")

    s = payload["summary"]
    console.rule(f"[bold]Results: {plugin}")
    if s:
        met_color = "green" if s["expectations_met"] == s["n_cases"] else "yellow"
        console.print(
            f"Expectations met: "
            f"[{met_color}]{s['expectations_met']}/{s['n_cases']}[/{met_color}]"
        )
        console.print(
            f"Judge: skill [green]{s['judge_wins_for_skill']}[/green] · "
            f"baseline [red]{s['judge_wins_for_baseline']}[/red] · "
            f"ties [yellow]{s['judge_ties']}[/yellow]"
        )
        console.print(
            f"Rubric: baseline {s['baseline_rubric_pass_rate']:.0%} → "
            f"skill {s['skill_rubric_pass_rate']:.0%} "
            f"(Δ {s['rubric_delta']:+.0%})"
        )
        console.print(f"CLI cost: ${s['total_cli_cost_usd']:.2f}")
    if failures:
        console.print(f"[red]{len(failures)} case(s) failed[/red]")
    console.print(f"\n  json: [cyan]{json_path}[/cyan]")
    console.print(f"  md:   [cyan]{md_path}[/cyan]")

    return md_path
