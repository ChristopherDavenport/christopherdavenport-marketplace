#!/usr/bin/env python3
"""Assert every plugin manifest in this marketplace can actually load.

Lives under evals/guardrails/ because guardrails is the plugin that ships hooks
and the plugin this caught, but it scans the whole marketplace: the hazard
belongs to the manifest format, not to any one plugin.

The hazard it exists for
------------------------
`hooks/hooks.json` is loaded automatically by convention. A manifest that ALSO
declares `"hooks": "./hooks/hooks.json"` makes the harness load the same file
twice, and it refuses:

    Hook load failed: Duplicate hooks file detected: ./hooks/hooks.json
    resolves to already-loaded file ... The standard hooks/hooks.json is
    loaded automatically, so manifest.hooks should only reference additional
    hook files.

The whole plugin then fails to load. Nothing else in this repo notices:
`claude plugin validate --strict` passes on the manifest, and the hook eval
invokes escapes.py directly rather than through the plugin loader, so it passes
too. The plugin was shipped broken and both green checks agreed it was fine.

That is the exact failure this marketplace's safety plugin exists to prevent --
an unloaded guard is indistinguishable from a permissive one -- so it gets a
check rather than a note.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTO_LOADED = {"hooks/hooks.json", "./hooks/hooks.json"}

# Manifest keys whose value is a path the harness also discovers by convention.
# Declaring one of these explicitly is the duplicate-load bug.
CONVENTIONAL = {"hooks": AUTO_LOADED}


def norm(value: str) -> str:
    return value.strip().lstrip("./")


def check(manifest: Path) -> list[str]:
    rel = manifest.relative_to(ROOT)
    try:
        data = json.loads(manifest.read_text())
    except json.JSONDecodeError as exc:
        return [f"{rel}: invalid JSON ({exc})"]

    problems = []
    for key, auto in CONVENTIONAL.items():
        value = data.get(key)
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        for v in values:
            if not isinstance(v, str):
                continue
            if v in auto or norm(v) in {norm(a) for a in auto}:
                target = manifest.parent.parent / norm(v)
                if target.exists():
                    problems.append(
                        f'{rel}: declares "{key}": "{v}", which the harness already '
                        f"loads by convention -- the plugin will fail to load with "
                        f'"Duplicate hooks file detected". Remove the key.'
                    )
    return problems


def main() -> int:
    manifests = sorted(
        p for p in ROOT.glob("*/*/.claude-plugin/plugin.json") if ".git" not in p.parts
    )
    if not manifests:
        print("  FATAL: no plugin manifests found", file=sys.stderr)
        return 70

    problems = []
    for m in manifests:
        problems.extend(check(m))

    for m in manifests:
        name = m.parent.parent.name
        bad = any(str(m.relative_to(ROOT)) in p for p in problems)
        mark = "\033[31mFAIL\033[0m" if bad else "\033[32mPASS\033[0m"
        print(f"  {mark}  {name}")

    print()
    if problems:
        print(f"  manifests: {len(manifests) - len(problems)}/{len(manifests)} loadable")
        for p in problems:
            print(f"    {p}", file=sys.stderr)
        return 1

    print(f"  manifests: {len(manifests)}/{len(manifests)} loadable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
