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


# --------------------------- irreversible work via the GitHub MCP server
#
# The Bash screen below catches `gh pr merge` and friends. That screen stopped
# covering the fleet the moment the plugins moved off `gh`: `gh` cannot reach
# the network from a sandboxed session at all (its Go TLS stack needs the macOS
# trust daemon, which the sandbox blocks), so the same operations now arrive as
# mcp__github__* tool calls -- which run in Claude Code's own process, outside
# both the sandbox and the Bash screen.
#
# A permission rule can deny a tool by NAME, and `mcp__github__merge_pull_request`
# is denied that way already. What a permission rule cannot see is an ARGUMENT,
# and that is where the interesting half lives: `push_files` is exactly the tool
# you want an agent using on a feature branch, and exactly the one that must not
# write to `main`. Same tool, opposite verdicts, decided by `branch`.
#
# So this mirrors the reversibility test the ref check below already applies --
# moving a feature branch is the autonomy target; writing straight to the
# default branch and skipping review is not.

MCP_GH_IRREVERSIBLE = {
    "mcp__github__merge_pull_request",
}
# Tools that commit content. Harmless on a topic branch, unreviewable on main.
MCP_GH_CONTENT_WRITE = {
    "mcp__github__push_files",
    "mcp__github__create_or_update_file",
    "mcp__github__delete_file",
}


def check_github_mcp(tool: str, tool_input: object) -> None:
    if tool in MCP_GH_IRREVERSIBLE:
        emit_deny(
            f"{tool} is irreversible and reaches other people -- run it yourself. "
            "This is the MCP spelling of `gh pr merge`, which the Bash screen "
            "already denies."
        )

    if tool not in MCP_GH_CONTENT_WRITE:
        return
    if not isinstance(tool_input, dict):
        return

    branch = tool_input.get("branch")
    # create_or_update_file/delete_file default to the repo's default branch
    # when `branch` is omitted, so absence is the dangerous case, not a pass.
    if branch is None:
        emit_deny(
            f"{tool} without an explicit `branch` commits to the repository's "
            "default branch, skipping review. Name a topic branch."
        )
    if isinstance(branch, str) and GH_DEFAULT_BRANCH.match(branch.strip()):
        emit_deny(
            f"{tool} targeting {branch!r} writes straight to the default branch "
            "and skips review. Push to a topic branch and open a pull request."
        )


# ------------------------------------- branch 1: unsandboxed Bash execution

FORBIDDEN_CMD = re.compile(
    r"""(?:^|[\s;&|(`])(
          sudo|doas|su
        | curl|wget|nc|ncat|telnet|ssh|scp|sftp|rsync
        | kubectl|helm|terraform|aws|az|gcloud
        | launchctl|crontab|systemctl
    )(?:$|[\s;&|)])""",
    re.VERBOSE,
)

# docker is deliberately NOT in the list above: it is the canonical
# excludedCommands case and `docker build` has to keep working, or the entry
# gets deleted. What matters is not the binary but the flags that hand the
# container the host -- a bind mount of /, the docker socket, host namespaces,
# or --privileged. Those are a sandbox escape wearing a container.
DOCKER_ESCAPE = re.compile(
    r"""\bdocker\b[^|;&]*?(?:
          --privileged
        | --(?:net|network|pid|ipc|uts)[=\s]+host
        | (?:-v|--volume)[=\s]+/(?::|\s|$)
        | /var/run/docker\.sock
    )""",
    re.VERBOSE,
)
PUBLISH_CMD = re.compile(
    r"\b(npm|pnpm|yarn|cargo|uv|pip|poetry)\s+publish\b|\bpip\s+upload\b"
)

# ---------------------------- always-on: irreversible work the sandbox permits
#
# Branch 1 only inspects calls carrying `dangerouslyDisableSandbox`. Two kinds
# of command slip past that gate while still doing something unrecoverable:
#
#   1. `sandbox.excludedCommands` entries run with no isolation and set nothing
#      on the tool call, so the flag check never fires. Such a binary is outside
#      the sandbox AND outside this hook -- the worst of both.
#   2. A *sandboxed* command still reaches every host in
#      `sandbox.network.allowedDomains`. The sandbox was never what stopped
#      `gh pr merge`; github.com is on the allowlist by necessity.
#
# So these are screened on every Bash call, sandboxed or not.
#
# gh is the motivating case, and permission rules cannot cover it: a rule
# naming `gh pr merge` is not matched by
#   gh api --method PUT repos/o/r/pulls/1/merge
# which merges the same pull request. `gh api` is the dominant idiom in
# practice, so the subcommand spelling is the *rare* path, not the common one.

GH_IRREVERSIBLE_SUB = re.compile(
    r"""\bgh\s+(?:
          pr\s+merge
        | repo\s+(?:delete|archive|rename)
        | release\s+(?:create|delete)
        | secret\s+set
        | ssh-key\s+add
    )\b""",
    re.VERBOSE,
)
# Stop at a shell separator: the method belongs to *this* gh api call, not to
# some later command in a chain.
GH_API_METHOD = re.compile(r"\bgh\s+api\b[^|;&]*?(?:-X|--method)[=\s]+([A-Za-z]+)")
GH_API_DANGER_PATH = re.compile(
    r"/pulls/\d+/merge|/actions/secrets/|/releases\b"
)
# Ref updates are the Data API's push, so the same reversibility test applies
# rather than a blanket block. Moving a feature branch is how you land work
# when a clone is not available -- undoable, and the autonomy target. Rewriting
# history, or writing straight to the default branch and skipping review, is
# not. `force` here is the API spelling of `git push --force`, which the
# permission rules already deny in its shell form.
GH_API_REF = re.compile(r"/git/refs/heads/(\S+?)(?:['\"]|\s|$)")
GH_API_FORCE = re.compile(r"\bforce\s*[=:]\s*true\b|\"force\"\s*:\s*true")
GH_DEFAULT_BRANCH = re.compile(r"^(?:main|master|trunk|develop)$")

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


def check_always(cmd: str) -> None:
    """Screen every Bash call for outward actions that cannot be undone.

    Runs regardless of `dangerouslyDisableSandbox`, because neither the sandbox
    nor a permissions rule reliably covers these -- see the ALWAYS-ON note.
    Deliberately narrow: it denies operations whose effect is visible to other
    people and not revertible by the agent, and nothing else. Reading, listing,
    checking out and opening a pull request all stay allowed.
    """
    if GH_IRREVERSIBLE_SUB.search(cmd):
        emit_deny(
            f"irreversible outward gh operation: {cmd[:200]!r}. Merging, deleting, "
            "renaming, releasing and writing secrets reach other people and cannot "
            "be undone by the agent -- run it yourself."
        )

    m = GH_API_METHOD.search(cmd)
    if m:
        method = m.group(1).upper()
        if method == "DELETE":
            emit_deny(
                f"gh api DELETE is irreversible by definition: {cmd[:200]!r}. "
                "Run it yourself if it is intended."
            )
        if method in ("PUT", "POST", "PATCH"):
            if GH_API_DANGER_PATH.search(cmd):
                emit_deny(
                    f"gh api {method} against a merge/secret/release endpoint: "
                    f"{cmd[:200]!r}. This is the spelling that routes around a "
                    "permissions rule naming the subcommand."
                )
            ref = GH_API_REF.search(cmd)
            if ref:
                if GH_API_FORCE.search(cmd):
                    emit_deny(
                        f"gh api {method} force-updating a ref rewrites history: "
                        f"{cmd[:200]!r}. This is `git push --force` by another name."
                    )
                if GH_DEFAULT_BRANCH.match(ref.group(1)):
                    emit_deny(
                        f"gh api {method} writing straight to {ref.group(1)!r}: "
                        f"{cmd[:200]!r}. That lands work without review. Move a "
                        "feature branch and open a pull request instead."
                    )


def check_unsandboxed_bash(cmd: str) -> None:
    if FORBIDDEN_CMD.search(cmd):
        emit_deny(
            "command opted out of the sandbox and uses a network/privilege/"
            f"deploy binary: {cmd[:200]!r}. Run it sandboxed, or add it to "
            "sandbox.excludedCommands deliberately."
        )
    if PUBLISH_CMD.search(cmd):
        emit_deny(f"unsandboxed publish command blocked: {cmd[:200]!r}")
    if DOCKER_ESCAPE.search(cmd):
        emit_deny(
            f"unsandboxed docker handing the container the host: {cmd[:200]!r}. "
            "A bind mount of /, the docker socket, a host namespace or "
            "--privileged undoes the isolation the sandbox provides."
        )

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
        cmd = ti.get("command", "")
        if not isinstance(cmd, str):
            emit_deny("Bash tool_input.command was not a string")

        # First, the checks that apply however the command runs. An
        # excludedCommands binary carries no flag, and a sandboxed command can
        # still reach every allowed host, so neither is covered below.
        check_always(cmd)

        # Then the sandbox-escape checks proper: an ordinary sandboxed call is
        # the OS's problem, not ours. Only inspect the ones that opted out.
        if not ti.get("dangerouslyDisableSandbox"):
            sys.exit(0)
        check_unsandboxed_bash(cmd)
    elif tool == "WebFetch" or tool.startswith("mcp__"):
        check_outbound(tool, ti)
        if tool.startswith("mcp__github__"):
            check_github_mcp(tool, ti)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as e:  # noqa: BLE001 -- fail closed on anything
        emit_deny(f"internal error, failing closed: {type(e).__name__}: {e}")
