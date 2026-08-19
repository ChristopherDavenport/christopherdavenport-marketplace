#!/usr/bin/env python3
"""replay.py -- backtest escapes.py against recorded audit data.

The assertion suite in `run.sh` is synthetic: hand-written payloads, in,
exit codes out. It proves the hook still denies what it was written to deny.
What it cannot prove is the number that actually decides whether a guard
survives contact with users -- **the false-positive rate on real traffic** --
because its allow cases were written by whoever wrote the deny rules, and
nobody writes an allow case for the idiom they did not think of.

`audit.sh` has been recording every tool call all along. This replays those
recordings through the current hook and reports what it would decide now.
Two things fall out that the synthetic suite structurally cannot give you:

  1. Denials on commands that really ran, and were fine. Every one is either
     a rule to narrow or an allow case to add to cases.json.
  2. Whether a branch is exercised at all. A guard on rare operations can sit
     at zero real hits for months, which is worth knowing before describing
     it as battle-tested.

This is a *reporting* tool, not a gate: real traffic changes between runs, so
a hard threshold would fail for reasons unrelated to the hook. Use
`--fail-over N` in CI if you want a ceiling anyway.

Usage:
    python3 evals/guardrails/replay.py                 # all recorded days
    python3 evals/guardrails/replay.py --since 2026-01-01
    python3 evals/guardrails/replay.py --reasons 40    # longer histogram
    python3 evals/guardrails/replay.py --fail-over 50  # exit 1 above N denials

Audit location resolves exactly as audit.sh writes it:
    $CLAUDE_GUARDRAILS_AUDIT_DIR, else $CLAUDE_PLUGIN_DATA, else
    ~/.claude/guardrails  -- with /audit/YYYY-MM-DD.jsonl beneath it.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE.parent.parent / "safety" / "guardrails" / "scripts" / "escapes.py"

# The hook's own matcher, from hooks.json. Anything else was never screened.
MATCHED = lambda t: t == "Bash" or t == "WebFetch" or t.startswith("mcp__")


def audit_dir() -> Path:
    base = (
        os.environ.get("CLAUDE_GUARDRAILS_AUDIT_DIR")
        or os.environ.get("CLAUDE_PLUGIN_DATA")
        or os.path.expanduser("~/.claude/guardrails")
    )
    return Path(base) / "audit"


def load(day_from: str | None) -> tuple[dict, int, int]:
    """Return {(tool, input_json, cwd): count}, total matched, total records."""
    d = audit_dir()
    if not d.is_dir():
        sys.exit(f"no audit directory at {d} -- has the audit hook ever run?")

    uniq: dict[tuple[str, str, str], int] = {}
    matched = records = 0
    fallback = os.getcwd()

    for f in sorted(d.glob("*.jsonl")):
        if day_from and f.stem < day_from:
            continue
        for line in f.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            records += 1
            # Skip the hook's own verdict records and audit breadcrumbs: they
            # are outcomes, not attempts, and replaying them is meaningless.
            if r.get("decision") or r.get("audit_error"):
                continue
            tool = r.get("tool") or ""
            if not MATCHED(tool):
                continue
            matched += 1
            cwd = r.get("cwd") or fallback
            if not os.path.isdir(cwd):
                # Recorded projects get deleted, moved, or were worktrees. The
                # path only affects the project-root checks, so substituting a
                # real directory keeps the run going; note it in the output.
                cwd = fallback
            key = (tool, json.dumps(r.get("input") or {}, sort_keys=True), cwd)
            uniq[key] = uniq.get(key, 0) + 1
    return uniq, matched, records


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", metavar="YYYY-MM-DD", help="skip earlier days")
    ap.add_argument("--reasons", type=int, default=25, help="histogram length")
    ap.add_argument("--fail-over", type=int, metavar="N",
                    help="exit 1 if more than N calls are denied")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args()

    if not HOOK.is_file():
        sys.exit(f"hook not found at {HOOK}")

    uniq, matched, records = load(args.since)
    if not matched:
        sys.exit("no hook-matching calls in the audit log for that range")

    if not args.json:
        print(f"{records} audit records -> {matched} hook-matching calls "
              f"-> {len(uniq)} unique (tool, input, cwd)", flush=True)

    denied = collections.Counter()
    reasons = collections.Counter()
    errors = 0
    total_denied = 0

    for i, ((tool, inp, cwd), weight) in enumerate(uniq.items(), 1):
        if not args.json and i % 2000 == 0:
            print(f"  ...{i}/{len(uniq)}", flush=True)
        payload = json.dumps(
            {"tool_name": tool, "tool_input": json.loads(inp), "cwd": cwd}
        )
        try:
            p = subprocess.run(
                [sys.executable, str(HOOK)], input=payload,
                capture_output=True, text=True, cwd=cwd, timeout=20,
                # Never let the caller's audit config make the replay write
                # verdict records into the real log -- this is a dry run.
                env={**os.environ, "CLAUDE_GUARDRAILS_AUDIT_OFF": "1"},
            )
        except Exception as e:
            errors += weight
            reasons[f"REPLAY ERROR: {type(e).__name__}"] += weight
            continue
        # Only exit 2 is a block. Per the hooks contract any other non-zero is
        # a "non-blocking error" and the call proceeds -- so it is not a deny.
        if p.returncode == 2:
            denied[tool] += weight
            total_denied += weight
            reasons[(p.stderr or "").strip().replace("guardrails: ", "")[:160]] += weight
        elif p.returncode != 0:
            errors += weight
            reasons[f"NON-BLOCKING ERROR exit={p.returncode}"] += weight

    rate = 100 * total_denied / matched

    if args.json:
        print(json.dumps({
            "records": records, "matched": matched, "unique": len(uniq),
            "denied": total_denied, "deny_rate_pct": round(rate, 3),
            "errors": errors, "by_tool": dict(denied),
        }, indent=2))
    else:
        print(f"\n=== DENIED {total_denied} of {matched} ({rate:.2f}%) ===")
        for k, v in denied.most_common():
            print(f"   {k:45s} {v}")
        if not denied:
            print("   (nothing -- every recorded call would be allowed)")
        if errors:
            print(f"\n!! {errors} calls errored during replay (see below)")
        print(f"\nreasons, weighted by occurrences (top {args.reasons}):")
        for k, v in reasons.most_common(args.reasons):
            print(f"   [{v:5d}] {k}")
        print("\nEach denial on a command that really ran is either a rule to "
              "narrow or an\nallow case to add to cases.json. A branch with "
              "zero hits is untested by\nthis run, whatever the synthetic "
              "suite says about it.")

    if args.fail_over is not None and total_denied > args.fail_over:
        print(f"\nFAIL: {total_denied} denials exceeds --fail-over {args.fail_over}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
