#!/usr/bin/env python3
"""contain.sh -- keep writes inside the project you are working in.

A PreToolUse hook on Bash | Write | Edit.*. Denies any write whose target
resolves outside ${CLAUDE_PROJECT_DIR}, plus network/privilege/deploy
binaries and pushes to remotes that leave the machine.

Why Python rather than bash: this does path resolution (symlink escapes,
non-existent targets, `..` traversal) and shell-command parsing. Getting
that wrong in bash is how fences develop holes -- the relative-traversal
case was a real miss, caught only by the test suite.

FAIL CLOSED. Per the hooks contract, a hook that exits 1 or times out is a
"non-blocking error" and *the tool call proceeds*. A containment hook with
that behaviour is worthless: any crash becomes an escape. So every
unexpected exception routes to deny().

Two blocking mechanisms together: hookSpecificOutput carries a readable
reason, and exit 2 blocks unconditionally even if that JSON is malformed.

Configuration (environment):
  CLAUDE_GUARDRAILS_ALLOW  colon-separated extra writable roots, e.g.
                           "/tmp:/var/folders". Empty by default -- the
                           project is the only writable root.
  CLAUDE_GUARDRAILS_OFF    "1" disables enforcement. Auditing is a separate
                           hook and keeps running.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CWD = os.getcwd()


def _project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env).resolve() if env else Path(CWD).resolve()


ROOT = _project_root()

# Extra writable roots are opt-in. Some workflows genuinely need a scratch
# directory; making that explicit beats a blanket /tmp exception nobody sees.
EXTRA: list[Path] = []


def _load_extra() -> list[Path]:
    out = []
    for p in os.environ.get("CLAUDE_GUARDRAILS_ALLOW", "").split(":"):
        if p.strip():
            try:
                out.append(Path(os.path.expanduser(p.strip())).resolve())
            except Exception:
                pass
    return out


FORBIDDEN_CMD = re.compile(
    r"""(?:^|[\s;&|(`])(
          sudo|doas|su
        | curl|wget|nc|ncat|telnet|ssh|scp|sftp|rsync
        | kubectl|helm|terraform|aws|az
        | launchctl|crontab|systemctl
    )(?:$|[\s;&|)])""",
    re.VERBOSE,
)
PUBLISH_CMD = re.compile(
    r"\b(npm|pnpm|yarn|cargo|uv|pip|poetry)\s+publish\b|\bpip\s+upload\b"
)
WRITE_VERB = re.compile(
    r"(?:^|[\s;&|(`])(rm|mv|cp|mkdir|rmdir|touch|ln|install|truncate|dd|chmod|chown|tee|sed)\b"
)
REDIRECT = re.compile(r"(?:^|[^0-9>])>{1,2}\s*([^\s;&|]+)")


def emit_deny(reason: str) -> None:
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"guardrails: {reason}",
        }
    }
    try:
        sys.stdout.write(json.dumps(payload))
        sys.stdout.flush()
    except Exception:
        pass
    print(f"guardrails: {reason}", file=sys.stderr)
    sys.exit(2)


def resolve(p: str) -> Path | None:
    try:
        expanded = os.path.expanduser(os.path.expandvars(p.strip().strip("'\"")))
        if not expanded:
            return None
        base = Path(expanded)
        if not base.is_absolute():
            base = Path(CWD) / base
        return Path(os.path.realpath(base))
    except Exception:
        return None


def looks_like_path(tok: str) -> bool:
    """Any token that could name a filesystem location.

    Deliberately generous: relative traversal (`../../x`) was the hole the
    test suite caught, so matching only absolute paths is insufficient.
    Generosity is safe because check_target() denies only when a token
    resolves OUTSIDE the project -- a false positive on, say, a sed script
    resolves to a nonexistent path inside the project and is allowed.
    """
    if not tok or tok.startswith("-"):
        return False
    return tok.startswith(("/", "~", "./", "../")) or "/" in tok or tok in (".", "..")


def inside(path: Path) -> bool:
    for root in [ROOT, *EXTRA]:
        if path == root or root in path.parents:
            return True
    return False


def check_target(raw: str, what: str) -> None:
    p = resolve(raw)
    if p is None:
        emit_deny(f"could not resolve {what} {raw!r}; refusing to guess")
    if not inside(p):
        emit_deny(
            f"{what} {p} is outside the project ({ROOT}). "
            "Set CLAUDE_GUARDRAILS_ALLOW to permit additional roots."
        )


def check_git_push(tokens: list[str]) -> None:
    try:
        i = tokens.index("push")
    except ValueError:
        return
    rest = [t for t in tokens[i + 1:] if not t.startswith("-")]
    remote = rest[0] if rest else "origin"

    if "://" in remote or re.match(r"^[\w.+-]+@[\w.-]+:", remote):
        emit_deny(f"git push to remote URL {remote!r} leaves this machine")

    url = remote
    if not ("/" in remote or remote.startswith(".")):
        try:
            url = subprocess.run(
                ["git", "remote", "get-url", remote],
                capture_output=True, text=True, timeout=5, cwd=CWD,
            ).stdout.strip()
        except Exception as e:
            emit_deny(f"could not resolve git remote {remote!r} ({e}); refusing to guess")
        if not url:
            emit_deny(f"git remote {remote!r} has no URL; refusing to guess")

    if "://" in url or re.match(r"^[\w.+-]+@[\w.-]+:", url):
        emit_deny(f"git remote {remote!r} -> {url!r} is a network remote")

    p = resolve(url)
    if p is None or not inside(p):
        emit_deny(f"git remote {remote!r} -> {url!r} resolves outside the project")


def check_bash(cmd: str) -> None:
    if FORBIDDEN_CMD.search(cmd):
        emit_deny(f"command uses a network/privilege/deploy binary: {cmd[:200]!r}")
    if PUBLISH_CMD.search(cmd):
        emit_deny(f"publish command blocked: {cmd[:200]!r}")

    try:
        tokens = shlex.split(cmd, comments=False)
    except ValueError:
        tokens = cmd.split()

    if tokens and tokens[0] == "git" and "push" in tokens:
        check_git_push(tokens)

    if re.search(r"\brm\b.*-[a-zA-Z]*[rf]", cmd):
        for t in tokens:
            if t.startswith("-"):
                continue
            p = resolve(t)
            if p and (p == ROOT or p in ROOT.parents or p == Path("/")):
                emit_deny(f"rm -rf targeting {p} would destroy the project or its parents")

    for m in REDIRECT.finditer(cmd):
        target = m.group(1)
        if target.startswith("&") or target in ("/dev/null", "/dev/stderr", "/dev/stdout"):
            continue
        check_target(target, "redirect target")

    if WRITE_VERB.search(cmd):
        for t in tokens:
            if looks_like_path(t):
                check_target(t, "write-command path")


def main() -> None:
    if os.environ.get("CLAUDE_GUARDRAILS_OFF") == "1":
        sys.exit(0)

    raw = sys.stdin.read()
    if not raw.strip():
        emit_deny("empty hook payload; refusing to guess intent")

    data = json.loads(raw)

    global CWD, ROOT, EXTRA
    payload_cwd = data.get("cwd")
    if isinstance(payload_cwd, str) and payload_cwd:
        CWD = payload_cwd
    ROOT = _project_root()
    EXTRA = _load_extra()

    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}

    if tool == "Bash":
        cmd = ti.get("command", "")
        if not isinstance(cmd, str):
            emit_deny("Bash tool_input.command was not a string")
        check_bash(cmd)
    else:
        for key in ("file_path", "notebook_path", "path"):
            val = ti.get(key)
            if isinstance(val, str) and val:
                check_target(val, f"{tool} {key}")

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 -- fail closed on anything
        emit_deny(f"internal error, failing closed: {type(e).__name__}: {e}")
