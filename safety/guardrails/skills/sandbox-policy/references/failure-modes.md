# Failure modes

Two kinds, and the second kind is the dangerous one.

**Loud failures** announce themselves: a command errors, the sandbox appends
the violation to the output, you fix the policy. Annoying, self-correcting.

**Silent no-ops** are a rule that looks right in a settings file and does
nothing. The session behaves exactly as if you'd written no policy at all, and
nothing anywhere reports a problem. Every one of these has bitten someone.

---

## Silent no-ops

### A key in a scope that ignores it

`filesystem.disabled`, `strictAllowlist`, `allowAppleEvents`, `mask` credential
entries, `tlsTerminate`, `allowPlaintextInject`, `awsPairs`, and `sigv4` are
honored **only** from user settings, managed settings, or `--settings`. Put any
of them in a repo's `.claude/settings.json` or `.claude/settings.local.json`
and they are ignored — no warning.

**Check:** `/sandbox` → Config tab shows resolved values. If what you wrote
isn't there, the scope is wrong.

### Relative paths resolving somewhere else

`./output` or `.` resolves relative to the **project root** in project
settings, and relative to **`~/.claude`** in user settings. The canonical
version of this bug:

```json
// in ~/.claude/settings.json -- does NOT do what it looks like
{ "sandbox": { "filesystem": { "denyRead": ["~/"], "allowRead": ["."] } } }
```

`.` is `~/.claude`, so the home-directory deny stands and project files become
unreadable. Correct placement is project settings; or write the absolute path.

### Permission-rule path prefixes reversed

Permission rules use `//path` for **absolute** and `/path` for
**project-relative**. Sandbox filesystem paths use ordinary conventions where
`/tmp/build` is absolute. So `Read(/~/.ssh/**)` — one slash — is a
project-relative rule that matches nothing, while looking like it guards your
keys. Absolute is `Read(//~/.ssh/**)`.

### Plugin `settings.json` carrying policy

A plugin's root `settings.json` supports **only** `agent` and
`subagentStatusLine`. A `permissions` or `sandbox` key there is dropped at load
time. This is why the guardrails plugin ships a *configurator* rather than a
policy — policy has to land in a real settings file.

### Hooks skipped in an untrusted directory

Hooks are only honored when the working directory is a **trusted** project
directory. A freshly created git worktree that has never been trusted silently
skips them — permissions still load, hooks do not, the session looks normal.

**Check:** run `/guardrails-doctor`, or confirm audit records are being
written.

### Sandbox unavailable, falling back quietly

By default, if the sandbox can't start (missing bubblewrap on Linux,
unsupported platform), Claude Code warns once and runs **unsandboxed**. In CI
that warning scrolls past and the run looks green.

**Fix:** `"failIfUnavailable": true`.

### An array key widened from a lower scope

Array keys — `allowWrite`, `allowRead`, `allowedDomains`, `excludedCommands` —
**merge across every scope** rather than being overridden. A locked-down
managed policy can be widened by a developer's user settings unless you set
`allowManagedReadPathsOnly` and `allowManagedDomainsOnly`.

`excludedCommands` has no such lockdown at all. It is always appendable, so
treat it as a compatibility list, not a security boundary.

### Ambiguous IPv6 entries dropped

An unbracketed multi-colon entry like `::1:443` parses two ways. In an
**allow** list Claude Code never widens beyond what you wrote and may drop the
entry entirely. Write `"[::1]:443"`.

**Check:** `/doctor` names the affected entries.

---

## Loud failures

| Symptom | Cause | Fix |
|---|---|---|
| `Read-only file system` (Linux/WSL) or a write denial on a path you expected to work | Outside the working directory, or a protected path | Add to `filesystem.allowWrite` — unless it's a protected path, which nothing lifts |
| A write to `/tmp/...` is denied although `/tmp` is in `allowWrite` | `/tmp` is special-cased: the sandbox hands out a session temp dir and denies the rest. Not the `/private/tmp` symlink — both spellings are denied, while sibling `allowWrite` paths in the same policy work | Write to `$TMPDIR` (already repointed into the session dir). Drop the `/tmp` entry; it reads like protection and grants nothing |
| A nested `claude -p` refuses to start: `Sandbox is required but failed to initialize: EPERM ... listen '/tmp/claude-<uid>/srt-mux-*.sock'` | A sandboxed session cannot create its control socket inside the outer session's temp dir | Expected with `failIfUnavailable: true`, and the setting is working — it refused rather than silently running unsandboxed. Run nested sessions from an unsandboxed parent |
| `git merge` / `git checkout` fails with `unable to unlink old` | Git needs to replace a file under a protected path or a `denyWrite` entry | Approve the unsandboxed retry, run the git command in another terminal, or add that command to `excludedCommands` if it recurs |
| TLS verification failures from `gh`, `gcloud`, `terraform` on macOS (`x509: OSStatus -26276`) | Go's verifier needs `com.apple.trustd.agent`; the sandbox denies the mach lookup. `curl` to the same host still returns 200, so it reads as a credential fault | Add to `excludedCommands` **with a glob** — `"gh *"`, not `"gh"`. With a MITM proxy + custom CA, `network.enableWeakerNetworkIsolation` instead |
| An `excludedCommands` entry appears to do nothing | The entry is a prefix glob over the whole tool call. `"gh"` misses `gh api …`; `"git fetch *"` misses `git -C /p fetch`; every compound (`cd x && …`), loop body and `bash script.sh` misses too | List each real form (`"gh *"`, `"git fetch *"`, `"git -C * fetch *"`) and issue network commands as standalone tool calls. Never a leading wildcard — see below |
| git over SSH fails with `This proxy requires authentication, and this client did not offer an authentication method` | macOS only. The injected `ProxyCommand` uses Apple's `nc`, which has no SOCKS-auth flag, against an auth-requiring proxy | Exempt git's network subcommands, or move to HTTPS. Not fixable from config: `GIT_SSH_COMMAND` is injected and beats `core.sshCommand` and `settings.env`. Note `~/.ssh` is also read-denied, so a fixed ProxyCommand alone still leaves no loadable key |
| A masked env var still fails auth over **git HTTPS**, though `curl` with a `Bearer` header works | Git authenticates with HTTP Basic, which base64-encodes `user:token`. The proxy substitutes literal sentinel strings and cannot find one inside base64 | Don't rely on `mask` for git. Exempt git's network subcommands, or put the token in a literal header the proxy can see |
| A GUI keychain-unlock prompt appears repeatedly, or `fatal: failed to get/store: 100001` | A credential helper is reaching the macOS keychain from inside the sandbox. Homebrew's git ships a **system** gitconfig setting `credential.helper = osxkeychain`, and git runs every configured helper — a narrower scoped helper does not replace it | Check `git config --show-origin --get-all credential.helper`. Use a transport that consults no helper (SSH), or clear the helper for that host before adding your own |
| macOS error `-600` from `open`, `osascript`, or a browser auth flow | Apple Events blocked | Prefer `excludedCommands` for the one command; `allowAppleEvents: true` works but removes code-execution isolation |
| `docker` commands fail | Fundamentally incompatible with the sandbox | `"excludedCommands": ["docker *"]` |
| Auth fails with a masked credential, no leak | `network.tlsTerminate` not set, so the proxy can't substitute and the sentinel reached the server | Set `tlsTerminate: true` in user or managed scope. Claude Code also reports this at startup |
| AWS requests rejected with a signature error | Only the secret key was masked, so SigV4 was signed with a placeholder the proxy can't detect | Mask `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` **together** |
| A command needs a host and there's no one to approve it | Headless run, no pre-allowed domain | Pre-allow in `network.allowedDomains`; set `strictAllowlist: true` so it fails fast instead of hanging |
| Windows binaries won't launch under WSL2 | Launch goes over a Unix socket the seccomp filter blocks | `allowAllUnixSockets`, or put the command in `excludedCommands` |

---

## Escalation risks worth refusing

These are configurations that technically work and quietly hand back
everything the sandbox was protecting:

- **`allowUnixSockets` with `/var/run/docker.sock`** — the Docker socket is
  root on the host. This is not a partial relaxation, it's a full bypass.
- **`filesystem.disabled: true` with commands auto-allowed** — a sandboxed
  command can write `~/.bashrc`, a binary on `$PATH`, or
  `~/.claude/settings.json`, and widen its own access on the next run.
  Network isolation alone does not contain that.
- **`allowAppleEvents: true`** — sandboxed commands can launch other
  applications *unsandboxed*, with no prompt.
- **A broad `allowWrite` next to a broad `allowedDomains`** — the two layers
  hold each other up. Without network isolation a compromised agent
  exfiltrates the files it can read; without filesystem isolation it
  backdoors its way to network access. Widening one undoes the other, so
  check both sides whenever you relax either.
