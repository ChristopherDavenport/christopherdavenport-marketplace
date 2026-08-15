#!/usr/bin/env python3
"""escapes.py -- guard the two paths that leave the OS sandbox.

A PreToolUse hook on `Bash | WebFetch | mcp__.*`.

This is deliberately NOT a general containment fence. Claude Code's built-in
Bash sandbox (Seatbelt on macOS, bubblewrap + seccomp on Linux/WSL2) already
does containment properly: kernel-enforced, transitive over child processes,
with a network egress allowlist and credential blocking. Reimplementing that
as regexes over a shell string is strictly worse -- `env curl`, `python3 -c`,
`xargs`, or a script written on one call and executed on the next all defeat
it, and every regex you add to chase those buys a false positive that pushes
someone to switch the whole thing off.

So this hook covers only what the sandbox does not:

  1. Bash calls carrying `dangerouslyDisableSandbox: true` -- the documented
     escape hatch, where the command runs on the host with no isolation.
     Rare, explicitly marked, and therefore worth a conservative check that
     would be intolerable on every call.

  2. MCP and WebFetch tool calls -- entirely outside the sandbox, which is
     Bash-only. These are the tools that publish: Slack, Jira, GitHub, an
     arbitrary URL. The risk here is not writing to the wrong path, it is
     sending a credential off the machine. So the check is credential shapes
     in the outbound payload, not paths.

If you set `"allowUnsandboxedCommands": false` in sandbox settings, branch 1
can never fire, which is the correct end state -- it is a backstop for
sessions that have not locked that down yet.

FAIL CLOSED. Per the hooks contract, a hook that exits 1 or times out is a
"non-blocking error" and *the tool call proceeds*. A hook guarding the escape
hatch with that behaviour is worthless, since any crash becomes an escape.
Every unexpected exception routes to deny().

Configuration (environment):
  CLAUDE_GUARDRAILS_ALLOW  colon-separated extra writable roots for the
                           unsandboxed-Bash branch, e.g. "/tmp:/var/folders".
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


# ---------------------------------------------------------------- deny/emit

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


# ------------------------------------------------- branch 2: outbound leaks

# High-specificity only. A generic "long random string" rule would fire on
# git SHAs, lockfile hashes, and base64 test fixtures -- and a leak detector
# that cries wolf on `pnpm-lock.yaml` gets disabled within a day.
CREDENTIAL_SHAPES: list[tuple[str, re.Pattern[str]]] = [
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("AWS secret access key",
     re.compile(r"AWS_SECRET_ACCESS_KEY\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("Slack token", re.compile(r"\bxox[abopsr]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI-style API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b")),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[A-Za-z0-9]{20,}\b")),
    ("JSON web token",
     re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
]


def check_outbound(tool: str, tool_input: object) -> None:
    """Deny a payload leaving the machine with a credential in it.

    The reason names the shape and the tool, never the matched text: a deny
    message is written into the transcript, so echoing the secret back would
    copy it somewhere new to apologise for finding it.
    """
    try:
        blob = json.dumps(tool_input, ensure_ascii=False)
    except Exception:
        blob = str(tool_input)

    for label, pattern in CREDENTIAL_SHAPES:
        if pattern.search(blob):
            emit_deny(
                f"{tool} payload contains what looks like a {label}. "
                "This tool sends data off the machine and is not covered by "
                "the Bash sandbox. Remove the credential, or reference it by "
                "name instead of value."
            )


# ------------------------------------- branch 1: unsandboxed Bash execution

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

    Deliberately generous: relative traversal (`../../x`) was a real miss,
    caught only by the test suite, so matching absolute paths alone is not
    enough. Generosity is safe because check_target() denies only when a
    token resolves OUTSIDE the project -- a false positive on, say, a sed
    script resolves to a nonexistent path inside the project and is allowed.
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
            f"{what} {p} is outside the project ({ROOT}), in a command that "
            "opted out of the sandbox. Drop dangerouslyDisableSandbox, or add "
            "the path to sandbox.filesystem.allowWrite so the OS enforces it."
        )


def check_git_push(tokens: list[str]) -> None:
    try:
        i = tokens.index("push")
    except ValueError:
        return
    rest = [t for t in tokens[i + 1:] if not t.startswith("-")]
    remote = rest[0] if rest else "origin"

    if "://" in remote or re.match(r"^[\w.+-]+@[\w.-]+:", remote):
        emit_deny(f"unsandboxed git push to remote URL {remote!r} leaves this machine")

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
        emit_deny(f"unsandboxed git push: remote {remote!r} -> {url!r} is a network remote")

    p = resolve(url)
    if p is None or not inside(p):
        emit_deny(f"git remote {remote!r} -> {url!r} resolves outside the project")


def check_unsandboxed_bash(cmd: str) -> None:
    if FORBIDDEN_CMD.search(cmd):
        emit_deny(
            "command opted out of the sandbox and uses a network/privilege/"
            f"deploy binary: {cmd[:200]!r}. Run it sandboxed, or add it to "
            "sandbox.excludedCommands deliberately."
        )
    if PUBLISH_CMD.search(cmd):
        emit_deny(f"unsandboxed publish command blocked: {cmd[:200]!r}")

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


# ------------------------------------------------------------------- driver

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
        # The whole point: a sandboxed Bash call is the OS's problem, not
        # ours. Only inspect the ones that opted out.
        if not ti.get("dangerouslyDisableSandbox"):
            sys.exit(0)
        cmd = ti.get("command", "")
        if not isinstance(cmd, str):
            emit_deny("Bash tool_input.command was not a string")
        check_unsandboxed_bash(cmd)
    elif tool == "WebFetch" or tool.startswith("mcp__"):
        check_outbound(tool, ti)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 -- fail closed on anything
        emit_deny(f"internal error, failing closed: {type(e).__name__}: {e}")
