#!/usr/bin/env python3
"""Compute, publish, and gate the context cost of every plugin in this marketplace.

    python3 scripts/plugin_costs.py            # print the table
    python3 scripts/plugin_costs.py --write    # regenerate COSTS.md
    python3 scripts/plugin_costs.py --sync     # push cost + metadata into marketplace.json
    python3 scripts/plugin_costs.py --check    # assert budgets; exit 1 if over
    python3 scripts/plugin_costs.py --json     # machine-readable

Why this exists
---------------
Anthropic's plugin catalog publishes, for every official plugin, the tokens it
adds to a session -- `always_on` and `on_invoke`, broken down per component --
so someone browsing can decide whether it is worth the context before
installing. Private marketplaces get none of that: they are absent from the
catalog entirely. `claude plugin details` computes the same numbers locally,
but only for a plugin that is already installed, which is exactly too late to
inform the decision.

So this computes it from source, publishes it in COSTS.md, and gates it.

The cost model
--------------
Costs split by when they are paid:

  always_on   Every session, whether or not the plugin is used. This is the
              number that matters: it is a tax on unrelated work. For a skill,
              agent, or command it is the name plus the frontmatter
              description -- what the harness lists so the model knows the
              thing exists.

  on_invoke   Paid each time the component actually fires. For a skill that is
              the SKILL.md body; for an agent, its prompt.

  lazy        Files under a skill's references/ directory, read only if the
              skill follows the link. Reported for awareness, not budgeted --
              moving bulk from SKILL.md into references/ is the main lever for
              cutting on_invoke, and that should look like a win here.

Hooks, MCP servers and LSP servers add no model context. `claude plugin
details` labels hooks "harness-only"; they are executed, not read.

chars are exact and are what the budgets gate on. Tokens are an estimate, for
readability and for comparability with the official catalog -- which likewise
stores exact per-component `chars` and only estimates `tokens` at the plugin
level.

CHARS_PER_TOKEN and COMPONENT_OVERHEAD were fitted against `claude plugin
details` across all 14 plugins in this marketplace: worst case 3.8% off, mean
1.4%. Re-fit with --calibrate if the harness's own estimator changes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
BUDGETS = Path(__file__).resolve().parent / "cost-budgets.json"
# Measurements for plugins hosted in their own repos. Committed, not fetched at
# read time: --write and --sync are asserted byte-identical in CI, so measuring a
# remote live would turn this repo red whenever an unrelated repo was pushed to.
# Refresh it deliberately with --refresh-remote.
REMOTE_COSTS = Path(__file__).resolve().parent / "remote-costs.json"
COSTS_MD = ROOT / "COSTS.md"

CHARS_PER_TOKEN = 3.95
COMPONENT_OVERHEAD = 2  # framing the harness adds per listed component

REPO_URL = "https://github.com/ChristopherDavenport/christopherdavenport-marketplace"
AUTHOR = {"name": "Chris Davenport", "url": "https://github.com/ChristopherDavenport"}

# The cost prefix stamped onto each marketplace description, and the pattern that
# strips previous ones so --sync is idempotent. The trailing `+` matters: a bad
# merge or a hand-edit can leave a description double-stamped, and stripping only
# the outermost would re-prefix on top of the survivor and compound every run.
COST_PREFIX = re.compile(r"^(?:~[\d.]+k? tok always-on\.\s*)+")

# Key order for a synced entry. Fixed so regeneration produces no reordering
# noise in the diff; description last because it is by far the longest.
ENTRY_ORDER = ["name", "source", "category", "homepage", "author", "description"]

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Handles `key: value` and folded blocks."""
    m = FRONTMATTER.match(text)
    if not m:
        return {}, text
    raw, body = m.group(1), text[m.end():]
    out: dict[str, str] = {}
    key, buf = None, []
    for line in raw.split("\n"):
        head = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if head and not line.startswith((" ", "\t")):
            if key:
                out[key] = " ".join(buf).strip()
            key, val = head.group(1), head.group(2).strip()
            buf = [] if val in (">", "|", ">-", "|-", ">+", "|+") else [val]
        elif key:
            buf.append(line.strip())
    if key:
        out[key] = " ".join(buf).strip()
    return out, body


def component_costs(plugin_dir: Path) -> list[dict]:
    """Every context-bearing component in a plugin, with exact char counts."""
    found: list[dict] = []

    for skill_md in sorted(plugin_dir.glob("skills/*/SKILL.md")):
        fm, body = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        name = fm.get("name") or skill_md.parent.name
        refs = sorted((skill_md.parent / "references").glob("*.md"))
        found.append({
            "kind": "skill",
            "name": name,
            "chars": {
                "always_on": len(name) + len(fm.get("description", "")),
                "on_invoke": len(body),
            },
            "lazy_chars": sum(len(p.read_text(encoding="utf-8")) for p in refs),
            "lazy_files": len(refs),
        })

    for pattern, kind in (("agents/*.md", "agent"), ("commands/*.md", "command")):
        for path in sorted(plugin_dir.glob(pattern)):
            fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            name = fm.get("name") or path.stem
            found.append({
                "kind": kind,
                "name": name,
                "chars": {
                    "always_on": len(name) + len(fm.get("description", "")),
                    "on_invoke": len(body),
                },
                "lazy_chars": 0,
                "lazy_files": 0,
            })

    return found


def to_tokens(chars: int, n_components: int) -> int:
    if chars <= 0:
        return 0
    return round(chars / CHARS_PER_TOKEN + COMPONENT_OVERHEAD * n_components)


def harness_only(plugin_dir: Path) -> list[str]:
    """Components that execute rather than occupy context."""
    out = []
    if (plugin_dir / "hooks" / "hooks.json").exists():
        out.append("hooks")
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("mcpServers"):
            out.append("mcpServers")
        if data.get("lspServers"):
            out.append("lspServers")
    if (plugin_dir / ".mcp.json").exists() and "mcpServers" not in out:
        out.append("mcpServers")
    return out


def measure(plugin_dir: Path) -> dict:
    """The cost of one plugin directory, wherever it came from."""
    comps = component_costs(plugin_dir)
    always = sum(c["chars"]["always_on"] for c in comps)
    invoke = sum(c["chars"]["on_invoke"] for c in comps)
    return {
        "components": comps,
        "harness_only": harness_only(plugin_dir),
        "chars": {"always_on": always, "on_invoke": invoke},
        "lazy_chars": sum(c["lazy_chars"] for c in comps),
        "tokens": {
            "always_on": to_tokens(always, len(comps)),
            "on_invoke": to_tokens(invoke, len(comps)),
        },
    }


def load_remote_costs() -> dict:
    if not REMOTE_COSTS.exists():
        return {}
    return json.loads(REMOTE_COSTS.read_text(encoding="utf-8"))


MEASURED_KEYS = ("components", "harness_only", "chars", "lazy_chars", "tokens")


def collect() -> list[dict]:
    """Every plugin in the marketplace, local ones measured now and remote ones
    read from the committed cache. A remote with no cache entry is skipped —
    silently absent is better than a confident zero, and --refresh-remote fixes it."""
    entries = json.loads(MARKETPLACE.read_text(encoding="utf-8"))["plugins"]
    cached = load_remote_costs()
    plugins = []
    for entry in entries:
        source = entry.get("source")

        if isinstance(source, str):
            plugin_dir = (ROOT / source.lstrip("./")).resolve()
            if not plugin_dir.is_dir():
                continue
            path = source.lstrip("./")
            plugins.append({
                "name": entry["name"],
                "path": path,
                "homepage": f"{REPO_URL}/tree/main/{path}",
                "category": plugin_dir.parent.name,
                "remote": False,
                **measure(plugin_dir),
            })
            continue

        repo = source.get("repo") if isinstance(source, dict) else None
        cache = cached.get(entry["name"])
        if not repo or not cache:
            continue
        plugins.append({
            "name": entry["name"],
            "path": None,
            "homepage": f"https://github.com/{repo}",
            "category": entry.get("category") or "workflow",
            "remote": True,
            "repo": repo,
            "commit": cache.get("commit"),
            **{k: cache[k] for k in MEASURED_KEYS},
        })

    plugins.sort(key=lambda p: -p["tokens"]["always_on"])
    return plugins


def find_plugin_root(repo_dir: Path) -> Path | None:
    """Where the plugin manifest lives — repo root for both of ours, but a repo
    may nest it."""
    if (repo_dir / ".claude-plugin" / "plugin.json").exists():
        return repo_dir
    for cand in sorted(repo_dir.glob("*/.claude-plugin/plugin.json")):
        return cand.parent.parent
    return None


def refresh_remote(dry_run: bool = False) -> int:
    """Shallow-clone each remote plugin, measure it, record the result.

    The only part of this script that touches the network, and it is never run
    by CI. The recorded commit is what makes the cached number auditable: it
    says exactly which tree was measured.
    """
    import subprocess
    import tempfile

    entries = json.loads(MARKETPLACE.read_text(encoding="utf-8"))["plugins"]
    out: dict[str, dict] = {}
    for entry in entries:
        src = entry.get("source")
        if not isinstance(src, dict) or src.get("source") != "github" or not src.get("repo"):
            continue
        repo = src["repo"]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "r"
            clone = subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet",
                 f"https://github.com/{repo}.git", str(dest)],
                capture_output=True, text=True)
            if clone.returncode != 0:
                print(f"  FAIL {repo}: {clone.stderr.strip()}", file=sys.stderr)
                return 1
            sha = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                                 capture_output=True, text=True).stdout.strip()
            root_dir = find_plugin_root(dest)
            if root_dir is None:
                print(f"  FAIL {repo}: no .claude-plugin/plugin.json", file=sys.stderr)
                return 1
            m = measure(root_dir)
        out[entry["name"]] = {"repo": repo, "commit": sha, **m}
        print(f"  {entry['name']:<24}{m['tokens']['always_on']:>6} tok always-on"
              f"   @ {sha[:12]}")

    if not out:
        print("  no remote plugins in marketplace.json")
        return 0
    if not dry_run:
        REMOTE_COSTS.write_text(
            json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8")
        print(f"\nwrote {REMOTE_COSTS.relative_to(ROOT)} ({len(out)} remote plugins)")
    return 0


def sync_marketplace(plugins: list[dict], dry_run: bool = False) -> tuple[str, str]:
    """Stamp measured cost and browse metadata into marketplace.json.

    The marketplace browser has no cost field -- the schema defines none, and the
    catalog that carries `tokens` for official plugins is server-generated and
    contains only claude-plugins-official. So the number goes in `description`,
    which is the one field guaranteed to render.

    Stamping it there is free, and that is measured rather than assumed. Padding
    a description by ~4000 characters and re-running `claude plugin details`:

        marketplace.json description   193 tok -> 193 tok   (no change)
        plugin.json description        193 tok -> 193 tok   (no change)
        SKILL.md frontmatter           193 tok -> 1193 tok  (+chars/4)

    Only the skill/agent/command frontmatter feeds always-on. If that ever stops
    being true, this function is the thing that turns a free annotation into a
    per-session tax on every plugin at once.

    `category` and `homepage` are filled in at the same time. Both render in the
    browser and neither was set on any entry; official plugins set them on
    272/286 and 270/286 respectively.
    """
    original = MARKETPLACE.read_text(encoding="utf-8")
    data = json.loads(original)
    by_name = {p["name"]: p for p in plugins}

    for entry in data["plugins"]:
        measured = by_name.get(entry["name"])
        desc = COST_PREFIX.sub("", entry.get("description", "")).strip()

        if measured:
            entry["description"] = f"~{measured['tokens']['always_on']} tok always-on. {desc}"
            entry["category"] = measured["category"]
            entry["homepage"] = measured["homepage"]
        else:
            # No measurement: a remote whose cache entry is missing. Claim
            # nothing rather than stamp a zero.
            entry["description"] = desc
            src = entry.get("source")
            if isinstance(src, dict) and src.get("repo"):
                entry.setdefault("homepage", f"https://github.com/{src['repo']}")
        entry["author"] = AUTHOR

        for key in list(entry):
            if key not in ENTRY_ORDER:
                ENTRY_ORDER.append(key)
        reordered = {k: entry[k] for k in ENTRY_ORDER if k in entry}
        entry.clear()
        entry.update(reordered)

    # ensure_ascii=False keeps em-dashes as em-dashes; a previous round-trip
    # escaped every one of them to — across the whole file.
    updated = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if not dry_run:
        MARKETPLACE.write_text(updated, encoding="utf-8")
    return original, updated


def load_budgets() -> dict:
    if not BUDGETS.exists():
        return {"default_always_on": None, "total_always_on": None, "plugins": {}}
    return json.loads(BUDGETS.read_text(encoding="utf-8"))


def check(plugins: list[dict]) -> int:
    b = load_budgets()
    default = b.get("default_always_on")
    per = b.get("plugins", {})
    failures = []

    for p in plugins:
        cap = per.get(p["name"], default)
        got = p["tokens"]["always_on"]
        if cap is None:
            continue
        mark = "FAIL" if got > cap else "ok"
        if got > cap:
            failures.append(
                f'{p["name"]}: always-on {got} tok > budget {cap}. Either trim the '
                f"frontmatter descriptions or raise the budget in "
                f"{BUDGETS.relative_to(ROOT)} — deliberately, with the diff visible."
            )
        print(f"  {mark:<4}  {p['name']:<24}{got:>6} tok   cap {cap}")

    total_cap = b.get("total_always_on")
    total = sum(p["tokens"]["always_on"] for p in plugins)
    if total_cap is not None:
        mark = "FAIL" if total > total_cap else "ok"
        print(f"\n  {mark:<4}  {'MARKETPLACE TOTAL':<24}{total:>6} tok   cap {total_cap}")
        if total > total_cap:
            failures.append(
                f"marketplace total {total} tok > budget {total_cap}. Every plugin "
                "here is individually reasonable and the sum is not."
            )

    print()
    if failures:
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("  Within budget.")
    return 0


def render_markdown(plugins: list[dict]) -> str:
    total_a = sum(p["tokens"]["always_on"] for p in plugins)
    total_i = sum(p["tokens"]["on_invoke"] for p in plugins)
    b = load_budgets()

    lines = [
        "# Context cost",
        "",
        "What each plugin costs you in context, so you can decide before installing.",
        "",
        "**Generated — do not edit.** Run `python3 scripts/plugin_costs.py --write`.",
        "",
        "| Plugin | Category | Always-on | On-invoke | Lazy | Components |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for p in plugins:
        named = ", ".join(f"{c['name']}" for c in p["components"])
        harness = "/".join(p["harness_only"])
        # A plugin can be all harness and no context — an MCP server with no
        # skills costs nothing always-on. "— + mcpServers" reads as a gap; the
        # bare harness list reads as the fact.
        comps = named or harness or "—"
        extra = f" + {harness}" if named and harness else ""
        lazy = f"{p['lazy_chars'] // 1000}k" if p["lazy_chars"] >= 1000 else (
            str(p["lazy_chars"]) if p["lazy_chars"] else "—")
        # Remote plugins link out to their own repo and are marked, because their
        # number is a cached measurement of another tree rather than of this one.
        target = p["path"] if not p["remote"] else p["homepage"]
        mark = " †" if p["remote"] else ""
        lines.append(
            f"| [`{p['name']}`]({target}){mark} | {p['category']} "
            f"| {p['tokens']['always_on']} | {p['tokens']['on_invoke']} | {lazy} "
            f"| {comps}{extra} |"
        )
    remotes = [p for p in plugins if p["remote"]]
    lines += [
        f"| **All {len(plugins)} together** | | **{total_a}** | {total_i} | | |",
        "",
    ]
    if remotes:
        lines += [
            "† Lives in its own repo. Measured at "
            + ", ".join(f"[`{p['name']}`]({p['homepage']}/tree/{(p['commit'] or '')[:7]})"
                        for p in remotes)
            + " and cached in [`scripts/remote-costs.json`](scripts/remote-costs.json);"
              " refresh with `python3 scripts/plugin_costs.py --refresh-remote`.",
            "",
        ]
    lines += [
        "## Reading this",
        "",
        "**Always-on** is the number that matters. It is paid on every session whether",
        "or not you use the plugin — a tax on unrelated work — and it is the sum of each",
        "component's name and description, which the harness lists so the model knows the",
        f"component exists. Enable every plugin here and you spend ~{total_a} tokens",
        "before typing anything.",
        "",
        "**On-invoke** is paid each time a skill or agent actually fires, and only then.",
        "A large on-invoke next to a small always-on is a good shape: it means the plugin",
        "stays out of the way until you need it.",
        "",
        "**Lazy** is the `references/` material a skill reads only if it follows the link.",
        "It is not budgeted. Moving bulk out of `SKILL.md` into `references/` cuts",
        "on-invoke and should read as a win.",
        "",
        "Hooks, MCP servers and LSP servers add no model context — they are executed,",
        "not read. `claude plugin details` labels them harness-only.",
        "",
        "## Why the number is also in each description",
        "",
        "Nothing reads this file. The marketplace schema defines no cost or token",
        "property, and the catalog that carries `tokens` for official plugins is",
        "generated by Anthropic and contains only `claude-plugins-official`.",
        "`claude plugin details` computes the same numbers locally but refuses a plugin",
        "that is not installed yet — which is exactly when you want them.",
        "",
        "So the always-on figure is stamped into each entry's `description` in",
        "`marketplace.json`, which is the one field the browser is guaranteed to render.",
        "",
        "Stamping it there is free, and that is measured rather than assumed — padding",
        "a description by ~4000 characters and re-reading `claude plugin details`:",
        "",
        "| Field padded | Always-on |",
        "| --- | --- |",
        "| `marketplace.json` description | 193 → 193, unchanged |",
        "| `plugin.json` description | 193 → 193, unchanged |",
        "| `SKILL.md` frontmatter description | 193 → 1193 |",
        "",
        "Only the skill, agent, and command frontmatter feeds always-on. `--sync` keeps",
        "the stamp in step with the measurement and CI fails if they drift, because a",
        "stale number shown at the moment of the decision is worse than no number.",
        "",
        "## Budgets",
        "",
        "`scripts/plugin_costs.py --check` fails when a plugin exceeds its always-on",
        "budget, so growth has to be deliberate rather than accidental. Budgets live in",
        "[`scripts/cost-budgets.json`](scripts/cost-budgets.json): default",
        f"{b.get('default_always_on')} tokens per plugin and {b.get('total_always_on')}",
        "across the marketplace, with per-plugin overrides for the ones that have",
        "earned more.",
        "",
        "## Accuracy",
        "",
        "Character counts are exact and are what the budgets gate on. Tokens are",
        f"estimated at {CHARS_PER_TOKEN} chars/token plus {COMPONENT_OVERHEAD} tokens of",
        "framing per component — fitted against `claude plugin details` across all",
        "plugins here, worst case 3.8% off, mean 1.4%.",
        "",
        "This mirrors how Anthropic's own catalog reports it: exact per-component",
        "`chars`, estimated `tokens` at the plugin level. The catalog covers official",
        "plugins only, which is why this file exists.",
        "",
    ]
    return "\n".join(lines)


def print_table(plugins: list[dict]) -> None:
    print(f"{'plugin':<24}{'always':>8}{'invoke':>9}{'lazy':>8}  components")
    for p in plugins:
        print(f"{p['name']:<24}{p['tokens']['always_on']:>8}{p['tokens']['on_invoke']:>9}"
              f"{p['lazy_chars']:>8}  {len(p['components'])}")
    print(f"{'TOTAL':<24}{sum(p['tokens']['always_on'] for p in plugins):>8}"
          f"{sum(p['tokens']['on_invoke'] for p in plugins):>9}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="regenerate COSTS.md")
    g.add_argument("--sync", action="store_true",
                   help="stamp cost + category/homepage/author into marketplace.json")
    g.add_argument("--check", action="store_true", help="assert budgets; exit 1 if over")
    g.add_argument("--json", action="store_true", help="machine-readable output")
    g.add_argument("--refresh-remote", action="store_true",
                   help="clone remote plugins and re-record their cost (network)")
    args = ap.parse_args()

    if args.refresh_remote:
        return refresh_remote()

    plugins = collect()
    if not plugins:
        print("FATAL: no plugins found in marketplace.json", file=sys.stderr)
        return 70

    if args.json:
        print(json.dumps({"plugins": plugins}, indent=2))
        return 0
    if args.check:
        return check(plugins)
    if args.write:
        COSTS_MD.write_text(render_markdown(plugins), encoding="utf-8")
        print(f"wrote {COSTS_MD.relative_to(ROOT)} ({len(plugins)} plugins)")
        return 0
    if args.sync:
        before, after = sync_marketplace(plugins)
        n = len(json.loads(after)["plugins"])
        print(f"synced {MARKETPLACE.relative_to(ROOT)} ({n} entries)"
              + ("" if before != after else " — already up to date"))
        return 0

    print_table(plugins)
    return 0


if __name__ == "__main__":
    sys.exit(main())
