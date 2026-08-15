#!/usr/bin/env python3
"""Assert every hook this plugin registers can actually be executed.

The gap this closes
-------------------
`audit.sh` and `verify-gate.sh` shipped with mode 100644. The harness runs a
`type: command` hook by executing the file, so both failed with "permission
denied" on every single tool call. Per the hooks contract a non-zero exit that
is not `2` is a *non-blocking error*: the tool call proceeds. So the audit log
was never written and the Stop gate never ran, silently, and the session looked
completely normal.

Nothing caught it. `claude plugin validate --strict` does not check mode bits.
The 40 hook cases invoke `escapes.py` through `python3 "$HOOK"`, which does not
need the executable bit and therefore passes against a file the harness cannot
run. `audit.sh` and `verify-gate.sh` had no cases at all -- listed under "Not
covered" in the eval report, where the gap was visible and still hid a total
failure of two of the three hooks.

Found by telemetry, not by tests: `hook_execution_complete` reported
`num_non_blocking_error: 1` on both PreToolUse and Stop.

What it checks, for every command in hooks/hooks.json
-----------------------------------------------------
1. the file exists at the path the manifest names
2. it is executable by the current user
3. git has it recorded as mode 100755 -- the mode bit is what propagates to a
   clone or a plugin install, so a locally-chmod'd file that is 100644 in the
   tree is still broken for everyone else
4. running it *directly*, the way the harness does, does not fail to exec
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "safety" / "guardrails"
HOOKS_JSON = PLUGIN / "hooks" / "hooks.json"

# A PreToolUse payload benign enough that every hook should allow it. Exit 2
# would mean "blocked", which for this input would itself be a failure.
PAYLOAD = json.dumps({
    "tool_name": "Bash",
    "tool_input": {"command": "echo hello"},
    "cwd": "/tmp",
    "hook_event_name": "PreToolUse",
})


def hook_commands() -> list[str]:
    data = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
    out = []
    for entries in data.get("hooks", {}).values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command")
                if cmd:
                    out.append(cmd)
    return out


def git_mode(path: Path) -> str | None:
    rel = path.relative_to(ROOT)
    res = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-s", str(rel)],
                         capture_output=True, text=True)
    m = re.match(r"^(\d{6})", res.stdout.strip())
    return m.group(1) if m else None


def main() -> int:
    if not HOOKS_JSON.exists():
        print("  FATAL: no hooks/hooks.json", file=sys.stderr)
        return 70

    commands = hook_commands()
    if not commands:
        print("  FATAL: hooks.json registers no commands", file=sys.stderr)
        return 70

    failures = []
    for cmd in commands:
        path = Path(cmd.replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN)))
        name = path.name
        problems = []

        if not path.exists():
            problems.append("missing")
        else:
            if not os.access(path, os.X_OK):
                problems.append("not executable (chmod +x)")
            mode = git_mode(path)
            if mode and mode != "100755":
                problems.append(f"git mode {mode}, expected 100755 — "
                                "a local chmod does not travel to a clone")
            if not problems:
                # Exec it the way the harness does: directly, not via an
                # interpreter. An interpreter would mask exactly this bug.
                try:
                    env = {**os.environ, "CLAUDE_PROJECT_DIR": "/tmp",
                           "CLAUDE_PLUGIN_ROOT": str(PLUGIN)}
                    res = subprocess.run([str(path)], input=PAYLOAD, capture_output=True,
                                         text=True, timeout=30, env=env)
                    # 0 = allow, 2 = block. Anything else is a non-blocking
                    # error, which means the guard silently did not apply.
                    if res.returncode not in (0, 2):
                        problems.append(
                            f"exit {res.returncode} — a non-blocking error, so the "
                            f"tool call proceeds unguarded: "
                            f"{(res.stderr or '').strip()[:80]}")
                except PermissionError:
                    problems.append("PermissionError on exec")
                except OSError as exc:
                    problems.append(f"failed to exec: {exc}")
                except subprocess.TimeoutExpired:
                    problems.append("timed out")

        if problems:
            failures.append((name, problems))
            print(f"  \033[31mFAIL\033[0m  {name:<22}{'; '.join(problems)}")
        else:
            print(f"  \033[32mPASS\033[0m  {name:<22}executable, git 100755, execs clean")

    print()
    if failures:
        print(f"  hooks: {len(commands) - len(failures)}/{len(commands)} runnable")
        return 1
    print(f"  hooks: {len(commands)}/{len(commands)} runnable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
