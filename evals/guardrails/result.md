# guardrails — assertion eval

**91/91 hook cases** (52 deny, 39 allow), **46/46 template checks** across
4 templates, **15/15 plugin manifests loadable**, and **3/3 hooks runnable**.
Mutation check passes.

Deterministic and free: crafted `PreToolUse` payloads in, exit codes out, plus
a parse-and-assert pass over the policy templates and every plugin manifest in
the marketplace. No model, no tokens, no network — so this runs on every change
rather than on a funded sweep.

```
./evals/guardrails/run.sh              # the suite
./evals/guardrails/run.sh --mutate     # prove the suite can fail
./evals/guardrails/replay.py           # backtest against recorded audit data
```

> These counts are regenerated from the suite rather than written by hand. An
> earlier revision of this file reported 40 cases while `cases.json` held 91 —
> a published result that undercounts its own suite invites exactly the wrong
> question about what else is stale.

## What is under test

Two artifacts, for two different rot modes.

**`safety/guardrails/scripts/escapes.py`** — the hook. Only exit `2` counts as
a block: per the hooks contract, any other non-zero is a "non-blocking error"
and the tool call proceeds, so a crash is an escape wearing a costume. The
suite asserts on exit code alone for that reason.

**`skills/sandbox-policy/references/templates.md`** — the four policy
templates, parsed out of the markdown by their `<!-- template: NAME -->`
markers. These are the plugin's actual product now: someone copies one into a
settings file and trusts it. Parsing catches syntax rot; the assertions catch
a well-meaning edit that quietly widens the policy, which still parses fine and
still reads as responsible.

## Hook coverage

| Group | Cases | What it establishes |
|---|---|---|
| Sandboxed Bash ignored | 3 allow | The hook stays out of the way of ordinary Bash — including `rm -rf /`, which is now the kernel's problem |
| Unsandboxed Bash denied | 15 deny | The `dangerouslyDisableSandbox` escape hatch is checked: network/privilege/deploy binaries, publishes, writes outside the project, relative traversal, redirects, `rm -rf` on the project or its parents, pushes to network remotes |
| Unsandboxed Bash allowed | 6 allow | Opting out is legitimate for local work — `docker build`, `/dev/null`, `2>&1`, in-project writes, read-only commands |
| Outbound payloads denied | 7 deny | Credential shapes in MCP and `WebFetch` inputs, including one nested inside a structured field |
| Outbound payloads allowed | 5 allow | Clean payloads, and the near-misses: git SHAs, lockfile integrity hashes, an env-var *name* with no value |
| Out of scope | 2 allow | `Read` and `Write` are permission-rule concerns; the hook must not touch them |
| Fail closed | 2 deny | Empty payload, malformed `tool_input` |

### The allow cases carry as much weight as the deny cases

A hook that blocks everything passes every deny test and also blocks the build.
That is the whole reason 39 of the 91 assert `0`.

Three of them are load-bearing beyond that:

- **`sandboxed-bash-ignored-rm`** feeds `rm -rf /` with no
  `dangerouslyDisableSandbox` flag and asserts the hook allows it. That looks
  alarming and is the point: this hook's premise is that sandboxed Bash is
  contained by the OS, and a hook that hedges by re-checking it anyway is the
  0.1 design creeping back in. If someone later "fixes" this case, the premise
  has changed and the README needs to change with it.
- **`mcp-git-sha-not-secret`** and **`mcp-lockfile-hash-not-secret`** pin the
  credential patterns against the false positives that would kill the feature.
  A leak detector that fires on `pnpm-lock.yaml` gets switched off in a day,
  and then it catches nothing at all.

## Template checks

Per template: sandbox enabled, filesystem isolation not disabled, no
`allowAppleEvents`, no `docker.sock` in `allowUnixSockets`, every credential
entry using a `mode` the harness recognises (an unknown mode is stripped at
load, so a typo silently removes the protection), `mask` entries accompanied by
`network.tlsTerminate` (without it masking cannot work), and `excludedCommands`
kept to at most three entries (each one runs with no isolation at all).

Per template, its reason for existing:

- **ci** — `failIfUnavailable`, `allowUnsandboxedCommands: false`,
  `strictAllowlist`. A runner missing bubblewrap otherwise runs unsandboxed and
  still reports green.
- **managed** — the three managed-only locks plus strict mode. Array keys merge
  across scopes, so without them a developer widens the policy locally.
- **solo** — credential file entries *and* `permissions.deny`. The sandbox
  default is that the entire computer is readable, and `sandbox.credentials`
  does not cover the `Read` tool.

## Mutation

`--mutate` replaces the hook with an always-allow stub and asserts every deny
case goes red. A guardrail suite that cannot fail is not testing anything, and
that failure is invisible — a green run looks identical whether the hook works
or is absent.

Verified in both directions during this rewrite: the hook mutation flips all 24
deny cases as expected, and deleting `failIfUnavailable` +
`allowUnsandboxedCommands` from the managed template drops it to 44/46 with
both missing locks named.

Two real bugs of exactly this shape were caught by earlier versions of this
suite: a timeout wrapper that silently no-op'd on macOS so a test never
executed and reported success, and a relative-traversal case that was never
checked at all.

## Manifest loadability

Added after v0.2.0 shipped with a manifest that could not load. `plugin.json`
declared `"hooks": "./hooks/hooks.json"`, a path the harness already loads by
convention, so the harness refused the duplicate and **the entire plugin failed
to load** — no hooks, no enforcement.

Both existing green checks agreed it was fine. `claude plugin validate --strict`
passes on such a manifest, and the 40 hook cases run `escapes.py` directly
rather than through the plugin loader, so they passed against a plugin that was
never loading in a real session.

That is precisely the failure this plugin exists to prevent — an unloaded guard
is indistinguishable from a permissive one — so `validate_manifests.py` now
asserts it, across every plugin in the marketplace rather than just this one,
since the hazard belongs to the manifest format. Verified in both directions:
reintroducing the key drops the run to 13/14 and names the offending file.

## Hook runnability

Added after `audit.sh` and `verify-gate.sh` were found to have shipped with mode
`100644`. The harness executes a `type: command` hook, so both failed with
"permission denied" on **every tool call since the plugin landed** — and per the
hooks contract a non-zero exit that is not `2` is a *non-blocking error*, so the
call proceeds. The audit log was never written once and the Stop gate never ran.

Every existing check agreed things were fine. `claude plugin validate --strict`
does not look at mode bits. The 40 hook cases invoke `escapes.py` via
`python3 "$HOOK"`, which does not need the executable bit, so they passed
against a file the harness could not run. The other two hooks had no cases at
all — listed under "Not covered" below, where the gap was documented and still
concealed a total failure of two thirds of the plugin.

It was found by telemetry rather than by tests: `hook_execution_complete`
reported `num_non_blocking_error: 1` on both `PreToolUse` and `Stop`.

`validate_hooks.py` now checks, for every command in `hooks.json`: the file
exists, is executable, is recorded in git as `100755` (a local `chmod` does not
travel to a clone or an install), and execs cleanly when run directly the way
the harness runs it. Verified in both directions — reverting one mode bit drops
the run to 2/3 and names the file.

## Replay: the non-synthetic tier

`replay.py` feeds every call recorded by `audit.sh` back through the current
hook and reports what it would decide now. It exists because the suite above,
however green, cannot produce the number that decides whether a guard survives
contact with users: **the false-positive rate on real traffic.** Its allow cases
were written by whoever wrote the deny rules, and nobody writes an allow case
for the idiom they did not think of.

Two things it surfaces that the assertion suite structurally cannot:

- **Denials on commands that really ran, and were fine.** Each one is either a
  rule to narrow or an allow case to add to `cases.json`. Observed categories
  worth triaging on any real corpus: redirects to a temp path outside the
  project, publishes to an internal registry, and commands whose quoting the
  resolver refuses to guess at (correct fail-closed behaviour, still a blocked
  legitimate command).
- **Whether a branch is exercised at all.** A guard on rare operations can sit
  at zero real hits indefinitely. The MCP argument-inspection branch is a
  standing example — a corpus can contain hundreds of MCP calls and *no*
  attempt against a guarded tool, which means that branch is covered by its 19
  synthetic cases and nothing else. Worth knowing before calling it tested.

It is a reporting tool, not a gate: real traffic changes between runs, so a hard
threshold would fail for reasons unrelated to the hook. `--fail-over N` is there
for CI if a ceiling is wanted anyway, and `--json` for trend collection.

Deny verdicts now land in the same audit log as the attempts (see
`escapes.py::_audit_deny`), so the log is self-sufficient — attempts from
`audit.sh`, verdicts from the hook that made them, joinable on
`(session, ts, tool)`. Before that, the log recorded only what was *tried*, and
answering "did the guard fire?" meant correlating with a separate telemetry
store whose decision column is mostly null.

Replay runs with `CLAUDE_GUARDRAILS_AUDIT_OFF=1` forced, so a dry run never
writes verdict records back into the corpus it is reading.

## Not covered

Stated rather than implied, because an eval's silence reads as coverage:

- **`audit.sh` and `verify-gate.sh` have no behavioural cases.** They are now
  asserted to be *runnable*, which is what was actually broken, but nothing
  checks that the audit log contains the right fields or that the Stop gate
  blocks on a red build. Both were exercised by hand.
- **Replay depends on a corpus.** On a fresh install there is nothing to replay,
  and the tier reports nothing rather than passing. It also cannot see calls the
  audit hook never recorded — and hooks are only honoured in a *trusted* project
  directory, so a fresh worktree silently contributes neither audit records nor
  enforcement.
- **The skills' prose** is not scored. `sandbox-policy`, `/guardrails-setup`,
  and `/guardrails-doctor` are judge-shaped work that has not been run — only
  the templates they ship are asserted.
- **Whether the OS sandbox itself holds** is Anthropic's test suite, not this
  one. This eval covers the plugin's seams around it.
