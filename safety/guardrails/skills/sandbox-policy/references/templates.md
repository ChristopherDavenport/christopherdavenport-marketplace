# Policy templates

Four shapes, increasing in strictness. Each is complete — copy the whole
block, don't merge fragments across templates. Every one of these is validated
by `evals/guardrails/run.sh`, which parses them out of this file, so keep the
fenced blocks and their `<!-- template: NAME -->` markers intact.

Where a template says it must live in a particular settings file, that is not
style advice — several keys are ignored from the wrong scope (see the scope
table in `SKILL.md`).

---

## 1. Solo laptop — sensible default

`~/.claude/settings.json`. Sandbox on, credentials blocked, nothing else
assumed about the project.

<!-- template: solo -->
```json
{
  "sandbox": {
    "enabled": true,
    "credentials": {
      "files": [
        { "path": "~/.aws", "mode": "deny" },
        { "path": "~/.ssh", "mode": "deny" },
        { "path": "~/.config/gcloud", "mode": "deny" },
        { "path": "~/.kube/config", "mode": "deny" },
        { "path": "~/.npmrc", "mode": "deny" }
      ],
      "envVars": [
        { "name": "GITHUB_TOKEN", "mode": "deny" },
        { "name": "GH_TOKEN", "mode": "deny" },
        { "name": "NPM_TOKEN", "mode": "deny" },
        { "name": "ANTHROPIC_API_KEY", "mode": "deny" },
        { "name": "AWS_SECRET_ACCESS_KEY", "mode": "deny" }
      ]
    }
  },
  "permissions": {
    "deny": [
      "Read(//~/.ssh/**)",
      "Read(//~/.aws/**)",
      "Read(//~/.config/gcloud/**)",
      "Read(//**/.env)",
      "Read(//**/.env.*)"
    ]
  }
}
```

The `permissions.deny` block is not redundant with `sandbox.credentials`:
the sandbox entries stop a *sandboxed command* from reading those files, the
permission rules stop the **`Read` tool**, which never enters the sandbox.

Trade-off to know: `envVars` `deny` unsets the variable, so `gh` and `npm`
stop authenticating inside the sandbox. If that bites, switch those two
entries to `mask` (see template 4) rather than deleting them.

---

## 2. Shared repo — project-scoped additions

`.claude/settings.json`, committed. Adds what *this* repo's build needs.
Array keys merge with the user-scope template above rather than replacing it.

<!-- template: repo -->
```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "allowWrite": ["~/.cache/go-build", "~/.npm", "./dist", "./.next"]
    },
    "network": {
      "allowedDomains": [
        "github.com",
        "*.githubusercontent.com",
        "registry.npmjs.org",
        "proxy.golang.org",
        "sum.golang.org"
      ]
    },
    "excludedCommands": ["docker *"]
  }
}
```

`./dist` and `./.next` resolve against the **project root** here. The same
strings in `~/.claude/settings.json` would resolve against `~/.claude` — one
of the quieter footguns in the system.

Keep `excludedCommands` to things that genuinely cannot be sandboxed. Every
entry is a command that runs with no isolation at all; `allowWrite` is almost
always the better answer for "it needs to write somewhere".

---

## 3. Headless / CI — no prompts available

No human to answer a domain prompt, so the allowlist has to be complete and
unlisted hosts must fail rather than hang. `strictAllowlist` is ignored from
project settings, so deliver this via `--settings` or user scope on the runner.

<!-- template: ci -->
```json
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "network": {
      "strictAllowlist": true,
      "allowedDomains": [
        "api.anthropic.com",
        "github.com",
        "registry.npmjs.org"
      ]
    },
    "credentials": {
      "envVars": [
        { "name": "AWS_SECRET_ACCESS_KEY", "mode": "deny" },
        { "name": "NPM_TOKEN", "mode": "deny" }
      ]
    }
  }
}
```

`failIfUnavailable` matters most here. On a runner image missing bubblewrap,
the default behaviour is a warning and unsandboxed execution — a security gate
that silently becomes a no-op is worse than no gate, because the CI log still
looks green.

---

## 4. Locked-down org — managed settings

`/Library/Application Support/ClaudeCode/managed-settings.json` (macOS),
`/etc/claude-code/managed-settings.json` (Linux/WSL), or server-managed
settings on Claude.ai. Developers cannot override the boolean keys, and the
two `allowManaged*Only` keys stop them widening the arrays.

<!-- template: managed -->
```json
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "allowManagedReadPathsOnly": true,
    "allowManagedDomainsOnly": true,
    "filesystem": {
      "allowRead": ["~/", "/usr", "/opt", "/etc"],
      "denyRead": ["~/.ssh", "~/.aws", "~/.config/gcloud"]
    },
    "network": {
      "tlsTerminate": true,
      "allowedDomains": [
        "api.anthropic.com",
        "github.com",
        "*.githubusercontent.com",
        "registry.npmjs.org"
      ]
    },
    "credentials": {
      "files": [
        { "path": "~/.ssh", "mode": "deny" },
        { "path": "~/.aws", "mode": "deny" }
      ],
      "envVars": [
        {
          "name": "GH_TOKEN",
          "mode": "mask",
          "injectHosts": ["api.github.com"]
        },
        { "name": "AWS_SECRET_ACCESS_KEY", "mode": "deny" }
      ]
    },
    "excludedCommands": ["docker *"]
  }
}
```

Notes specific to this one:

- `allowManagedReadPathsOnly` makes the `allowRead` list authoritative, so it
  has to be complete enough for builds to run — that list is the whole
  readable filesystem for sandboxed commands. Widen it deliberately after
  testing, not preemptively.
- The `mask` entry keeps `gh` working while never handing the real token to
  the command: it sees a sentinel, and the proxy substitutes the real value
  only on requests to `api.github.com`. This is why `tlsTerminate` is on —
  without it the sentinel goes to GitHub unchanged and auth fails. Claude Code
  reports that misconfiguration at startup.
- Because managed settings configure `sandbox.filesystem` and list a `deny`
  credentials entry, `filesystem.disabled` becomes managed-only — developers
  can't switch filesystem isolation off.
- `excludedCommands` has **no** managed-only lockdown. Developers can append.
  Keep the list narrow and treat it as advisory rather than a boundary.
