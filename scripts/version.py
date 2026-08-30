#!/usr/bin/env python3
"""One version for the whole repo, stamped by CI on merge.

    python3 scripts/version.py              # print the current version
    python3 scripts/version.py --next       # print the version the next release would use
    python3 scripts/version.py --release    # compute the next version and stamp it everywhere
    python3 scripts/version.py --set X.Y.Z  # stamp a specific version everywhere
    python3 scripts/version.py --check      # report manifests that disagree; exit 1 on drift

Why this exists
---------------
Every plugin here used to carry its own version, bumped by hand by whoever --
or whatever -- last edited it. Nothing enforced that and nothing did it: the
manifests sat at 0.1.x while the skills underneath them were rewritten, and no
tag or release was ever cut. A version nobody maintains is worse than none,
because it still reads as a claim about what changed.

So version is a property of the repo, not of a plugin, and merging is what
publishes it. Whoever edits a skill edits the skill and stops; the release job
on main computes the next version, stamps it into every manifest, tags it and
cuts the release. There is nothing left to remember.

Dropping the field instead was the other option, and it is not available:
`claude plugin validate --strict` warns on a plugin manifest with no version
and asks for semver.

The scheme
----------
CalVer, shaped so it is also valid semver:

    YYYY . MMDD . N     2026.829.0    first release on 29 Aug 2026
                        2026.829.1    second release that day
                        2026.903.0    next one, 3 Sep
                        2027.104.0    4 Jan 2027

MMDD carries no leading zero -- semver forbids one -- and still orders
correctly as an integer, since 104 < 829 < 1103. Dates answer the only
question a version can honestly answer for a repo of skills, which is how
fresh this is, and they never require anyone to rule on whether an edit to a
reference file was breaking.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "package.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"

VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
FIELD_RE = re.compile(r'"version"\s*:\s*"[^"]*"')


def manifests() -> list[Path]:
    """Everything that carries the version, in a stable order.

    The glob is the layout (category/plugin/.claude-plugin/plugin.json), and
    the marketplace entries are the backstop: a plugin listed there but living
    somewhere else on disk would otherwise be stamped by nobody, which is the
    exact failure this script exists to remove.
    """
    found = {PACKAGE_JSON, MARKETPLACE}
    found |= set(ROOT.glob("*/*/.claude-plugin/plugin.json"))
    for entry in json.loads(MARKETPLACE.read_text(encoding="utf-8"))["plugins"]:
        source = entry.get("source")
        if isinstance(source, str):
            path = ROOT / source.lstrip("./") / ".claude-plugin" / "plugin.json"
            if path.is_file():
                found.add(path)
    return sorted(found)


def parse(version: str | None) -> tuple[int, int, int] | None:
    m = VERSION_RE.match(version or "")
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def read_version(path: Path) -> str | None:
    return json.loads(path.read_text(encoding="utf-8")).get("version")


def current() -> str | None:
    return read_version(PACKAGE_JSON)


def tagged() -> list[tuple[int, int, int]]:
    """Versions already tagged. Absent git, or a shallow clone with no tags,
    this is empty and package.json alone decides -- which is why the release
    job checks out with fetch-depth: 0."""
    try:
        out = subprocess.run(["git", "tag", "--list", "v*"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return [(int(m[1]), int(m[2]), int(m[3]))
            for m in (TAG_RE.match(t) for t in out.split()) if m]


def next_version() -> str:
    """Today's date, plus however many releases today has already had.

    UTC because that is the clock the runner keeps; a release cut at 8pm
    Central belongs to the next day's number and nothing breaks if it does.
    """
    today = datetime.now(timezone.utc).date()
    year, mmdd = today.year, int(f"{today.month:02d}{today.day:02d}")

    seen = [v for v in [parse(current()), *tagged()] if v]
    same_day = [v[2] for v in seen if (v[0], v[1]) == (year, mmdd)]
    candidate = (year, mmdd, max(same_day) + 1 if same_day else 0)

    # A version must never go backwards, and the date can: a clock skew, a
    # tag cut from a machine a day ahead, a release restored from a revert.
    # Ordering beats being literally today's date.
    if seen and candidate <= max(seen):
        high = max(seen)
        candidate = (high[0], high[1], high[2] + 1)

    return "%d.%d.%d" % candidate


def stamp(path: Path, version: str) -> bool:
    """Rewrite this manifest's version, touching nothing else.

    A json.load/json.dump round-trip would reflow the whole file to this
    script's formatting -- package.json's one-line arrays would come back
    multi-line, and every diff would be noise. So the field is replaced as
    text, and the result is parsed to prove both that it is still JSON and
    that the line replaced was the top-level one.
    """
    text = path.read_text(encoding="utf-8")
    new = FIELD_RE.sub(f'"version": "{version}"', text, count=1)

    if json.loads(new).get("version") != version:
        # Either there was no version field, or the first match was a nested
        # one. Reflow, which cannot miss, and keep the field where the other
        # manifests carry it.
        data = json.loads(text)
        data.pop("version", None)
        rebuilt: dict = {}
        for key, value in data.items():
            rebuilt[key] = value
            if key == "description" or (key == "name" and "description" not in data):
                rebuilt["version"] = version
        rebuilt.setdefault("version", version)
        new = json.dumps(rebuilt, indent=2, ensure_ascii=False) + "\n"

    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def stamp_all(version: str) -> int:
    if not parse(version):
        print(f"FATAL: {version!r} is not MAJOR.MINOR.PATCH", file=sys.stderr)
        return 70
    changed = [p for p in manifests() if stamp(p, version)]
    for path in changed:
        print(f"  {path.relative_to(ROOT)}", file=sys.stderr)
    print(f"stamped {version} into {len(changed)} manifest(s)", file=sys.stderr)
    return 0


def check() -> int:
    want = current()
    problems = []
    if not parse(want):
        problems.append(f"package.json: version {want!r} is not MAJOR.MINOR.PATCH")
    for path in manifests():
        got = read_version(path)
        if got != want:
            problems.append(f"{path.relative_to(ROOT)}: {got!r}, expected {want!r}")
    if problems:
        print("Version drift:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print("\nRun: python3 scripts/version.py --set " + str(want), file=sys.stderr)
        return 1
    print(f"{len(manifests())} manifests agree on {want}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--next", action="store_true",
                   help="print the version the next release would use")
    g.add_argument("--release", action="store_true",
                   help="stamp the next version everywhere; print it on stdout")
    g.add_argument("--set", metavar="X.Y.Z", help="stamp a specific version everywhere")
    g.add_argument("--check", action="store_true", help="report drift; exit 1 if any")
    args = ap.parse_args()

    if args.next:
        print(next_version())
        return 0
    if args.release:
        version = next_version()
        rc = stamp_all(version)
        # stdout is the version and nothing else -- the release job reads it.
        if rc == 0:
            print(version)
        return rc
    if args.set:
        return stamp_all(args.set)
    if args.check:
        return check()

    print(current())
    return 0


if __name__ == "__main__":
    sys.exit(main())
