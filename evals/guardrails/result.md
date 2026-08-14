# guardrails — eval result

**34 / 34 passed. Mutation check: passed.**

```
./evals/guardrails/run.sh            # 34/34, fence holds
./evals/guardrails/run.sh --mutate   # 34/34, suite detects a neutered hook
```

## Why this eval has a different shape

Every other plugin here is a **skill**, so the harness can ask the same
question twice — once with the skill loaded, once without — and have a judge
pick the better answer.

`guardrails` ships **hooks**. There is no answer to compare. What it produces
is a *decision*, and a decision is directly assertable: feed the hook a
`PreToolUse` payload and check the exit code. `2` = blocked, `0` = allowed.

That makes this eval **deterministic and free** — no model, no tokens, no
network — so it runs on every change instead of on a funded sweep.

## Coverage

| Class | Cases | What it establishes |
|---|---|---|
| Path containment | 8 | Writes outside the project are denied, whether via `Write`/`Edit`, shell redirection, `tee`, or a state-changing command |
| Relative traversal | 4 | `../../../../x` is denied — **regression cases**; matching only absolute paths was a real hole |
| Network / privilege / deploy | 6 | `curl`, `wget`, `sudo`, `kubectl`, `terraform`, `npm publish` |
| Off-machine git remotes | 2 | URL and scp-style remote specs |
| Fail-closed | 1 | A malformed payload denies rather than allows |
| Self-protection | 2 | The agent cannot edit the user's Claude config or the hook constraining it |
| **Legitimate work** | **10** | `make`, `go test`, `npm test`, `git commit`, `/dev/null`, in-project relative paths, `sed -i`, `grep` |

The 10 `allow` cases matter as much as the 24 `deny` cases. **A fence that
blocks everything passes every deny test and is useless** — it would also
block the build. Both directions are the test.

## The mutation check

`--mutate` replaces the hook with an always-allow stub and asserts every deny
case goes red.

This is not a nicety. A guardrail suite that *cannot fail* is not testing
anything, and that failure mode is invisible: a green run looks identical
whether the fence is working or absent. Two bugs of exactly this shape were
found while developing these hooks — one where a timeout wrapper silently
no-op'd on macOS so the test never executed and reported success, and one
where relative-path traversal was never checked at all.

Run `--mutate` whenever the hook changes.

## Not covered here

- **Live wiring.** This suite tests the hook's decisions in isolation. That
  the plugin is loaded and the hook actually fires is verified separately by
  installing the plugin and confirming audit records appear — see the
  plugin README.
- **Permissions.** Plugins cannot ship `permissions.allow` / `permissions.deny`
  (only `agent` and `subagentStatusLine` are supported in a plugin's
  `settings.json`). The hook layer and the permission layer cover different
  failure modes — see the plugin README for why you want both.
