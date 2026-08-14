# guardrails

Harness-enforced safety rails for agentic sessions. Three hooks:

| Hook | Event | What it does | Fails how |
|---|---|---|---|
| `contain.sh` | `PreToolUse` on `Bash\|Write\|Edit.*` | Denies writes outside the project, network/privilege/deploy binaries, and pushes to off-machine remotes | **Closed** — any internal error denies |
| `audit.sh` | `PreToolUse` on `*` | Appends every tool call to a JSONL log | Never blocks, never crashes |
| `verify-gate.sh` | `Stop` | Refuses to let the agent finish on a red build | Inert until configured |

The point of putting this in hooks rather than a prompt: **hooks are enforced
by the harness, so they hold when the model is wrong.** A `CLAUDE.md` that
says "don't write outside the repo" is a request. This is a control.

## Install

```
/plugin marketplace add christopherdavenport/christopherdavenport-marketplace
/plugin install guardrails@christopherdavenport
```

Containment and auditing are active immediately. The verify gate is opt-in —
see below.

## Configuration

All optional; the defaults are the safe ones.

| Variable | Default | Effect |
|---|---|---|
| `CLAUDE_GUARDRAILS_VERIFY` | *unset* | Command the Stop gate runs, e.g. `make verify`. **Unset = gate disabled.** |
| `CLAUDE_GUARDRAILS_VERIFY_TIMEOUT` | `300` | Seconds before the verify command is killed |
| `CLAUDE_GUARDRAILS_ALLOW` | *empty* | Colon-separated extra writable roots, e.g. `/tmp:/var/folders` |
| `CLAUDE_GUARDRAILS_OFF` | *unset* | `1` disables containment (auditing continues) |
| `CLAUDE_GUARDRAILS_AUDIT_OFF` | *unset* | `1` disables auditing |
| `CLAUDE_GUARDRAILS_AUDIT_DIR` | `${CLAUDE_PLUGIN_DATA}/audit` | Where audit logs are written |

### The verify gate is deliberately opt-in

It is the one hook that must not guess. A `Stop` gate that assumed
`make verify` would block every turn in every repository that hasn't got one —
for a plugin other people install, that is hostile. So it stays inert until
you name the command, scoped to repos that actually have one:

```sh
# .envrc, shell profile, or wherever it is scoped per-project
export CLAUDE_GUARDRAILS_VERIFY="make verify"
```

Then an agent cannot end its turn on a failing build. This converts *"the
agent says it works"* into *"the build says it works"*, which is the whole
point.

## What this does not do

**It does not ship permissions.** Plugins cannot: only `agent` and
`subagentStatusLine` are supported in a plugin's `settings.json`, and an
unrecognised `permissions` key is silently ignored at load time — it would
look correct and do nothing.

That is worth understanding rather than working around, because **the two
layers cover different failure modes**:

|  | Permissions | Hooks |
|---|---|---|
| Can crash? | No — harness-enforced | **Yes, and they fail open** — a hook that exits 1 or times out is a "non-blocking error" and the call proceeds |
| Survive `bypassPermissions`? | **No** — skipped entirely | Yes |

So they cover each other, and you want both. Keep permission rules in
`settings.json` (or enterprise managed settings for org-wide policy) and let
this plugin carry the enforcement that survives `bypassPermissions`.

`contain.sh` fails *closed* specifically because of that first row: a
containment hook that fails open is worthless, since any crash becomes an
escape.

## Verifying it is actually working

A hook that is not wired looks exactly like a hook that permits everything.
After installing, confirm audit records appear:

```sh
ls "$(ls -d ~/.claude/plugins/data/*/audit 2>/dev/null | head -1)"
```

An empty or missing audit directory after a session with tool calls means the
hooks are not firing.

> **Known gotcha:** hooks are only honoured when the working directory is a
> *trusted* project directory. Running in a freshly created git worktree that
> has never been trusted will silently skip hooks — permissions still load,
> hooks do not, and the session looks entirely normal. This was measured, not
> theorised: identical runs produced audit records from a trusted root and
> none from a fresh worktree.

## Eval

`evals/guardrails/` — 34 assertion-based cases, deterministic and free (no
model). Includes a `--mutate` mode that replaces the hook with an always-allow
stub and asserts the suite goes red, because a guardrail suite that cannot
fail is not testing anything.
