#!/usr/bin/env python3
"""Trigger evals — does a skill actually load when it should?

The judge-based harness in `evals/src/evals/` injects SKILL.md straight into
the system prompt, so the model never *chooses* the skill. That measures prose
quality and is blind to selection: a skill whose description talks it out of
firing scores perfectly and never runs in production.

This suite closes that gap. It scaffolds a realistic project, loads the
*competing* sibling plugins together, sends a prompt in the overlap zone, and
asserts on which skills the model actually invoked via the Skill tool.

Two arms, so a description change is measurable rather than asserted:

    source  the working tree — what you just edited
    cache   ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/, the
            installed copy, which still holds the previous release's text

Skill selection is stochastic, so each arm runs N times and the result is a
fire rate, not a boolean. Treat a single run as a smoke test.

    uv run python evals/triggering/run.py                    # source, n=3
    uv run python evals/triggering/run.py --arm both -n 3    # A/B
    uv run python evals/triggering/run.py --case lit-*       # filter

Costs real tokens: roughly $0.30 per run, so ~$1 per case per arm at n=3.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
MARKETPLACE = HERE.parent.parent
MARKETPLACE_NAME = "christopherdavenport"
CACHE_ROOT = Path.home() / ".claude" / "plugins" / "cache" / MARKETPLACE_NAME

# Do NOT add `--bare` here. It forces a minimal allowlist (Bash, Edit, Read)
# with **no Skill tool** and ignores `--tools`, so skills can never be invoked
# under it whatever a description says — every case then reports a clean,
# confident zero that means nothing. The `assert_skill_tool` guard below exists
# because this suite was first written with `--bare` and produced exactly that.
#
# Losing `--bare` costs hermeticity: hooks and user settings apply. MCP servers
# are dropped via --strict-mcp-config (they otherwise add ~180 tools and a lot
# of selection noise); the scaffold runs in a fresh temp dir so no CLAUDE.md is
# discovered.
TOOLS = "Bash,Edit,Read,Write,Glob,Grep,Skill"

# The competitive field is deliberately the *full* enabled plugin set, not just
# the plugins a case names: suppression is an inter-skill effect, and the
# production failure this suite exists to catch happened with everything
# enabled. (`--settings '{"enabledPlugins":{}}'` does not narrow it — `--bare`
# sets `--settings` itself and wins.) The case's own `--plugin-dir` entries
# shadow their installed copies, which is what makes the two arms differ.


@dataclass
class RunResult:
    offered: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    invoked: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    turns: int = 0
    error: str | None = None


def resolve_plugin_dir(rel: str, arm: str) -> Path:
    """Map a marketplace-relative plugin path to the dir for this arm."""
    src = MARKETPLACE / rel
    if arm == "source":
        return src
    name = src.name
    versions = sorted(p for p in (CACHE_ROOT / name).glob("*") if p.is_dir())
    if not versions:
        raise FileNotFoundError(
            f"no installed copy of {name!r} under {CACHE_ROOT} — "
            f"the 'cache' arm needs the plugin installed"
        )
    return versions[-1]


def build_workdir(scaffold: str, tmp: Path) -> Path:
    work = tmp / "work"
    if scaffold and scaffold != "none":
        shutil.copytree(HERE / "scaffolds" / scaffold, work)
    else:
        work.mkdir()
    return work


def parse_stream(stdout: str) -> RunResult:
    res = RunResult()
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = rec.get("type")
        if kind == "system" and "skills" in rec:
            res.offered = rec["skills"]
            res.tools = rec.get("tools", [])
        elif kind == "assistant":
            for block in rec.get("message", {}).get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    skill = block.get("input", {}).get("skill")
                    if skill:
                        res.invoked.append(skill)
        elif kind == "result":
            res.cost_usd = rec.get("total_cost_usd") or 0.0
            res.turns = rec.get("num_turns") or 0
    return res


def run_once(case: dict, arm: str, model: str | None) -> RunResult:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        work = build_workdir(case.get("scaffold", "none"), tmp)
        cmd = [
            "claude", "--print",
            "--output-format", "stream-json", "--verbose",
            "--strict-mcp-config",
            "--tools", TOOLS,
        ]
        if model:
            cmd += ["--model", model]
        for rel in case["plugins"]:
            cmd += ["--plugin-dir", str(resolve_plugin_dir(rel, arm))]
        # The prompt goes on stdin, not argv: `--tools` is variadic, so a
        # trailing positional prompt gets swallowed into the tool list whenever
        # nothing separates them (e.g. a case with no `plugins`).

        try:
            proc = subprocess.run(
                cmd, cwd=work, capture_output=True, text=True,
                input=case["prompt"], timeout=900, check=False,
            )
        except subprocess.TimeoutExpired:
            return RunResult(error="timeout after 900s")

    res = parse_stream(proc.stdout)
    if proc.returncode != 0 and not res.invoked and not res.offered:
        res.error = (proc.stderr or proc.stdout or "")[-400:].strip() or "non-zero exit"
    elif res.tools and "Skill" not in res.tools:
        # Harness fault, not a case failure — without the Skill tool the model
        # physically cannot invoke a skill, and every case would report a
        # confident, meaningless zero.
        res.error = f"Skill tool not exposed (tools={res.tools}) — check --tools"
    return res


def score(case: dict, res: RunResult) -> tuple[bool, list[str], list[str]]:
    """Return (passed, missing, unexpected)."""
    expect = set(case.get("expect", []))
    permitted = set(case.get("permitted", []))
    invoked = set(res.invoked)
    missing = sorted(expect - invoked)
    unexpected = sorted(invoked - expect - permitted)
    return (not missing), missing, unexpected


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--arm", choices=["source", "cache", "both"], default="source")
    ap.add_argument("-n", "--runs", type=int, default=3)
    ap.add_argument("--case", default="*", help="glob over case ids")
    ap.add_argument("--model", default=None)
    ap.add_argument("--json", dest="json_out", default=None)
    args = ap.parse_args()

    cases = [
        c for c in yaml.safe_load((HERE / "cases.yaml").read_text())
        if fnmatch.fnmatch(c["id"], args.case)
    ]
    if not cases:
        print(f"no cases match {args.case!r}", file=sys.stderr)
        return 2

    arms = ["cache", "source"] if args.arm == "both" else [args.arm]
    report: list[dict] = []
    total_cost = 0.0
    any_fail = False

    for case in cases:
        print(f"\n\033[1m{case['id']}\033[0m")
        print(f"  expect: {', '.join(case.get('expect', [])) or '(none)'}")
        for arm in arms:
            fired = 0
            details: list[dict] = []
            for i in range(args.runs):
                try:
                    res = run_once(case, arm, args.model)
                except FileNotFoundError as e:
                    print(f"  {arm:6s} skipped — {e}")
                    break
                total_cost += res.cost_usd
                if res.error:
                    print(f"  {arm:6s} run {i + 1}: \033[31merror\033[0m {res.error}")
                    details.append({"run": i + 1, "error": res.error})
                    continue
                ok, missing, unexpected = score(case, res)
                fired += ok
                mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
                extra = f" missing={missing}" if missing else ""
                extra += f" also={unexpected}" if unexpected else ""
                print(
                    f"  {arm:6s} run {i + 1}: {mark} "
                    f"invoked={res.invoked or '[]'}{extra} "
                    f"(${res.cost_usd:.3f}, {res.turns} turns, "
                    f"{len(res.offered)} skills offered)"
                )
                details.append({
                    "run": i + 1, "passed": ok, "invoked": res.invoked,
                    "missing": missing, "unexpected": unexpected,
                    "cost_usd": res.cost_usd, "offered_count": len(res.offered),
                })
            else:
                rate = fired / args.runs
                colour = "\033[32m" if rate == 1 else ("\033[33m" if rate else "\033[31m")
                print(f"  {arm:6s} \033[1mfire rate {colour}{fired}/{args.runs}\033[0m")
                if arm == "source" and rate < 1:
                    any_fail = True
                report.append({
                    "case": case["id"], "arm": arm,
                    "fired": fired, "runs": args.runs, "details": details,
                })

    print(f"\ntotal cost ${total_cost:.2f}")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2))
        print(f"wrote {args.json_out}")
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
