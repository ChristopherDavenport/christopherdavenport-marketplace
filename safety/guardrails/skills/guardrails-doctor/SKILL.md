---
name: guardrails-doctor
description: Check what protection is actually in effect in this session, rather than what the settings files claim. Verifies the sandbox is enabled and enforcing, that guardrails hooks are firing, that credential and permission rules cover the tools they need to, and reports the gaps. Use when the user asks whether guardrails are working, whether the sandbox is on, why a hook did not fire, or wants an audit of current protection.
---

# /guardrails-doctor

An unloaded control looks exactly like a permissive one. Nothing errors,
nothing warns, and the session behaves normally right up until it matters.
This skill closes that gap by checking effect, not configuration.

Report findings as a table with a verdict per layer. Be blunt about what is
**not** protected — a report that only lists green checks is the same failure
mode as a fence that isn't wired up.

## 1. Is the sandbox on and enforcing?

Ask the user to run `/sandbox` and paste the **Config** tab. You cannot
determine this from settings files alone — the resolved config accounts for
scope precedence, managed overrides, and keys silently ignored from the wrong
scope.

Check for, and report each:

- **Enabled at all.** If not, everything below is moot; that's the headline.
- **`failIfUnavailable`.** If unset and a dependency is missing, Claude Code
  warned once at startup and is running **unsandboxed** right now. On Linux
  and WSL2, confirm the dependencies exist:
  ```sh
  command -v bwrap || echo "MISSING: bubblewrap -- sandbox cannot start"
  command -v socat || echo "MISSING: socat -- network proxy unavailable"
  ```
  On macOS, Seatbelt is built in and there is nothing to install. On native
  Windows the sandbox does not run at all.
- **`allowUnsandboxedCommands`.** If not `false`, the model can retry any
  failed command outside the sandbox with `dangerouslyDisableSandbox`.
- **`excludedCommands`.** Each entry runs with no isolation. List them; a
  long list means the sandbox covers less than it appears to.

  Then check each entry two ways, because both failures are silent and they
  point in opposite directions:

  1. **Does it match anything?** Entries are prefix globs over the whole Bash
     call. `"gh"` does not match `gh api user`, and `"git fetch *"` does not
     match `git -C /path fetch origin`. An entry that never fires reads as an
     exemption and grants nothing — the symptom is the tool failing, never
     the policy looking wrong. Ask what the real invocations look like and
     compare them to the entries character by character.
  2. **What did excluding it give up?** An excluded command escapes *every*
     layer, including `credentials`. If `gh` is excluded, the
     `GITHUB_TOKEN` deny no longer applies to it and gh prefers that variable
     over its keyring; if `docker` is excluded, so is the socket policy.
     Report the specific credential rule each exclusion voids, and what
     scope-limited credential could replace it. This is the finding people
     miss, because the exemption and the credential rule usually live ten
     lines apart in the same file and look like they compose.
- **`filesystem.disabled`.** If true, there is no filesystem isolation at all,
  and a sandboxed command can widen its own access on the next run.
- **Read policy.** The default is *the entire computer readable*. Unless you
  see `credentials.files` entries or a `denyRead`, `~/.ssh` and
  `~/.aws/credentials` are readable by every sandboxed command. This is the
  most commonly missed gap — report it as a finding, not a footnote.
- **Network.** Empty `allowedDomains` means every new host prompts (fine
  interactively, a hang in headless runs). Without `strictAllowlist`, a
  prompt is an approval away from egress.

## 2. Are the hooks firing?

Hooks are only honored when the working directory is a **trusted** project
directory. A freshly created git worktree that has never been trusted silently
skips them — permissions still load, hooks do not, and nothing says so.

The audit hook is the canary, because it runs on every tool call:

```sh
ls -la "${CLAUDE_GUARDRAILS_AUDIT_DIR:-$HOME/.claude/plugins/data}"/**/audit 2>/dev/null \
  || ls -d ~/.claude/plugins/data/*/audit 2>/dev/null
```

Then confirm records exist for *today* and for *this* working directory:

```sh
tail -3 "$(ls -t ~/.claude/plugins/data/*/audit/*.jsonl 2>/dev/null | head -1)"
```

- No audit directory, or no records after a session with tool calls → **hooks
  are not running.** Most likely the directory is untrusted; also check the
  plugin is enabled (`/plugin`).
- Records present but `cwd` is a different path → you are checking the wrong
  session's log.
- `jq` missing → `audit.sh` exits silently by design. Report it; the audit
  layer is off.

Note that `escapes.py` is deliberately quiet in normal use: it only inspects
Bash calls that set `dangerouslyDisableSandbox`, plus `WebFetch` and MCP
payloads. Absence of denials is expected and is not evidence it is loaded —
the audit log is the evidence.

### Firing is not the same as succeeding

A hook that *runs and errors* is a separate failure from one that never runs,
and it is the more dangerous of the two: per the hooks contract, any exit
that is not `2` is a **non-blocking error**, so the guarded tool call
proceeds. The session looks completely normal. The audit log check above will
not catch it — the hook fired, it just did not work.

`escapes.py` routes every exception to `deny()` for exactly this reason, but
that contract only holds **once the interpreter is running**. It cannot cover
a hook that fails to start: a lost execute bit, a missing interpreter on a
different machine, or the plugin directory being swapped underneath a running
session by an auto-update. Those all present identically — one hook of two,
non-blocking, tens of milliseconds, no output.

You cannot see this from the filesystem. It needs the hook telemetry:

```sh
echo "${CLAUDE_CODE_ENABLE_TELEMETRY:-<unset — hook errors are invisible>}"
```

With the OTel sink running, `hook_execution_complete` carries the counts. Any
non-zero error total is a guard that silently did not apply, so report the
count and the window, not a pass/fail:

```sql
SELECT ts, hook_name, num_hooks, num_success, num_errors, duration_ms
FROM hook_runs WHERE num_errors > 0 ORDER BY ts;
```

A tight burst across several sessions points at a plugin update rather than a
code fault — check whether the installed version changed in that window.
Without telemetry, say plainly in the report that this layer is unverifiable
rather than marking it green.

## 3. What is covered outside the sandbox?

The sandbox is **Bash-only**. Check the permission rules for the tools it
never sees:

```sh
cat .claude/settings.json ~/.claude/settings.json 2>/dev/null | grep -A20 '"permissions"'
```

- Is there a `Read` deny for credential paths? `sandbox.credentials` does
  **not** stop the `Read` tool.
- Are the prefixes right? Absolute is `//path`; `/path` is project-relative
  and will match nothing where you meant a home-directory path.
- MCP tools: list what is connected (`/mcp`). Anything that publishes — Slack,
  Jira, GitHub — can carry data off the machine with no sandbox involvement.
  The `escapes.py` hook screens those payloads for credential shapes, which is
  a backstop, not a boundary.

## 4. Is the verify gate active?

```sh
echo "${CLAUDE_GUARDRAILS_VERIFY:-<unset -- gate inert>}"
```

If unset, the agent can end a turn on a red build. If set, confirm the command
actually exists in this repo — a verify command that always fails blocks every
turn, and one that always passes (a missing target that exits 0) is worse than
nothing.

## 5. Report

One table, one verdict per layer, plus a short list of concrete gaps ranked by
what they'd let through. For each gap, name the specific key that closes it
and the scope it has to live in. Offer `/guardrails-setup` to apply them.

Do not soften the summary. "Sandbox on, but every credential on this machine
is readable and three commands are excluded from isolation" is the useful
sentence; "protection is configured" is not.
