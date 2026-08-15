---
name: guardrails-setup
description: Generate and install a tested sandbox + permissions policy for this repository. Inspects the project to learn what its build actually needs (write paths, network hosts, incompatible tools), proposes a minimal `sandbox` block, writes it to the right settings scope, and verifies it loaded. Use when the user asks to set up guardrails, enable the sandbox, lock down an agent session, or says a sandbox policy is blocking their build.
---

# /guardrails-setup

Produce a sandbox policy that is **tight enough to matter and loose enough to
survive**. A policy that blocks the build gets deleted within a day, so the
work here is mostly discovering what the build genuinely needs before
restricting anything.

Load the `sandbox-policy` skill for the key reference, scope rules, and
templates. This skill is the procedure.

## 1. Establish the starting point

Do not propose anything before you know what is already in effect.

```sh
cat .claude/settings.json 2>/dev/null
cat .claude/settings.local.json 2>/dev/null
cat ~/.claude/settings.json 2>/dev/null
```

Also check for managed settings — if the org already enforces a policy, your
job is to fit inside it, not to duplicate or fight it:

```sh
cat "/Library/Application Support/ClaudeCode/managed-settings.json" 2>/dev/null   # macOS
cat /etc/claude-code/managed-settings.json 2>/dev/null                            # Linux/WSL
```

Ask the user to run `/sandbox` and report the **Config** tab if anything looks
ambiguous. That tab shows resolved settings, which is ground truth; the files
are only inputs.

## 2. Learn what the build needs

Read, don't guess. Guessed policy is how you end up with a `denyRead` that
breaks the test suite.

**Write paths outside the repo** — look for tool caches in build config:
`go.mod` (→ `~/.cache/go-build`, `~/go/pkg/mod`), `package.json` (→ `~/.npm`,
`~/.cache/yarn`, `.next`, `dist`), `Cargo.toml` (→ `~/.cargo`), `pyproject.toml`
/ `uv.lock` (→ `~/.cache/uv`), `Makefile` targets, Dockerfiles.

**Network hosts** — registries the build fetches from. Read lockfiles and CI
workflow files (`.github/workflows/*.yml`) rather than assuming; the CI config
usually names every host the build actually touches.

**Incompatible tools** — grep the scripts and Makefile for `docker`, `gh`,
`gcloud`, `terraform`, `open`, `osascript`. These are the `excludedCommands`
candidates. Note them; don't add them yet.

**Existing secrets on the machine** — `ls ~/.aws ~/.ssh ~/.config/gcloud
~/.kube 2>/dev/null` tells you which credential entries are worth writing.
Enumerate only what exists; there is no built-in deny list, so an entry for a
directory that isn't there is dead weight in the file.

## 3. Choose the scope

| What you're writing | Where it goes | Why |
|---|---|---|
| Repo-specific write paths, domains, `excludedCommands` | `.claude/settings.json`, committed | Everyone on the repo needs it; array keys merge with user scope |
| Credential blocks, `strictAllowlist`, anything in the managed-only list | `~/.claude/settings.json` | Ignored from project scope — silently |
| One person's local exception | `.claude/settings.local.json` | Gitignored |
| Org policy | managed settings | Only scope a developer can't override |

If a rule needs user scope and the user only asked about this repo, say so
explicitly and write both files. Splitting is not a complication to hide — a
credential rule written into project settings is a rule that does nothing.

## 4. Propose before writing

Show the JSON and a one-line justification per key. Call out anything that
will change how their tools behave — especially:

- `credentials.envVars` `deny` **breaks** `gh` and `npm` inside the sandbox.
  Offer `mask` (user scope, needs `network.tlsTerminate`) as the alternative.
- `strictAllowlist: true` turns a domain prompt into a hard failure.
- Every `excludedCommands` entry is a command with **no isolation at all**.

Get agreement, then write. Merge into existing settings rather than
overwriting — read the file, add keys, preserve everything else.

## 5. Verify it actually loaded

This step is not optional. An unloaded policy is indistinguishable from a
permissive one, and that is the failure mode this whole plugin exists to
prevent.

1. Ask the user to run `/sandbox` and confirm the **Config** tab shows the
   resolved paths and domains you wrote.
2. Run `/doctor` — it flags unreliable domain spellings.
3. Exercise the build: run the project's test or build command and confirm it
   still passes under the sandbox. If it fails, the violation details are
   appended to the command output, naming the blocked path or host. Widen with
   `allowWrite` / `allowedDomains` — reach for `excludedCommands` only when the
   tool is genuinely incompatible.
4. Confirm the guardrails hooks are firing (`/guardrails-doctor`), since hooks
   are skipped entirely in an untrusted directory.

## 6. Report

State plainly: what is now enforced, what is deliberately still open, and
which file each rule lives in. If you left something out because it would
break the build, say that rather than quietly omitting it — the user may
decide the breakage is acceptable, and that call is theirs.
