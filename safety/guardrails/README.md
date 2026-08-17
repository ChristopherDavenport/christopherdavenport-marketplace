# guardrails

Containment for agentic sessions, built **on** Claude Code's OS-level sandbox
rather than around it.

The sandbox is the fence: Seatbelt on macOS, bubblewrap + seccomp on
Linux/WSL2, kernel-enforced, transitive over child processes, with a network
egress allowlist and credential blocking. It is a better fence than anything a
plugin can build. What a plugin can add is the part that is actually hard —
knowing what to put in it, getting it into a scope that honors it, proving it
loaded, and covering the specific things the sandbox does not see.

## What's in it

| Component | Kind | What it does |
|---|---|---|
| `sandbox-policy` | skill | The reference: `sandbox.*` keys, which scopes silently ignore which keys, four validated policy templates, symptom→fix failure modes |
| `/guardrails-setup` | skill | Inspects the repo to learn what its build needs, proposes a minimal policy, writes it to the right scope, verifies it loaded |
| `/guardrails-doctor` | skill | Reports what is **enforced**, not what is configured — sandbox state, whether hooks are firing, what's uncovered |
| `escapes.py` | `PreToolUse` hook | Guards the two paths that leave the sandbox. **Fails closed** |
| `audit.sh` | `PreToolUse` hook | Appends every tool call to JSONL. Never blocks, never crashes |
| `verify-gate.sh` | `Stop` hook | Refuses to let an agent finish on a red build. Inert until configured |

## Install

```
/plugin marketplace add christopherdavenport/christopherdavenport-marketplace
/plugin install guardrails@christopherdavenport
```

Then `/guardrails-setup`. Installing the plugin alone changes almost nothing —
a plugin **cannot ship a policy**, only the means to write one. See
[Why a configurator](#why-a-configurator-and-not-a-fence).

## Why a configurator and not a fence

Version 0.1 of this plugin shipped `contain.sh`: a `PreToolUse` hook that
regex-matched shell commands for network binaries and resolved write paths
against the project root. It passed 34 assertion cases. It was also the wrong
shape, for a reason that isn't a bug list:

**It was a denylist over shell text.** Shell has unbounded spellings of the
same action — `env curl`, `$(printf 'cur'; printf 'l')`, `python3 -c
"urllib…"`, `xargs`, a script written into the repo on one call and executed
on the next. `python3 -c "open('/etc/hosts','w')"` never touched its write-verb
list at all. And it saw only the parent command, never the child processes a
build spawns. The sandbox sees every syscall, from every descendant.

The second problem was the cure: fail-closed matching over a generous path
heuristic produces false denials on ordinary commands, and the documented
escape was `CLAUDE_GUARDRAILS_OFF=1` — all or nothing. Guardrails that misfire
get switched off, and that one switched off wholesale.

The 0.1 README also argued that hooks were uniquely necessary because
permissions are skipped under `--dangerously-skip-permissions`. That was true
of permissions, but the sandbox is **both** harness-enforced **and**
bypass-surviving — the docs' own matrix lists the effect of
`--dangerously-skip-permissions` on the sandbox as "Nothing". So the argument
that justified a hand-rolled fence doesn't hold.

What survived the rewrite is the judgment, not the regex — which failure modes
matter, which configurations are silent no-ops, why a green run proves nothing.
That is now the `sandbox-policy` skill.

## The layers

| Layer | Enforced by | Covers | Survives `--dangerously-skip-permissions` |
|---|---|---|---|
| **Sandbox** | OS kernel | Bash **and all child processes** — filesystem, network, credentials | **Yes** |
| **Permission rules** | Claude Code, pre-call | Every tool, including `Read`, `Edit`, `WebFetch`, MCP | No — skipped |
| **Hooks** | Claude Code, pre-call | Every tool | Yes, but **fail open** — a hook that exits 1 or times out is a "non-blocking error" and the call proceeds |
| **CLAUDE.md** | The model, if it feels like it | — | It's a request, not a control |

You want the first two. This plugin helps you write them, and uses the third
only where the first two structurally can't reach.

## What the hooks actually cover

The sandbox is **Bash-only** and stops at the escape hatch. `escapes.py` takes
exactly those two gaps and nothing else:

1. **MCP and `WebFetch` payloads** — entirely outside the sandbox. These are
   the tools that publish (Slack, Jira, GitHub, any URL), so the check is
   credential *shapes* in the outbound payload, not paths. Eleven
   high-specificity patterns; git SHAs and lockfile integrity hashes are
   explicitly tested as non-matches, because a leak detector that fires on
   `pnpm-lock.yaml` is disabled within a day. Deny reasons name the shape,
   never the matched text.

2. **Bash calls carrying `dangerouslyDisableSandbox: true`** — the documented
   escape hatch, where the command runs on the host with no isolation. Rare
   and explicitly marked, so a conservative check is proportionate here in a
   way it never was on every call. Ordinary sandboxed Bash is otherwise
   ignored, including `rm -rf /` — that is the kernel's job now, and the eval
   asserts the hook stays out of the way.

3. **Every Bash call, for irreversible outward operations** — a small,
   deliberately narrow set that neither of the layers above actually covers:

   - `sandbox.excludedCommands` runs a binary with **no isolation and no
     flag** on the tool call, so branch 2 never sees it. Such a binary is
     outside the sandbox *and* outside this hook unless something screens it
     unconditionally.
   - A properly sandboxed command still reaches every host in
     `sandbox.network.allowedDomains`. The sandbox was never what stopped
     `gh pr merge`; `github.com` is on that allowlist by necessity.

   `gh` is the motivating case, and a permission rule cannot substitute:
   a rule naming `gh pr merge` does not match
   `gh api --method PUT repos/o/r/pulls/1/merge`, which merges the same pull
   request — and `gh api` is the dominant idiom in real use, so the
   subcommand spelling is the rare path rather than the common one. Merging,
   deleting a repo, publishing a release, writing a secret and `gh api
   DELETE` are denied. Reading, listing, `gh run watch` and **opening** a pull
   request stay allowed; a PR you can close is the autonomy target, not a
   threat.

Set `"allowUnsandboxedCommands": false` and branch 2 can never fire, which is
the correct end state. It's a backstop for sessions not yet locked down.
Branch 3 is unaffected by that setting, by design.

`docker` is deliberately absent from branch 2's binary list — it is the
canonical `excludedCommands` entry and `docker build` has to keep working, or
the entry gets deleted within a day. What is denied is the flag set that hands
the container the host: a bind mount of `/`, the docker socket, a host
namespace, or `--privileged`.

`escapes.py` still **fails closed**: per the hooks contract, an exit 1 or a
timeout is a "non-blocking error" and the call proceeds, so a hook guarding an
escape hatch that failed open would be worthless. Every unexpected exception
routes to deny.

## Configuration

All optional; the defaults are the safe ones.

| Variable | Default | Effect |
|---|---|---|
| `CLAUDE_GUARDRAILS_VERIFY` | *unset* | Command the Stop gate runs, e.g. `make verify`. **Unset = gate disabled.** |
| `CLAUDE_GUARDRAILS_VERIFY_TIMEOUT` | `300` | Seconds before the verify command is killed |
| `CLAUDE_GUARDRAILS_ALLOW` | *empty* | Colon-separated extra roots the unsandboxed-Bash branch will permit |
| `CLAUDE_GUARDRAILS_OFF` | *unset* | `1` disables `escapes.py` (auditing continues) |
| `CLAUDE_GUARDRAILS_AUDIT_OFF` | *unset* | `1` disables auditing |
| `CLAUDE_GUARDRAILS_AUDIT_DIR` | `${CLAUDE_PLUGIN_DATA}/audit` | Where audit logs are written |

Sandbox and permission policy is **not** configured here — it lives in
`settings.json`, because that's the only place the harness reads it from.
`/guardrails-setup` writes it.

### The verify gate is deliberately opt-in

It is the one hook that must not guess. A `Stop` gate assuming `make verify`
would block every turn in every repo without one — hostile in a plugin other
people install. So it stays inert until you name the command:

```sh
export CLAUDE_GUARDRAILS_VERIFY="make verify"
```

Then an agent cannot end a turn on a failing build. This converts *"the agent
says it works"* into *"the build says it works"*, which is the whole point.

## Why the policy isn't shipped in the plugin

A plugin's root `settings.json` supports **only** `agent` and
`subagentStatusLine`. A `permissions` or `sandbox` key there is dropped at
load — it would look correct and do nothing. Plugin-defined agents likewise
can't carry `hooks`, `mcpServers`, or `permissionMode` frontmatter.

That's a deliberate boundary, not an oversight to route around: policy belongs
in a settings file the user or their administrator controls. Hence a skill that
writes one, rather than a plugin that pretends to be one.

## Verifying it is actually working

An unloaded control looks exactly like a permissive one. Run
`/guardrails-doctor`, or check by hand:

```sh
ls "$(ls -d ~/.claude/plugins/data/*/audit 2>/dev/null | head -1)"
```

An empty or missing audit directory after a session with tool calls means the
hooks are not firing.

> **Known gotcha:** hooks are only honoured when the working directory is a
> *trusted* project directory. A freshly created git worktree that has never
> been trusted silently skips hooks — permissions still load, hooks do not, and
> the session looks entirely normal. This was measured, not theorised:
> identical runs produced audit records from a trusted root and none from a
> fresh worktree.

For the sandbox, `/sandbox` → **Config** tab is ground truth. It shows resolved
settings after scope precedence and after keys ignored from the wrong scope
have been dropped; the files are only inputs to it.

## Eval

`evals/guardrails/run.sh` — deterministic and free (no model, no tokens), so it
runs on every change rather than on a funded sweep. Two parts:

- **40 hook cases.** The allow cases carry as much weight as the deny ones: a
  hook that blocks everything passes every deny test and also blocks the build.
  The sandboxed-Bash allow cases matter most, since this hook's premise is that
  it stays out of the way.
- **46 template checks.** The templates are the product now — someone will copy
  one into a settings file and trust it. Parsing catches rot; assertions catch
  a well-meaning edit that quietly widens the policy, which still parses fine
  and still looks responsible.

`run.sh --mutate` replaces the hook with an always-allow stub and asserts the
suite goes red, because a guardrail suite that cannot fail is not testing
anything — and that failure is invisible, since a green run looks the same
whether the hook works or is absent.
