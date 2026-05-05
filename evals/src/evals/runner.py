"""Orchestrator: load a plugin's cases, run baseline + skill across N models, score, report."""

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

from . import inference, judge, report, rubric

EVALS_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = EVALS_DIR / "results"

VALID_EXPECTATIONS = {"skill_wins", "tie", "skill_wins_strict"}

# Up to 3 models per case; bound the inner pool to that.
_MAX_MODEL_WORKERS = 3


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


def _run_one_model(
    case: dict[str, Any],
    plugin_dir: Path,
    rng_seed: int,
    via_cli: bool,
    model_alias: str,
) -> dict[str, Any]:
    """Run baseline + skill + judge for ONE (case, model) pair."""
    prompt = case["prompt"]
    rubric_spec = case.get("rubric", [])
    expectation = case["expectation"]
    criterion_names = [c["name"] for c in rubric_spec]

    if via_cli:
        baseline = inference.cli_run(prompt, plugin_dir=None, model_alias=model_alias)
        skill = inference.cli_run(prompt, plugin_dir=plugin_dir, model_alias=model_alias)
    else:
        baseline = inference.sdk_run(prompt, plugin_dir=None, model_alias=model_alias)
        skill = inference.sdk_run(prompt, plugin_dir=plugin_dir, model_alias=model_alias)

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


def _run_one_case(
    case: dict[str, Any],
    plugin_dir: Path,
    case_idx: int,
    via_cli: bool,
    models: list[str],
) -> dict[str, Any]:
    """Run all models for one case. Models run in parallel under SDK; serial under CLI."""
    per_model: dict[str, dict[str, Any]] = {}

    # CLI subprocess concurrency would crush the local `claude` invocation —
    # serialize models within a case for CLI; parallelize for SDK.
    inner_workers = 1 if via_cli else min(_MAX_MODEL_WORKERS, len(models))

    if inner_workers == 1:
        for m_idx, alias in enumerate(models):
            seed = case_idx * 100 + m_idx
            per_model[alias] = _run_one_model(case, plugin_dir, seed, via_cli, alias)
    else:
        with ThreadPoolExecutor(max_workers=inner_workers) as pool:
            futs = {
                pool.submit(
                    _run_one_model, case, plugin_dir, case_idx * 100 + m_idx, via_cli, alias
                ): alias
                for m_idx, alias in enumerate(models)
            }
            for f in as_completed(futs):
                alias = futs[f]
                per_model[alias] = f.result()

    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "expectation": case["expectation"],
        "judge_focus": case.get("judge_focus", ""),
        "models": per_model,
    }


def run_plugin(
    plugin: str,
    case_ids: list[str] | None,
    workers: int,
    console: Console,
    *,
    models: list[str],
    via_cli: bool = False,
) -> Path:
    plugin_dir, all_cases = _load_plugin(plugin)
    cases = _filter_cases(all_cases, case_ids)

    backend_label = "CLI subprocess" if via_cli else "SDK direct"
    console.print(
        f"[bold]Running {len(cases)} case(s) × {len(models)} model(s) for plugin "
        f"[green]{plugin}[/green][/bold]"
    )
    console.print(f"  plugin dir: [dim]{plugin_dir}[/dim]")
    console.print(f"  backend:    [dim]{backend_label}[/dim]")
    console.print(f"  models:     [dim]{', '.join(models)}[/dim]")
    console.print(f"  workers:    [dim]{workers} cases × "
                  f"{1 if via_cli else min(_MAX_MODEL_WORKERS, len(models))} models[/dim]")

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
                pool.submit(_run_one_case, case, plugin_dir, idx, via_cli, models): (idx, case["id"])
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
    payload = report.serialize_results(plugin, completed, models)
    payload["backend"] = "cli" if via_cli else "sdk"
    payload["models"] = models

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = RESULTS_DIR / f"{plugin}-{stamp}.json"
    md_path = RESULTS_DIR / f"{plugin}-{stamp}.md"

    report.write_json(json_path, payload)
    report.write_markdown(md_path, payload)

    # Canonical copy alongside cases.yaml. Overwritten on every full SDK run so
    # reviewers can diff to see how a skill change moved the numbers. CLI runs
    # go only to the gitignored scratch dir so the canonical stays a consistent
    # comparison surface across plugins.
    if not case_ids and not via_cli:
        canonical_md = EVALS_DIR / plugin / "result.md"
        canonical_json = EVALS_DIR / plugin / "result.json"
        report.write_json(canonical_json, payload)
        report.write_markdown(canonical_md, payload)
        console.print(f"  canonical md:   [cyan]{canonical_md}[/cyan]")

    s = payload["summary"]
    console.rule(f"[bold]Results: {plugin}")
    if s:
        for alias in models:
            ms = s["per_model"][alias]
            met_color = "green" if ms["expectations_met"] == ms["n_cases"] else "yellow"
            console.print(
                f"[bold]{alias:6s}[/bold]  "
                f"expectations [{met_color}]{ms['expectations_met']}/{ms['n_cases']}[/{met_color}]  "
                f"judge skill [green]{ms['judge_wins_for_skill']}[/green]/"
                f"baseline [red]{ms['judge_wins_for_baseline']}[/red]/"
                f"ties [yellow]{ms['judge_ties']}[/yellow]  "
                f"rubric Δ {ms['rubric_delta']:+.0%}"
            )
        console.print(f"\nTotal cost: ${s['total_cost_usd']:.2f}")
    if failures:
        console.print(f"[red]{len(failures)} case(s) failed[/red]")
    console.print(f"\n  json: [cyan]{json_path}[/cyan]")
    console.print(f"  md:   [cyan]{md_path}[/cyan]")

    return md_path
