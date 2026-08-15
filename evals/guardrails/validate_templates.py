#!/usr/bin/env python3
"""Validate the policy templates the sandbox-policy skill ships.

The templates are the plugin's actual product now -- someone will copy one
into a settings file and trust it. Two things can rot them: JSON that no
longer parses, and a well-meaning edit that quietly widens the policy. The
first is caught by parsing; the second needs assertions, because a template
that grants more access still parses fine and still looks responsible.

Each check states what it is protecting against, since "assert not disabled"
is meaningless in a diff six months from now.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = (
    HERE.parent.parent
    / "safety/guardrails/skills/sandbox-policy/references/templates.md"
)

BLOCK = re.compile(
    r"<!--\s*template:\s*([\w-]+)\s*-->\s*```json\n(.*?)\n```",
    re.DOTALL,
)

EXPECTED = {"solo", "repo", "ci", "managed"}

failures: list[str] = []
checks = 0


def check(name: str, condition: bool, why: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(f"{name}: {why}")


def main() -> int:
    if not TEMPLATES.exists():
        print(f"FATAL: {TEMPLATES} not found", file=sys.stderr)
        return 70

    text = TEMPLATES.read_text()
    found = {name: body for name, body in BLOCK.findall(text)}

    missing = EXPECTED - found.keys()
    if missing:
        print(f"FATAL: templates missing markers: {sorted(missing)}", file=sys.stderr)
        return 1

    parsed: dict[str, dict] = {}
    for name, body in found.items():
        try:
            parsed[name] = json.loads(body)
        except json.JSONDecodeError as e:
            failures.append(f"{name}: does not parse as JSON ({e})")

    for name, cfg in parsed.items():
        sb = cfg.get("sandbox", {})

        check(name, sb.get("enabled") is True,
              "sandbox.enabled must be true -- a template that ships the "
              "sandbox off is worse than no template, it looks like coverage")

        check(name, sb.get("filesystem", {}).get("disabled") is not True,
              "filesystem.disabled turns off the whole filesystem layer and "
              "lets a command widen its own access on the next run")

        check(name, sb.get("allowAppleEvents") is not True,
              "allowAppleEvents lets sandboxed commands launch other apps "
              "unsandboxed with no prompt")

        socks = sb.get("network", {}).get("allowUnixSockets", [])
        check(name, not any("docker.sock" in str(s) for s in socks),
              "allowing docker.sock is a full host bypass, not a relaxation")

        # Credential entries must use a mode the harness recognises. An
        # unknown mode is stripped at load, so a typo silently removes the
        # protection while the file still reads as if it were there.
        creds = sb.get("credentials", {})
        for group in ("files", "envVars"):
            for entry in creds.get(group, []):
                key = entry.get("path") or entry.get("name") or "<unnamed>"
                check(name, entry.get("mode") in ("deny", "mask"),
                      f"credentials.{group} entry {key!r} has mode "
                      f"{entry.get('mode')!r}; unknown modes are stripped at load")

        # mask needs the proxy to terminate TLS, or the sentinel reaches the
        # server unchanged and auth fails -- a broken template, not a leak.
        masks = [e for g in ("files", "envVars") for e in creds.get(g, [])
                 if e.get("mode") == "mask"]
        if masks:
            check(name, sb.get("network", {}).get("tlsTerminate") is True,
                  "template uses credential masking without network."
                  "tlsTerminate; masking cannot work without it")

        # excludedCommands entries run with no isolation whatsoever, and the
        # key has no managed-only lockdown. Keep the shipped lists tiny.
        excluded = sb.get("excludedCommands", [])
        check(name, len(excluded) <= 3,
              f"excludedCommands has {len(excluded)} entries; each one runs "
              "outside the sandbox entirely, so a shipped default should be "
              "minimal")

    # Template-specific guarantees, i.e. the reason each one exists at all.
    ci = parsed.get("ci", {}).get("sandbox", {})
    check("ci", ci.get("failIfUnavailable") is True,
          "without failIfUnavailable a CI runner missing bubblewrap runs "
          "unsandboxed and still reports green")
    check("ci", ci.get("allowUnsandboxedCommands") is False,
          "headless runs must not allow the dangerouslyDisableSandbox retry")
    check("ci", ci.get("network", {}).get("strictAllowlist") is True,
          "with no human to answer a domain prompt, an unlisted host must "
          "fail rather than block")

    managed = parsed.get("managed", {}).get("sandbox", {})
    for key in ("failIfUnavailable", "allowManagedReadPathsOnly",
                "allowManagedDomainsOnly"):
        check("managed", managed.get(key) is True,
              f"{key} missing -- array keys merge across scopes, so without "
              "the managed-only locks a developer can widen the policy")
    check("managed", managed.get("allowUnsandboxedCommands") is False,
          "an org policy that permits the escape hatch is advisory")

    solo = parsed.get("solo", {}).get("sandbox", {})
    check("solo", bool(solo.get("credentials", {}).get("files")),
          "the sandbox default is that the entire computer is readable; a "
          "baseline template that does not block credential files leaves the "
          "gap it exists to close")
    check("solo", bool(parsed.get("solo", {}).get("permissions", {}).get("deny")),
          "sandbox.credentials does not cover the Read tool; the baseline "
          "needs permission deny rules too")

    for f in failures:
        print(f"  \033[31mFAIL\033[0m  {f}")
    print(f"\n  templates: {checks - len(failures)}/{checks} checks passed "
          f"across {len(parsed)} templates")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
