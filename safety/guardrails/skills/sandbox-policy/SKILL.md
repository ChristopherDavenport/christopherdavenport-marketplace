---
name: sandbox-policy
description: Author, review, or debug Claude Code sandbox and permission policy — the `sandbox.*` settings keys (filesystem allowWrite/denyRead, network allowedDomains, credentials deny/mask), permission allow/deny rules, settings-scope precedence, and managed-settings rollout for an org. Use when writing or changing `.claude/settings.json`, `~/.claude/settings.json`, or `managed-settings.json`; when a sandboxed command fails on a path or host; when deciding between `allowWrite` and `excludedCommands`; or when someone asks how to stop an agent writing outside the repo, reaching the network, or reading credentials. Not for the guardrails hooks themselves (see the plugin README).
---

# Sandbox and permission policy

Containment in Claude Code is a layered thing, and the layers are not
interchangeable. Getting this right is mostly about putting each rule in the
layer that can actually enforce it.

## The layers, in the order you should reach for them

| Layer | Enforced by | Covers | Survives `--dangerously-skip-permissions` |
|---|---|---|---|
| **Sandbox** | OS kernel (Seatbelt / bubblewrap + seccomp) | Bash commands **and all their child processes** — filesystem, network egress, credentials | **Yes** |
| **Permission rules** | Claude Code, before the call | Every tool, including `Read`, `Edit`, `WebFetch`, MCP | No — skipped entirely |
| **Hooks** | Claude Code, before the call | Every tool | Yes, but **fail open** — a hook that exits 1 or times out is a "non-blocking error" and the call proceeds |
| **Prompt / CLAUDE.md** | The model, if it feels like it | Everything and nothing | It is a request, not a control |

The single most common mistake is writing a rule at layer 4 that belongs at
layer 1. "Don't write outside the repo" in `CLAUDE.md` is a wish.
`sandbox.enabled: true` is a kernel boundary.

The second most common is reimplementing layer 1 at layer 3 — a hook that
regex-matches shell strings for `curl`. Shell has unbounded spellings of the
same action (`env curl`, `$(printf 'cur'; printf 'l')`, `python3 -c`, a script
written on one call and run on the next), and the hook sees only the parent
command, never the child processes it spawns. The sandbox sees every syscall.

## Start here: the baseline policy

Enable the sandbox. That one key does more than any amount of hand-written
rule-writing:

```json
{
  "sandbox": {
    "enabled": true
  }
}
```

Defaults you get immediately:

- **Write**: only the working directory, its subdirectories, and the session
  temp directory (`$TMPDIR` is repointed there for sandboxed commands).
- **Network**: nothing pre-allowed. The first connection to a new domain
  prompts; `allowedDomains` pre-approves.
- **Read**: **the entire computer.** This is the default people are surprised
  by — `~/.ssh` and `~/.aws/credentials` are readable unless you say otherwise.
  See [Close the read gap](#close-the-read-gap).
- **Protected paths**: writes to `.claude/settings*`, `.claude/hooks`,
  `.claude/skills`, `.mcp.json`, `.git/config`, `.bashrc`, and `~/.claude` are
  denied even inside writable directories, so a command can't grant itself
  more access for the next call. No `allowWrite` entry lifts this.

## Close the read gap

The default read policy is the biggest hole in a bare `enabled: true`. Two
ways to close it, and they compose:

**Targeted — block the credentials, keep everything else readable.** Start
here; it is much less likely to break a build than a blanket `denyRead`.

```json
{
  "sandbox": {
    "enabled": true,
    "credentials": {
      "files": [
        { "path": "~/.aws", "mode": "deny" },
        { "path": "~/.ssh", "mode": "deny" },
        { "path": "~/.config/gcloud", "mode": "deny" },
        { "path": "~/.kube/config", "mode": "deny" }
      ],
      "envVars": [
        { "name": "GITHUB_TOKEN", "mode": "deny" },
        { "name": "NPM_TOKEN", "mode": "deny" },
        { "name": "ANTHROPIC_API_KEY", "mode": "deny" }
      ]
    }
  }
}
```

There is **no built-in credential deny list** — only what you enumerate is
blocked. `envVars` deny unsets the variable for sandboxed commands; note that
it therefore breaks tools that need it (`gh`, `npm`). If you need the tool to
keep working, use `mode: "mask"` instead — the command sees a per-session
sentinel and the sandbox proxy swaps in the real value only for the hosts in
`injectHosts`. Masking requires `network.tlsTerminate` (the proxy has to see
request contents to substitute), and is honored only from user, managed, or
`--settings` scopes — never from a repo's `.claude/settings.json`.

Platform caveat: `mask` on a *file* substitutes a sentinel copy on Linux/WSL2,
but on **macOS it just blocks the file**, same as `deny`.

**Broad — deny the home directory, re-allow the project.** Only works from
*project* settings, because `.` resolves relative to the settings file's scope
(project root for `.claude/settings.json`, `~/.claude` for user settings):

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "denyRead": ["~/"],
      "allowRead": ["."]
    }
  }
}
```

Overlap resolution: the more specific path wins, in both directions. A narrow
`allowRead` re-opens part of a denied region; an exact `denyRead` holds inside
a wider allow, so a broad allow can't silently re-expose a secret.

## Granting access without punching a hole

When a tool needs to write outside the working directory, there are two moves
and they are not equivalent:

| Move | Effect | Use when |
|---|---|---|
| `filesystem.allowWrite: ["~/.kube"]` | Widens the sandbox by exactly that path; everything else still enforced | **Default choice.** The tool needs one location |
| `excludedCommands: ["docker *"]` | That command runs **entirely outside** the sandbox — no filesystem, no network, no credential enforcement | Last resort: the tool is fundamentally incompatible |

Prefer `allowWrite` every time it will do. `excludedCommands` also has no
managed-only lockdown — a developer can always append to it — so in an org
policy keep that list short and specific.

Known cases that genuinely need `excludedCommands`:

- `docker` — incompatible with the sandbox outright.
- Go-based CLIs on macOS (`gh`, `gcloud`, `terraform`) — TLS verification
  fails under Seatbelt. (If you run a MITM proxy with a custom CA via
  `httpProxyPort`, set `network.enableWeakerNetworkIsolation` instead.)
- `open` / `osascript` / browser auth flows on macOS fail with error `-600`
  because Apple Events are blocked. `allowAppleEvents: true` fixes it but
  removes code-execution isolation — a sandboxed command can then launch
  other apps unsandboxed. Excluding the one command is usually better.

## Network

No domains are pre-allowed. Pre-approve the ones a build genuinely needs:

```json
{
  "sandbox": {
    "enabled": true,
    "network": {
      "allowedDomains": ["github.com", "*.npmjs.org", "proxy.golang.org"]
    }
  }
}
```

`WebFetch(domain:...)` permission allow-rules feed the same allowlist.
By default an unlisted domain **prompts**; set `strictAllowlist: true` (user,
managed, or `--settings` scope only — ignored in a repo) to deny outright.

Write IPv6 literals bracketed: `"[::1]"`, or `"[::1]:443"` for one port.
Unbracketed multi-colon entries are ambiguous; Claude Code resolves them
conservatively and `/doctor` will name the ones it can't read reliably.

The built-in proxy filters on requested hostname and **does not terminate TLS
by default**, so it is a domain allowlist, not content inspection. If your
threat model needs inspection, use `network.tlsTerminate` or a custom proxy.

## Scope: where a rule has to live to work

Precedence, highest first: **managed → CLI `--settings` → local
(`.claude/settings.local.json`) → project (`.claude/settings.json`) → user
(`~/.claude/settings.json`)**.

But precedence isn't the whole story — several security-sensitive keys are
**ignored** from lower scopes rather than overridden, so a rule in the wrong
file looks correct and does nothing:

| Key | Honored from |
|---|---|
| `filesystem.disabled` | User, managed, `--settings` only — a checked-out repo can't turn filesystem isolation off |
| `strictAllowlist` | User, managed, `--settings` only |
| `credentials` `mask` entries, `network.tlsTerminate`, `credentials.allowPlaintextInject`, `awsPairs`, `sigv4` | User, managed, `--settings` only |
| `allowAppleEvents` | User, managed, `--settings` only |
| Everything else | Any scope |

Merge behaviour differs by type: **scalars** take the highest-precedence
value, **arrays merge across every scope** (so a lower scope can *add* to
`allowWrite`, `excludedCommands`, `allowRead`, `allowedDomains`). A `deny`
credential entry from any scope sticks — no scope can remove one another
scope added.

## Org rollout

Deliver `sandbox` keys through managed settings (MDM file, or server-managed
settings on Claude.ai):

```json
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "allowManagedReadPathsOnly": true,
    "allowManagedDomainsOnly": true
  }
}
```

- `failIfUnavailable` — a missing dependency (bubblewrap on Linux) stops
  Claude Code from starting instead of silently falling back to unsandboxed
  execution. Without this, a security gate degrades to a warning.
- `allowUnsandboxedCommands: false` — "strict sandbox mode". The model's
  `dangerouslyDisableSandbox` retry is ignored entirely; commands run
  sandboxed or are listed in `excludedCommands`.
- `allowManagedReadPathsOnly` / `allowManagedDomainsOnly` — otherwise the
  array-merge rule lets a developer widen read paths and domains locally.

Managed settings file locations: macOS
`/Library/Application Support/ClaudeCode/managed-settings.json`, Linux/WSL
`/etc/claude-code/managed-settings.json`, Windows
`C:\Program Files\ClaudeCode\`. Drop-ins in `managed-settings.d/*.json` merge
alphabetically after it.

The sandbox does **not** run on native Windows. Scope the policy to macOS and
Linux, or require WSL2 / a container for those hosts.

## What the sandbox does not cover

Be precise about this, because the gaps are where the remaining risk lives:

- **Bash only.** In-process tools — `Read`, `Edit`, `WebFetch`, `WebSearch` —
  and **every MCP tool** run outside it. `sandbox.credentials` blocks a
  sandboxed *command* from reading `~/.aws/credentials`; it does not stop the
  `Read` tool. Use permission `deny` rules for those:

  ```json
  {
    "permissions": {
      "deny": ["Read(//~/.ssh/**)", "Read(//~/.aws/**)", "Read(//**/.env)"]
    }
  }
  ```

  Note the prefix difference: permission rules use `//path` for absolute and
  `/path` for project-relative, while sandbox filesystem paths use ordinary
  conventions (`/tmp/build` is absolute). Getting these backwards is a common
  silent no-op.

- **Exfiltration via MCP.** A Slack or Jira tool call can carry a secret off
  the machine and no sandbox layer sees it. The guardrails `escapes.py` hook
  covers the obvious credential shapes here.

- **TLS contents**, by default (see Network above).

- **Unix sockets.** `allowUnixSockets` can hand over the host — allowing
  `/var/run/docker.sock` is equivalent to disabling everything.

- **`filesystem.disabled: true`** turns off the whole filesystem layer. With
  commands auto-allowed, a sandboxed command can then write `~/.bashrc`, a
  binary on `$PATH`, or `~/.claude/settings.json` and widen its own access on
  the next run. Only use it for workloads trusted not to escalate.

## Verifying, rather than assuming

An unloaded policy looks exactly like a permissive one. Always confirm:

- `/sandbox` → **Config** tab shows the *resolved* settings, including every
  protected path and denied-within-allowed entry. This is ground truth; the
  settings file is only an input to it.
- `/doctor` flags unreliable domain spellings and other config problems.
- For hooks specifically: hooks are only honored when the working directory is
  a **trusted** project directory. A fresh git worktree that has never been
  trusted silently skips hooks — permissions still load, hooks do not, and the
  session looks entirely normal.

## References

- `references/templates.md` — copy-paste policies for the common shapes
  (solo laptop, shared repo, CI, locked-down org).
- `references/failure-modes.md` — symptom → cause → fix for sandbox errors,
  and the silent no-ops worth knowing about.
