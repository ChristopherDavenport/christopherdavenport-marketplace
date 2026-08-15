# guardrails — assertion eval

**40/40 hook cases** (24 deny, 16 allow) and **46/46 template checks** across
4 templates. Mutation check passes.

Deterministic and free: crafted `PreToolUse` payloads in, exit codes out, plus
a parse-and-assert pass over the policy templates. No model, no tokens, no
network — so this runs on every change rather than on a funded sweep.

```
./evals/guardrails/run.sh              # the suite
./evals/guardrails/run.sh --mutate     # prove the suite can fail
```

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
That is the whole reason 16 of the 40 assert `0`.

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

## Not covered

Stated rather than implied, because an eval's silence reads as coverage:

- **`audit.sh` and `verify-gate.sh`** have no cases. Both were exercised by
  hand; neither is a decision-maker, so an exit-code assertion says little.
- **The skills' prose** is not scored. `sandbox-policy`, `/guardrails-setup`,
  and `/guardrails-doctor` are judge-shaped work that has not been run — only
  the templates they ship are asserted.
- **Whether the OS sandbox itself holds** is Anthropic's test suite, not this
  one. This eval covers the plugin's seams around it.
